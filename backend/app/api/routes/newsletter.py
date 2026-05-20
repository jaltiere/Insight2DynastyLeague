from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.deps import get_league_id
from app.services.newsletter_service import get_newsletter_data

router = APIRouter()


@router.get("/newsletter/{week}")
async def get_newsletter(
    week: int,
    league_id: str = Depends(get_league_id),
    season: Optional[int] = Query(None, description="Season year, defaults to current"),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregate all newsletter data for the given week.

    Returns high/low scores, league median, top players per position,
    season leaders (The 1's), rookie report, playoff picture,
    potential points ranking, and matchup recaps.
    """
    return await get_newsletter_data(db, week, season, league_id=league_id)
