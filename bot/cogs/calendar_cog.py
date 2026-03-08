import datetime
import logging
from collections import defaultdict

import discord
from discord.ext import commands
from discord.commands import SlashCommandGroup
from sqlalchemy import select

from bot.core.calendar_service import calendar_service, SLOT_DURATION_MINUTES
from bot.db.database import get_session
from bot.db.models import Student, ScheduledMeeting

logger = logging.getLogger("beiet.cogs.calendar")


class CalendarCog(commands.Cog, name="Calendar"):
    """Cog for scheduling and calendar operations."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    agenda = SlashCommandGroup("agenda", "Comandos para listar disponibilidad y agendar citas")

    @agenda.command(name="disponibilidad", description="Consulta los horarios disponibles del profesor.")
    async def disponibilidad(self, ctx: discord.ApplicationContext):
        """Fetches the availability of the professor via Google Calendar."""
        await ctx.defer()

        free_slots = await calendar_service.get_availability_slots(days=7)

        if free_slots is None:
            embed = discord.Embed(
                title="📅 Disponibilidad del Profesor BEIET",
                description="⚠️ El servicio de calendario no está configurado (Mock Mode).\nEl profesor tiene disponibilidad simulada el Viernes a las 15:00.",
                color=discord.Color.blue()
            )
            await ctx.followup.send(embed=embed)
            return

        if not free_slots:
            embed = discord.Embed(
                title="📅 Disponibilidad del Profesor BEIET",
                description="No hay bloques disponibles en los próximos 7 días.",
                color=discord.Color.orange()
            )
            await ctx.followup.send(embed=embed)
            return

        # Group slots by date for readability
        by_date: dict[str, list[str]] = defaultdict(list)
        for slot in free_slots:
            date_key = slot.start.strftime("%A %d/%m/%Y")
            by_date[date_key].append(
                f"`{slot.start.strftime('%H:%M')}` - `{slot.end.strftime('%H:%M')}`"
            )

        lines: list[str] = []
        current_len = 0
        for date_label, times in by_date.items():
            day_block = f"**{date_label}**\n{', '.join(times)}\n"
            if current_len + len(day_block) > 3900:
                lines.append("...y más bloques disponibles.")
                break
            lines.append(day_block)
            current_len += len(day_block)

        description = "\n".join(lines)

        embed = discord.Embed(
            title="📅 Disponibilidad del Profesor BEIET",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Bloques de {SLOT_DURATION_MINUTES} min · Usa /agenda cita para reservar")
        await ctx.followup.send(embed=embed)

    @agenda.command(name="cita", description="Agenda una cita de tutoría (Meet) con el profesor.")
    async def cita(
        self,
        ctx: discord.ApplicationContext,
        tema: discord.Option(str, "Tema a revisar (ej. Método Simplex)"),  # type: ignore
        dia: discord.Option(int, "Día (número del mes)"),  # type: ignore
        mes: discord.Option(int, "Mes (número 1-12)"),  # type: ignore
        hora: discord.Option(str, "Hora de inicio (formato 24h, ej. 15:30)")  # type: ignore
    ):
        """Schedules a calendar event for a tutoring session."""
        await ctx.defer()

        # 1. Registration check
        student = None
        async for session in get_session():
            stmt = select(Student).where(Student.discord_id == str(ctx.author.id))
            result = await session.execute(stmt)
            student = result.scalar_one_or_none()

        if not student:
            await ctx.followup.send("❌ Debes usar `/registro` antes de agendar una cita.")
            return

        # 2. Parse and validate datetime
        try:
            hora_parts = hora.split(":")
            if len(hora_parts) != 2:
                raise ValueError("Formato de hora inválido. Usa HH:MM.")

            now = datetime.datetime.now(calendar_service.timezone)
            year = now.year

            start_time = datetime.datetime(
                year=year, month=mes, day=dia,
                hour=int(hora_parts[0]), minute=int(hora_parts[1]),
                tzinfo=calendar_service.timezone
            )

            if start_time < now:
                if start_time.month < now.month:
                    start_time = start_time.replace(year=year + 1)
                else:
                    await ctx.followup.send("❌ La fecha solicitada está en el pasado.")
                    return

        except (ValueError, OverflowError) as e:
            await ctx.followup.send(f"❌ Error al procesar la fecha. Verifica que los números sean correctos. ({str(e)})")
            return

        # 3. Conflict detection
        has_conflict = await calendar_service.check_conflict(start_time, duration_minutes=SLOT_DURATION_MINUTES)
        if has_conflict:
            await ctx.followup.send(
                "❌ El horario solicitado no está disponible (fuera del horario hábil "
                "09:00-18:00 L-V, o ya hay un evento agendado). "
                "Consulta `/agenda disponibilidad` para ver bloques libres."
            )
            return

        # 4. Create Google Calendar event
        meeting_result = await calendar_service.create_meeting(
            student_name=student.name,
            topic=tema,
            start_time=start_time,
            duration_minutes=SLOT_DURATION_MINUTES
        )

        if meeting_result is None:
            await ctx.followup.send("❌ Hubo un error al agendar la reunión (credenciales o permisos de Google).")
            return

        # 5. Persist to DB
        async for session in get_session():
            try:
                scheduled = ScheduledMeeting(
                    student_id=student.id,
                    subject=student.subject,
                    scheduled_at=start_time,
                    duration_minutes=SLOT_DURATION_MINUTES,
                    google_event_id=meeting_result.get("google_event_id"),
                    meet_link=meeting_result.get("meet_link"),
                    topic=tema,
                    status="confirmed",
                )
                session.add(scheduled)
                await session.commit()
            except Exception as e:
                logger.warning(f"Could not persist scheduled meeting for student {ctx.author.id}: {e}")

        # 6. Confirmation embed
        is_mock = meeting_result.get("mock", False)
        if is_mock:
            embed_desc = (
                "⚠️ (Mock Mode) Cita agendada exitosamente en el simulador.\n"
                f"**Fecha:** {start_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"**Tema:** {tema}"
            )
        else:
            meet_link = meeting_result.get("meet_link", "No disponible")
            embed_desc = (
                f"**Cita agendada exitosamente.**\n"
                f"**Fecha:** {start_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"**Tema:** {tema}\n"
                f"**Duración:** {SLOT_DURATION_MINUTES} minutos\n\n"
                f"🔗 [Enlace de Google Meet]({meet_link})"
            )

        embed = discord.Embed(
            title="✅ Reunión Confirmada",
            description=embed_desc,
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Estudiante: {student.name}")
        await ctx.followup.send(embed=embed)


def setup(bot):
    bot.add_cog(CalendarCog(bot))
