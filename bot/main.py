"""
BEIET Bot — Main Entry Point.

Discord bot using Pycord with automatic cog loading, event handling,
and graceful startup/shutdown.
"""

import asyncio
import logging
import os
import sys

import discord
from discord.ext import commands

from bot.config import config

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s │ %(levelname)-8s │ %(name)-20s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("beiet")

# ─────────────────────────────────────────────
# Bot setup
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True   # Required for reading messages
intents.dm_messages = True       # Required for DM support
intents.members = True           # Required for student tracking

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,  # Custom help via slash command
)

_commands_synced_once = False


@bot.event
async def on_ready():
    """Triggered when the bot connects to Discord."""
    global _commands_synced_once

    logger.info(f"✅ BEIET Bot online as {bot.user} (ID: {bot.user.id})")
    logger.info(f"   Connected to {len(bot.guilds)} server(s)")
    for guild in bot.guilds:
        logger.info(f"   📡 {guild.name} (ID: {guild.id})")

    # Set rich presence
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="/ayuda │ Tutor BEIET",
        )
    )

    # Initialize DB (create tables)
    from bot.db.database import init_db
    try:
        await init_db()
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")

    if not _commands_synced_once:
        try:
            # Sync global commands first, then mirror to guild commands for instant visibility.
            guild_ids = [guild.id for guild in bot.guilds]
            await bot.sync_commands(
                force=True,
                method="bulk",
                delete_existing=True,
                register_guild_commands=False,
            )
            for guild_id in guild_ids:
                await bot.register_commands(
                    guild_id=guild_id,
                    method="bulk",
                    force=True,
                    delete_existing=True,
                )
            _commands_synced_once = True
            logger.info("   ✓ Slash commands synchronized with Discord")
        except Exception as e:
            logger.error(f"❌ Failed to synchronize slash commands: {e}", exc_info=True)


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error: Exception):
    """Global error handler for slash commands."""
    if isinstance(error, commands.CommandOnCooldown):
        msg = f"⏳ Espera {error.retry_after:.1f}s antes de usar este comando de nuevo."
    elif isinstance(error, commands.MissingPermissions):
        msg = "🔒 No tienes permisos para usar este comando."
    else:
        logger.error(f"Command error in /{ctx.command or 'unknown'}: {error}", exc_info=True)
        msg = "❌ Ocurrió un error procesando tu solicitud. Intenta de nuevo."
    
    # Send reaction/response safely
    try:
        if ctx.response.is_done():
            await ctx.followup.send(msg, ephemeral=True)
        else:
            await ctx.respond(msg, ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to send error response: {e}")


@bot.event
async def on_message(message: discord.Message):
    """Handle regular messages (DMs and channel mentions)."""
    # Ignore own messages
    if message.author == bot.user:
        return

    # Process DMs — route to tutor
    if isinstance(message.channel, discord.DMChannel):
        # Import here to avoid circular imports
        tutor_cog = bot.get_cog("Tutor")
        if tutor_cog:
            await tutor_cog.handle_dm(message)
        return

    # Process mentions in server channels
    if bot.user in message.mentions:
        tutor_cog = bot.get_cog("Tutor")
        if tutor_cog:
            await tutor_cog.handle_mention(message)
        return

    # Process regular commands
    await bot.process_commands(message)


# ─────────────────────────────────────────────
# Cog loading
# ─────────────────────────────────────────────

COGS = [
    "bot.cogs.registration",
    "bot.cogs.tutor",
    "bot.cogs.quiz",
    "bot.cogs.progress",
    "bot.cogs.calendar_cog",
    "bot.cogs.interactivo",
    "bot.cogs.admin",
]


def load_cogs():
    """Load all cog modules."""
    for cog_path in COGS:
        try:
            bot.load_extension(cog_path)
            logger.info(f"   ✓ Loaded cog: {cog_path.split('.')[-1]}")
        except Exception as e:
            logger.warning(f"   ✗ Failed to load {cog_path}: {e}")


# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────

def main():
    """Start the BEIET bot."""
    if not config.discord_token:
        logger.error("❌ DISCORD_TOKEN not set. Copy .env.example to .env and fill in your token.")
        sys.exit(1)

    if not config.gemini_api_key:
        logger.warning("⚠️  GEMINI_API_KEY not set. LLM features will be disabled.")

    logger.info("🤖 Starting BEIET — Adaptive University Tutor Bot")
    logger.info(f"   Python {sys.version}")
    logger.info(f"   Pycord {discord.__version__}")

    # Ensure data directory exists
    config.data_dir.mkdir(parents=True, exist_ok=True)

    # Load cogs
    load_cogs()

    # Run bot
    bot.run(config.discord_token)


if __name__ == "__main__":
    main()
