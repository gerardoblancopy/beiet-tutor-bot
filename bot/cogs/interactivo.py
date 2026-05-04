import logging
import discord
from discord.ext import commands
from bot.config import config

logger = logging.getLogger("beiet.cogs.interactivo")

class InteractivoView(discord.ui.View):
    """View with buttons to open interactive tools."""
    def __init__(self, mode: str = "costs"):
        super().__init__(timeout=None)
        if mode == "costs":
            self.add_item(discord.ui.Button(
                label="📈 Abrir Simulador de Costos",
                url=config.interactive_costs_url,
                style=discord.ButtonStyle.link
            ))
        elif mode == "transport":
            self.add_item(discord.ui.Button(
                label="🚚 Abrir Modelo de Transporte",
                url=config.interactive_transport_url,
                style=discord.ButtonStyle.link
            ))
        elif mode == "rutacorta":
            self.add_item(discord.ui.Button(
                label="🛤️ Abrir Ruta Más Corta",
                url=config.interactive_rutacorta_url,
                style=discord.ButtonStyle.link
            ))
        elif mode == "arbolmin":
            self.add_item(discord.ui.Button(
                label="🌳 Abrir Árbol de Expansión Mínima",
                url=config.interactive_arbolmin_url,
                style=discord.ButtonStyle.link
            ))
        elif mode == "flujomax":
            self.add_item(discord.ui.Button(
                label="🌊 Abrir Flujo Máximo",
                url=config.interactive_flujomax_url,
                style=discord.ButtonStyle.link
            ))

