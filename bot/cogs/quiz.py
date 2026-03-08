import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from bot.db.database import get_session
from bot.db.models import Student, QuizResult
from bot.core.quiz_generator import generate_quiz_json, create_pdf_guide
from bot.core.student_tracker import update_lo_progress
from bot.config import config
from sqlalchemy import select

logger = logging.getLogger("beiet.cogs.quiz")


class QuizView(discord.ui.View):
    """View handling the interactive buttons for a single question."""
    def __init__(self, question, student_id: int, subject: str):
        super().__init__(timeout=300)  # 5 minutes to answer
        self.question = question
        self.student_id = student_id
        self.subject = subject

        # Add a button for each option
        self.add_item(QuizButton("A", question.option_a, discord.ButtonStyle.primary))
        self.add_item(QuizButton("B", question.option_b, discord.ButtonStyle.secondary))
        self.add_item(QuizButton("C", question.option_c, discord.ButtonStyle.success))
        self.add_item(QuizButton("D", question.option_d, discord.ButtonStyle.danger))


class QuizButton(discord.ui.Button):
    def __init__(self, letter: str, label: str, style: discord.ButtonStyle):
        # Truncate label if it's too long for a Discord button (max 80 chars)
        display_label = label if len(label) <= 75 else label[:72] + "..."
        super().__init__(label=f"{letter}) {display_label}", style=style, custom_id=f"quiz_btn_{letter}")
        self.letter = letter

    async def callback(self, interaction: discord.Interaction):
        view: QuizView = self.view
        
        if interaction.user.id != view.student_id:
            await interaction.response.send_message("❌ Esta pregunta no es para ti. Genera tu propio simulacro.", ephemeral=True)
            return

        raw_correct_letter = view.question.correct_letter
        correct_letter = raw_correct_letter.strip().upper() if raw_correct_letter else ""
        valid_options = {"A", "B", "C", "D"}
        has_valid_correct_letter = correct_letter in valid_options
        is_correct = has_valid_correct_letter and (self.letter == correct_letter)

        if not has_valid_correct_letter:
            logger.warning(
                "LLM returned invalid correct_letter '%s' for quiz question, skipping persistence.",
                raw_correct_letter,
            )
        
        # Disable all buttons
        for child in view.children:
            child.disabled = True

        if not has_valid_correct_letter:
            color = discord.Color.orange()
            title = "⚠️ No se pudo verificar la respuesta"
        else:
            color = discord.Color.green() if is_correct else discord.Color.red()
            title = "✅ ¡Correcto!" if is_correct else "❌ Incorrecto"
        
        embed = discord.Embed(title=title, color=color)
        display_correct_letter = correct_letter if has_valid_correct_letter else "No disponible"
        embed.add_field(name="La respuesta era:", value=f"**{display_correct_letter}**", inline=False)
        embed.add_field(name="Feedback del Tutor:", value=view.question.feedback, inline=False)
        if not has_valid_correct_letter:
            embed.add_field(
                name="Estado del intento",
                value="No se registró progreso porque la clave generada fue inválida.",
                inline=False,
            )

        # Respond to Discord immediately (must be within 3 seconds)
        await interaction.response.edit_message(view=view, embed=embed)

        if not has_valid_correct_letter:
            return

        # Validate lo_code against known LOs to avoid persisting LLM hallucinations
        score = 1.0 if is_correct else 0.0
        raw_lo_code = view.question.lo_code
        subject_config = config.SUBJECTS.get(view.subject)
        valid_lo_codes = subject_config.learning_outcomes.keys() if subject_config else set()
        lo_code = raw_lo_code.strip().upper() if raw_lo_code else None
        if lo_code and lo_code not in valid_lo_codes:
            logger.warning(f"LLM returned unknown lo_code '{lo_code}' for subject '{view.subject}', skipping LOProgress update.")
            lo_code = None

        # Persist quiz result and RA progress after responding to Discord
        async for session in get_session():
            try:
                stmt = select(Student).where(Student.discord_id == str(view.student_id))
                result = await session.execute(stmt)
                student = result.scalar_one_or_none()

                if student:
                    if lo_code:
                        await update_lo_progress(session, student.id, student.subject, lo_code, score)

                    quiz_result = QuizResult(
                        student_id=student.id,
                        subject=student.subject,
                        lo_codes=lo_code,
                        score=score,
                        total_questions=1,
                        correct_answers=1 if is_correct else 0,
                        feedback=view.question.feedback,
                    )
                    session.add(quiz_result)
                    await session.commit()

                    if lo_code:
                        embed.set_footer(text=f"Progreso actualizado · {lo_code} {'✅' if is_correct else '❌'}")
                        await interaction.edit_original_response(embed=embed)
            except Exception as e:
                logger.warning(f"Could not persist quiz result for student {view.student_id}: {e}")


