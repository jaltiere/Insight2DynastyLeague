from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()


@router.get("/league-history")
async def get_all_history(db: AsyncSession = Depends(get_db)):
    """Get all season winners (champion, division winners, consolation)."""
    # TODO: Implement league history
    return {"message": "League history endpoint - to be implemented"}


@router.get("/league-history/{season}")
async def get_season_history(season: int, db: AsyncSession = Depends(get_db)):
    """Get specific season winners."""
    # TODO: Implement season-specific history
    return {"message": f"Season {season} history - to be implemented"}
