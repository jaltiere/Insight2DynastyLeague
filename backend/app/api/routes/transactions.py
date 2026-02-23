from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import Transaction, Season, Roster, User, Player
from typing import List, Dict, Any

router = APIRouter()


@router.get("/transactions/recent")
async def get_recent_transactions(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent transactions with player and owner details."""
    result = await db.execute(
        select(Transaction, Season)
        .join(Season, Transaction.season_id == Season.id)
        .order_by(desc(Transaction.status_updated))
        .limit(limit)
    )
    txns_with_seasons = result.all()

    if not txns_with_seasons:
        return {"transactions": []}

    # Collect all player IDs and roster IDs we need to resolve
    all_player_ids = set()
    all_roster_ids = set()
    season_ids = set()
    for txn, season in txns_with_seasons:
        if txn.adds:
            all_player_ids.update(txn.adds.keys())
            all_roster_ids.update(txn.adds.values())
        if txn.drops:
            all_player_ids.update(txn.drops.keys())
            all_roster_ids.update(txn.drops.values())
        if txn.roster_ids:
            all_roster_ids.update(txn.roster_ids)
        season_ids.add(season.id)

    # Batch-load players
    player_map: Dict[str, Player] = {}
    if all_player_ids:
        result = await db.execute(
            select(Player).where(Player.id.in_(list(all_player_ids)))
        )
        for p in result.scalars().all():
            player_map[p.id] = p

    # Batch-load rosters + users for owner names
    roster_to_user: Dict[int, Dict[str, str]] = {}
    if all_roster_ids:
        # Roster IDs in transactions are Sleeper roster_ids (not DB PKs)
        result = await db.execute(
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .where(
                Roster.season_id.in_(list(season_ids)),
                Roster.roster_id.in_([int(r) for r in all_roster_ids if r is not None])
            )
        )
        for roster, user in result.all():
            roster_to_user[(roster.season_id, roster.roster_id)] = {
                "user_id": user.id,
                "username": user.display_name or user.username,
                "team_name": roster.team_name,
            }

    # Build response
    transactions = []
    for txn, season in txns_with_seasons:
        # Resolve adds
        adds = []
        if txn.adds:
            for player_id, roster_id in txn.adds.items():
                player = player_map.get(str(player_id))
                adds.append({
                    "player_id": str(player_id),
                    "player_name": player.full_name if player else f"Player {player_id}",
                    "position": player.position if player else None,
                    "team": player.team if player else None,
                    "roster_id": roster_id,
                })

        # Resolve drops
        drops = []
        if txn.drops:
            for player_id, roster_id in txn.drops.items():
                player = player_map.get(str(player_id))
                drops.append({
                    "player_id": str(player_id),
                    "player_name": player.full_name if player else f"Player {player_id}",
                    "position": player.position if player else None,
                    "team": player.team if player else None,
                    "roster_id": roster_id,
                })

        # Resolve owners involved
        owners = []
        if txn.roster_ids:
            for rid in txn.roster_ids:
                owner_info = roster_to_user.get((season.id, int(rid)))
                if owner_info:
                    owners.append(owner_info)

        # Draft picks in trade
        draft_picks = []
        if txn.picks:
            for pick in txn.picks:
                pick_owner = roster_to_user.get((season.id, pick.get("roster_id")))
                draft_picks.append({
                    "season": pick.get("season"),
                    "round": pick.get("round"),
                    "roster_id": pick.get("roster_id"),
                    "previous_owner_id": pick.get("previous_owner_id"),
                    "owner_id": pick.get("owner_id"),
                    "owner_name": pick_owner["username"] if pick_owner else None,
                })

        transactions.append({
            "id": txn.id,
            "type": txn.type,
            "status": txn.status,
            "season": season.year,
            "week": txn.week,
            "waiver_bid": txn.waiver_bid,
            "adds": adds,
            "drops": drops,
            "owners": owners,
            "draft_picks": draft_picks,
            "status_updated": txn.status_updated,
            "metadata_notes": txn.metadata_notes,
        })

    return {"transactions": transactions}
