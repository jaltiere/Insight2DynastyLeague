from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import Draft, DraftPick, Player, Roster, User
from typing import List, Dict, Any

router = APIRouter()


@router.get("/drafts")
async def get_all_drafts(db: AsyncSession = Depends(get_db)):
    """Get all draft years available."""
    result = await db.execute(
        select(Draft).order_by(desc(Draft.year))
    )
    drafts = result.scalars().all()

    draft_list = []
    for draft in drafts:
        draft_list.append({
            "draft_id": draft.id,
            "year": draft.year,
            "type": draft.type,
            "status": draft.status,
            "rounds": draft.rounds
        })

    return {
        "total_drafts": len(draft_list),
        "drafts": draft_list
    }


@router.get("/drafts/{year}")
async def get_draft_by_year(year: int, db: AsyncSession = Depends(get_db)):
    """Get draft results for a specific year."""
    # Get draft for this year
    result = await db.execute(
        select(Draft).where(Draft.year == year)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft for year {year} not found")

    # Get all picks for this draft
    result = await db.execute(
        select(DraftPick)
        .where(DraftPick.draft_id == draft.id)
        .order_by(DraftPick.pick_no)
    )
    picks = result.scalars().all()

    # Get all players, rosters, and users to enrich pick data
    player_ids = [p.player_id for p in picks if p.player_id]
    roster_ids = [p.roster_id for p in picks if p.roster_id]

    # Fetch players
    player_map = {}
    if player_ids:
        result = await db.execute(
            select(Player).where(Player.id.in_(player_ids))
        )
        players = result.scalars().all()
        player_map = {p.id: p for p in players}

    # Fetch rosters to get user info
    roster_to_user = {}
    if roster_ids:
        result = await db.execute(
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .where(Roster.roster_id.in_(roster_ids))
        )
        for roster, user in result.all():
            roster_to_user[roster.roster_id] = {
                "user_id": user.id,
                "display_name": user.display_name or user.username
            }

    # Build picks list with enriched data
    picks_list = []
    for pick in picks:
        player = player_map.get(pick.player_id)
        owner = roster_to_user.get(pick.roster_id)

        pick_data = {
            "pick_no": pick.pick_no,
            "round": pick.round,
            "pick_in_round": pick.pick_in_round,
            "roster_id": pick.roster_id,
            "player_id": pick.player_id,
        }

        # Add player info if available
        if player:
            pick_data.update({
                "player_name": player.full_name,
                "position": player.position,
                "team": player.team
            })

        # Add owner info if available
        if owner:
            pick_data.update({
                "owner_user_id": owner["user_id"],
                "owner_display_name": owner["display_name"]
            })

        picks_list.append(pick_data)

    return {
        "draft_id": draft.id,
        "year": draft.year,
        "type": draft.type,
        "status": draft.status,
        "rounds": draft.rounds,
        "total_picks": len(picks_list),
        "picks": picks_list
    }
