import importlib
import sys


def _load_rag(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    if "bot.core.rag" in sys.modules:
        return importlib.reload(sys.modules["bot.core.rag"])
    return importlib.import_module("bot.core.rag")


def test_embedding_fallback_matches_model_dimension(monkeypatch, tmp_path):
    """On embed failure the fallback vector must match the model dimension
    (gemini-embedding-001 = 3072), not the stale 768 from text-embedding-004."""
    rag = _load_rag(monkeypatch, tmp_path)

    class _Boom:
        class models:
            @staticmethod
            def embed_content(*a, **k):
                raise RuntimeError("boom")

    monkeypatch.setattr(rag.genai, "Client", lambda **k: _Boom())
    fn = rag.GeminiEmbeddingFunction(api_key="test-key")

    out = fn(["alguna consulta"])
    assert len(out) == 1
    assert len(out[0]) == 3072


def test_embedding_skips_empty_text_without_api_call(monkeypatch, tmp_path):
    """Empty/whitespace input (e.g. audio-only messages) must not hit the API
    (which 400s on empty Part) and must return an aligned zero vector."""
    rag = _load_rag(monkeypatch, tmp_path)

    calls = {"n": 0}

    class _Stub:
        class models:
            @staticmethod
            def embed_content(*a, **k):
                calls["n"] += 1
                raise AssertionError("embed_content called for empty text")

    monkeypatch.setattr(rag.genai, "Client", lambda **k: _Stub())
    fn = rag.GeminiEmbeddingFunction(api_key="test-key")

    out = fn(["", "   "])
    assert calls["n"] == 0
    assert all(len(v) == 3072 for v in out)


def test_retrieve_context_skips_empty_query(monkeypatch, tmp_path):
    """An empty query must skip retrieval (audio-only messages) rather than
    embed a zero vector and pull arbitrary neighbors."""
    rag = _load_rag(monkeypatch, tmp_path)

    context = rag.rag_service.retrieve_context("optimizacion", "   ", n_results=2)
    assert "no se encontraron" in context.lower()


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
