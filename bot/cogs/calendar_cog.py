import datetime
import logging
import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from dateutil import tz

from bot.core.calendar_service import calendar_service

logger = logging.getLogger("beiet.cogs.calendar")

class CalendarCog(commands.Cog, name="Calendar"):
    """Cog for scheduling and calendar operations."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timezone = tz.gettz('America/Santiago')

    agenda = SlashCommandGroup("agenda", "Comandos para listar disponibilidad y agendar citas")

    @agenda.command(name="disponibilidad", description="Consulta los horarios en los que el profesor está ocupado o libre.")
    async def disponibilidad(self, ctx: discord.ApplicationContext):
        """Fetches the availability of the professor via Google Calendar."""
        await ctx.defer()
        
        availability_text = calendar_service.get_availability(days=7)
        
        embed = discord.Embed(
            title="📅 Disponibilidad del Profesor BEIET",
            description=availability_text,
            color=discord.Color.blue()
        )
        embed.set_footer(text="Usa /agenda cita para solicitar una reserva en un horario libre.")
        
        await ctx.followup.send(embed=embed)


    @agenda.command(name="cita", description="Agenda una cita de tutoría (Meet) con el profesor.")
    async def cita(
        self, 
        ctx: discord.ApplicationContext, 
        tema: discord.Option(str, "Tema a revisar (ej. Método Simplex)"), # type: ignore
        dia: discord.Option(int, "Día (número del mes)"), # type: ignore
        mes: discord.Option(int, "Mes (número 1-12)"), # type: ignore
        hora: discord.Option(str, "Hora de inicio (formato 24h, ej. 15:30)") # type: ignore
    ):
        """Schedules a calendar event for a tutoring session."""
        await ctx.defer()
        
        try:
            # Parse time
            hora_parts = hora.split(":")
            if len(hora_parts) != 2:
                raise ValueError("Formato de hora inválido. Usa HH:MM.")
                
            now = datetime.datetime.now(self.timezone)
            year = now.year
            
            # Create aware datetime object
            start_time = datetime.datetime(
                year=year, 
                month=mes, 
                day=dia, 
                hour=int(hora_parts[0]), 
                minute=int(hora_parts[1]),
                tzinfo=self.timezone
            )
            
            # Simple check if requested past date
            if start_time < now:
                # Perhaps they meant next year? Simple fallback for now
                if start_time.month < now.month:
                    start_time = start_time.replace(year=year + 1)
                else:
                    await ctx.followup.send("❌ La fecha solicitada está en el pasado.")
                    return

            # Call core service
            meet_link = calendar_service.create_meeting(
                student_name=ctx.author.display_name,
                topic=tema,
                start_time=start_time,
                duration_minutes=30
            )
            
            if meet_link:
                if meet_link.startswith("⚠️"):
                    # Mock mode message
                    embed_desc = meet_link
                else:
                    embed_desc = f"**Cita agendada exitosamente.**\nSe ha reservado tu bloque el **{start_time.strftime('%Y-%m-%d %H:%M')}**.\n\n🔗 [Enlace de Google Meet]({meet_link})"
                
                embed = discord.Embed(title="✅ Reunión Confirmada", description=embed_desc, color=discord.Color.green())
                await ctx.followup.send(embed=embed)
            else:
                await ctx.followup.send("❌ Hubo un error al agendar la reunión (Credenciales o permisos de Google).")

        except Exception as e:
            logger.error(f"Error scheduling meeting: {e}")
            await ctx.followup.send(f"❌ Error al procesar la fecha. Verifica que los números sean correctos. ({str(e)})")


def setup(bot):
    bot.add_cog(CalendarCog(bot))
