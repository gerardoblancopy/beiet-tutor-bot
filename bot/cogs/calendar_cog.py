import logging

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup

from bot.config import config

logger = logging.getLogger("beiet.cogs.calendar")

APPOINTMENT_LINK = config.google_appointment_link


class CalendarCog(commands.Cog, name="Calendar"):
    """Cog for scheduling tutoring sessions via Google Appointment Scheduling."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    agenda = SlashCommandGroup("agenda", "Comandos para agendar tutorías")

    @agenda.command(name="disponibilidad", description="Consulta los horarios disponibles del profesor.")
    async def disponibilidad(self, ctx: discord.ApplicationContext):
        """Shows the professor's availability via Google Appointment link."""
        if not APPOINTMENT_LINK:
            await ctx.respond(
                "⚠️ El link de agendamiento no está configurado. "
                "Contacta al profesor directamente.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📅 Disponibilidad del Profesor BEIET",
            description=(
                "Consulta los horarios disponibles y agenda tu tutoría "
                "directamente desde Google Calendar:\n\n"
                f"🔗 **[Agendar Tutoría]({APPOINTMENT_LINK})**"
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text="El link muestra solo los horarios disponibles del profesor.")
        await ctx.respond(embed=embed)

    @agenda.command(name="cita", description="Agenda una cita de tutoría con el profesor.")
    async def cita(self, ctx: discord.ApplicationContext):
        """Redirects to the Google Appointment Scheduling link."""
        if not APPOINTMENT_LINK:
            await ctx.respond(
                "⚠️ El link de agendamiento no está configurado. "
                "Contacta al profesor directamente.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="📅 Agendar Tutoría",
            description=(
                "Para agendar una cita de tutoría, usa el siguiente link.\n"
                "Podrás ver los horarios disponibles y elegir el que más te convenga:\n\n"
                f"🔗 **[Agendar Tutoría]({APPOINTMENT_LINK})**"
            ),
            color=discord.Color.green(),
        )
        embed.set_footer(text="La cita se confirmará automáticamente por Google Calendar.")
        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(CalendarCog(bot))
