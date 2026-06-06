import os
import logging
from pathlib import Path
from typing import List
from contextlib import contextmanager

# ─── MONKEYPATCH ─────────────────────────────────────────────────────────────
# Surgical fix for macOS Sonoma / Dropbox / Pydantic stat() errors.
# We hide the .env file from Pydantic's automatic environment discovery
# to avoid "Operation not permitted" (EPERM) on stat() calls.
_original_is_file = Path.is_file
def _safe_is_file(self):
    if self.name in [".env", "bot.env"]:
        # Pretend neither .env nor bot.env exist for Pydantic/Chroma
        return False
    return _original_is_file(self)

@contextmanager
def mask_env_and_stat():
    """Context manager to hide .env and bot-specific env vars."""
    # 1. Mask pathlib.Path.is_file
    Path.is_file = _safe_is_file
    
    # 2. Mask os.environ
    forbidden = [
        "DISCORD_TOKEN", "GEMINI_API_KEY", "GOOGLE_CALENDAR_CREDENTIALS",
        "PROFESSOR_CALENDAR_ID", "DATABASE_URL", "CHROMA_PERSIST_DIR",
        "BOT_PREFIX", "DEFAULT_SUBJECT", "LOG_LEVEL"
    ]
    backup = {k: os.environ.get(k) for k in forbidden if k in os.environ}
    for k in backup:
        del os.environ[k]
        
    try:
        yield
    finally:
        # Restore everything
        Path.is_file = _original_is_file
        os.environ.update({k: v for k, v in backup.items() if v is not None})

# ─── SECURE IMPORT ───────────────────────────────────────────────────────────
with mask_env_and_stat():
    import chromadb
    from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
    from chromadb.config import Settings
# ─────────────────────────────────────────────────────────────────────────────

from google import genai
from bot.config import config

logger = logging.getLogger("beiet.rag")

# Embedding output dimension per Gemini model. This MUST match the dimension
# the Chroma collection was built with: a wrong fallback dimension makes Chroma
# reject the vector ("expecting embedding with dimension of N, got M") and the
# whole query fails. gemini-embedding-001 defaults to 3072; text-embedding-004
# is 768. Keep this in sync whenever model_name changes.
_MODEL_EMBED_DIMS = {
    "gemini-embedding-001": 3072,
    "text-embedding-004": 768,
}
_DEFAULT_EMBED_DIM = 3072


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function for ChromaDB using Google's new genai SDK."""

    def __init__(self, api_key: str, model_name: str = "gemini-embedding-001"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.embed_dim = _MODEL_EMBED_DIMS.get(model_name, _DEFAULT_EMBED_DIM)

    def __call__(self, input: Documents) -> Embeddings:
        """Embeds a list of strings using the Gemini model."""
        if not input:
            return []

        embeddings = []
        for text in input:
            # Empty/whitespace content (e.g. audio-only messages) makes the API
            # return 400 "content contains an empty Part"; skip the call and
            # return an aligned zero vector so the batch stays positionally valid.
            if not text or not text.strip():
                embeddings.append([0.0] * self.embed_dim)
                continue
            try:
                response = self.client.models.embed_content(
                    model=self.model_name,
                    contents=text
                )
                embeddings.append(response.embeddings[0].values)
            except Exception as e:
                logger.warning(f"Error embedding text: {e}")
                embeddings.append([0.0] * self.embed_dim)
        return embeddings


class RAGService:
    """Service to handle document retrieval for subjects."""

    def __init__(self, persist_dir: str = None):
        # Use the persist_dir from config if not provided, fallback to data/chroma_data
        if persist_dir is None:
            self.persist_dir = config.chroma_persist_dir or str(config.base_dir / "data" / "chroma_data")
        else:
            self.persist_dir = persist_dir
            
        self.client = None
        self.embedding_fn = None
        self._initialize_client()
        self._initialize_embedding_function()

    def _initialize_client(self):
        """Internal helper to initialize Chroma safely."""
        if self.client is not None:
            return
            
        with mask_env_and_stat():
            try:
                self.client = chromadb.PersistentClient(
                    path=self.persist_dir,
                    settings=Settings(anonymized_telemetry=False, is_persistent=True)
                )
            except Exception as e:
                logger.error(f"Failed to initialize PersistentClient at {self.persist_dir}: {e}. Falling back to EphemeralClient.")
                self.client = chromadb.EphemeralClient(
                    settings=Settings(anonymized_telemetry=False)
                )

    def _initialize_embedding_function(self):
        """Initialize embeddings only when an API key is available."""
        if self.embedding_fn is not None:
            return

        if not config.gemini_api_key:
            return

        try:
            self.embedding_fn = GeminiEmbeddingFunction(api_key=config.gemini_api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini embedding function: {e}")
            self.embedding_fn = None

    def get_collection(self, subject: str):
        """Retrieve or create a ChromaDB collection for the given subject."""
        self._initialize_client()
        self._initialize_embedding_function()

        if self.embedding_fn is None:
            raise RuntimeError("GEMINI_API_KEY is required to create/query embedding collections.")

        subject_config = config.SUBJECTS.get(subject)
        if not subject_config:
            raise ValueError(f"Unknown subject: {subject}")
            
        collection_name = subject_config.collection_name
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": f"Knowledge base for {subject_config.name}"}
        )

    def retrieve_context(self, subject: str, query: str, n_results: int = 5) -> str:
        """Retrieves document chunks for a query."""
        if not config.gemini_api_key:
            return "⚠️ Búsqueda RAG deshabilitada (Falta API Key)."

        # Empty queries (e.g. audio-only messages with no text) have nothing to
        # match; skip retrieval instead of pulling arbitrary nearest neighbors.
        if not query or not query.strip():
            return "No se encontraron fragmentos relevantes."

        try:
            collection = self.get_collection(subject)
            if collection.count() == 0:
                return "No hay documentos cargados en la base de conocimientos."
            
            results = collection.query(query_texts=[query], n_results=n_results)
            if not results["documents"] or not results["documents"][0]:
                return "No se encontraron fragmentos relevantes."
                
            formatted_context = "### Material de Referencia Recuperado:\n\n"
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                source = metadata.get("source", "Desconocido")
                page = metadata.get("page", "?")
                topic = metadata.get("topic", "")
                citation = f"[Fuente: {source}, p.{page}]"
                if topic:
                    citation += f" - Tema: {topic}"
                formatted_context += f"{citation}\n{doc}\n\n---\n\n"
            return formatted_context.strip()
        except Exception as e:
            print(f"Error querying RAG: {e}")
            return "Ocurrió un error al consultar el material de estudio."

# Create a persistent singleton instance
rag_service = RAGService()
