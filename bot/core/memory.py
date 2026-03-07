"""
BEIET — Core Memory System.

Handles persistent student conversations, session management,
and automatic summarization of older context.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import config
from bot.db.models import Student, ConversationMessage, ConversationSummary
from bot.core.llm import generate_summary

logger = logging.getLogger("beiet.memory")

# ─────────────────────────────────────────────
# Session Management
# ─────────────────────────────────────────────

async def get_or_create_session(
    session: AsyncSession, student_id: int, subject: str
) -> str:
    """Get active session ID or create a new one if timeout exceeded."""
    
    # Find latest message for this student and subject
    stmt = (
        select(ConversationMessage)
        .where(
            ConversationMessage.student_id == student_id,
            ConversationMessage.subject == subject
        )
        .order_by(desc(ConversationMessage.timestamp))
        .limit(1)
    )
    result = await session.execute(stmt)
    last_msg = result.scalar_one_or_none()
    
    now = datetime.now(timezone.utc)
    
    if not last_msg:
        # First message ever
        return str(uuid.uuid4())
        
    # Check timeout
    # Convert scalar datetime back to aware datetime if needed by DB driver
    last_time = last_msg.timestamp
    if last_time.tzinfo is None:
        last_time = last_time.replace(tzinfo=timezone.utc)
        
    timeout_delta = timedelta(minutes=config.session_timeout_minutes)
    
    if now - last_time > timeout_delta:
        # Timeout exceeded, create new session and trigger summarization (async task idea)
        logger.info(f"New session created for student {student_id} (Timeout exceeded)")
        return str(uuid.uuid4())
        
    return last_msg.session_id


# ─────────────────────────────────────────────
# Message History
# ─────────────────────────────────────────────

async def add_message(
    session: AsyncSession,
    student_id: int,
    subject: str,
    role: str,
    content: str,
    has_attachment: bool = False,
    attachment_type: str = None
) -> str:
    """Add a message to the persistent history."""
    
    session_id = await get_or_create_session(session, student_id, subject)
    
    msg = ConversationMessage(
        student_id=student_id,
        session_id=session_id,
        role=role,
        content=content,
        subject=subject,
        has_attachment=has_attachment,
        attachment_type=attachment_type
    )
    
    session.add(msg)
    await session.commit()
    
    # Check if we need to summarize (fire and forget in production, awaiting here for simplicity)
    await check_summarization(session, student_id, subject)
    
    return session_id


async def get_conversation_context(
    session: AsyncSession, student_id: int, subject: str, limit: int = None
) -> list[dict]:
    """
    Retrieve the context window for the LLM.
    Returns: [{"role": "user", "content": "..."}, ...]
    Prepends the active summary if one exists.
    """
    if limit is None:
        limit = config.max_conversation_messages
        
    # 1. Get current summary
    stmt_sum = (
        select(ConversationSummary)
        .where(
            ConversationSummary.student_id == student_id,
            ConversationSummary.subject == subject
        )
        .order_by(desc(ConversationSummary.updated_at))
        .limit(1)
    )
    result_sum = await session.execute(stmt_sum)
    summary = result_sum.scalar_one_or_none()
    
    context = []
    
    if summary:
        context.append({
            "role": "system",
            "content": f"[Previous Conversation Summary]\n{summary.summary_text}"
        })
        
    # 2. Get recent messages
    stmt_msg = (
        select(ConversationMessage)
        .where(
            ConversationMessage.student_id == student_id,
            ConversationMessage.subject == subject
        )
        .order_by(desc(ConversationMessage.timestamp))
        .limit(limit)
    )
    result_msg = await session.execute(stmt_msg)
    # They come out newest first, need oldest first for LLM
    recent_messages = list(result_msg.scalars())
    recent_messages.reverse()
    
    for msg in recent_messages:
        context.append({
            "role": msg.role,
            "content": msg.content
        })
        
    return context


# ─────────────────────────────────────────────
# Summarization
# ─────────────────────────────────────────────

async def check_summarization(session: AsyncSession, student_id: int, subject: str):
    """Check if message count exceeds threshold, create summary if needed."""
    
    # Optimization: count messages not yet summarized
    # In a full implementation, we'd mark messages as 'summarized=True'
    # For now, simplistic approach: count total messages
    
    stmt = select(ConversationMessage).where(
        ConversationMessage.student_id == student_id,
        ConversationMessage.subject == subject
    )
    # A real implementation would use func.count()
    result = await session.execute(stmt)
    messages = list(result.scalars())
    
    if len(messages) > config.summary_threshold:
        logger.info(f"Triggering summarization for student {student_id}")
        
        # Get older messages to summarize (keep last 5 intact)
        to_summarize = messages[:-5]
        
        # Get existing summary text if any
        existing_summary_text = ""
        stmt_sum = select(ConversationSummary).where(
            ConversationSummary.student_id == student_id,
            ConversationSummary.subject == subject
        ).order_by(desc(ConversationSummary.updated_at)).limit(1)
        res_sum = await session.execute(stmt_sum)
        old_sum = res_sum.scalar_one_or_none()
        if old_sum:
            existing_summary_text = old_sum.summary_text
            
        # Format text for LLM
        convo_text = "\n".join([f"{m.role}: {m.content}" for m in to_summarize])
        
        try:
            # Generate new summary
            new_summary_text = await generate_summary(existing_summary_text, convo_text)
            
            # Update or create summary record
            if old_sum:
                old_sum.summary_text = new_summary_text
                old_sum.message_count += len(to_summarize)
                old_sum.updated_at = datetime.now(timezone.utc)
            else:
                new_sum = ConversationSummary(
                    student_id=student_id,
                    subject=subject,
                    summary_text=new_summary_text,
                    message_count=len(to_summarize)
                )
                session.add(new_sum)
                
            # Delete summarized messages to save space/context
            for msg in to_summarize:
                await session.delete(msg)
                
            await session.commit()
            logger.info(f"Summarization complete for student {student_id}")
            
        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")
            await session.rollback()
