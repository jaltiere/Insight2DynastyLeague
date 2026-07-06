from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Union, Any
from pydantic import field_validator
import json

_LEAGUES_FILE = Path(__file__).resolve().parent.parent / "leagues.json"


def _load_leagues() -> list[dict[str, Any]]:
    """Load league configs from leagues.json."""
    if _LEAGUES_FILE.exists():
        with open(_LEAGUES_FILE) as f:
            return json.load(f)
    return []


LEAGUES: list[dict[str, Any]] = _load_leagues()
LEAGUES_BY_SLUG: dict[str, dict[str, Any]] = {lg["slug"]: lg for lg in LEAGUES}
LEAGUES_BY_ID: dict[str, dict[str, Any]] = {lg["id"]: lg for lg in LEAGUES}
DEFAULT_LEAGUE: dict[str, Any] | None = next((lg for lg in LEAGUES if lg.get("default")), LEAGUES[0] if LEAGUES else None)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Insight2Dynasty API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "mysql+aiomysql://insight2dynasty_user:insight2dynasty_pass@localhost:3307/insight2dynasty"

    # Sleeper API (kept for sync_service compatibility; defaults to default league)
    SLEEPER_LEAGUE_ID: str = DEFAULT_LEAGUE["id"] if DEFAULT_LEAGUE else "1313933992642220032"
    SLEEPER_BASE_URL: str = "https://api.sleeper.app/v1"

    # Anthropic API (for AI-generated recaps)
    ANTHROPIC_API_KEY: str = ""  # Required for recap generation

    # CORS
    CORS_ORIGINS: Union[list[str], str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:5177", "http://localhost:5178", "http://localhost:5179", "http://localhost:3000"]


    # Trade Calculator
    # "1qb" uses oneQBValues, "superflex" uses superflexValues from KTC
    KTC_SCORING_FORMAT: str = "1qb"

    # Security
    CRON_SECRET: str = "change-me-in-production"  # For securing scheduled sync endpoints

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = Path(__file__).resolve().parent.parent / ".env"
        case_sensitive = True
        # Ignore unknown keys in .env so removing a setting from this class
        # never breaks startup for environments with a stale env file.
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
