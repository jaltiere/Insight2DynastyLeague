from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import Season

router = APIRouter()


@router.get("/seasons")
async def get_all_seasons(db: AsyncSession = Depends(get_db)):
    """Get list of all available season years."""
    result = await db.execute(
        select(Season.year).order_by(desc(Season.year))
    )
    years = [row[0] for row in result.all()]
    return {"seasons": years}
