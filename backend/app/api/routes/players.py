from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from app.database import get_db
from app.models import Player
from typing import Optional, List, Dict, Any

router = APIRouter()


@router.get("/players")
async def get_players(
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by player name"),
    position: Optional[str] = Query(None, description="Filter by position (QB, RB, WR, TE, K, DEF)"),
    team: Optional[str] = Query(None, description="Filter by NFL team"),
    limit: int = Query(50, le=100, description="Number of results (max 100)"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """Get players with optional search and filtering."""

    # Build query
    query = select(Player)

    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Player.full_name.like(search_term),
                Player.first_name.like(search_term),
                Player.last_name.like(search_term)
            )
        )

    if position:
        query = query.where(Player.position == position.upper())

    if team:
        query = query.where(Player.team == team.upper())

    # Get total count for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination and ordering
    query = query.order_by(Player.full_name).offset(offset).limit(limit)

    # Execute query
    result = await db.execute(query)
    players = result.scalars().all()

    # Format response
    player_list = []
    for player in players:
        player_list.append({
            "id": player.id,
            "full_name": player.full_name,
            "position": player.position,
            "team": player.team,
            "number": player.number,
            "age": player.age,
            "status": player.status,
            "injury_status": player.injury_status,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "players": player_list
    }


@router.get("/players/{player_id}")
async def get_player_details(player_id: str, db: AsyncSession = Depends(get_db)):
    """Get individual player details."""
    result = await db.execute(
        select(Player).where(Player.id == player_id)
    )
    player = result.scalar_one_or_none()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return {
        "id": player.id,
        "first_name": player.first_name,
        "last_name": player.last_name,
        "full_name": player.full_name,
        "position": player.position,
        "team": player.team,
        "number": player.number,
        "age": player.age,
        "height": player.height,
        "weight": player.weight,
        "college": player.college,
        "years_exp": player.years_exp,
        "status": player.status,
        "injury_status": player.injury_status,
        "stats": player.stats,
    }
