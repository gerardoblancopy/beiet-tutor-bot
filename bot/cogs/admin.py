import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from sqlalchemy import select, func

from bot.db.database import get_session
from bot.db.models import Student, ConversationMessage

logger = logging.getLogger("beiet.cogs.admin")

class AdminCog(commands.Cog, name="Admin"):
    """Cog for professor administration and analytics."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    admin = SlashCommandGroup("admin", "Comandos de administración exclusivos para el profesor")

    @admin.command(name="resumen", description="Muestra un resumen de los estudiantes registrados y la actividad del bot.")
    async def resumen(self, ctx: discord.ApplicationContext):
        """Generates an admin dashboard summary."""
        # Simple security check: Ensure the user calling this is an admin/server owner.
        is_admin = False
        if ctx.guild and hasattr(ctx.author, "guild_permissions"):
            is_admin = ctx.author.guild_permissions.administrator
        
        # Also allow bot owner regardless of server perms
        if not is_admin:
            is_admin = await self.bot.is_owner(ctx.author)

        if not is_admin:
            await ctx.respond("❌ Solo los administradores o el profesor pueden usar este comando.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        
        try:
            async for session in get_session():
                # Count total students
                result_students = await session.execute(select(func.count()).select_from(Student))
                total_students = result_students.scalar() or 0
                
                # Count total interactions
                result_msgs = await session.execute(select(func.count()).select_from(ConversationMessage))
                total_msgs = result_msgs.scalar() or 0
                
                # Distribution by Subject
                stmt_dist = select(Student.subject, func.count(Student.id)).group_by(Student.subject)
                dist_result = await session.execute(stmt_dist)
                distribution = dist_result.all()
                
            embed = discord.Embed(
                title="⚙️ Panel de Control: BEIET Tutor",
                description="Resumen de actividad y adopción del bot asistente.",
                color=discord.Color.dark_purple()
            )
            
            embed.add_field(name="Estudiantes Registrados", value=f"**{total_students}**", inline=True)
            embed.add_field(name="Total de Mensajes/Consultas", value=f"**{total_msgs}**", inline=True)
            
            # Map distribution
            dist_text = ""
            for subj, count in distribution:
                dist_text += f"• {subj.title()}: {count} alumnos\n"
                
            if dist_text:
                embed.add_field(name="Por Asignatura", value=dist_text, inline=False)
            else:
                embed.add_field(name="Por Asignatura", value="No hay datos aún.", inline=False)
                
            embed.set_footer(text="BEIET System - Faculty Dashboard")
            
            await ctx.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in admin summary: {e}")
            await ctx.followup.send("❌ Error al acceder a la base de datos de administración.")


def setup(bot):
    bot.add_cog(AdminCog(bot))
