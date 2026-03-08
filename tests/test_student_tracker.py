import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.core.student_tracker import get_weakest_lo
from bot.db.models import Base, LOProgress, Student


@pytest.mark.asyncio
async def test_get_weakest_lo_returns_none_when_no_progress(tmp_path):
    db_path = tmp_path / "tracker_empty.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        student = Student(discord_id="1", name="Test", subject="optimizacion")
        session.add(student)
        await session.commit()

        lo_code, lo_desc = await get_weakest_lo(session, student.id, "optimizacion")
        assert lo_code is None
        assert "No sufficient data" in lo_desc

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_weakest_lo_returns_lowest_score(tmp_path):
    db_path = tmp_path / "tracker_scored.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        student = Student(discord_id="2", name="Test 2", subject="optimizacion")
        session.add(student)
        await session.flush()

        session.add_all(
            [
                LOProgress(
                    student_id=student.id,
                    subject="optimizacion",
                    lo_code="RA1",
                    score=0.2,
                    attempts=1,
                ),
                LOProgress(
                    student_id=student.id,
                    subject="optimizacion",
                    lo_code="RA2",
                    score=0.8,
                    attempts=1,
                ),
            ]
        )
        await session.commit()

        lo_code, lo_desc = await get_weakest_lo(session, student.id, "optimizacion")
        assert lo_code == "RA1"
        assert "Formular problemas de optimización lineal y no lineal" in lo_desc

    await engine.dispose()
