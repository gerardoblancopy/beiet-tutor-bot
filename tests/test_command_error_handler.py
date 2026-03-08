import pytest
from discord.ext import commands

from bot.main import on_application_command_error


class _Response:
    def __init__(self, done: bool = False):
        self._done = done

    def is_done(self) -> bool:
        return self._done

    def mark_done(self) -> None:
        self._done = True


class _Followup:
    def __init__(self):
        self.sent = []

    async def send(self, message: str, ephemeral: bool = False):
        self.sent.append((message, ephemeral))


class _Ctx:
    def __init__(self, response_done: bool = False):
        self.response = _Response(done=response_done)
        self.followup = _Followup()
        self.responded = []
        self.command = None

    async def respond(self, message: str, ephemeral: bool = False):
        self.responded.append((message, ephemeral))
        self.response.mark_done()


@pytest.mark.asyncio
async def test_cooldown_error_sends_single_response():
    ctx = _Ctx(response_done=False)
    err = commands.CommandOnCooldown(
        commands.Cooldown(1, 10),
        retry_after=3.5,
        type=commands.BucketType.user,
    )

    await on_application_command_error(ctx, err)

    assert len(ctx.responded) == 1
    assert len(ctx.followup.sent) == 0
    assert "3.5s" in ctx.responded[0][0]


@pytest.mark.asyncio
async def test_missing_permissions_uses_followup_when_response_done():
    ctx = _Ctx(response_done=True)
    err = commands.MissingPermissions(["administrator"])

    await on_application_command_error(ctx, err)

    assert len(ctx.responded) == 0
    assert len(ctx.followup.sent) == 1
    assert "No tienes permisos" in ctx.followup.sent[0][0]
