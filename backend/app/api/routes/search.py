from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.database import get_db
from app.models import Player, User, Draft
from typing import List, Dict, Any

router = APIRouter()

MAX_PER_TYPE = 5
MIN_QUERY_LENGTH = 2


@router.get("/search")
async def global_search(
    q: str = Query(..., min_length=MIN_QUERY_LENGTH, description="Search query"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Search across players, owners, and drafts."""
    term = f"%{q.strip()}%"

    # Run sequentially — AsyncSession is not safe for concurrent use
    players = await _search_players(db, term)
    owners = await _search_owners(db, term)
    drafts = await _search_drafts(db, q.strip())

    return {
        "query": q.strip(),
        "results": players + owners + drafts,
    }


async def _search_players(db: AsyncSession, term: str) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Player)
        .where(
            or_(
                Player.full_name.ilike(term),
                Player.first_name.ilike(term),
                Player.last_name.ilike(term),
            )
        )
        .order_by(Player.full_name)
        .limit(MAX_PER_TYPE)
    )
    players = result.scalars().all()
    return [
        {
            "type": "player",
            "id": p.id,
            "label": p.full_name or f"{p.first_name} {p.last_name}".strip(),
            "subtitle": " · ".join(filter(None, [p.position, p.team])),
        }
        for p in players
    ]


async def _search_owners(db: AsyncSession, term: str) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(User)
        .where(
            or_(
                User.display_name.ilike(term),
                User.username.ilike(term),
            )
        )
        .order_by(User.display_name)
        .limit(MAX_PER_TYPE)
    )
    owners = result.scalars().all()
    return [
        {
            "type": "owner",
            "id": u.id,
            "label": u.display_name or u.username,
            "subtitle": "Owner",
            "meta": {"avatar": u.avatar},
        }
        for u in owners
    ]


async def _search_drafts(db: AsyncSession, q: str) -> List[Dict[str, Any]]:
    # Only match drafts when the query looks like a year or "draft"
    if not (q.isdigit() or "draft" in q.lower()):
        return []

    query = select(Draft).order_by(Draft.year.desc()).limit(MAX_PER_TYPE)
    if q.isdigit():
        query = query.where(Draft.year == int(q))

    result = await db.execute(query)
    drafts = result.scalars().all()
    return [
        {
            "type": "draft",
            "id": d.id,
            "label": f"{d.year} Draft",
            "subtitle": f"{d.rounds} rounds · {d.status}" if d.rounds else d.status or "",
            "meta": {"year": d.year},
        }
        for d in drafts
    ]
