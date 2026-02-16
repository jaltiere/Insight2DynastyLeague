from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()


@router.get("/matchups/head-to-head/{owner1}/{owner2}")
async def get_head_to_head(owner1: str, owner2: str, db: AsyncSession = Depends(get_db)):
    """Get head-to-head history between two owners."""
    # TODO: Implement H2H logic
    return {"message": f"H2H between {owner1} and {owner2} - to be implemented"}
