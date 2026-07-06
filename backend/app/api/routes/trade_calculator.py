"""Trade Calculator endpoints.

Provides roster-aware trade evaluation data:
  GET /trade-calculator/owners                    — all current-season owners (+ classification)
  GET /trade-calculator/roster/{user_id}          — owner's roster with KTC values + league PPG delta
  GET /trade-calculator/roster-picks/{user_id}    — picks owned by a team, tiered by standing
  GET /trade-calculator/pick-values               — all cached pick values (RDP entries)
  GET /trade-calculator/h2h-trades/{uid_a}/{uid_b}— past trade history between two owners
  POST /trade-calculator/refresh                  — manual KTC refresh (CRON_SECRET auth)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, or_, func

from app.database import get_db
from app.api.deps import get_league_id, verify_cron_secret
from app.models import Player, Roster, Season, User, Transaction, MatchupPlayerPoint, Matchup, League
from app.models.player_value import PlayerValue
from app.config import get_settings
from app.services.ktc_service import refresh_ktc_values
from app.services.sleeper_client import sleeper_client
from app.api.routes.power_rankings import _calculate_player_stats

router = APIRouter()


async def _get_current_season(db: AsyncSession, league_id: str):
    result = await db.execute(
        select(Season)
        .where(Season.group_id == league_id)
        .order_by(desc(Season.year))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _get_league_scoring_format(db: AsyncSession, league_id: str) -> str:
    """Return 'superflex' or '1qb' based on the league's roster positions."""
    result = await db.execute(
        select(League)
        .join(Season, League.id == Season.league_id)
        .where(Season.group_id == league_id)
        .order_by(desc(Season.year))
        .limit(1)
    )
    league = result.scalar_one_or_none()
    positions = league.roster_positions if league else []
    return "superflex" if "SUPER_FLEX" in (positions or []) else "1qb"


async def _build_value_map(db: AsyncSession, superflex: bool = False) -> dict[str, int]:
    """Return {player_id: ktc_value} for all cached player rows."""
    col = PlayerValue.superflex_value if superflex else PlayerValue.value
    result = await db.execute(
        select(PlayerValue.player_id, col).where(
            PlayerValue.player_id.isnot(None)
        )
    )
    return {row[0]: (row[1] or 0) for row in result.all()}


