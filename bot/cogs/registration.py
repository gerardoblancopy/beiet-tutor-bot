"""
BEIET — Student Registration Cog.

Handles `/registro` and `/perfil` commands.
"""

import discord
from discord.ext import commands
from sqlalchemy import select

from bot.config import config
from bot.db.database import get_session
from bot.db.models import Student


class Registration(commands.Cog):
    """Student registration and profile management."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(name="registro", description="Regístrate en el tutor BEIET")
    async def register(
        self, 
        ctx: discord.ApplicationContext,
        nombre: discord.Option(str, "Tu nombre completo"),
        rut: discord.Option(str, "Tu RUT completo (ej: 12345678-9)", required=False),
        asignatura: discord.Option(str, "Asignatura a cursar", choices=list(config.SUBJECTS.keys()), default=config.DEFAULT_SUBJECT)
    ):
        """Register a new student."""
        await ctx.defer(ephemeral=True)
        
        discord_id = str(ctx.author.id)
        
        async for session in get_session():
            # Check if already registered
            stmt = select(Student).where(Student.discord_id == discord_id)
            result = await session.execute(stmt)
            existing_student = result.scalar_one_or_none()
            
            if existing_student:
                await ctx.respond(f"✅ Ya estás registrado como **{existing_student.name}** en **{config.SUBJECTS[existing_student.subject].name}**.")
                return
                
            # Create new student
            new_student = Student(
                discord_id=discord_id,
                name=nombre,
                rut=rut,
                subject=asignatura
            )
            session.add(new_student)
            await session.commit()
            
            subject_name = config.SUBJECTS[asignatura].name
            
            embed = discord.Embed(
                title="🎓 Registro Exitoso",
                description=f"Hola **{nombre}**, bienvenido(a) al tutor BEIET para **{subject_name}**.",
                color=discord.Color.green()
            )
            embed.add_field(name="¿Cómo empezar?", value="Envíame un mensaje directo (DM) o mencióname aquí para empezar a estudiar.")
            
            await ctx.respond(embed=embed, ephemeral=True)


    @discord.slash_command(name="perfil", description="Ver tu perfil de estudiante")
    async def profile(self, ctx: discord.ApplicationContext):
        """View student profile."""
        await ctx.defer(ephemeral=True)
        
        discord_id = str(ctx.author.id)
        
        async for session in get_session():
            stmt = select(Student).where(Student.discord_id == discord_id)
            result = await session.execute(stmt)
            student = result.scalar_one_or_none()
            
            if not student:
                await ctx.respond("❌ No estás registrado. Usa `/registro` primero.", ephemeral=True)
                return
                
            if student.subject not in config.SUBJECTS:
                await ctx.respond(f"⚠️ Asignatura '{student.subject}' no reconocida.", ephemeral=True)
                return
            
            subject_name = config.SUBJECTS[student.subject].name
            
            embed = discord.Embed(
                title=f"👤 Perfil de Estudiante",
                color=discord.Color.blue()
            )
            embed.add_field(name="Nombre", value=student.name, inline=True)
            if student.rut:
                embed.add_field(name="RUT", value=student.rut, inline=True)
            embed.add_field(name="Asignatura", value=subject_name, inline=False)
            embed.set_footer(text=f"ID: {discord_id} • Registrado: {student.created_at.strftime('%Y-%m-%d')}")
            
            await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(Registration(bot))
