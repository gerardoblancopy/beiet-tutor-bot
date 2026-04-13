"""
BEIET Bot — Configuration Management.

Loads settings from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load `.env` as default, keep `bot.env` as backward-compatible fallback.
# `override=False` (default) preserves values that are already set.
load_dotenv(".env")
load_dotenv("bot.env")

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

    # Discord & Gemini (loaded from `.env`/`bot.env` via load_dotenv)
    @property
    def discord_token(self) -> str:
        return os.getenv("DISCORD_TOKEN", "")

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    # AI Models
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    gemini_temperature_factual: float = 0.2
    gemini_temperature_creative: float = 0.7

    # Memory
    max_conversation_messages: int = 20   # Keep last N messages in context
    summary_threshold: int = 15           # Summarize when exceeding this count
    session_timeout_minutes: int = 30     # New session after N minutes of inactivity

    # Solver
    solver_timeout_seconds: int = 30
    solver_max_memory_mb: int = 256

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Paths (Absolute)
    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.resolve()

    @property
    def data_dir(self) -> Path:
        d = self.base_dir / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def database_url(self) -> str:
        # Resolve DB path absolutely
        raw_url = os.getenv("DATABASE_URL", "")
        if raw_url.startswith("sqlite+aiosqlite:///"):
            db_path_part = raw_url.replace("sqlite+aiosqlite:///", "")
            if not os.path.isabs(db_path_part):
                db_path = (self.base_dir / db_path_part).resolve()
                return f"sqlite+aiosqlite:///{db_path}"
        
        # Fallback to default in data/beiet.db
        return f"sqlite+aiosqlite:///{self.data_dir / 'beiet.db'}"

    @property
    def chroma_persist_dir(self) -> str:
        p = os.getenv("CHROMA_PERSIST_DIR", "chroma_data")
        if not os.path.isabs(p):
            return str((self.base_dir / p).resolve())
        return p

    @property
    def SUBJECTS(self) -> dict[str, SubjectConfig]:
        return SUBJECTS

    @property
    def DEFAULT_SUBJECT(self) -> str:
        return list(SUBJECTS.keys())[0]

    # Google Calendar Appointment Scheduling
    @property
    def google_appointment_link(self) -> str:
        return os.getenv("GOOGLE_APPOINTMENT_LINK", "")

    # Interactive Tools
    @property
    def interactive_costs_url(self) -> str:
        return "https://gerardoblancopy.github.io/geometria-costos/"

    @property
    def interactive_transport_url(self) -> str:
        return "https://transporte.gerardoblanco.com"



# Singleton
config = BotConfig()
