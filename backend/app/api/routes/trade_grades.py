from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.trade_grading import TradeGradingService

router = APIRouter()


@router.get("/trade-grades")
async def get_trade_grades(
    season: Optional[int] = Query(None),
    sort: str = Query("lopsided"),
    owner_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Grade all completed trades based on post-trade asset performance."""
    service = TradeGradingService(db)
    trades = await service.grade_all_trades(season=season, owner_id=owner_id)

    if sort == "lopsided":
        trades.sort(key=lambda t: t["lopsidedness"], reverse=True)
    elif sort == "recent":
        trades.sort(key=lambda t: t["date"] or 0, reverse=True)
    elif sort == "even":
        trades.sort(key=lambda t: t["lopsidedness"])

    return {"trades": trades}


@router.get("/trade-grades/{trade_id}")
async def get_trade_grade(
    trade_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the grade for a single trade."""
    service = TradeGradingService(db)
    result = await service.grade_single_trade(trade_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return result
