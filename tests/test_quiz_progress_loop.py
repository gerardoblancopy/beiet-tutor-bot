from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import bot.cogs.quiz as quiz_module


class _FakeExecuteResult:
    def __init__(self, student):
        self._student = student

    def scalar_one_or_none(self):
        return self._student


class _FakeSession:
    def __init__(self, student):
        self._student = student
        self.added = []
        self.commits = 0

    async def execute(self, _stmt):
        return _FakeExecuteResult(self._student)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


class _FakeResponse:
    def __init__(self):
        self.edits = []
        self.messages = []

    async def edit_message(self, *, view, embed):
        self.edits.append((view, embed))

    async def send_message(self, message, ephemeral=False):
        self.messages.append((message, ephemeral))


class _FakeInteraction:
    def __init__(self, user_id: int):
        self.user = SimpleNamespace(id=user_id)
        self.response = _FakeResponse()
        self.original_edits = []

    async def edit_original_response(self, *, embed):
        self.original_edits.append(embed)


def _build_question(lo_code: str):
    return SimpleNamespace(
        statement="Pregunta de prueba",
        option_a="opcion A",
        option_b="opcion B",
        option_c="opcion C",
        option_d="opcion D",
        correct_letter="A",
        feedback="Retroalimentacion de prueba",
        lo_code=lo_code,
    )


@pytest.mark.asyncio
async def test_quiz_callback_updates_lo_progress_when_lo_code_is_valid(monkeypatch):
    student = SimpleNamespace(id=7, discord_id="123", subject="optimizacion")
    fake_session = _FakeSession(student=student)

    async def _fake_get_session():
        yield fake_session

    update_lo_progress_mock = AsyncMock()
    monkeypatch.setattr(quiz_module, "get_session", _fake_get_session)
    monkeypatch.setattr(quiz_module, "update_lo_progress", update_lo_progress_mock)

    view = quiz_module.QuizView(_build_question("RA1"), student_id=123, subject="optimizacion")
    button = view.children[0]  # A
    interaction = _FakeInteraction(user_id=123)

    await button.callback(interaction)

    update_lo_progress_mock.assert_awaited_once_with(fake_session, 7, "optimizacion", "RA1", 1.0)
    assert fake_session.commits == 1
    assert len(fake_session.added) == 1
    assert fake_session.added[0].lo_codes == "RA1"
    assert len(interaction.response.edits) == 1
    assert len(interaction.original_edits) == 1


@pytest.mark.asyncio
async def test_quiz_callback_skips_lo_progress_when_lo_code_is_invalid(monkeypatch):
    student = SimpleNamespace(id=8, discord_id="456", subject="optimizacion")
    fake_session = _FakeSession(student=student)

    async def _fake_get_session():
        yield fake_session

    update_lo_progress_mock = AsyncMock()
    monkeypatch.setattr(quiz_module, "get_session", _fake_get_session)
    monkeypatch.setattr(quiz_module, "update_lo_progress", update_lo_progress_mock)

    view = quiz_module.QuizView(_build_question("ZZ99"), student_id=456, subject="optimizacion")
    button = view.children[0]  # A
    interaction = _FakeInteraction(user_id=456)

    await button.callback(interaction)

    update_lo_progress_mock.assert_not_awaited()
    assert fake_session.commits == 1
    assert len(fake_session.added) == 1
    assert fake_session.added[0].lo_codes is None
    assert len(interaction.response.edits) == 1
    assert len(interaction.original_edits) == 0
