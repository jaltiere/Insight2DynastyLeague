from fastapi import APIRouter
from app.config import LEAGUES

router = APIRouter()


@router.get("/leagues")
async def list_leagues():
    """Return all configured leagues."""
    return [
        {
            "id": lg["id"],
            "slug": lg["slug"],
            "name": lg["name"],
            "default": lg.get("default", False),
        }
        for lg in LEAGUES
    ]
