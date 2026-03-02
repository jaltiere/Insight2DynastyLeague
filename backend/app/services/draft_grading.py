"""Draft grading service - scores each owner's draft performance based on
player performance after the draft.

Algorithm:
1. For each draft, get all picks by owner
2. Calculate weighted points for each drafted player after draft date
3. Sum total value per owner
4. Calculate average value per pick across all owners
5. Grade each owner based on their value share (A+ to F scale)
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
    User,
)

# Weights for starter vs bench scoring (same as trade grading)
STARTER_WEIGHT = 1.5
BENCH_WEIGHT = 0.1


def _value_share_to_grade(share: float) -> str:
    """Map a 0.0-1.0 value share to a letter grade.

    For drafts, we compare each owner's total value to the average.
    share = owner_value / average_value
    - 1.0 = average draft (C grade)
    - >1.0 = above average
    - <1.0 = below average
    """
    if share >= 1.80:
        return "A+"
    if share >= 1.60:
        return "A"
    if share >= 1.40:
        return "A-"
    if share >= 1.20:
        return "B+"
    if share >= 1.10:
        return "B"
    if share >= 0.90:
        return "B-"
    if share >= 0.80:
        return "C+"
    if share >= 0.70:
        return "C"
    if share >= 0.60:
        return "C-"
    if share >= 0.50:
        return "D+"
    if share >= 0.40:
        return "D"
    if share >= 0.30:
        return "D-"
    return "F"


class DraftGradingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def grade_all_drafts(
        self,
        draft_type: Optional[str] = None,  # "startup" or "rookie"
        owner_id: Optional[str] = None,
    ) -> List[dict]:
        """Grade all drafts. Optionally filter by draft type or owner."""
        drafts = await self._fetch_drafts(draft_type)
        if not drafts:
            return []

        # Build maps
        user_roster_map = await self._build_user_roster_map()
        roster_to_user = await self._build_roster_to_user_map()

        # Get all player IDs from all drafts
        all_player_ids: Set[str] = set()
        for draft in drafts:
            result = await self.db.execute(
                select(DraftPick.player_id)
                .where(
                    DraftPick.draft_id == draft.id,
                    DraftPick.player_id.isnot(None),
                )
            )
            for (pid,) in result.all():
                all_player_ids.add(pid)

        player_map = await self._build_player_map(all_player_ids)
        points_index = await self._fetch_all_player_points(all_player_ids)

        graded: List[dict] = []
        for draft in drafts:
            g = await self._grade_draft(
                draft,
                user_roster_map,
                roster_to_user,
                player_map,
                points_index,
            )
            # Filter by owner if specified
            if owner_id:
                # Check if this owner participated in this draft
                has_owner = any(
                    owner["user_id"] == owner_id for owner in g["owners"]
                )
                if not has_owner:
                    continue
            graded.append(g)

        return graded

    async def grade_single_draft(self, draft_id: str) -> Optional[dict]:
        """Grade a single draft by its ID."""
        result = await self.db.execute(
            select(Draft).where(Draft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            return None

        user_roster_map = await self._build_user_roster_map()
        roster_to_user = await self._build_roster_to_user_map()

        # Get player IDs from this draft
        result = await self.db.execute(
            select(DraftPick.player_id)
            .where(
                DraftPick.draft_id == draft.id,
                DraftPick.player_id.isnot(None),
            )
        )
        player_ids = {pid for (pid,) in result.all() if pid}

        player_map = await self._build_player_map(player_ids)
        points_index = await self._fetch_all_player_points(player_ids)

        return await self._grade_draft(
            draft,
            user_roster_map,
            roster_to_user,
            player_map,
            points_index,
        )

    # ------------------------------------------------------------------
    # Data fetching helpers
    # ------------------------------------------------------------------

    async def _fetch_drafts(
        self, draft_type: Optional[str] = None
    ) -> List[Draft]:
        """Fetch all completed drafts, optionally filtered by type.

        Startup draft = 25-round linear draft (the initial league draft)
        Rookie drafts = all subsequent annual rookie drafts
        """
        query = select(Draft).where(Draft.status == "complete")

        # Filter by draft type:
        # "startup" = 25-round linear draft
        # "rookie" = all other drafts (typically 3-5 rounds)
        if draft_type == "startup":
            # Startup draft has 25 rounds and type "linear"
            query = query.where(Draft.rounds >= 20, Draft.type == "linear")
        elif draft_type == "rookie":
            # Rookie drafts have fewer rounds (typically 3-5)
            query = query.where(Draft.rounds < 20)

        query = query.order_by(Draft.year.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

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
        self, player_ids: Set[str]
    ) -> Dict[str, dict]:
        """player_id -> {full_name, position, team}"""
        if not player_ids:
            return {}
        result = await self.db.execute(
            select(Player).where(Player.id.in_(list(player_ids)))
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
        self, player_ids: Set[str]
    ) -> Dict:
        """Returns index keyed by (player_id, db_roster_id, season_year, week)
        -> (points, is_starter)."""
        if not player_ids:
            return {}
        result = await self.db.execute(
            select(
                MatchupPlayerPoint.player_id,
                MatchupPlayerPoint.points,
                MatchupPlayerPoint.is_starter,
                MatchupPlayerPoint.roster_id,
                Matchup.week,
                Season.year.label("season_year"),
            )
            .join(Matchup, MatchupPlayerPoint.matchup_id == Matchup.id)
            .join(Season, Matchup.season_id == Season.id)
            .where(MatchupPlayerPoint.player_id.in_(list(player_ids)))
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

    # ------------------------------------------------------------------
    # Computation helpers
    # ------------------------------------------------------------------

    def _calculate_player_value(
        self,
        player_id: str,
        user_id: str,
        draft_season_year: int,
        points_index: Dict,
        user_roster_map: Dict[str, Set[int]],
    ) -> Tuple[float, int, int]:
        """Sum weighted points for a player on ANY roster belonging to
        user_id after the draft. Returns (total_value, starter_weeks,
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
            # Only count points from draft year onwards
            if year < draft_season_year:
                continue

            weight = STARTER_WEIGHT if is_starter else BENCH_WEIGHT
            total += pts * weight
            if is_starter:
                starter_weeks += 1
            else:
                bench_weeks += 1

        return total, starter_weeks, bench_weeks

    def _weeks_since_draft(
        self,
        draft_season_year: int,
        points_index: Dict,
    ) -> int:
        """Approximate number of weeks of data after the draft."""
        max_year = draft_season_year
        max_week = 0
        for (_, _, year, week) in points_index:
            if year > max_year or (year == max_year and week > max_week):
                max_year = year
                max_week = week
        if max_year == draft_season_year:
            return max_week
        # Approximate weeks across seasons (17 weeks per season)
        return max_week + (max_year - draft_season_year) * 17

    # ------------------------------------------------------------------
    # Core grade computation
    # ------------------------------------------------------------------

    async def _grade_draft(
        self,
        draft: Draft,
        user_roster_map: Dict[str, Set[int]],
        roster_to_user: Dict[int, str],
        player_map: Dict,
        points_index: Dict,
    ) -> dict:
        """Grade a single draft by calculating each owner's total pick value."""
        draft_year = draft.year

        # Get all picks for this draft
        result = await self.db.execute(
            select(DraftPick)
            .where(DraftPick.draft_id == draft.id)
            .order_by(DraftPick.pick_no)
        )
        picks = result.scalars().all()

        # Get season for this draft
        result = await self.db.execute(
            select(Season).where(Season.id == draft.season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            return None

        # Get roster info to map roster_id to user
        roster_ids = list(set(p.roster_id for p in picks if p.roster_id))
        result = await self.db.execute(
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .where(
                Roster.roster_id.in_(roster_ids),
                Roster.season_id == season.id,
            )
        )
        roster_info_map = {}
        for roster, user in result.all():
            roster_info_map[roster.roster_id] = {
                "user_id": user.id,
                "username": user.display_name or user.username,
                "avatar": user.avatar,
            }

        # Group picks by owner
        picks_by_owner: Dict[str, List[DraftPick]] = defaultdict(list)
        for pick in picks:
            if pick.roster_id and pick.player_id:
                info = roster_info_map.get(pick.roster_id)
                if info:
                    picks_by_owner[info["user_id"]].append(pick)

        # Calculate value for each owner
        owner_data: List[dict] = []
        total_value_sum = 0.0

        for user_id, user_picks in picks_by_owner.items():
            total_value = 0.0
            pick_details = []

            for pick in user_picks:
                pinfo = player_map.get(pick.player_id, {})
                val, s_wks, b_wks = self._calculate_player_value(
                    pick.player_id,
                    user_id,
                    draft_year,
                    points_index,
                    user_roster_map,
                )

                total_value += val
                pick_details.append({
                    "pick_no": pick.pick_no,
                    "round": pick.round,
                    "player_id": pick.player_id,
                    "player_name": pinfo.get("full_name", f"Player {pick.player_id}"),
                    "position": pinfo.get("position"),
                    "team": pinfo.get("team"),
                    "weighted_points": round(val, 2),
                    "starter_weeks": s_wks,
                    "bench_weeks": b_wks,
                    "total_weeks": s_wks + b_wks,
                })

            roster_id = user_picks[0].roster_id if user_picks else None
            info = roster_info_map.get(roster_id, {})

            owner_data.append({
                "user_id": user_id,
                "username": info.get("username", "Unknown"),
                "avatar": info.get("avatar"),
                "total_value": round(total_value, 2),
                "num_picks": len(user_picks),
                "avg_value_per_pick": round(total_value / len(user_picks), 2) if user_picks else 0,
                "picks": pick_details,
            })
            total_value_sum += total_value

        # Calculate average value and assign grades
        num_owners = len(owner_data)
        avg_value = total_value_sum / num_owners if num_owners > 0 else 0

        for owner in owner_data:
            if avg_value > 0:
                share = owner["total_value"] / avg_value
            else:
                share = 1.0
            owner["value_vs_average"] = round(share, 4)
            owner["grade"] = _value_share_to_grade(share)

        # Sort by total value descending
        owner_data.sort(key=lambda x: x["total_value"], reverse=True)

        weeks_of_data = self._weeks_since_draft(draft_year, points_index)

        return {
            "draft_id": draft.id,
            "year": draft_year,
            "type": draft.type,
            "rounds": draft.rounds,
            "weeks_of_data": weeks_of_data,
            "avg_value": round(avg_value, 2),
            "total_picks": len(picks),
            "owners": owner_data,
        }
