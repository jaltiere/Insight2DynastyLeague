from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.sleeper_client import sleeper_client
from app.models import (
    League, User, Season, Roster, Matchup, Player, Transaction, Draft, DraftPick,
    SeasonAward, MatchupPlayerPoint
)
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SyncService:
    """Service to sync data from Sleeper API to database."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = sleeper_client

    @staticmethod
    def _safe_int(value):
        """Convert value to int or None if empty/invalid."""
        if value is None or value == '' or value == 'None':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    async def sync_all_history(self) -> Dict[str, Any]:
        """Sync all historical seasons by walking the previous_league_id chain."""
        try:
            # Walk the chain to collect all league IDs
            league_chain = []
            current_id = self.client.league_id
            while current_id:
                league_data = await self.client.get_league(current_id)
                league_chain.append((current_id, league_data))
                current_id = league_data.get("previous_league_id")

            # Reverse so we process oldest first
            league_chain.reverse()

            nfl_state = await self.client.get_nfl_state()
            synced_seasons = []

            for league_id, league_data in league_chain:
                year = int(league_data.get("season"))
                status = league_data.get("status")
                settings = league_data.get("settings", {})
                logger.info(f"Syncing {year} season (league_id={league_id}, status={status})")

                # Sync league record
                await self._sync_league_data(league_data)

                # Sync users from this season's league
                users_data = await self.client.get_users(league_id)
                await self._sync_users(users_data)

                # Sync season metadata
                await self._sync_season(league_data, year)

                # Sync rosters
                rosters_data = await self.client.get_rosters(league_id)
                await self._sync_rosters(rosters_data, year, users_data)

                # Flush to ensure rosters are visible for matchup/awards sync
                await self.db.flush()

                # Sync matchups (including playoffs for completed seasons)
                if status == "complete":
                    reg_weeks = settings.get("playoff_week_start", 15) - 1
                    playoff_rounds = settings.get("playoff_rounds", 3)
                    total_weeks = reg_weeks + playoff_rounds
                    await self._sync_matchups_for_league(year, total_weeks, league_id)
                else:
                    # In-progress season: sync up to current week
                    await self._sync_matchups_for_league(
                        year, nfl_state.get("week", 1), league_id
                    )

                # Sync drafts
                drafts_data = await self.client.get_drafts(league_id)
                await self._sync_drafts(drafts_data, year)

                # Sync season awards from bracket data (completed seasons only)
                if status == "complete":
                    await self._sync_season_awards(league_id, year)

                # Sync transactions
                if status == "complete":
                    tx_total_weeks = reg_weeks + playoff_rounds
                else:
                    tx_total_weeks = nfl_state.get("week", 1)
                await self._sync_transactions(league_id, year, tx_total_weeks)

                synced_seasons.append(year)
                await self.db.flush()

            # Sync players once (shared across all seasons)
            current_season_year = int(nfl_state.get("season", 2024))
            await self._sync_players(current_season_year)

            await self.db.commit()

            return {
                "status": "success",
                "message": f"Synced {len(synced_seasons)} seasons",
                "seasons": synced_seasons
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error syncing historical data: {e}")
            raise

    async def sync_league(self) -> Dict[str, Any]:
        """Sync complete league data from Sleeper (current season only)."""
        try:
            # Get current NFL state
            nfl_state = await self.client.get_nfl_state()
            current_season = nfl_state.get("season")

            # Sync league info
            league_data = await self.client.get_league()
            await self._sync_league_data(league_data)

            # Sync users
            users_data = await self.client.get_users()
            await self._sync_users(users_data)

            # Sync current season
            await self._sync_season(league_data, current_season)

            # Sync rosters (pass users_data for team names from user metadata)
            rosters_data = await self.client.get_rosters()
            await self._sync_rosters(rosters_data, current_season, users_data)

            # Sync matchups for all weeks
            await self._sync_matchups_for_league(current_season, nfl_state.get("week", 1))

            # Sync drafts
            drafts_data = await self.client.get_drafts()
            await self._sync_drafts(drafts_data, current_season)

            # Flush to ensure rosters are visible for awards sync
            await self.db.flush()

            # Sync season awards from bracket data
            await self._sync_season_awards(
                league_data.get("league_id"), int(current_season)
            )

            # Sync transactions
            await self._sync_transactions(
                league_data.get("league_id"),
                int(current_season),
                nfl_state.get("week", 1)
            )

            # Sync players (this is a large dataset)
            await self._sync_players(int(current_season))

            await self.db.commit()

            return {
                "status": "success",
                "message": "League data synced successfully",
                "season": current_season
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error syncing league data: {e}")
            raise

    async def _sync_league_data(self, league_data: Dict[str, Any]):
        """Sync league configuration."""
        league_id = league_data.get("league_id")

        # Check if league exists
        result = await self.db.execute(
            select(League).where(League.id == league_id)
        )
        league = result.scalar_one_or_none()

        if league:
            # Update existing
            league.name = league_data.get("name")
            league.season = league_data.get("season")
            league.status = league_data.get("status")
            league.settings = league_data.get("settings", {})
            league.scoring_settings = league_data.get("scoring_settings", {})
            league.roster_positions = league_data.get("roster_positions", [])
            league.league_metadata = league_data.get("metadata", {})
        else:
            # Create new
            league = League(
                id=league_id,
                name=league_data.get("name"),
                sport="nfl",
                season=league_data.get("season"),
                status=league_data.get("status"),
                settings=league_data.get("settings", {}),
                scoring_settings=league_data.get("scoring_settings", {}),
                roster_positions=league_data.get("roster_positions", []),
                league_metadata=league_data.get("metadata", {})
            )
            self.db.add(league)

        logger.info(f"Synced league: {league.name}")

    async def _sync_users(self, users_data: List[Dict[str, Any]]):
        """Sync league users (owners)."""
        for user_data in users_data:
            user_id = user_data.get("user_id")

            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()

            if user:
                user.username = user_data.get("username") or user_data.get("display_name")
                user.display_name = user_data.get("display_name")
                user.avatar = user_data.get("avatar")
            else:
                user = User(
                    id=user_id,
                    username=user_data.get("username") or user_data.get("display_name"),
                    display_name=user_data.get("display_name"),
                    avatar=user_data.get("avatar"),
                    is_active=True
                )
                self.db.add(user)

        logger.info(f"Synced {len(users_data)} users")

    async def _sync_season(self, league_data: Dict[str, Any], year: int):
        """Sync season metadata."""
        league_id = league_data.get("league_id")
        settings = league_data.get("settings", {})

        result = await self.db.execute(
            select(Season).where(
                Season.league_id == league_id,
                Season.year == year
            )
        )
        season = result.scalar_one_or_none()

        if season:
            season.num_divisions = settings.get("divisions", 2)
            season.playoff_structure = settings.get("playoff_structure", {})
            season.regular_season_weeks = settings.get("playoff_week_start", 14) - 1
            season.playoff_weeks = settings.get("playoff_rounds", 3)
        else:
            season = Season(
                league_id=league_id,
                year=year,
                num_divisions=settings.get("divisions", 2),
                playoff_structure=settings.get("playoff_structure", {}),
                regular_season_weeks=settings.get("playoff_week_start", 14) - 1,
                playoff_weeks=settings.get("playoff_rounds", 3)
            )
            self.db.add(season)

        await self.db.flush()
        logger.info(f"Synced season {year}")

    async def _sync_rosters(self, rosters_data: List[Dict[str, Any]], year: int,
                            users_data: List[Dict[str, Any]] = None):
        """Sync team rosters."""
        # Get season
        result = await self.db.execute(
            select(Season).where(Season.year == year)
        )
        season = result.scalar_one_or_none()
        if not season:
            logger.error(f"Season {year} not found")
            return

        # Build user_id -> team_name mapping from users metadata
        user_team_names = {}
        if users_data:
            for user_data in users_data:
                uid = user_data.get("user_id")
                team_name = (user_data.get("metadata") or {}).get("team_name")
                if uid and team_name:
                    user_team_names[uid] = team_name

        for roster_data in rosters_data:
            roster_id = roster_data.get("roster_id")

            result = await self.db.execute(
                select(Roster).where(
                    Roster.season_id == season.id,
                    Roster.roster_id == roster_id
                )
            )
            roster = result.scalar_one_or_none()

            owner_id = roster_data.get("owner_id")
            settings = roster_data.get("settings", {})
            team_name = user_team_names.get(owner_id)

            if roster:
                roster.user_id = owner_id
                roster.team_name = team_name
                roster.wins = settings.get("wins", 0)
                roster.losses = settings.get("losses", 0)
                roster.ties = settings.get("ties", 0)
                roster.points_for = int(settings.get("fpts", 0) or 0)
                roster.points_against = int(settings.get("fpts_against", 0) or 0)
                roster.players = roster_data.get("players", [])
                roster.starters = roster_data.get("starters", [])
                roster.reserve = roster_data.get("reserve", [])
                roster.taxi = roster_data.get("taxi", [])
                roster.settings = settings
            else:
                roster = Roster(
                    roster_id=roster_id,
                    season_id=season.id,
                    user_id=owner_id,
                    team_name=team_name,
                    division=settings.get("division"),
                    wins=settings.get("wins", 0),
                    losses=settings.get("losses", 0),
                    ties=settings.get("ties", 0),
                    points_for=int(settings.get("fpts", 0) or 0),
                    points_against=int(settings.get("fpts_against", 0) or 0),
                    players=roster_data.get("players", []),
                    starters=roster_data.get("starters", []),
                    reserve=roster_data.get("reserve", []),
                    taxi=roster_data.get("taxi", []),
                    settings=settings
                )
                self.db.add(roster)

        await self.db.flush()
        logger.info(f"Synced {len(rosters_data)} rosters")

    async def _sync_matchups_for_league(self, year: int, through_week: int,
                                         league_id: str = None):
        """Sync matchups for all weeks up to through_week, including playoffs."""
        result = await self.db.execute(
            select(Season).where(Season.year == year)
        )
        season = result.scalar_one_or_none()
        if not season:
            return

        last_week = min(through_week, season.regular_season_weeks + season.playoff_weeks)

        # Fetch bracket data if we're syncing playoff weeks
        playoff_roster_ids = set()
        consolation_roster_ids = set()
        if last_week > season.regular_season_weeks:
            playoff_roster_ids, consolation_roster_ids = await self._get_bracket_roster_ids(league_id)

        for week in range(1, last_week + 1):
            if week <= season.regular_season_weeks:
                match_type = "regular"
            else:
                match_type = None  # Determined per-matchup from bracket data

            matchups_data = await self.client.get_matchups(week, league_id)
            await self._process_week_matchups(
                matchups_data, season.id, week, match_type,
                playoff_roster_ids, consolation_roster_ids
            )

        logger.info(f"Synced matchups for {year} weeks 1-{last_week}")

    async def _get_bracket_roster_ids(self, league_id: str = None):
        """Fetch bracket data and return sets of roster IDs for playoff vs consolation."""
        playoff_roster_ids = set()
        consolation_roster_ids = set()

        try:
            winners_bracket = await self.client.get_winners_bracket(league_id)
            for entry in winners_bracket:
                if entry.get("t1"):
                    playoff_roster_ids.add(entry["t1"])
                if entry.get("t2"):
                    playoff_roster_ids.add(entry["t2"])
        except Exception as e:
            logger.warning(f"Could not fetch winners bracket: {e}")

        try:
            losers_bracket = await self.client.get_losers_bracket(league_id)
            for entry in losers_bracket:
                if entry.get("t1"):
                    consolation_roster_ids.add(entry["t1"])
                if entry.get("t2"):
                    consolation_roster_ids.add(entry["t2"])
        except Exception as e:
            logger.warning(f"Could not fetch losers bracket: {e}")

        return playoff_roster_ids, consolation_roster_ids

    async def _process_week_matchups(self, matchups_data: List[Dict[str, Any]],
                                      season_id: int, week: int,
                                      match_type: str = "regular",
                                      playoff_roster_ids: set = None,
                                      consolation_roster_ids: set = None):
        """Process matchups for a specific week."""
        # Group matchups by matchup_id
        matchup_groups = {}
        for matchup in matchups_data:
            mid = matchup.get("matchup_id")
            if mid:
                if mid not in matchup_groups:
                    matchup_groups[mid] = []
                matchup_groups[mid].append(matchup)

        # Create/update matchup records
        for matchup_id, teams in matchup_groups.items():
            if len(teams) != 2:
                continue  # Skip bye weeks or incomplete matchups

            team1, team2 = teams[0], teams[1]

            # Classify playoff-week matchups using bracket data
            effective_match_type = match_type
            if effective_match_type is None:
                sleeper_rid_1 = team1.get("roster_id")
                sleeper_rid_2 = team2.get("roster_id")
                if (playoff_roster_ids and
                        (sleeper_rid_1 in playoff_roster_ids or
                         sleeper_rid_2 in playoff_roster_ids)):
                    effective_match_type = "playoff"
                elif (consolation_roster_ids and
                      (sleeper_rid_1 in consolation_roster_ids or
                       sleeper_rid_2 in consolation_roster_ids)):
                    effective_match_type = "consolation"
                else:
                    effective_match_type = "playoff"  # Fallback

            # Get roster database IDs
            roster1 = await self._get_roster_by_roster_id(season_id, team1.get("roster_id"))
            roster2 = await self._get_roster_by_roster_id(season_id, team2.get("roster_id"))

            if not roster1 or not roster2:
                continue

            result = await self.db.execute(
                select(Matchup).where(
                    Matchup.season_id == season_id,
                    Matchup.week == week,
                    Matchup.matchup_id == matchup_id
                )
            )
            matchup = result.scalar_one_or_none()

            points1 = team1.get("points", 0) or 0
            points2 = team2.get("points", 0) or 0
            winner_id = roster1.id if points1 > points2 else (roster2.id if points2 > points1 else None)

            if matchup:
                matchup.home_points = points1
                matchup.away_points = points2
                matchup.winner_roster_id = winner_id
                matchup.match_type = effective_match_type
            else:
                matchup = Matchup(
                    season_id=season_id,
                    week=week,
                    matchup_id=matchup_id,
                    home_roster_id=roster1.id,
                    away_roster_id=roster2.id,
                    home_points=points1,
                    away_points=points2,
                    winner_roster_id=winner_id,
                    match_type=effective_match_type
                )
                self.db.add(matchup)

            # Flush to get matchup.id for player points
            await self.db.flush()

            # Store per-player points for both teams
            await self._sync_player_points(matchup, roster1, team1)
            await self._sync_player_points(matchup, roster2, team2)

    async def _get_roster_by_roster_id(self, season_id: int, roster_id: int):
        """Get roster by season and roster_id."""
        result = await self.db.execute(
            select(Roster).where(
                Roster.season_id == season_id,
                Roster.roster_id == roster_id
            )
        )
        return result.scalar_one_or_none()

    async def _sync_player_points(self, matchup: Matchup, roster: Roster,
                                   team_data: Dict[str, Any]):
        """Store per-player points for a team in a matchup."""
        players_points = team_data.get("players_points") or {}
        starters = set(team_data.get("starters") or [])

        if not players_points:
            return

        for player_id, points in players_points.items():
            # Check for existing record
            result = await self.db.execute(
                select(MatchupPlayerPoint).where(
                    MatchupPlayerPoint.matchup_id == matchup.id,
                    MatchupPlayerPoint.roster_id == roster.id,
                    MatchupPlayerPoint.player_id == str(player_id)
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.points = points or 0.0
                existing.is_starter = str(player_id) in starters
            else:
                self.db.add(MatchupPlayerPoint(
                    matchup_id=matchup.id,
                    roster_id=roster.id,
                    player_id=str(player_id),
                    points=points or 0.0,
                    is_starter=str(player_id) in starters,
                ))

    async def _sync_drafts(self, drafts_data: List[Dict[str, Any]], year: int):
        """Sync draft data."""
        # Get season
        result = await self.db.execute(
            select(Season).where(Season.year == year)
        )
        season = result.scalar_one_or_none()
        if not season:
            return

        for draft_data in drafts_data:
            draft_id = draft_data.get("draft_id")

            # Fetch full draft details to get slot_to_roster_id
            draft_detail = await self.client.get_draft(draft_id)
            slot_to_roster = draft_detail.get("slot_to_roster_id") or draft_data.get("draft_order") or {}

            result = await self.db.execute(
                select(Draft).where(Draft.id == draft_id)
            )
            draft = result.scalar_one_or_none()

            if draft:
                draft.status = draft_data.get("status")
                draft.settings = draft_data.get("settings", {})
                draft.draft_order = slot_to_roster
            else:
                draft = Draft(
                    id=draft_id,
                    season_id=season.id,
                    year=int(draft_data.get("season", year)),
                    type=draft_data.get("type"),
                    status=draft_data.get("status"),
                    rounds=draft_data.get("settings", {}).get("rounds"),
                    settings=draft_data.get("settings", {}),
                    draft_order=slot_to_roster
                )
                self.db.add(draft)

            # Sync draft picks
            await self._sync_draft_picks(draft_id)

        await self.db.flush()
        logger.info(f"Synced {len(drafts_data)} drafts")

    async def _sync_draft_picks(self, draft_id: str):
        """Sync picks for a specific draft."""
        picks_data = await self.client.get_draft_picks(draft_id)

        for pick_data in picks_data:
            pick_no = pick_data.get("pick_no")

            result = await self.db.execute(
                select(DraftPick).where(
                    DraftPick.draft_id == draft_id,
                    DraftPick.pick_no == pick_no
                )
            )
            pick = result.scalar_one_or_none()

            if pick:
                pick.player_id = pick_data.get("player_id")
                pick.pick_metadata = pick_data.get("metadata", {})
            else:
                pick = DraftPick(
                    draft_id=draft_id,
                    pick_no=pick_no,
                    round=pick_data.get("round"),
                    pick_in_round=pick_data.get("draft_slot"),
                    roster_id=pick_data.get("roster_id"),
                    player_id=pick_data.get("player_id"),
                    pick_metadata=pick_data.get("metadata", {})
                )
                self.db.add(pick)

    async def _sync_players(self, current_season_year: int):
        """Sync all NFL players (large dataset)."""
        logger.info("Starting player sync (this may take a while)...")

        players_data = await self.client.get_all_players()

        count = 0
        for player_id, player_data in players_data.items():
            # Only sync active players to reduce database size
            if player_data.get("active", False):
                result = await self.db.execute(
                    select(Player).where(Player.id == player_id)
                )
                player = result.scalar_one_or_none()

                full_name = f"{player_data.get('first_name', '')} {player_data.get('last_name', '')}".strip()

                # Compute rookie_year from years_exp
                years_exp = self._safe_int(player_data.get("years_exp"))
                rookie_year = (current_season_year - years_exp) if years_exp is not None else None

                if player:
                    player.first_name = player_data.get("first_name")
                    player.last_name = player_data.get("last_name")
                    player.full_name = full_name
                    player.position = player_data.get("position")
                    player.team = player_data.get("team")
                    player.number = player_data.get("number")
                    player.age = player_data.get("age")
                    player.status = player_data.get("status")
                    player.injury_status = player_data.get("injury_status")
                    player.years_exp = years_exp
                    player.rookie_year = rookie_year
                else:
                    player = Player(
                        id=player_id,
                        first_name=player_data.get("first_name"),
                        last_name=player_data.get("last_name"),
                        full_name=full_name,
                        position=player_data.get("position"),
                        team=player_data.get("team"),
                        number=self._safe_int(player_data.get("number")),
                        age=self._safe_int(player_data.get("age")),
                        height=player_data.get("height"),
                        weight=self._safe_int(player_data.get("weight")),
                        college=player_data.get("college"),
                        years_exp=years_exp,
                        rookie_year=rookie_year,
                        status=player_data.get("status"),
                        injury_status=player_data.get("injury_status")
                    )
                    self.db.add(player)

                count += 1

                # Commit in batches to avoid memory issues
                if count % 500 == 0:
                    await self.db.flush()
                    logger.info(f"Synced {count} players...")

        logger.info(f"Completed player sync: {count} players")

    async def _sync_season_awards(self, league_id: str, year: int):
        """Sync season awards (champion, division winners, consolation) from bracket data."""
        # Get season
        result = await self.db.execute(
            select(Season).where(Season.year == year)
        )
        season = result.scalar_one_or_none()
        if not season:
            logger.warning(f"Season {year} not found, skipping awards sync")
            return

        # Clear existing awards for this season to avoid duplicates on re-sync
        result = await self.db.execute(
            select(SeasonAward).where(SeasonAward.season_id == season.id)
        )
        existing_awards = result.scalars().all()
        for award in existing_awards:
            await self.db.delete(award)

        # Get rosters for roster_id -> user_id mapping
        result = await self.db.execute(
            select(Roster).where(Roster.season_id == season.id)
        )
        rosters = result.scalars().all()
        roster_to_user = {r.roster_id: r.user_id for r in rosters}

        # --- Champion from winners bracket ---
        try:
            winners_bracket = await self.client.get_winners_bracket(league_id)
            champion_roster_id = self._get_bracket_winner(winners_bracket)
            if champion_roster_id and champion_roster_id in roster_to_user:
                self.db.add(SeasonAward(
                    season_id=season.id,
                    user_id=roster_to_user[champion_roster_id],
                    award_type="champion",
                    roster_id=champion_roster_id,
                ))
        except Exception as e:
            logger.warning(f"Could not fetch winners bracket for {year}: {e}")

        # --- Consolation winner from losers bracket ---
        try:
            losers_bracket = await self.client.get_losers_bracket(league_id)
            consolation_roster_id = self._get_bracket_winner(losers_bracket)
            if consolation_roster_id and consolation_roster_id in roster_to_user:
                self.db.add(SeasonAward(
                    season_id=season.id,
                    user_id=roster_to_user[consolation_roster_id],
                    award_type="consolation",
                    roster_id=consolation_roster_id,
                ))
        except Exception as e:
            logger.warning(f"Could not fetch losers bracket for {year}: {e}")

        # --- Division winners from roster standings ---
        divisions: Dict[int, List[Roster]] = {}
        for roster in rosters:
            div = roster.division
            if div is not None:
                divisions.setdefault(div, []).append(roster)

        for div_num, div_rosters in divisions.items():
            # Best record: most wins, then most points_for as tiebreaker
            div_rosters.sort(key=lambda r: (r.wins or 0, r.points_for or 0), reverse=True)
            winner = div_rosters[0]
            if winner.user_id:
                self.db.add(SeasonAward(
                    season_id=season.id,
                    user_id=winner.user_id,
                    award_type="division_winner",
                    award_detail=f"Division {div_num}",
                    roster_id=winner.roster_id,
                    final_record=f"{winner.wins or 0}-{winner.losses or 0}-{winner.ties or 0}",
                    points_for=winner.points_for,
                ))

        logger.info(f"Synced season awards for {year}")

    async def _sync_transactions(self, league_id: str, year: int, through_week: int):
        """Sync transactions for a season."""
        result = await self.db.execute(
            select(Season).where(Season.year == year)
        )
        season = result.scalar_one_or_none()
        if not season:
            return

        count = 0
        for week in range(1, through_week + 1):
            try:
                txns_data = await self.client.get_transactions(week, league_id)
            except Exception as e:
                logger.warning(f"Could not fetch transactions for {year} week {week}: {e}")
                continue

            for txn_data in txns_data:
                txn_id = txn_data.get("transaction_id")
                if not txn_id:
                    continue

                result = await self.db.execute(
                    select(Transaction).where(Transaction.id == str(txn_id))
                )
                existing = result.scalar_one_or_none()

                txn_settings = txn_data.get("settings") or {}
                waiver_bid = txn_settings.get("waiver_bid")
                txn_metadata = txn_data.get("metadata") or {}
                metadata_notes = txn_metadata.get("notes")

                if existing:
                    existing.status = txn_data.get("status")
                    existing.adds = txn_data.get("adds")
                    existing.drops = txn_data.get("drops")
                    existing.picks = txn_data.get("draft_picks")
                    existing.settings = txn_settings
                    existing.waiver_bid = waiver_bid
                    existing.status_updated = txn_data.get("status_updated")
                    existing.metadata_notes = metadata_notes
                else:
                    self.db.add(Transaction(
                        id=str(txn_id),
                        season_id=season.id,
                        type=txn_data.get("type"),
                        status=txn_data.get("status"),
                        week=week,
                        roster_ids=txn_data.get("roster_ids"),
                        adds=txn_data.get("adds"),
                        drops=txn_data.get("drops"),
                        players=txn_data.get("players"),
                        picks=txn_data.get("draft_picks"),
                        settings=txn_settings,
                        waiver_bid=waiver_bid,
                        status_updated=txn_data.get("status_updated"),
                        metadata_notes=metadata_notes,
                    ))
                    count += 1

        await self.db.flush()
        logger.info(f"Synced {count} new transactions for {year}")

    @staticmethod
    def _get_bracket_winner(bracket: List[Dict[str, Any]]) -> int | None:
        """Find the winner of a bracket (champion or consolation champion).

        The championship/consolation final is the match in the highest round
        with p=1 (1st place match). The 'w' field is the winning roster_id.
        """
        if not bracket:
            return None

        max_round = max(m.get("r", 0) for m in bracket)
        # Find the 1st place match in the final round
        for match in bracket:
            if match.get("r") == max_round and match.get("p") == 1:
                return match.get("w")

        # Fallback: if no p=1 match, look for the only match in the final round
        final_matches = [m for m in bracket if m.get("r") == max_round]
        if len(final_matches) == 1:
            return final_matches[0].get("w")

        return None

