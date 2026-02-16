from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()


@router.get("/standings")
async def get_current_standings(db: AsyncSession = Depends(get_db)):
    """Get current season standings."""
    # TODO: Implement standings logic
    return {"message": "Current standings endpoint - to be implemented"}


@router.get("/standings/{season}")
async def get_historical_standings(season: int, db: AsyncSession = Depends(get_db)):
    """Get historical standings for a specific season."""
    # TODO: Implement historical standings logic
    return {"message": f"Historical standings for season {season} - to be implemented"}
