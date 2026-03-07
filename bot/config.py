"""
BEIET Bot — Configuration Management.

Loads settings from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Subject definitions
# ─────────────────────────────────────────────

@dataclass
class SubjectConfig:
    """Configuration for a single university course."""
    name: str
    code: str
    collection_name: str  # ChromaDB collection
    learning_outcomes: dict[str, str] = field(default_factory=dict)
    textbook: str = ""
    data_dir: str = ""


# Define subjects — learning outcomes are placeholders until professor provides them
SUBJECTS: dict[str, SubjectConfig] = {
    "optimizacion": SubjectConfig(
        name="Métodos de Optimización",
        code="OPT",
        collection_name="optimizacion",
        textbook="Libro de Métodos de Optimización",
        data_dir="data/optimizacion",
        learning_outcomes={
            "RA1": "Formular problemas de optimización lineal y no lineal",
            "RA2": "Aplicar métodos de solución para problemas LP y MIP",
            "RA3": "Interpretar resultados y análisis de sensibilidad",
            "RB1": "Implementar algoritmos de optimización en Python",
            "RB2": "Resolver problemas de ingeniería mediante optimización",
        },
    ),
    "mercados": SubjectConfig(
        name="Mercados Eléctricos",
        code="MKT",
        collection_name="mercados_electricos",
        textbook="Fundamentals of Power Markets",
        data_dir="data/mercados",
        learning_outcomes={
            "RA1": "Comprender la estructura de mercados eléctricos",
            "RA2": "Analizar mecanismos de formación de precios",
            "RA3": "Modelar el despacho económico y unit commitment",
            "RB1": "Evaluar regulación y política energética",
            "RB2": "Aplicar herramientas computacionales al análisis de mercados",
        },
    ),
}

# ─────────────────────────────────────────────
# Bot configuration
# ─────────────────────────────────────────────

@dataclass
class BotConfig:
    """Global bot configuration."""

    # Discord
    discord_token: str = os.getenv("DISCORD_TOKEN", "")

    # Gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_temperature_factual: float = 0.2
    gemini_temperature_creative: float = 0.7

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/beiet.db")

    # ChromaDB
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

    # Google Calendar
    google_calendar_credentials: str = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "")
    professor_calendar_id: str = os.getenv("PROFESSOR_CALENDAR_ID", "")

    # Memory
    max_conversation_messages: int = 20   # Keep last N messages in context
    summary_threshold: int = 15           # Summarize when exceeding this count
    session_timeout_minutes: int = 30     # New session after N minutes of inactivity

    # Solver
    solver_timeout_seconds: int = 30
    solver_max_memory_mb: int = 256

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Paths
    base_dir: Path = Path(__file__).parent.parent

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "beiet.db"


# Singleton
config = BotConfig()
