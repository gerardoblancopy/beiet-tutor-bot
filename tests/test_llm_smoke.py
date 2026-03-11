import pytest

from bot.core.llm import generate_response


@pytest.mark.asyncio
async def test_generate_response_without_api_key_returns_structured_payload(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")

    result = await generate_response(
        system_prompt="Sistema",
        context=[],
        user_message="hola",
    )

    assert isinstance(result, dict)
    assert {"text", "input_tokens", "output_tokens", "cost"}.issubset(result.keys())
    assert "GEMINI_API_KEY" in result["text"]
    assert result["input_tokens"] == 0
    assert result["output_tokens"] == 0