class QuizTracker(commands.Cog):
    """Cog for generating quizzes and PDF study guides."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    quiz = SlashCommandGroup(
        "quiz",
        "Comandos para evaluaciones y guías de estudio",
        contexts={discord.InteractionContextType.guild},
    )

    async def _send_pdf_guide(self, ctx: discord.ApplicationContext, tema: str) -> None:
        """Shared handler for PDF guide generation commands."""
        await ctx.defer()

        student = None
        async for session in get_session():
            stmt = select(Student).where(Student.discord_id == str(ctx.author.id))
            result = await session.execute(stmt)
            student = result.scalar_one_or_none()

            if not student:
                await ctx.followup.send("❌ Debes usar `/registro` antes de solicitar guías.")
                return

        await ctx.followup.send(
            f"⏳ El Profesor BEIET está redactando tu guía de 5 preguntas sobre '{tema}'. Esto tomará unos 20 segundos..."
        )

        quiz_data = await generate_quiz_json(student.subject, tema, num_questions=5)
        if not quiz_data or not quiz_data.questions:
            await ctx.followup.send("⚠️ Error al generar el contenido de la guía.")
            return

        pdf_buffer = create_pdf_guide(quiz_data)
        filename = f"Guia_BEIET_{tema.replace(' ', '_')}.pdf"
        file = discord.File(fp=pdf_buffer, filename=filename)

        await ctx.channel.send(
            content=f"✅ ¡Aquí tienes tu guía de estudio de {student.subject}! ¡Mucho éxito, {student.name}!",
            file=file,
        )

    @quiz.command(name="simulacro", description="Genera una pregunta rápida e interactiva (Choice) para practicar.")
    async def simulacro(self, ctx: discord.ApplicationContext, tema: str):
        """Generates a 1-question interactive quiz."""
        await ctx.defer()
        
        # 1. Get student to know their subject
        async for session in get_session():
            stmt = select(Student).where(Student.discord_id == str(ctx.author.id))
            result = await session.execute(stmt)
            student = result.scalar_one_or_none()
            
            if not student:
                await ctx.followup.send("❌ Debes usar `/registro` antes de tomar un simulacro.")
                return

        # 2. Fetch Quiz JSON
        quiz_data = await generate_quiz_json(student.subject, tema, num_questions=1)
        if not quiz_data or not quiz_data.questions:
            await ctx.followup.send("⚠️ Hubo un problema contactando al profesor para generar la pregunta. Revisa el tema o inténtalo más tarde.")
            return
            
        q = quiz_data.questions[0]
        
        # 3. Create Embed for question
        embed = discord.Embed(
            title="🔍 Simulacro Rápido BEIET", 
            description=f"**Tema:** {tema}\n\n{q.statement}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Haz clic en la alternativa correcta abajo.")
        
        # 4. Render View with buttons
        view = QuizView(q, ctx.author.id, student.subject)

        await ctx.followup.send(embed=embed, view=view)


    @quiz.command(name="guia_pdf", description="Genera una guía de ejercicios en PDF y te la envía al chat.")
    async def guia_pdf(self, ctx: discord.ApplicationContext, tema: str):
        """Generates a 5-question PDF study guide."""
        await self._send_pdf_guide(ctx, tema)

    @quiz.command(name="guia", description="Alias de guia_pdf para facilitar la búsqueda en Discord.")
    async def guia(self, ctx: discord.ApplicationContext, tema: str):
        """Alias for guia_pdf."""
        await self._send_pdf_guide(ctx, tema)

    @discord.slash_command(
        name="guia_pdf",
        description="Genera una guía de ejercicios en PDF y te la envía al chat.",
        contexts={discord.InteractionContextType.guild},
    )
    async def guia_pdf_direct(
        self,
        ctx: discord.ApplicationContext,
        tema: discord.Option(str, "Tema para la guía (ej: Método Simplex)"),
    ):
        """Top-level alias for users that cannot see /quiz guia_pdf in autocomplete."""
        await self._send_pdf_guide(ctx, tema)

    @discord.slash_command(
        name="guia",
        description="Genera una guía de ejercicios en PDF y te la envía al chat.",
        contexts={discord.InteractionContextType.guild},
    )
    async def guia_direct(
        self,
        ctx: discord.ApplicationContext,
        tema: discord.Option(str, "Tema para la guía (ej: Método Simplex)"),
    ):
        """Top-level /guia alias."""
        await self._send_pdf_guide(ctx, tema)


def setup(bot):
    bot.add_cog(QuizTracker(bot))
