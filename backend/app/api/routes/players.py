from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, cast, String, Integer
from app.database import get_db
from app.models import Player, MatchupPlayerPoint, Matchup, Season, Roster, User, Transaction, DraftPick, Draft
from typing import Optional, List, Dict, Any
import asyncio

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
    """Get individual player details including scoring history, ownership history, and draft history."""
    result = await db.execute(
        select(Player).where(Player.id == player_id)
    )
    player = result.scalar_one_or_none()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Run supplemental queries concurrently
    scoring_task = _get_scoring_history(db, player_id)
    current_owner_task = _get_current_owner(db, player_id)
    ownership_task = _get_ownership_history(db, player_id)
    draft_task = _get_draft_history(db, player_id)

    scoring_history, current_owner, ownership_history, draft_history = await asyncio.gather(
        scoring_task, current_owner_task, ownership_task, draft_task
    )

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
        "scoring_history": scoring_history,
        "current_owner": current_owner,
        "ownership_history": ownership_history,
        "draft_history": draft_history,
    }


async def _get_scoring_history(db: AsyncSession, player_id: str) -> List[Dict]:
    """Aggregate fantasy points by season for a player."""
    stmt = (
        select(
            Season.year,
            func.sum(MatchupPlayerPoint.points).label("total_points"),
            func.count(MatchupPlayerPoint.id).label("games"),
            func.avg(MatchupPlayerPoint.points).label("avg_points"),
            func.sum(
                cast(MatchupPlayerPoint.is_starter, Integer)
            ).label("starter_games"),
        )
        .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
        .join(Season, Matchup.season_id == Season.id)
        .where(MatchupPlayerPoint.player_id == player_id)
        .group_by(Season.year)
        .order_by(Season.year)
    )
    rows = (await db.execute(stmt)).all()
    return [
        {
            "season": row.year,
            "total_points": round(row.total_points or 0, 2),
            "games": row.games or 0,
            "avg_points": round(row.avg_points or 0, 2),
            "starter_games": row.starter_games or 0,
        }
        for row in rows
    ]


async def _get_current_owner(db: AsyncSession, player_id: str) -> Optional[Dict]:
    """Find the current owner of the player (latest season roster)."""
    max_year_subq = select(func.max(Season.year)).scalar_subquery()
    stmt = (
        select(Roster, User, Season.year)
        .join(User, Roster.user_id == User.id)
        .join(Season, Roster.season_id == Season.id)
        .where(Season.year == max_year_subq)
        .where(cast(Roster.players, String).like(f'%"{player_id}"%'))
    )
    row = (await db.execute(stmt)).first()
    if not row:
        return None
    roster, user, year = row
    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "username": user.username,
        "avatar": user.avatar,
        "team_name": roster.team_name,
        "roster_id": roster.roster_id,
        "season": year,
    }


async def _get_ownership_history(db: AsyncSession, player_id: str) -> List[Dict]:
    """Build a timeline of ownership events for a player from transactions.

    Trades (player in both adds and drops of the same transaction) are merged
    into a single event with from_owner and to_owner. Waiver/FA claims and
    plain drops are single-sided events.
    """
    stmt = (
        select(Transaction, Season.year)
        .join(Season, Transaction.season_id == Season.id)
        .where(
            or_(
                cast(Transaction.adds, String).like(f'%"{player_id}"%'),
                cast(Transaction.drops, String).like(f'%"{player_id}"%'),
            )
        )
        .order_by(Season.year, Transaction.week)
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return []

    # Collect all (season_id, roster_id) pairs that need owner resolution
    lookup_pairs: set = set()
    for txn, year in rows:
        adds = txn.adds or {}
        drops = txn.drops or {}
        if player_id in adds:
            lookup_pairs.add((txn.season_id, int(adds[player_id])))
        if player_id in drops:
            lookup_pairs.add((txn.season_id, int(drops[player_id])))

    roster_lookup: Dict[tuple, Dict] = {}
    for season_id, roster_id in lookup_pairs:
        r_stmt = (
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .where(Roster.season_id == season_id)
            .where(Roster.roster_id == roster_id)
        )
        r_row = (await db.execute(r_stmt)).first()
        if r_row:
            r, u = r_row
            roster_lookup[(season_id, roster_id)] = {
                "user_id": u.id,
                "display_name": u.display_name,
                "username": u.username,
            }

    events = []
    for txn, year in rows:
        adds = txn.adds or {}
        drops = txn.drops or {}
        in_adds = player_id in adds
        in_drops = player_id in drops

        if in_adds and in_drops:
            # Trade: player moves from one owner to another in the same transaction
            from_roster_id = int(drops[player_id])
            to_roster_id = int(adds[player_id])
            events.append({
                "event_type": "trade",
                "season": year,
                "week": txn.week,
                "from_owner": roster_lookup.get((txn.season_id, from_roster_id)),
                "to_owner": roster_lookup.get((txn.season_id, to_roster_id)),
            })
        elif in_adds:
            # Waiver claim or free agent signing
            to_roster_id = int(adds[player_id])
            events.append({
                "event_type": txn.type,  # "waiver" or "free_agent"
                "season": year,
                "week": txn.week,
                "from_owner": None,
                "to_owner": roster_lookup.get((txn.season_id, to_roster_id)),
            })
        else:
            # Plain drop / release
            from_roster_id = int(drops[player_id])
            events.append({
                "event_type": "release",
                "season": year,
                "week": txn.week,
                "from_owner": roster_lookup.get((txn.season_id, from_roster_id)),
                "to_owner": None,
            })

    return events


async def _get_draft_history(db: AsyncSession, player_id: str) -> List[Dict]:
    """Find draft pick(s) for this player across all drafts."""
    stmt = (
        select(DraftPick, Draft.year, Draft.type)
        .join(Draft, DraftPick.draft_id == Draft.id)
        .where(DraftPick.player_id == player_id)
        .order_by(Draft.year)
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return []

    # Look up owner names via roster (season-scoped)
    results = []
    for pick, year, draft_type in rows:
        # Find the roster/user for this pick's roster_id in this draft's season
        r_stmt = (
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .join(Season, Roster.season_id == Season.id)
            .where(Season.year == year)
            .where(Roster.roster_id == pick.roster_id)
        )
        r_row = (await db.execute(r_stmt)).first()
        owner = {}
        if r_row:
            r, u = r_row
            owner = {
                "user_id": u.id,
                "display_name": u.display_name,
                "username": u.username,
            }
        results.append({
            "year": year,
            "draft_type": draft_type,
            "round": pick.round,
            "pick_in_round": pick.pick_in_round,
            "overall_pick": pick.pick_no,
            "owner": owner,
        })

    return results