@router.get("/trade-calculator/owners")
async def get_owners(
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Return all owners in the current season with roster_id, team info, and classification."""
    from app.api.routes.roster_analysis import _classify_team
    from statistics import median

    season = await _get_current_season(db, league_id)
    if not season:
        return {"season": None, "owners": []}

    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id)
        .order_by(User.display_name)
    )
    rows = result.all()

    # Compute classification for each roster (reuse roster_analysis logic)
    all_player_ids: set[str] = set()
    for roster, _ in rows:
        if roster.players:
            all_player_ids.update(roster.players)

    player_stats = await _calculate_player_stats(list(all_player_ids), db) if all_player_ids else {}

    from app.api.routes.power_rankings import _calculate_avg_roster_age, _calculate_player_power_score
    from app.models import Player as PlayerModel

    players_result = await db.execute(
        select(PlayerModel).where(PlayerModel.id.in_(list(all_player_ids)))
    ) if all_player_ids else None
    players_dict = {p.id: p for p in (players_result.scalars().all() if players_result else [])}

    # Compute per-roster total_score and avg_age
    roster_scores: list[float] = []
    roster_data: list[tuple] = []
    for roster, user in rows:
        player_ids = roster.players or []
        total_score = 0.0
        ages = []
        for pid in player_ids:
            p = players_dict.get(pid)
            if not p:
                continue
            ppg = player_stats.get(pid, 0.0)
            score = (await _calculate_player_power_score(p, ppg, db)).power_score
            total_score += score
            if p.age:
                ages.append(p.age)
        avg_age = sum(ages) / len(ages) if ages else 0.0
        roster_data.append((roster, user, total_score, avg_age))
        roster_scores.append(total_score)

    median_score = median(roster_scores) if roster_scores else 0.0

    owners = []
    for roster, user, total_score, avg_age in roster_data:
        classification = _classify_team(avg_age, total_score, median_score)
        owners.append({
            "user_id": user.id,
            "display_name": user.display_name or user.username,
            "username": user.username,
            "avatar": user.avatar,
            "team_name": roster.team_name,
            "roster_id": roster.roster_id,
            "classification": classification,
            "avg_age": round(avg_age, 1),
        })

    return {"season": season.year, "owners": owners}


@router.get("/trade-calculator/roster/{user_id}")
async def get_roster_with_values(
    user_id: str,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Return an owner's current roster with KTC values attached to each player."""
    season = await _get_current_season(db, league_id)
    if not season:
        raise HTTPException(status_code=404, detail="No current season found")

    # Get roster
    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id, Roster.user_id == user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Owner not found in current season")

    roster, user = row
    player_ids: list[str] = roster.players or []
    taxi_ids: list[str] = roster.taxi or []

    if not player_ids:
        return {
            "user_id": user_id,
            "display_name": user.display_name or user.username,
            "team_name": roster.team_name,
            "players": [],
        }

    # Fetch player details
    p_result = await db.execute(
        select(Player).where(Player.id.in_(player_ids))
    )
    players_by_id = {p.id: p for p in p_result.scalars().all()}

    # Fetch KTC values for these players using the league's scoring format
    scoring_format = await _get_league_scoring_format(db, league_id)
    superflex = scoring_format == "superflex"
    val_col = PlayerValue.superflex_value if superflex else PlayerValue.value
    rank_col = PlayerValue.superflex_rank if superflex else PlayerValue.rank
    v_result = await db.execute(
        select(PlayerValue.player_id, val_col, rank_col).where(
            PlayerValue.player_id.in_(player_ids)
        )
    )
    values_by_id = {row[0]: (row[1] or 0, row[2]) for row in v_result.all()}

    # Fetch league PPG for each player (all-time avg in this league's scoring)
    league_ppg = await _calculate_player_stats(player_ids, db)

    # Build league-wide position avg PPG across ALL rosters (not just this owner's)
    all_rosters_result = await db.execute(
        select(Roster).where(Roster.season_id == season.id)
    )
    all_player_ids_league: list[str] = []
    for r in all_rosters_result.scalars().all():
        all_player_ids_league.extend(r.players or [])

    all_players_result = await db.execute(
        select(Player).where(Player.id.in_(all_player_ids_league))
    )
    all_players_by_id = {p.id: p for p in all_players_result.scalars().all()}
    all_league_ppg = await _calculate_player_stats(all_player_ids_league, db)

    pos_ppg: dict[str, list[float]] = {}
    for pid in all_player_ids_league:
        p = all_players_by_id.get(pid)
        if not p or not p.position:
            continue
        ppg = all_league_ppg.get(pid, 0.0)
        if ppg > 0:
            pos_ppg.setdefault(p.position, []).append(ppg)

    players_out = []
    for pid in player_ids:
        p = players_by_id.get(pid)
        if not p:
            continue
        ktc_value, ktc_rank = values_by_id.get(pid, (0, None))
        ppg = league_ppg.get(pid, 0.0)

        # PPG delta vs position average in this league
        pos_avg = (
            sum(pos_ppg.get(p.position or '', [])) / len(pos_ppg[p.position])
            if p.position and pos_ppg.get(p.position)
            else None
        )
        ppg_delta_pct = (
            round(((ppg - pos_avg) / pos_avg) * 100)
            if pos_avg and pos_avg > 0 and ppg > 0
            else None
        )

        players_out.append({
            "player_id": pid,
            "full_name": p.full_name,
            "position": p.position,
            "team": p.team,
            "age": p.age,
            "status": p.status,
            "injury_status": p.injury_status,
            "ktc_value": ktc_value,
            "ktc_rank": ktc_rank,
            "league_ppg": round(ppg, 1) if ppg else None,
            "league_ppg_delta_pct": ppg_delta_pct,  # +12 means 12% above pos avg
            "on_taxi": pid in taxi_ids,
        })

    # Sort by position order, then by KTC value descending
    POSITION_ORDER = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DEF": 5}
    players_out.sort(key=lambda x: (POSITION_ORDER.get(x["position"] or "", 99), -x["ktc_value"]))

    return {
        "user_id": user_id,
        "display_name": user.display_name or user.username,
        "team_name": roster.team_name,
        "scoring_format": scoring_format,
        "players": players_out,
    }


@router.get("/trade-calculator/search")
async def search_players(
    q: str = Query(..., min_length=2, description="Player name search"),
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Search players by name, returning KTC values. Supports free-form lookup."""
    scoring_format = await _get_league_scoring_format(db, league_id)
    superflex = scoring_format == "superflex"
    val_col = PlayerValue.superflex_value if superflex else PlayerValue.value
    rank_col = PlayerValue.superflex_rank if superflex else PlayerValue.rank

    search_term = f"%{q}%"
    result = await db.execute(
        select(Player)
        .where(
            or_(
                Player.full_name.ilike(search_term),
                Player.first_name.ilike(search_term),
                Player.last_name.ilike(search_term),
            )
        )
        .order_by(Player.full_name)
        .limit(25)
    )
    players = result.scalars().all()

    if not players:
        return {"players": [], "scoring_format": scoring_format}

    player_ids = [p.id for p in players]
    v_result = await db.execute(
        select(PlayerValue.player_id, val_col, rank_col).where(
            PlayerValue.player_id.in_(player_ids)
        )
    )
    values_by_id = {row[0]: (row[1] or 0, row[2]) for row in v_result.all()}

    out = []
    for p in players:
        ktc_value, ktc_rank = values_by_id.get(p.id, (0, None))
        out.append({
            "player_id": p.id,
            "full_name": p.full_name,
            "position": p.position,
            "team": p.team,
            "age": p.age,
            "status": p.status,
            "injury_status": p.injury_status,
            "ktc_value": ktc_value,
            "ktc_rank": ktc_rank,
        })

    out.sort(key=lambda x: x["ktc_value"], reverse=True)
    return {"players": out, "scoring_format": scoring_format}


@router.get("/trade-calculator/pick-values")
async def get_pick_values(
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Return all cached draft pick values grouped by year and round."""
    scoring_format = await _get_league_scoring_format(db, league_id)
    superflex = scoring_format == "superflex"

    result = await db.execute(
        select(PlayerValue)
        .where(PlayerValue.position == "RDP")
        .order_by(PlayerValue.value.desc())
    )
    picks = result.scalars().all()

    out = []
    for pick in picks:
        # pick_key format: "2026_1_early"
        if not pick.pick_key:
            continue
        parts = pick.pick_key.split("_")
        if len(parts) != 3:
            continue
        year, round_num, tier = parts
        value = (pick.superflex_value or pick.value) if superflex else pick.value
        rank = (pick.superflex_rank or pick.rank) if superflex else pick.rank
        out.append({
            "pick_key": pick.pick_key,
            "ktc_name": pick.ktc_name,
            "year": int(year),
            "round": int(round_num),
            "tier": tier,
            "value": value,
            "rank": rank,
        })

    return {"picks": out, "scoring_format": scoring_format}


@router.get("/trade-calculator/roster-picks/{user_id}")
async def get_roster_picks(
    user_id: str,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Return all draft picks currently owned by a team, with tier and KTC value.

    Tier (early/mid/late) is estimated from the original team's current record:
      worst records → earliest draft slots → "early" (highest value)
      best records  → latest draft slots   → "late"  (lowest value)
    """
    season = await _get_current_season(db, league_id)
    if not season:
        raise HTTPException(status_code=404, detail="No season data found")

    # ── 1. Load all rosters with win/loss records ──────────────────────────
    result = await db.execute(
        select(Roster, User)
        .join(User, Roster.user_id == User.id)
        .where(Roster.season_id == season.id)
    )
    roster_rows = result.all()

    if not roster_rows:
        raise HTTPException(status_code=404, detail="No rosters found")

    roster_info: dict[int, dict] = {}  # sleeper roster_id -> info
    user_roster_id: int | None = None

    for roster, user in roster_rows:
        roster_info[roster.roster_id] = {
            "wins": roster.wins or 0,
            "losses": roster.losses or 0,
            "user_id": user.id,
            "display_name": user.display_name or user.username,
            "team_name": roster.team_name,
        }
        if user.id == user_id:
            user_roster_id = roster.roster_id

    if user_roster_id is None:
        raise HTTPException(status_code=404, detail="Owner not found in current season")

    # ── 2. Rank teams by record (worst → picks earliest → "early") ─────────
    total_teams = len(roster_info)
    sorted_by_record = sorted(
        roster_info.items(),
        key=lambda x: (x[1]["wins"], -x[1]["losses"]),  # ascending wins = worse
    )
    # rank 1 = worst team = picks first = highest-value pick
    roster_rank: dict[int, int] = {
        rid: rank + 1 for rank, (rid, _) in enumerate(sorted_by_record)
    }

    def rank_to_tier(rank: int) -> str:
        third = total_teams / 3
        if rank <= third:
            return "early"
        elif rank <= third * 2:
            return "mid"
        else:
            return "late"

    # ── 3. Fetch live traded picks from Sleeper ────────────────────────────
    try:
        traded_raw = await sleeper_client.get_traded_picks(league_id)
    except Exception:
        traded_raw = []

    # Determine which future seasons are referenced, default to next year
    future_seasons = sorted({int(p["season"]) for p in traded_raw}) or [season.year + 1]

    # ── 4. Build traded-away and traded-in sets ────────────────────────────
    # traded_away: (season, round, original_roster_id) where user is previous_owner
    traded_away: set[tuple] = set()
    # traded_in: picks from other teams now owned by user
    traded_in: list[dict] = []

    for pick in traded_raw:
        p_season = int(pick["season"])
        p_round = pick["round"]
        p_roster = pick["roster_id"]      # original owner
        p_owner = pick["owner_id"]        # current owner
        p_prev = pick["previous_owner_id"]

        if p_prev == user_roster_id and p_owner != user_roster_id:
            traded_away.add((p_season, p_round, p_roster))

        if p_owner == user_roster_id and p_roster != user_roster_id:
            traded_in.append(pick)

    # ── 5. Determine number of rounds from upcoming draft ──────────────────
    # Use the most recent pre_draft/complete draft round count, fallback to 4
    try:
        drafts_raw = await sleeper_client.get_drafts(league_id)
        num_rounds = 4
        for draft in drafts_raw:
            if draft.get("status") in ("pre_draft", "drafting"):
                num_rounds = draft.get("settings", {}).get("rounds", 4)
                break
    except Exception:
        num_rounds = 4

    # ── 6. Fetch KTC pick values from DB ──────────────────────────────────
    scoring_format = await _get_league_scoring_format(db, league_id)
    superflex = scoring_format == "superflex"
    pv_result = await db.execute(
        select(PlayerValue).where(PlayerValue.position == "RDP")
    )
    ktc_picks: dict[str, dict] = {}
    for pv in pv_result.scalars().all():
        if pv.pick_key:
            value = (pv.superflex_value or pv.value) if superflex else pv.value
            rank = (pv.superflex_rank or pv.rank) if superflex else pv.rank
            ktc_picks[pv.pick_key] = {"value": value, "ktc_name": pv.ktc_name, "rank": rank}

    # ── 7. Assemble pick list ──────────────────────────────────────────────
    picks_out = []

    def build_pick(p_season: int, p_round: int, original_roster_id: int) -> dict:
        rank = roster_rank.get(original_roster_id, (total_teams // 2) + 1)
        tier = rank_to_tier(rank)
        pick_key = f"{p_season}_{p_round}_{tier}"
        ktc = ktc_picks.get(pick_key, {})
        orig = roster_info.get(original_roster_id, {})
        return {
            "year": p_season,
            "round": p_round,
            "original_roster_id": original_roster_id,
            "original_team": orig.get("team_name") or orig.get("display_name", "Unknown"),
            "original_record": f"{orig.get('wins', 0)}-{orig.get('losses', 0)}",
            "tier": tier,
            "estimated_pick_slot": rank,
            "pick_key": pick_key,
            "ktc_name": ktc.get("ktc_name", f"{p_season} {tier.title()} {p_round}{'st' if p_round == 1 else 'nd' if p_round == 2 else 'rd' if p_round == 3 else 'th'}"),
            "value": ktc.get("value", 0),
            "own_pick": original_roster_id == user_roster_id,
        }

    # User's own picks (each future season, each round) minus traded away
    for p_season in future_seasons:
        for rnd in range(1, num_rounds + 1):
            if (p_season, rnd, user_roster_id) not in traded_away:
                picks_out.append(build_pick(p_season, rnd, user_roster_id))

    # Picks received from other teams
    for pick in traded_in:
        picks_out.append(build_pick(int(pick["season"]), pick["round"], pick["roster_id"]))

    # Sort: season asc, round asc, own picks first
    picks_out.sort(key=lambda p: (p["year"], p["round"], 0 if p["own_pick"] else 1))

    return {"roster_id": user_roster_id, "picks": picks_out, "scoring_format": scoring_format}


@router.get("/trade-calculator/h2h-trades/{user_id_a}/{user_id_b}")
async def get_h2h_trade_history(
    user_id_a: str,
    user_id_b: str,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Return the trade history between two specific owners, graded."""
    from app.services.trade_grading import TradeGradingService

    svc = TradeGradingService(db)
    all_trades = await svc.grade_all_trades()

    # Filter to trades involving BOTH owners
    h2h_trades = []
    for trade in all_trades:
        user_ids_in_trade = {s["user_id"] for s in trade["sides"]}
        if user_id_a in user_ids_in_trade and user_id_b in user_ids_in_trade:
            h2h_trades.append(trade)

    if not h2h_trades:
        return {"trades": [], "summary": None}

    # Build summary stats per owner
    stats: dict[str, dict] = {
        user_id_a: {"wins": 0, "total_value": 0.0, "grades": []},
        user_id_b: {"wins": 0, "total_value": 0.0, "grades": []},
    }

    for trade in h2h_trades:
        if trade["anomaly"]:
            continue
        sides_by_user = {s["user_id"]: s for s in trade["sides"]}
        side_a = sides_by_user.get(user_id_a)
        side_b = sides_by_user.get(user_id_b)
        if not side_a or not side_b:
            continue
        stats[user_id_a]["total_value"] += side_a["total_value"]
        stats[user_id_b]["total_value"] += side_b["total_value"]
        if side_a["grade"] not in ("N/A",):
            stats[user_id_a]["grades"].append(side_a["grade"])
        if side_b["grade"] not in ("N/A",):
            stats[user_id_b]["grades"].append(side_b["grade"])
        # Winner = higher value share
        if side_a["value_share"] > side_b["value_share"]:
            stats[user_id_a]["wins"] += 1
        elif side_b["value_share"] > side_a["value_share"]:
            stats[user_id_b]["wins"] += 1

    # Most common grade helper
    from collections import Counter
    def _most_common_grade(grades: list[str]) -> str | None:
        if not grades:
            return None
        return Counter(grades).most_common(1)[0][0]

    summary = {
        user_id_a: {
            "wins": stats[user_id_a]["wins"],
            "typical_grade": _most_common_grade(stats[user_id_a]["grades"]),
        },
        user_id_b: {
            "wins": stats[user_id_b]["wins"],
            "typical_grade": _most_common_grade(stats[user_id_b]["grades"]),
        },
        "total_trades": len(h2h_trades),
    }

    # Build trade output for the frontend
    trades_out = []
    for trade in h2h_trades:
        sides_by_user = {s["user_id"]: s for s in trade["sides"]}
        side_a = sides_by_user.get(user_id_a, {})
        side_b = sides_by_user.get(user_id_b, {})

        def _slim_assets(side: dict) -> dict:
            assets = side.get("assets_received", {})
            players = [
                {"player_name": p.get("player_name"), "position": p.get("position")}
                for p in assets.get("players", [])
            ]
            picks = [
                {"season": p.get("season"), "round": p.get("round"), "slot": p.get("slot")}
                for p in assets.get("draft_picks", [])
            ]
            return {"players": players, "picks": picks}

        trades_out.append({
            "trade_id": trade["trade_id"],
            "season": trade["season"],
            "week": trade["week"],
            "anomaly": trade["anomaly"],
            "sides": {
                user_id_a: {
                    "owner_name": side_a.get("owner_name"),
                    "grade": side_a.get("grade"),
                    "value_share": side_a.get("value_share"),
                    "total_value": side_a.get("total_value"),
                    "assets_received": _slim_assets(side_a),
                },
                user_id_b: {
                    "owner_name": side_b.get("owner_name"),
                    "grade": side_b.get("grade"),
                    "value_share": side_b.get("value_share"),
                    "total_value": side_b.get("total_value"),
                    "assets_received": _slim_assets(side_b),
                },
            },
        })

    return {"trades": trades_out, "summary": summary}


@router.post("/trade-calculator/refresh", dependencies=[Depends(verify_cron_secret)])
async def refresh_values(
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a KTC value refresh. Requires CRON_SECRET bearer token."""
    settings = get_settings()
    result = await refresh_ktc_values(db, scoring_format=settings.KTC_SCORING_FORMAT)
    # refresh_ktc_values only flushes (sync_league owns the commit when it
    # calls the service); as a standalone endpoint we commit here.
    await db.commit()
    return result
