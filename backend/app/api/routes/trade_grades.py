from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.api.deps import get_league_id
from app.services.trade_grading import GRADE_ORDER, TradeGradingService

router = APIRouter()


@router.get("/trade-grades")
async def get_trade_grades(
    league_id: str = Depends(get_league_id),
    season: Optional[int] = Query(None),
    sort: str = Query("lopsided"),
    owner_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Grade all completed trades based on post-trade asset performance."""
    service = TradeGradingService(db, league_id=league_id)
    trades = await service.grade_all_trades(season=season, owner_id=owner_id)

    def _winner_grade_rank(trade: dict) -> int:
        """Rank of the winning side's grade. Anomalies return -1 (sort last)."""
        ranks = [
            GRADE_ORDER.index(side["grade"])
            for side in trade["sides"]
            if side["grade"] in GRADE_ORDER
        ]
        return max(ranks) if ranks else -1

    if sort == "lopsided":
        # Sort by winner's actual (capped) grade first, then raw lopsidedness.
        # Anomalies always sink to the bottom (grade_rank == -1).
        trades.sort(
            key=lambda t: (_winner_grade_rank(t), t["lopsidedness"]),
            reverse=True,
        )
    elif sort == "recent":
        trades.sort(key=lambda t: t["date"] or 0, reverse=True)
    elif sort == "even":
        # Anomalies have lopsidedness ≈ 1.0 so they naturally sink to the
        # bottom of the even (lowest lopsidedness first) sort — no change needed.
        trades.sort(key=lambda t: t["lopsidedness"])

    return {"trades": trades}


@router.get("/trade-grades/{trade_id}")
async def get_trade_grade(
    trade_id: str,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the grade for a single trade."""
    service = TradeGradingService(db, league_id=league_id)
    result = await service.grade_single_trade(trade_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return result
