"""
BEIET Bot — Student Tracker.

Manages updating and retrieving Learning Outcome (LO/RA) progress.
"""

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import LOProgress
from bot.config import config

async def update_lo_progress(
    session: AsyncSession,
    student_id: int,
    subject: str,
    lo_code: str,
    score: float,
    notes: str = ""
) -> LOProgress:
    """Update or create progress for a specific learning outcome."""
    stmt = select(LOProgress).where(
        LOProgress.student_id == student_id,
        LOProgress.subject == subject,
        LOProgress.lo_code == lo_code
    )
    result = await session.execute(stmt)
    progress = result.scalar_one_or_none()
    
    if progress:
        # Simple moving average for score update (can be more sophisticated later)
        progress.score = (progress.score * progress.attempts + score) / (progress.attempts + 1)
        progress.attempts += 1
        progress.last_assessed = datetime.now(timezone.utc)
        if notes:
            progress.notes = notes
    else:
        # Create new progress entry
        progress = LOProgress(
            student_id=student_id,
            subject=subject,
            lo_code=lo_code,
            score=score,
            attempts=1,
            last_assessed=datetime.now(timezone.utc),
            notes=notes
        )
        session.add(progress)
    
    await session.commit()
    return progress

async def get_student_progress(session: AsyncSession, student_id: int, subject: str) -> dict[str, LOProgress]:
    """Retrieve all learning outcome progress for a student in a subject."""
    stmt = select(LOProgress).where(
        LOProgress.student_id == student_id,
        LOProgress.subject == subject
    )
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    return {p.lo_code: p for p in records}

async def get_weakest_lo(session: AsyncSession, student_id: int, subject: str) -> tuple[str, str]:
    """Identify the weakest Learning Outcome for targeted intervention."""
    stmt = select(LOProgress).where(
        LOProgress.student_id == student_id,
        LOProgress.subject == subject
    ).order_by(LOProgress.score.asc()).limit(1)
    
    result = await session.execute(stmt)
    weakest = result.scalar_one_or_none()
    
    if weakest:
        subject_config = config.SUBJECTS.get(subject)
        desc = subject_config.learning_outcomes.get(weakest.lo_code, "Unknown LO")
        return weakest.lo_code, desc
    
    return None, "No sufficient data to determine weakest outcome."
