"""Central application settings.

All configuration flows through :data:`SETTINGS`, loaded once from environment
variables (with a ``.env`` file honored if present). The platform is *free-first*:
with no environment configured at all, ``APP_MODE`` defaults to ``demo`` and the
app runs entirely on bundled fixture data with zero network calls.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Load .env if python-dotenv is available. Never required.
try:  # pragma: no cover - trivial import guard
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass


# Project root = parent of the config/ package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEMO_DIR = DATA_DIR / "demo"
CACHE_DIR = DATA_DIR / "cache"


class AppMode(str, Enum):
    """How the platform sources data."""

    DEMO = "demo"  # bundled fixtures, no network
    LIVE = "live"  # SEC EDGAR (+ optional FMP/FRED)


class AIProvider(str, Enum):
    OLLAMA = "ollama"  # local, free (default)
    GEMINI = "gemini"


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_bool(name: str, default: bool = False) -> bool:
    raw = _get(name, str(default)).lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of runtime configuration."""

    mode: AppMode = AppMode.DEMO
    sec_user_agent: str = ""
    fmp_api_key: str = ""
    fred_api_key: str = ""
    ai_provider: AIProvider = AIProvider.OLLAMA
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    gemini_api_key: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    local_db_path: str = "data/valuation_platform.sqlite"

    # Data-quality tunables (see §10, §12).
    segment_reconciliation_tolerance: float = 0.02  # 2% sum-vs-consolidated gap
    request_timeout_seconds: float = 20.0

    # Directories (not from env; derived).
    project_root: Path = field(default=PROJECT_ROOT)
    demo_dir: Path = field(default=DEMO_DIR)
    cache_dir: Path = field(default=CACHE_DIR)

    @property
    def is_demo(self) -> bool:
        return self.mode is AppMode.DEMO

    @property
    def fmp_enabled(self) -> bool:
        return bool(self.fmp_api_key)

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)


def load_settings() -> Settings:
    """Build a :class:`Settings` from the current environment."""
    mode_raw = _get("APP_MODE", "demo").lower()
    mode = AppMode.LIVE if mode_raw == "live" else AppMode.DEMO

    provider_raw = _get("AI_PROVIDER", "ollama").lower()
    provider = AIProvider.GEMINI if provider_raw == "gemini" else AIProvider.OLLAMA

    return Settings(
        mode=mode,
        sec_user_agent=_get(
            "SEC_USER_AGENT",
            "valuation-platform (contact: set SEC_USER_AGENT in .env)",
        ),
        fmp_api_key=_get("FMP_API_KEY"),
        fred_api_key=_get("FRED_API_KEY"),
        ai_provider=provider,
        ollama_base_url=_get("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=_get("OLLAMA_MODEL", "llama3.1"),
        gemini_api_key=_get("GEMINI_API_KEY"),
        supabase_url=_get("SUPABASE_URL"),
        supabase_anon_key=_get("SUPABASE_ANON_KEY"),
        local_db_path=_get("LOCAL_DB_PATH", "data/valuation_platform.sqlite"),
    )


# Module-level singleton used across the app.
SETTINGS = load_settings()
