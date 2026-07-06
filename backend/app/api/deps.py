import secrets

from fastapi import Header, HTTPException
from app.config import LEAGUES_BY_SLUG, get_settings
from typing import Any

# Placeholder shipped in config.py defaults; never valid in a real deployment.
_CRON_SECRET_PLACEHOLDER = "change-me-in-production"


def verify_cron_secret(authorization: str = Header(None)) -> None:
    """Require a valid CRON_SECRET bearer token.

    Raises 503 when the server has no real secret configured (unset or the
    shipped placeholder), so a missing env var can never leave admin
    endpoints open behind a publicly known default.
    """
    settings = get_settings()
    if not settings.CRON_SECRET or settings.CRON_SECRET == _CRON_SECRET_PLACEHOLDER:
        raise HTTPException(
            status_code=503,
            detail="CRON_SECRET is not configured on the server",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
        )

    token = authorization.removeprefix("Bearer ")
    if not secrets.compare_digest(token, settings.CRON_SECRET):
        raise HTTPException(status_code=403, detail="Invalid cron secret")


def get_league_config(league_slug: str) -> dict[str, Any]:
    """Resolve a league slug from the URL path to its full config dict.

    Raises 404 if the slug is not in leagues.json.
    """
    config = LEAGUES_BY_SLUG.get(league_slug)
    if not config:
        raise HTTPException(status_code=404, detail=f"League '{league_slug}' not found")
    return config


def get_league_id(league_slug: str) -> str:
    """Resolve a league slug to its Sleeper league ID string."""
    return get_league_config(league_slug)["id"]
