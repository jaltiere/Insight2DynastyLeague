from fastapi import HTTPException
from app.config import LEAGUES_BY_SLUG
from typing import Any


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
