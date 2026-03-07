import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from io import BytesIO

from bot.db.database import get_session
from bot.db.models import Student
from bot.core.quiz_generator import generate_quiz_json, create_pdf_guide
from sqlalchemy import select

logger = logging.getLogger("beiet.cogs.quiz")


class QuizView(discord.ui.View):
    """View handling the interactive buttons for a single question."""
    def __init__(self, question, student_id: int):
        super().__init__(timeout=300)  # 5 minutes to answer
        self.question = question
        self.student_id = student_id
        
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
        
        if str(interaction.user.id) != str(view.student_id):
            await interaction.response.send_message("❌ Esta pregunta no es para ti. Genera tu propio simulacro.", ephemeral=True)
            return
            
        is_correct = (self.letter == view.question.correct_letter)
        
        # Disable all buttons
        for child in view.children:
            child.disabled = True
            
        color = discord.Color.green() if is_correct else discord.Color.red()
        title = "✅ ¡Correcto!" if is_correct else "❌ Incorrecto"
        
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="La respuesta era:", value=f"**{view.question.correct_letter}**", inline=False)
        embed.add_field(name="Feedback del Tutor:", value=view.question.feedback, inline=False)
        
        # We could update LO progress in DB here if we had the precise LO Code attached.
        # For now, we provide the pedagogical feedback.
        
        await interaction.response.edit_message(view=view, embed=embed)


class QuizTracker(commands.Cog):
    """Cog for generating quizzes and PDF study guides."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    quiz = SlashCommandGroup("quiz", "Comandos para evaluaciones y guías de estudio")

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
        view = QuizView(q, ctx.author.id)
        
        await ctx.followup.send(embed=embed, view=view)


    @quiz.command(name="guia_pdf", description="Genera una guía de ejercicios en PDF y te la envía al chat.")
    async def guia_pdf(self, ctx: discord.ApplicationContext, tema: str):
        """Generates a 5-question PDF study guide."""
        await ctx.defer()
        
        async for session in get_session():
            stmt = select(Student).where(Student.discord_id == str(ctx.author.id))
            result = await session.execute(stmt)
            student = result.scalar_one_or_none()
            
            if not student:
                await ctx.followup.send("❌ Debes usar `/registro` antes de solicitar guías.")
                return
                
        await ctx.followup.send(f"⏳ El Profesor BEIET está redactando tu guía de 5 preguntas sobre '{tema}'. Esto tomará unos 20 segundos...")

        quiz_data = await generate_quiz_json(student.subject, tema, num_questions=5)
        if not quiz_data or not quiz_data.questions:
            await ctx.followup.send("⚠️ Error al generar el contenido de la guía.")
            return
            
        # Create PDF
        pdf_buffer = create_pdf_guide(quiz_data)
        
        filename = f"Guia_BEIET_{tema.replace(' ', '_')}.pdf"
        file = discord.File(fp=pdf_buffer, filename=filename)
        
        await ctx.channel.send(content=f"✅ ¡Aquí tienes tu guía de estudio de {student.subject}! ¡Mucho éxito, {student.name}!", file=file)


def setup(bot):
    bot.add_cog(QuizTracker(bot))
