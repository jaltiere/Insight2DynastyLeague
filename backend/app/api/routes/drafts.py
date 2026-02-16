from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()


@router.get("/drafts")
async def get_all_drafts(db: AsyncSession = Depends(get_db)):
    """Get all draft years available."""
    # TODO: Implement drafts list
    return {"message": "All drafts endpoint - to be implemented"}


@router.get("/drafts/{year}")
async def get_draft_by_year(year: int, db: AsyncSession = Depends(get_db)):
    """Get draft results for a specific year."""
    # TODO: Implement draft details by year
    return {"message": f"Draft results for {year} - to be implemented"}
