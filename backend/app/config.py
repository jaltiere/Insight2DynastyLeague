from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Union
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Insight2Dynasty API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "mysql+aiomysql://insight2dynasty_user:insight2dynasty_pass@localhost:3307/insight2dynasty"

    # Sleeper API
    SLEEPER_LEAGUE_ID: str = "1313933992642220032"
    SLEEPER_BASE_URL: str = "https://api.sleeper.app/v1"

    # CORS
    CORS_ORIGINS: Union[list[str], str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:3000"]

    # API Rate Limiting
    SLEEPER_RATE_LIMIT: int = 900  # Stay under 1000/min

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
