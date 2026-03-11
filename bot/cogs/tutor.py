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
from bot.core.quiz_generator import create_pdf_guide, generate_quiz_json
from bot.db.database import get_session
from bot.db.models import Student
from bot.core.memory import add_message, get_conversation_context
from bot.core.llm import generate_response
from bot.core.rag import rag_service
from bot.core.student_tracker import get_weakest_lo
from bot.prompts.tutor_system import get_tutor_system_prompt

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

    async def _handle_dm_quiz_shortcuts(self, message: discord.Message, student: Student, content: str) -> bool:
        """Handle DM text shortcuts for quiz guide generation."""
        topic = ""
        normalized = content.strip()

        if normalized.startswith("/guia_pdf"):
            topic = normalized[len("/guia_pdf"):].strip()
        elif normalized.startswith("/quiz "):
            parts = normalized.split(maxsplit=2)
            if len(parts) >= 2 and parts[1] in {"guia_pdf", "guia"}:
                topic = parts[2].strip() if len(parts) == 3 else ""
            else:
                return False
        else:
            return False

        if not topic:
            await message.channel.send("ℹ️ Uso: `/quiz guia_pdf <tema>` o `/guia_pdf <tema>`")
            return True

        await message.channel.send(
            f"⏳ Generando tu guía de 5 preguntas sobre '{topic}'. Esto tomará unos 20 segundos..."
        )

        quiz_data = await generate_quiz_json(student.subject, topic, num_questions=5)
        if not quiz_data or not quiz_data.questions:
            await message.channel.send("⚠️ Error al generar el contenido de la guía.")
            return True

        pdf_buffer = create_pdf_guide(quiz_data)
        filename = f"Guia_BEIET_{topic.replace(' ', '_')}.pdf"
        file = discord.File(fp=pdf_buffer, filename=filename)
        await message.channel.send(
            content=f"✅ Aquí tienes tu guía de estudio de {student.subject}, {student.name}.",
            file=file,
        )
        return True


    async def process_tutoring_message(self, message: discord.Message, is_dm: bool):
        """Core logic for generating a response."""
        
        # 1. Show typing indicator immediately
        async with message.channel.typing():
            # Clean content (remove mention tags if any)
            content = message.content.replace(f"<@{self.bot.user.id}>", "").strip()

            discord_id = str(message.author.id)
            student = await self.get_student(discord_id)

            # 2. Resolve subject & student info
            # Detect subject based on guild name first
            subject = None
            if message.guild:
                gn = message.guild.name.lower()
                if "optimizacion" in gn:
                    subject = "optimizacion"
                elif "mercados" in gn:
                    subject = "mercados"

            if student:
                student_name = student.name
                if not subject:
                    subject = student.subject
            else:
                student_name = message.author.display_name
                if not subject:
                    subject = config.DEFAULT_SUBJECT

            if student and is_dm and content.startswith("/"):
                if await self._handle_dm_quiz_shortcuts(message, student, content):
                    return
                await message.channel.send("ℹ️ Usa los slash commands en el servidor. En DM puedes escribirme sin `/`.")
                return

            # 3. Check for attachments (images/voice)
            has_attachment = len(message.attachments) > 0
            attachment_type = None
            media_data = None
            mime_type = None

            if has_attachment:
                att = message.attachments[0]
                if att.content_type and att.content_type.startswith("image/"):
                    attachment_type = "image"
                    media_data = await att.read()
                    mime_type = att.content_type
                elif att.content_type and att.content_type.startswith("audio/"):
                    attachment_type = "voice"
                    media_data = await att.read()
                    mime_type = att.content_type
                else:
                    attachment_type = "file"

            # 4. Process with LLM
            async for session in get_session():
                try:
                    context = []
                    rag_context = ""
                    weakest_lo_name = ""

                    if student:
                        # Registered: full memory + progress tracking
                        await add_message(
                            session=session,
                            student_id=student.id,
                            subject=subject,
                            role="user",
                            content=content,
                            has_attachment=has_attachment,
                            attachment_type=attachment_type
                        )
                        context = await get_conversation_context(
                            session=session,
                            student_id=student.id,
                            subject=subject
                        )
                        weakest_lo_code, weakest_lo_desc = await get_weakest_lo(session, student.id, subject)
                        if weakest_lo_code:
                            weakest_lo_name = f"{weakest_lo_code}: {weakest_lo_desc}"

                    # Assemble System Prompt
                    system_prompt = get_tutor_system_prompt(
                        subject_name=config.SUBJECTS[subject].name,
                        student_name=student_name,
                        weakest_lo=weakest_lo_name
                    )

                    # 3.5 Dual-Expert Logic: Check if we should query both collections
                    # If we are in DMs or if subject detection was ambiguous, or if specific user needs it
                    all_subjects_to_query = [subject]
                    
                    # Detect if user is in both key servers (if bot has access to member lists)
                    # For now, if it's a DM or the user is the owner/admin, or if it's the specific user "gerardoblanco"
                    # We can also just search both if the query seems to warrant it, 
                    # but let's stick to: if DM or in a "general" context, query both.
                    if not message.guild or subject not in ["optimizacion", "mercados"]:
                         all_subjects_to_query = list(config.SUBJECTS.keys())
                    
                    # RAG Retrieval (handle multiple subjects if needed)
                    rag_context_parts = []
                    for s in all_subjects_to_query:
                        s_context = rag_service.retrieve_context(
                            subject=s,
                            query=content[:500],
                            n_results=2 if len(all_subjects_to_query) > 1 else 3
                        )
                        if "Ocurrió un error" not in s_context and "No se encontraron" not in s_context:
                            rag_context_parts.append(f"--- CONTEXTO: {config.SUBJECTS[s].name} ---\n{s_context}")
                    
                    rag_context = "\n\n".join(rag_context_parts) if rag_context_parts else "No se encontró contexto específico en las bases de datos."

                    # Generate response
                    bot_response_data = await generate_response(
                        system_prompt=system_prompt,
                        context=context,
                        user_message=content,
                        rag_context=rag_context,
                        use_grounding=True,
                        media_data=media_data,
                        mime_type=mime_type
                    )

                    reply_text = bot_response_data.get("text", "")
                    in_toks = bot_response_data.get("input_tokens", 0)
                    out_toks = bot_response_data.get("output_tokens", 0)
                    cost = bot_response_data.get("cost", 0.0)

                    # Save bot response (only for registered students)
                    if student:
                        await add_message(
                            session=session,
                            student_id=student.id,
                            subject=subject,
                            role="assistant",
                            content=reply_text,
                            input_tokens=in_toks,
                            output_tokens=out_toks,
                            cost=cost
                        )

                    # 5. Send reply (with chunking for Discord limits)
                    if len(reply_text) <= 2000:
                        await message.reply(reply_text)
                    else:
                        chunks = [reply_text[i:i+1900] for i in range(0, len(reply_text), 1900)]
                        for i, chunk in enumerate(chunks):
                            if i == 0:
                                await message.reply(chunk)
                            else:
                                await message.channel.send(chunk)

                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    await message.reply("⚠️ Hubo un error procesando tu mensaje. Intenta de nuevo más tarde.")


def setup(bot):
    bot.add_cog(Tutor(bot))
