"""
BEIET — Database Connection & Session Management.

Provides async SQLAlchemy engine and session factory.
Auto-creates tables on first run.
"""

import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from bot.config import config
from bot.db.models import Base

logger = logging.getLogger("beiet.db")

# ─────────────────────────────────────────────
# Engine & Session Factory
# ─────────────────────────────────────────────

engine = create_async_engine(
    config.database_url,
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Create all tables if they don't exist."""
    # Ensure the data directory exists
    db_dir = Path(config.database_url.replace("sqlite+aiosqlite:///", "")).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables initialized")


async def get_session() -> AsyncSession:
    """Get a new async database session."""
    async with async_session() as session:
        yield session
