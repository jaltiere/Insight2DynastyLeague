"""Trade grading service — scores each side of a trade based on post-trade
player performance, draft-pick resolution, and position replacement.

For detailed algorithm documentation, see: backend/docs/TRADE_GRADING.md
"""

from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Draft,
    DraftPick,
    Matchup,
    MatchupPlayerPoint,
    Player,
    Roster,
    Season,
    Transaction,
    User,
)

# Weights
STARTER_WEIGHT = 1.5
BENCH_WEIGHT = 0.1

# Discount applied to projected (unused) draft pick values
FUTURE_PICK_DISCOUNT = 0.7

# Replacement-factor window (weeks before/after trade)
REPLACEMENT_WINDOW = 4


def _value_share_to_grade(share: float) -> str:
    """Map a 0.0-1.0 value share to a letter grade.

    Centered around 50% (fair trade) for balanced grading.
    In 2-sided trades: 50% = B-/C+ range, creating bell curve distribution.
    """
    if share >= 0.70:
        return "A+"
    if share >= 0.65:
        return "A"
    if share >= 0.60:
        return "A-"
    if share >= 0.56:
        return "B+"
    if share >= 0.52:
        return "B"
    if share >= 0.48:
        return "B-"
    if share >= 0.44:
        return "C+"
    if share >= 0.40:
        return "C"
    if share >= 0.35:
        return "C-"
    if share >= 0.30:
        return "D+"
    if share >= 0.25:
        return "D"
    if share >= 0.20:
        return "D-"
    return "F"


class TradeGradingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def grade_all_trades(
        self,
        season: Optional[int] = None,
        owner_id: Optional[str] = None,
    ) -> List[dict]:
        """Grade every completed trade.  Optionally filter by season/owner."""
        trades = await self._fetch_trades(season, owner_id)
        if not trades:
            return []

        # Collect player IDs from trades
        all_player_ids: set = set()
        for txn, season_obj in trades:
            if txn.adds:
                all_player_ids.update(txn.adds.keys())
            if txn.drops:
                all_player_ids.update(txn.drops.keys())

        # Build maps that span ALL seasons (not just trade seasons)
        user_roster_map = await self._build_user_roster_map()
        roster_to_user = await self._build_roster_to_user_map()
        sleeper_roster_map = await self._build_sleeper_roster_map()

        pick_baselines = await self._calculate_pick_baselines()
        pick_index, draft_order_map = await self._resolve_picks()

        # Include resolved draft pick player IDs
        all_player_ids.update(pick_index.values())

        player_map = await self._build_player_map(all_player_ids)
        points_index = await self._fetch_all_player_points(all_player_ids)
        position_points = await self._fetch_position_starter_points()

        graded: List[dict] = []
        for txn, season_obj in trades:
            g = self._grade_trade(
                txn,
                season_obj,
                sleeper_roster_map,
                user_roster_map,
                roster_to_user,
                player_map,
                points_index,
                position_points,
                pick_baselines,
                pick_index,
                draft_order_map,
            )
            graded.append(g)
        return graded

    async def grade_single_trade(self, trade_id: str) -> Optional[dict]:
        """Grade a single trade by its transaction id."""
        result = await self.db.execute(
            select(Transaction, Season)
            .join(Season, Transaction.season_id == Season.id)
            .where(
                Transaction.id == trade_id,
                Transaction.type == "trade",
                Transaction.status == "complete",
            )
        )
        row = result.first()
        if not row:
            return None
        txn, season_obj = row

        all_player_ids: set = set()
        if txn.adds:
            all_player_ids.update(txn.adds.keys())
        if txn.drops:
            all_player_ids.update(txn.drops.keys())

        user_roster_map = await self._build_user_roster_map()
        roster_to_user = await self._build_roster_to_user_map()
        sleeper_roster_map = await self._build_sleeper_roster_map()
        pick_baselines = await self._calculate_pick_baselines()
        pick_index, draft_order_map = await self._resolve_picks()

        all_player_ids.update(pick_index.values())
        player_map = await self._build_player_map(all_player_ids)
        points_index = await self._fetch_all_player_points(all_player_ids)
        position_points = await self._fetch_position_starter_points()

        return self._grade_trade(
            txn,
            season_obj,
            sleeper_roster_map,
            user_roster_map,
            roster_to_user,
            player_map,
            points_index,
            position_points,
            pick_baselines,
            pick_index,
            draft_order_map,
        )

    # ------------------------------------------------------------------
    # Data fetching helpers (batch)
    # ------------------------------------------------------------------

    async def _fetch_trades(
        self,
        season: Optional[int] = None,
        owner_id: Optional[str] = None,
    ) -> List[Tuple[Transaction, Season]]:
        query = (
            select(Transaction, Season)
            .join(Season, Transaction.season_id == Season.id)
            .where(
                Transaction.type == "trade",
                Transaction.status == "complete",
            )
            .order_by(Transaction.status_updated.desc())
        )
        if season is not None:
            query = query.where(Season.year == season)
        result = await self.db.execute(query)
        trades = list(result.all())

        if owner_id is not None:
            # Find all sleeper roster_ids for this owner across all seasons
            r_result = await self.db.execute(
                select(Roster.roster_id, Roster.season_id).where(
                    Roster.user_id == owner_id
                )
            )
            owner_rids: Set[Tuple[int, int]] = set()
            for rid, sid in r_result.all():
                owner_rids.add((sid, rid))

            # Filter trades to those involving this owner
            filtered = []
            for txn, season_obj in trades:
                if txn.roster_ids:
                    for rid in txn.roster_ids:
                        if (season_obj.id, int(rid)) in owner_rids:
                            filtered.append((txn, season_obj))
                            break
            trades = filtered

        return trades

    async def _build_sleeper_roster_map(
        self,
    ) -> Dict[Tuple[int, int], dict]:
        """(season_id, sleeper_roster_id) -> {user_id, username, team_name,
        db_roster_id}"""
        result = await self.db.execute(
            select(Roster, User).join(User, Roster.user_id == User.id)
        )
        mapping: Dict[Tuple[int, int], dict] = {}
        for roster, user in result.all():
            mapping[(roster.season_id, roster.roster_id)] = {
                "user_id": user.id,
                "username": user.display_name or user.username,
                "team_name": roster.team_name,
                "db_roster_id": roster.id,
            }
        return mapping

    async def _build_user_roster_map(self) -> Dict[str, Set[int]]:
        """user_id -> set of all db_roster_ids across all seasons."""
        result = await self.db.execute(select(Roster.user_id, Roster.id))
        mapping: Dict[str, Set[int]] = defaultdict(set)
        for user_id, db_id in result.all():
            if user_id:
                mapping[user_id].add(db_id)
        return dict(mapping)

    async def _build_roster_to_user_map(self) -> Dict[int, str]:
        """db_roster_id -> user_id."""
        result = await self.db.execute(select(Roster.id, Roster.user_id))
        return {db_id: uid for db_id, uid in result.all() if uid}

    async def _build_player_map(
        self, player_ids: set
    ) -> Dict[str, dict]:
        """player_id -> {full_name, position, team}"""
        if not player_ids:
            return {}
        result = await self.db.execute(
            select(Player).where(
                Player.id.in_([str(pid) for pid in player_ids])
            )
        )
        mapping: Dict[str, dict] = {}
        for p in result.scalars().all():
            mapping[p.id] = {
                "full_name": p.full_name,
                "position": p.position,
                "team": p.team,
            }
        return mapping

    async def _fetch_all_player_points(
        self, player_ids: set
    ) -> Dict:
        """Returns index keyed by (player_id, db_roster_id, season_year, week)
        -> (points, is_starter).  We keep db_roster_id so we can translate
        to user_id via roster_to_user at query time."""
        if not player_ids:
            return {}
        result = await self.db.execute(
            select(
                MatchupPlayerPoint.player_id,
                MatchupPlayerPoint.points,
                MatchupPlayerPoint.is_starter,
                MatchupPlayerPoint.roster_id,  # DB PK of roster
                Matchup.week,
                Season.year.label("season_year"),
            )
            .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
            .join(Season, Matchup.season_id == Season.id)
            .where(
                MatchupPlayerPoint.player_id.in_(
                    [str(pid) for pid in player_ids]
                )
            )
        )
        index: Dict[tuple, tuple] = {}
        for row in result.all():
            key = (
                row.player_id,
                row.roster_id,
                row.season_year,
                row.week,
            )
            index[key] = (row.points or 0.0, bool(row.is_starter))
        return index

    async def _fetch_position_starter_points(self) -> Dict:
        """Returns index:
        (db_roster_id, season_year, week, position)
          -> total_starter_points_at_position
        """
        result = await self.db.execute(
            select(
                MatchupPlayerPoint.roster_id,
                MatchupPlayerPoint.player_id,
                MatchupPlayerPoint.points,
                Matchup.week,
                Season.year.label("season_year"),
            )
            .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
            .join(Season, Matchup.season_id == Season.id)
            .where(MatchupPlayerPoint.is_starter.is_(True))
        )

        rows = result.all()
        player_ids_needed = {r.player_id for r in rows}
        pos_map: Dict[str, str] = {}
        if player_ids_needed:
            p_result = await self.db.execute(
                select(Player.id, Player.position).where(
                    Player.id.in_(list(player_ids_needed))
                )
            )
            for pid, pos in p_result.all():
                pos_map[pid] = pos

        index: Dict[tuple, float] = defaultdict(float)
        for r in rows:
            position = pos_map.get(r.player_id)
            if not position:
                continue
            key = (r.roster_id, r.season_year, r.week, position)
            index[key] += r.points or 0.0
        return dict(index)

    async def _calculate_pick_baselines(self) -> Dict[int, float]:
        """Average weighted points-per-week for players drafted in each
        round across all league drafts."""
        result = await self.db.execute(
            select(DraftPick.round, DraftPick.player_id).where(
                DraftPick.player_id.isnot(None)
            )
        )
        picks = result.all()
        if not picks:
            return {}

        round_players: Dict[int, set] = defaultdict(set)
        for rnd, pid in picks:
            round_players[rnd].add(pid)

        all_drafted_pids = set()
        for pids in round_players.values():
            all_drafted_pids.update(pids)

        result = await self.db.execute(
            select(
                MatchupPlayerPoint.player_id,
                MatchupPlayerPoint.points,
                MatchupPlayerPoint.is_starter,
            ).where(
                MatchupPlayerPoint.player_id.in_(list(all_drafted_pids))
            )
        )

        player_stats: Dict[str, dict] = defaultdict(
            lambda: {"weighted_total": 0.0, "weeks": 0}
        )
        for row in result.all():
            w = STARTER_WEIGHT if row.is_starter else BENCH_WEIGHT
            player_stats[row.player_id]["weighted_total"] += (
                row.points or 0.0
            ) * w
            player_stats[row.player_id]["weeks"] += 1

        baselines: Dict[int, float] = {}
        for rnd, pids in round_players.items():
            ppw_values = []
            for pid in pids:
                stats = player_stats.get(pid)
                if stats and stats["weeks"] > 0:
                    ppw_values.append(
                        stats["weighted_total"] / stats["weeks"]
                    )
            baselines[rnd] = (
                sum(ppw_values) / len(ppw_values) if ppw_values else 0.0
            )
        return baselines

    async def _resolve_picks(self) -> Tuple[
        Dict[Tuple[int, int, int], str],
        Dict[int, Dict[int, int]],
    ]:
        """Returns:
        1. pick_index: (draft_year, round, pick_in_round) -> player_id
           Each slot in each round is unique, so this is 1:1.
        2. draft_order_map: draft_year -> {sleeper_roster_id -> slot}
           Inverted draft order so we can map a roster's "original pick"
           to the slot it occupies.
        """
        # Build pick index keyed on slot (pick_in_round) for uniqueness
        result = await self.db.execute(
            select(
                Draft.year,
                DraftPick.round,
                DraftPick.pick_in_round,
                DraftPick.player_id,
            )
            .join(DraftPick, Draft.id == DraftPick.draft_id)
            .where(Draft.status == "complete", DraftPick.player_id.isnot(None))
        )
        pick_index: Dict[Tuple[int, int, int], str] = {}
        for year, rnd, slot, player_id in result.all():
            pick_index[(year, rnd, slot)] = player_id

        # Build inverted draft order: year -> {roster_id -> slot}
        draft_result = await self.db.execute(
            select(Draft.year, Draft.draft_order).where(
                Draft.status == "complete",
                Draft.draft_order.isnot(None),
            )
        )
        draft_order_map: Dict[int, Dict[int, int]] = {}
        for year, order in draft_result.all():
            if order:
                # draft_order is {slot_str: roster_id}, invert to
                # {roster_id: slot_int}
                inverted: Dict[int, int] = {}
                for slot_str, rid in order.items():
                    inverted[int(rid)] = int(slot_str)
                draft_order_map[year] = inverted

        return pick_index, draft_order_map

    # ------------------------------------------------------------------
    # Computation helpers
    # ------------------------------------------------------------------

    def _calculate_player_value(
        self,
        player_id: str,
        user_id: str,
        trade_season_year: int,
        trade_week: int,
        points_index: Dict,
        roster_to_user: Dict[int, str],
        user_roster_map: Dict[str, Set[int]],
    ) -> Tuple[float, int, int]:
        """Sum weighted points for a player on ANY roster belonging to
        user_id after the trade.  Returns (total_value, starter_weeks,
        bench_weeks)."""
        total = 0.0
        starter_weeks = 0
        bench_weeks = 0

        # All db_roster_ids that belong to this user
        user_rids = user_roster_map.get(user_id, set())

        for key, (pts, is_starter) in points_index.items():
            pid, rid, year, week = key
            if pid != str(player_id):
                continue
            if rid not in user_rids:
                continue
            # Only count weeks after the trade
            if year < trade_season_year:
                continue
            if year == trade_season_year and week <= trade_week:
                continue
            weight = STARTER_WEIGHT if is_starter else BENCH_WEIGHT
            total += pts * weight
            if is_starter:
                starter_weeks += 1
            else:
                bench_weeks += 1

        return total, starter_weeks, bench_weeks

    def _calculate_replacement_factor(
        self,
        position: Optional[str],
        user_id: str,
        trade_season_year: int,
        trade_week: int,
        position_points: Dict,
        user_roster_map: Dict[str, Set[int]],
    ) -> float:
        """Compute replacement factor (0.5 = replaced well, 1.0 = big hole)."""
        if not position:
            return 1.0

        user_rids = user_roster_map.get(user_id, set())

        before_pts: List[float] = []
        after_pts: List[float] = []

        for w in range(
            max(1, trade_week - REPLACEMENT_WINDOW + 1), trade_week + 1
        ):
            for rid in user_rids:
                key = (rid, trade_season_year, w, position)
                val = position_points.get(key)
                if val is not None:
                    before_pts.append(val)

        for w in range(
            trade_week + 1, trade_week + REPLACEMENT_WINDOW + 1
        ):
            for rid in user_rids:
                key = (rid, trade_season_year, w, position)
                val = position_points.get(key)
                if val is not None:
                    after_pts.append(val)

        if not before_pts or not after_pts:
            return 1.0

        before_avg = sum(before_pts) / len(before_pts)
        after_avg = sum(after_pts) / len(after_pts)

        if before_avg <= 0:
            return 1.0

        if after_avg >= before_avg:
            return 0.5

        return 1.0 - (after_avg / before_avg) * 0.5

    def _weeks_since_trade(
        self,
        trade_season_year: int,
        trade_week: int,
        points_index: Dict,
    ) -> int:
        """Approximate number of weeks of data after the trade."""
        max_year = trade_season_year
        max_week = trade_week
        for (_, _, year, week) in points_index:
            if year > max_year or (year == max_year and week > max_week):
                max_year = year
                max_week = week
        if max_year == trade_season_year:
            return max(0, max_week - trade_week)
        return (max_week) + (max_year - trade_season_year - 1) * 17 + (
            17 - trade_week
        )

    # ------------------------------------------------------------------
    # Core grade computation
    # ------------------------------------------------------------------

    def _grade_trade(
        self,
        txn: Transaction,
        season_obj: Season,
        sleeper_roster_map: Dict,
        user_roster_map: Dict[str, Set[int]],
        roster_to_user: Dict[int, str],
        player_map: Dict,
        points_index: Dict,
        position_points: Dict,
        pick_baselines: Dict,
        pick_index: Dict,
        draft_order_map: Dict,
    ) -> dict:
        trade_year = season_obj.year
        trade_week = txn.week or 0

        roster_ids = txn.roster_ids or []
        adds = txn.adds or {}
        drops = txn.drops or {}
        picks = txn.picks or []

        # Build per-side assets
        sides_data: Dict[int, dict] = {}
        for rid in roster_ids:
            rid = int(rid)
            sides_data[rid] = {
                "roster_id": rid,
                "players_received": [],
                "picks_received": [],
                "players_given": [],
            }

        for player_id, target_rid in adds.items():
            target_rid = int(target_rid)
            if target_rid in sides_data:
                sides_data[target_rid]["players_received"].append(
                    str(player_id)
                )

        for player_id, source_rid in drops.items():
            source_rid = int(source_rid)
            if source_rid in sides_data:
                sides_data[source_rid]["players_given"].append(
                    str(player_id)
                )

        for pick in picks:
            owner_id = pick.get("owner_id")
            prev_owner_id = pick.get("previous_owner_id")
            if owner_id is not None and prev_owner_id is not None:
                owner_id = int(owner_id)
                prev_owner_id = int(prev_owner_id)
                if owner_id != prev_owner_id and owner_id in sides_data:
                    sides_data[owner_id]["picks_received"].append(pick)

        # Calculate values for each side
        sides_output: List[dict] = []
        for rid, data in sides_data.items():
            roster_info = sleeper_roster_map.get(
                (season_obj.id, rid), {}
            )
            user_id = roster_info.get("user_id", "")

            total_value = 0.0
            player_details = []

            for pid in data["players_received"]:
                pinfo = player_map.get(str(pid), {})
                if user_id:
                    val, s_wks, b_wks = self._calculate_player_value(
                        pid,
                        user_id,
                        trade_year,
                        trade_week,
                        points_index,
                        roster_to_user,
                        user_roster_map,
                    )
                else:
                    val, s_wks, b_wks = 0.0, 0, 0

                # Find which side gave this player away
                giving_rid = None
                for other_rid, other_data in sides_data.items():
                    if other_rid != rid and str(pid) in [
                        str(p) for p in other_data.get("players_given", [])
                    ]:
                        giving_rid = other_rid
                        break

                repl_factor = 1.0
                if giving_rid is not None:
                    giving_info = sleeper_roster_map.get(
                        (season_obj.id, giving_rid), {}
                    )
                    giving_user_id = giving_info.get("user_id")
                    if giving_user_id:
                        repl_factor = self._calculate_replacement_factor(
                            pinfo.get("position"),
                            giving_user_id,
                            trade_year,
                            trade_week,
                            position_points,
                            user_roster_map,
                        )

                adjusted_value = val * repl_factor
                total_value += adjusted_value

                player_details.append({
                    "player_id": str(pid),
                    "player_name": pinfo.get(
                        "full_name", f"Player {pid}"
                    ),
                    "position": pinfo.get("position"),
                    "weighted_points": round(val, 2),
                    "adjusted_points": round(adjusted_value, 2),
                    "starter_weeks": s_wks,
                    "bench_weeks": b_wks,
                    "replacement_factor": round(repl_factor, 2),
                })

            # Draft picks
            pick_details = []
            for pick in data["picks_received"]:
                # Sleeper stores season as string in JSON; cast to int
                pick_season_raw = pick.get("season")
                try:
                    pick_season = int(pick_season_raw) if pick_season_raw is not None else None
                except (ValueError, TypeError):
                    pick_season = pick_season_raw
                pick_round = pick.get("round")
                # roster_id = original owner's slot, owner_id = current
                original_roster = pick.get("roster_id")

                # Look up the draft slot for the original roster
                resolved_player_id = None
                if pick_season and original_roster is not None:
                    order = draft_order_map.get(pick_season, {})
                    slot = order.get(int(original_roster))
                    if slot is not None:
                        resolved_player_id = pick_index.get(
                            (pick_season, pick_round, slot)
                        )

                if resolved_player_id and user_id:
                    # Pick was used — use actual player's points
                    p_val, _, _ = self._calculate_player_value(
                        resolved_player_id,
                        user_id,
                        trade_year,
                        trade_week,
                        points_index,
                        roster_to_user,
                        user_roster_map,
                    )
                    pick_value = p_val
                    status = "actual"
                    drafted_player = player_map.get(
                        resolved_player_id, {}
                    ).get("full_name", f"Player {resolved_player_id}")
                else:
                    # Pick not yet used — project with discount
                    ppw = pick_baselines.get(pick_round, 0.0)
                    weeks_est = self._weeks_since_trade(
                        trade_year, trade_week, points_index
                    )
                    pick_value = ppw * max(weeks_est, 1) * FUTURE_PICK_DISCOUNT
                    status = "projected"
                    drafted_player = None

                total_value += pick_value
                pick_details.append({
                    "season": pick_season,
                    "round": pick_round,
                    "status": status,
                    "value": round(pick_value, 2),
                    "drafted_player": drafted_player,
                })

            sides_output.append({
                "roster_id": rid,
                "owner_name": roster_info.get("username", "Unknown"),
                "user_id": user_id,
                "total_value": round(total_value, 2),
                "assets_received": {
                    "players": player_details,
                    "draft_picks": pick_details,
                },
            })

        # Compute grades
        total_trade_value = sum(s["total_value"] for s in sides_output)
        for side in sides_output:
            if total_trade_value > 0:
                share = side["total_value"] / total_trade_value
            else:
                share = 1.0 / max(len(sides_output), 1)
            side["value_share"] = round(share, 4)
            side["grade"] = _value_share_to_grade(share)

        sides_output.sort(key=lambda s: s["value_share"], reverse=True)

        shares = [s["value_share"] for s in sides_output]
        lopsidedness = (max(shares) - min(shares)) if shares else 0.0

        weeks_of_data = self._weeks_since_trade(
            trade_year, trade_week, points_index
        )

        return {
            "trade_id": txn.id,
            "season": trade_year,
            "week": trade_week,
            "date": txn.status_updated,
            "weeks_of_data": weeks_of_data,
            "lopsidedness": round(lopsidedness, 4),
            "sides": sides_output,
        }
