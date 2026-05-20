from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.api.deps import get_league_id
from app.models import Season

router = APIRouter()


@router.get("/seasons")
async def get_all_seasons(
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get list of all available season years."""
    result = await db.execute(
        select(Season.year)
        .where(Season.group_id == league_id)
        .order_by(desc(Season.year))
    )
    years = [row[0] for row in result.all()]
    return {"seasons": years}
