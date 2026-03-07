"""
BEIET — Core Tutoring Cog.

Handles main conversation flow, RAG integration, and adapting to
student progress. Responds to both DMs and channel mentions.
"""

import logging
import discord
from discord.ext import commands
from sqlalchemy import select

from bot.config import config
from bot.db.database import get_session
from bot.db.models import Student
from bot.core.memory import add_message, get_conversation_context
from bot.core.llm import generate_response

logger = logging.getLogger("beiet.tutor")


class Tutor(commands.Cog):
    """Main tutoring interaction handler."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_student(self, discord_id: str) -> Student | None:
        """Helper to get student by Discord ID."""
        async for session in get_session():
            stmt = select(Student).where(Student.discord_id == discord_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()


    async def handle_dm(self, message: discord.Message):
        """Process direct messages."""
        logger.info(f"Received DM from {message.author}: {message.content[:20]}...")
        await self.process_tutoring_message(message, is_dm=True)


    async def handle_mention(self, message: discord.Message):
        """Process channel mentions."""
        logger.info(f"Received mention in {message.guild.name} from {message.author}")
        await self.process_tutoring_message(message, is_dm=False)


    async def process_tutoring_message(self, message: discord.Message, is_dm: bool):
        """Core logic for generating a response."""
        
        # 1. Show typing indicator immediately
        async with message.channel.typing():
            
            discord_id = str(message.author.id)
            student = await self.get_student(discord_id)
            
            # 2. Require registration
            if not student:
                warn_msg = "❌ Hola. Primero debes registrarte usando el comando `/registro` en el servidor."
                if is_dm:
                    await message.channel.send(warn_msg)
                else:
                    await message.reply(warn_msg)
                return

            # Clean content (remove mention tags if any)
            content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()
            
            # 3. Check for attachments (images/voice)
            has_attachment = len(message.attachments) > 0
            attachment_type = None
            if has_attachment:
                att = message.attachments[0]
                if att.content_type and att.content_type.startswith("image/"):
                    attachment_type = "image"
                elif att.content_type and att.content_type.startswith("audio/"):
                    attachment_type = "voice"
                else:
                    attachment_type = "file"
                    
            # 4. Process with LLM via persistent memory context
            async for session in get_session():
                try:
                    # Save user message
                    await add_message(
                        session=session,
                        student_id=student.id,
                        subject=student.subject,
                        role="user",
                        content=content,
                        has_attachment=has_attachment,
                        attachment_type=attachment_type
                    )
                    
                    # Fetch context window
                    context = await get_conversation_context(
                        session=session,
                        student_id=student.id,
                        subject=student.subject
                    )
                    
                    # TODO: Phase 3/4 - Inject RAG context and LO status here
                    system_prompt = f"Eres el tutor BEIET para {config.SUBJECTS[student.subject].name}. El estudiante es {student.name}."
                    
                    # Generate response
                    bot_response = await generate_response(
                        system_prompt=system_prompt,
                        context=context,
                        user_message=content
                    )
                    
                    # Save bot response
                    await add_message(
                        session=session,
                        student_id=student.id,
                        subject=student.subject,
                        role="assistant",
                        content=bot_response
                    )
                    
                    # 5. Send reply
                    await message.reply(bot_response)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await message.reply("⚠️ Hubo un error procesando tu mensaje. Intenta de nuevo más tarde.")


def setup(bot):
    bot.add_cog(Tutor(bot))
