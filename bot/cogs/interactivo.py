import logging
import discord
from discord.ext import commands
from bot.config import config

logger = logging.getLogger("beiet.cogs.interactivo")

class InteractivoView(discord.ui.View):
    """View with a button to open the interactive tool."""
    def __init__(self):
        super().__init__(timeout=None)
        # Add a link button
        self.add_item(discord.ui.Button(
            label="📈 Abrir Simulador de Costos",
            url=config.interactive_costs_url,
            style=discord.ButtonStyle.link
        ))

class InteractivoCog(commands.Cog, name="Interactivo"):
    """Cog for economics interactive tools."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(
        name="geometria_costos",
        description="Despliega la herramienta interactiva de Geometría de las Curvas de Costos."
    )
    async def geometria_costos(self, ctx: discord.ApplicationContext):
        """Displays an embed with the link to the interactive tool."""
        embed = discord.Embed(
            title="📐 Geometría de las Curvas de Costos — BEIET Interactivo",
            description=(
                "¡Hola! Soy el Profesor BEIET. He preparado una herramienta interactiva "
                "para que puedas explorar visualmente cómo se comportan los costos de una empresa.\n\n"
                "**¿Qué puedes aprender con este simulador?**\n"
                "🔹 Relación entre Producción y Costos.\n"
                "🔹 Costos Medios (ATC, AVC, AFC) y Marginales (MC).\n"
                "🔹 El concepto de 'La Envolvente' de largo plazo (LRAC).\n"
                "🔹 Intersecciones clave: ¿Dónde el costo marginal cruza al medio?\n\n"
                "Haz clic en el botón de abajo para abrir la aplicación en tu navegador. "
                "¡Es totalmente visual y dinámica!"
            ),
            color=discord.Color.from_rgb(245, 158, 11)  # Amber color from the web app
        )
        
        # Add a nice thumbnail if possible (generic icon or bot icon fallback)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3501/3501170.png")  # Geometry/Math icon
        
        embed.add_field(
            name="URL de acceso", 
            value=f"🔗 [Acceder directamente]({config.interactive_costs_url})", 
            inline=False
        )
        
        embed.set_footer(text="Prof. Gerardo Blanco • BEIET Tutor")
        
        await ctx.respond(embed=embed, view=InteractivoView())

def setup(bot):
    bot.add_cog(InteractivoCog(bot))
