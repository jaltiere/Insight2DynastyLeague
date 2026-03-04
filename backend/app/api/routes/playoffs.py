from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models import Season
from app.services.playoff_odds import calculate_playoff_odds

router = APIRouter()


@router.get("/playoffs")
async def get_current_playoff_odds(db: AsyncSession = Depends(get_db)):
    """Get playoff odds for the current (most recent) season."""
    result = await db.execute(
        select(Season).order_by(desc(Season.year)).limit(1)
    )
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail="No season data found")

    data = await calculate_playoff_odds(db, season.year)
    if data is None:
        raise HTTPException(status_code=404, detail="No season data found")

    return data


@router.get("/playoffs/{season_year}")
async def get_historical_playoff_odds(
    season_year: int, db: AsyncSession = Depends(get_db)
):
    """Get playoff odds for a specific season."""
    data = await calculate_playoff_odds(db, season_year)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Season {season_year} not found")

    return data
