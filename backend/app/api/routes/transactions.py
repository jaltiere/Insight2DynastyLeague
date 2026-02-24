from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, case
from app.database import get_db
from app.models import Transaction, Season, Roster, User, Player
from typing import List, Dict, Any, Optional

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
                    owners.append({**owner_info, "roster_id": int(rid)})

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


@router.get("/transactions/summary")
async def get_transaction_summary(
    season: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction counts per owner, optionally filtered by season year."""
    # Build base query for transactions
    query = select(Transaction, Season).join(
        Season, Transaction.season_id == Season.id
    ).where(Transaction.status == "complete")

    if season is not None:
        query = query.where(Season.year == season)

    result = await db.execute(query)
    txns_with_seasons = result.all()

    # Get all season IDs involved
    season_ids = {s.id for _, s in txns_with_seasons}

    # Build roster_id -> user mapping for all relevant seasons
    roster_to_user: Dict[tuple, Dict[str, str]] = {}
    if season_ids:
        result = await db.execute(
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .where(Roster.season_id.in_(list(season_ids)))
        )
        for roster, user in result.all():
            roster_to_user[(roster.season_id, roster.roster_id)] = {
                "user_id": user.id,
                "username": user.display_name or user.username,
                "team_name": roster.team_name,
            }

    # Count transactions per user per type
    # Key: user_id -> {username, team_name, waiver_adds, free_agent_adds, trades}
    user_counts: Dict[str, Dict[str, Any]] = {}

    for txn, season_obj in txns_with_seasons:
        if not txn.roster_ids:
            continue
        for rid in txn.roster_ids:
            owner_info = roster_to_user.get((season_obj.id, int(rid)))
            if not owner_info:
                continue
            uid = owner_info["user_id"]
            if uid not in user_counts:
                user_counts[uid] = {
                    "user_id": uid,
                    "username": owner_info["username"],
                    "team_name": owner_info["team_name"],
                    "waiver_adds": 0,
                    "free_agent_adds": 0,
                    "trades": 0,
                }
            # Update latest team_name (in case it changed across seasons)
            user_counts[uid]["username"] = owner_info["username"]
            user_counts[uid]["team_name"] = owner_info["team_name"]

            if txn.type == "waiver":
                user_counts[uid]["waiver_adds"] += 1
            elif txn.type == "free_agent":
                user_counts[uid]["free_agent_adds"] += 1
            elif txn.type == "trade":
                user_counts[uid]["trades"] += 1

    # Add total and convert to list
    summary = []
    for uid, counts in user_counts.items():
        counts["total"] = (
            counts["waiver_adds"] + counts["free_agent_adds"] + counts["trades"]
        )
        summary.append(counts)

    # Sort by total descending by default
    summary.sort(key=lambda x: x["total"], reverse=True)

    return {"summary": summary}


@router.get("/transactions/by-owner")
async def get_transactions_by_owner(
    user_id: str = Query(...),
    type: str = Query(...),
    season: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get full transaction details for a specific owner and type."""
    # First, find the roster_ids for this user in relevant seasons
    roster_query = select(Roster.roster_id, Roster.season_id).where(
        Roster.user_id == user_id
    )
    if season is not None:
        roster_query = roster_query.join(
            Season, Roster.season_id == Season.id
        ).where(Season.year == season)

    result = await db.execute(roster_query)
    user_rosters = result.all()  # [(roster_id, season_id), ...]

    if not user_rosters:
        return {"transactions": []}

    # Build a set of (season_id, roster_id) tuples for this user
    user_roster_set = {(sid, rid) for rid, sid in user_rosters}
    season_ids = {sid for _, sid in user_rosters}

    # Get all transactions of this type in these seasons
    txn_query = (
        select(Transaction, Season)
        .join(Season, Transaction.season_id == Season.id)
        .where(
            Transaction.type == type,
            Transaction.status == "complete",
            Transaction.season_id.in_(list(season_ids)),
        )
        .order_by(desc(Transaction.status_updated))
    )

    if season is not None:
        txn_query = txn_query.where(Season.year == season)

    result = await db.execute(txn_query)
    txns_with_seasons = result.all()

    # Filter to only transactions involving this user's roster
    filtered_txns = []
    for txn, season_obj in txns_with_seasons:
        if txn.roster_ids:
            for rid in txn.roster_ids:
                if (season_obj.id, int(rid)) in user_roster_set:
                    filtered_txns.append((txn, season_obj))
                    break

    if not filtered_txns:
        return {"transactions": []}

    # Reuse the enrichment logic from get_recent_transactions
    all_player_ids = set()
    all_roster_ids = set()
    enrich_season_ids = set()
    for txn, season_obj in filtered_txns:
        if txn.adds:
            all_player_ids.update(txn.adds.keys())
            all_roster_ids.update(txn.adds.values())
        if txn.drops:
            all_player_ids.update(txn.drops.keys())
            all_roster_ids.update(txn.drops.values())
        if txn.roster_ids:
            all_roster_ids.update(txn.roster_ids)
        enrich_season_ids.add(season_obj.id)

    player_map: Dict[str, Player] = {}
    if all_player_ids:
        result = await db.execute(
            select(Player).where(Player.id.in_(list(all_player_ids)))
        )
        for p in result.scalars().all():
            player_map[p.id] = p

    roster_to_user: Dict[tuple, Dict[str, str]] = {}
    if all_roster_ids:
        result = await db.execute(
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .where(
                Roster.season_id.in_(list(enrich_season_ids)),
                Roster.roster_id.in_(
                    [int(r) for r in all_roster_ids if r is not None]
                ),
            )
        )
        for roster, user in result.all():
            roster_to_user[(roster.season_id, roster.roster_id)] = {
                "user_id": user.id,
                "username": user.display_name or user.username,
                "team_name": roster.team_name,
            }

    transactions = []
    for txn, season_obj in filtered_txns:
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

        owners = []
        if txn.roster_ids:
            for rid in txn.roster_ids:
                owner_info = roster_to_user.get((season_obj.id, int(rid)))
                if owner_info:
                    owners.append({**owner_info, "roster_id": int(rid)})

        draft_picks = []
        if txn.picks:
            for pick in txn.picks:
                pick_owner = roster_to_user.get(
                    (season_obj.id, pick.get("roster_id"))
                )
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
            "season": season_obj.year,
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