class InteractivoCog(commands.Cog, name="Interactivo"):
    """Cog for economics and optimization interactive tools."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(
        name="geometria_costos",
        description="Despliega la herramienta interactiva de Geometría de las Curvas de Costos."
    )
    async def geometria_costos(self, ctx: discord.ApplicationContext):
        """Displays an embed with the link to the costs interactive tool."""
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
            color=discord.Color.from_rgb(245, 158, 11)  # Amber color
        )
        
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3501/3501170.png")
        embed.add_field(
            name="URL de acceso", 
            value=f"🔗 [Acceder directamente]({config.interactive_costs_url})", 
            inline=False
        )
        embed.set_footer(text="Prof. Gerardo Blanco • BEIET Tutor")
        
        await ctx.respond(embed=embed, view=InteractivoView(mode="costs"))

    @discord.slash_command(
        name="transporte",
        description="Despliega la herramienta interactiva del Modelo de Transporte (Optimización)."
    )
    async def transporte(self, ctx: discord.ApplicationContext):
        """Displays an embed with the link to the transport interactive tool."""
        embed = discord.Embed(
            title="🚛 Modelo de Transporte — BEIET Interactivo",
            description=(
                "¡Hola! Soy el Profesor BEIET. He preparado una herramienta interactiva "
                "para que puedas resolver y visualizar problemas de **Modelo de Transporte**.\n\n"
                "**¿Qué puedes hacer con este simulador?**\n"
                "🔹 Configurar orígenes (oferta) y destinos (demanda).\n"
                "🔹 Resolver usando Esquina Noroeste, Costo Mínimo o Vogel.\n"
                "🔹 Optimizar con el método MODI.\n"
                "🔹 Visualizar paso a paso el ciclo de mejora.\n\n"
                "Haz clic en el botón de abajo para abrir la aplicación. "
                "¡Es ideal para practicar tus ejercicios de Optimización!"
            ),
            color=discord.Color.from_rgb(59, 130, 246)  # Blue color
        )
        
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2830/2830305.png") # Truck icon
        embed.add_field(
            name="URL de acceso", 
            value=f"🔗 [Acceder directamente]({config.interactive_transport_url})", 
            inline=False
        )
        embed.set_footer(text="Prof. Gerardo Blanco • BEIET Tutor")
        
        await ctx.respond(embed=embed, view=InteractivoView(mode="transport"))

    # ─────────────────────────────────────────────
    # Network Methods (Métodos de Redes)
    # ─────────────────────────────────────────────

    @discord.slash_command(
        name="rutacorta",
        description="Despliega la herramienta interactiva de Ruta Más Corta (Shortest Path)."
    )
    async def rutacorta(self, ctx: discord.ApplicationContext):
        """Displays an embed with the link to the Shortest Path interactive tool."""
        embed = discord.Embed(
            title="🛤️ Ruta Más Corta — BEIET Interactivo",
            description=(
                "¡Hola! Soy el Profesor BEIET. He preparado una herramienta interactiva "
                "para que puedas resolver problemas de **Ruta Más Corta** en redes.\n\n"
                "**¿Qué puedes hacer con este simulador?**\n"
                "🔹 Construir grafos dirigidos y no dirigidos.\n"
                "🔹 Aplicar el algoritmo de Dijkstra paso a paso.\n"
                "🔹 Visualizar la ruta óptima entre nodos.\n"
                "🔹 Analizar distancias mínimas en la red.\n\n"
                "Haz clic en el botón de abajo para abrir la aplicación. "
                "¡Perfecto para practicar Métodos de Redes!"
            ),
            color=discord.Color.from_rgb(16, 185, 129)  # Emerald green
        )

        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/9437/9437297.png")  # Route icon
        embed.add_field(
            name="URL de acceso",
            value=f"🔗 [Acceder directamente]({config.interactive_rutacorta_url})",
            inline=False
        )
        embed.set_footer(text="Prof. Gerardo Blanco • BEIET Tutor")

        await ctx.respond(embed=embed, view=InteractivoView(mode="rutacorta"))

    @discord.slash_command(
        name="arbolmin",
        description="Despliega la herramienta interactiva de Árbol de Expansión Mínima (MST)."
    )
    async def arbolmin(self, ctx: discord.ApplicationContext):
        """Displays an embed with the link to the Minimum Spanning Tree interactive tool."""
        embed = discord.Embed(
            title="🌳 Árbol de Expansión Mínima — BEIET Interactivo",
            description=(
                "¡Hola! Soy el Profesor BEIET. He preparado una herramienta interactiva "
                "para que puedas resolver problemas de **Árbol de Expansión Mínima (MST)**.\n\n"
                "**¿Qué puedes hacer con este simulador?**\n"
                "🔹 Construir grafos con pesos en las aristas.\n"
                "🔹 Aplicar los algoritmos de Kruskal y Prim.\n"
                "🔹 Visualizar la selección de aristas paso a paso.\n"
                "🔹 Obtener el árbol de costo mínimo que conecta todos los nodos.\n\n"
                "Haz clic en el botón de abajo para abrir la aplicación. "
                "¡Ideal para dominar los problemas de conectividad en redes!"
            ),
            color=discord.Color.from_rgb(139, 92, 246)  # Violet/purple
        )

        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1535/1535012.png")  # Tree icon
        embed.add_field(
            name="URL de acceso",
            value=f"🔗 [Acceder directamente]({config.interactive_arbolmin_url})",
            inline=False
        )
        embed.set_footer(text="Prof. Gerardo Blanco • BEIET Tutor")

        await ctx.respond(embed=embed, view=InteractivoView(mode="arbolmin"))

    @discord.slash_command(
        name="flujomax",
        description="Despliega la herramienta interactiva de Flujo Máximo (Max Flow)."
    )
    async def flujomax(self, ctx: discord.ApplicationContext):
        """Displays an embed with the link to the Max Flow interactive tool."""
        embed = discord.Embed(
            title="🌊 Flujo Máximo — BEIET Interactivo",
            description=(
                "¡Hola! Soy el Profesor BEIET. He preparado una herramienta interactiva "
                "para que puedas resolver problemas de **Flujo Máximo** en redes.\n\n"
                "**¿Qué puedes hacer con este simulador?**\n"
                "🔹 Modelar redes con capacidades en los arcos.\n"
                "🔹 Aplicar el algoritmo de Ford-Fulkerson.\n"
                "🔹 Identificar caminos de aumento y el corte mínimo.\n"
                "🔹 Visualizar el flujo óptimo de la red paso a paso.\n\n"
                "Haz clic en el botón de abajo para abrir la aplicación. "
                "¡Esencial para entender problemas de capacidad en redes!"
            ),
            color=discord.Color.from_rgb(14, 165, 233)  # Sky blue
        )

        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/4149/4149677.png")  # Flow icon
        embed.add_field(
            name="URL de acceso",
            value=f"🔗 [Acceder directamente]({config.interactive_flujomax_url})",
            inline=False
        )
        embed.set_footer(text="Prof. Gerardo Blanco • BEIET Tutor")

        await ctx.respond(embed=embed, view=InteractivoView(mode="flujomax"))


def setup(bot):
    bot.add_cog(InteractivoCog(bot))
