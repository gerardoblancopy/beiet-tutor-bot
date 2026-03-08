import importlib
import sys


def test_rag_service_starts_without_api_key(monkeypatch, tmp_path):
    # Keep env deterministic for module import.
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))

    if "bot.core.rag" in sys.modules:
        rag = importlib.reload(sys.modules["bot.core.rag"])
    else:
        rag = importlib.import_module("bot.core.rag")

    assert rag.rag_service is not None
    assert rag.rag_service.embedding_fn is None

    context = rag.rag_service.retrieve_context("optimizacion", "simplex", n_results=1)
    assert "deshabilitada" in context.lower()
