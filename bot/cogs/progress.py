"""
BEIET — Student Progress Cog.

Handles `/progreso` and `/ranking` commands.
"""

import discord
from discord.ext import commands
from sqlalchemy import select

from bot.config import config
from bot.db.database import get_session
from bot.db.models import Student, LOProgress
from bot.core.student_tracker import get_student_progress

class Progress(commands.Cog):
    """Student progress tracking."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(name="progreso", description="Ver tu progreso en los Resultados de Aprendizaje (RA)")
    async def view_progress(self, ctx: discord.ApplicationContext):
        """View LO progress for the current student."""
        await ctx.defer(ephemeral=True)
        
        discord_id = str(ctx.author.id)
        
        async for session in get_session():
            # Get student
            stmt = select(Student).where(Student.discord_id == discord_id)
            result = await session.execute(stmt)
            student = result.scalar_one_or_none()
            
            if not student:
                await ctx.respond("❌ No estás registrado. Usa `/registro` primero.", ephemeral=True)
                return
                
            subject_name = config.SUBJECTS[student.subject].name
            learning_outcomes = config.SUBJECTS[student.subject].learning_outcomes
            
            # Fetch progress records
            progress_data = await get_student_progress(session, student.id, student.subject)
            
            embed = discord.Embed(
                title=f"📊 Progreso Académico",
                description=f"**{student.name}** | {subject_name}",
                color=discord.Color.gold()
            )
            
            if not learning_outcomes:
                embed.add_field(name="Información", value="Los RA no están configurados para esta asignatura.")
            else:
                for lo_code, description in learning_outcomes.items():
                    prog = progress_data.get(lo_code)
                    if prog:
                        # Convert 0-1 score to percentage
                        score_pct = int(prog.score * 100)
                        # Build a simple progress bar
                        blocks = int(prog.score * 10)
                        bar = "🟩" * blocks + "⬜" * (10 - blocks)
                        value = f"{bar} **{score_pct}%**\n_(Intentos: {prog.attempts})_"
                    else:
                        value = "⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ **0%**\n_(Sin evaluar aún)_"
                        
                    embed.add_field(name=f"{lo_code}: {description}", value=value, inline=False)
            
            await ctx.respond(embed=embed, ephemeral=True)

def setup(bot):
    bot.add_cog(Progress(bot))
