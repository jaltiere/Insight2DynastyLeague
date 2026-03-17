import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from anthropic import AsyncAnthropic
import json

from app.models.matchup import Matchup
from app.models.matchup_player_point import MatchupPlayerPoint
from app.models.matchup_recap import MatchupRecap
from app.models.roster import Roster
from app.models.user import User
from app.models.player import Player
from app.models.season import Season

logger = logging.getLogger(__name__)


class MatchupRecapService:
    """Service for generating AI-powered matchup recaps and predictions."""

    def __init__(self, db: AsyncSession, anthropic_api_key: str):
        """Initialize the recap service.

        Args:
            db: AsyncSession for database operations
            anthropic_api_key: API key for Claude API (empty string enables mock mode)
        """
        self.db = db
        self.mock_mode = not anthropic_api_key or anthropic_api_key == ""
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key) if anthropic_api_key and not self.mock_mode else None

        if self.mock_mode:
            logger.info("MatchupRecapService running in MOCK MODE - generating placeholder recaps")

    async def generate_weekly_recaps(self, season_id: int, week: int) -> int:
        """Generate recaps for all completed matchups in a week.

        Args:
            season_id: Season ID
            week: Week number

        Returns:
            Number of recaps generated
        """
        if not self.anthropic_client and not self.mock_mode:
            logger.warning("Anthropic API key not configured and not in mock mode, skipping recap generation")
            return 0

        mode_str = "MOCK MODE" if self.mock_mode else "API MODE"
        logger.info(f"Generating recaps for season {season_id}, week {week} ({mode_str})")

        # Fetch all matchups for the week
        result = await self.db.execute(
            select(Matchup)
            .where(and_(Matchup.season_id == season_id, Matchup.week == week))
        )
        matchups = result.scalars().all()

        if not matchups:
            logger.warning(f"No matchups found for season {season_id}, week {week}")
            return 0

        recap_count = 0
        for matchup in matchups:
            try:
                # Build context for this matchup
                context = await self._build_recap_context(matchup)

                # Generate recap using Claude API
                recap_text = await self._call_claude_api(
                    self._build_recap_prompt(context),
                    "recap"
                )

                # Store recap in database
                await self._store_recap(
                    matchup_id=matchup.id,
                    recap_text=recap_text,
                    recap_type="playoff" if matchup.match_type == "playoff" else "weekly",
                    week=week,
                    season_id=season_id,
                    metadata=context.get("metadata", {})
                )

                recap_count += 1
                logger.info(f"Generated recap for matchup {matchup.id}")

            except Exception as e:
                logger.error(f"Failed to generate recap for matchup {matchup.id}: {e}")
                # Continue with other matchups

        await self.db.commit()
        logger.info(f"Generated {recap_count} recaps for week {week}")
        return recap_count

    async def generate_current_week_predictions(
        self, season_id: int, week: int, regenerate: bool = False
    ) -> int:
        """Generate predictions for current week matchups.

        Args:
            season_id: Season ID
            week: Week number
            regenerate: If True, regenerate existing predictions

        Returns:
            Number of predictions generated
        """
        if not self.anthropic_client and not self.mock_mode:
            logger.warning("Anthropic API key not configured and not in mock mode, skipping prediction generation")
            return 0

        mode_str = "MOCK MODE" if self.mock_mode else "API MODE"
        logger.info(f"Generating predictions for season {season_id}, week {week} (regenerate={regenerate}) ({mode_str})")

        # Fetch current week matchups
        result = await self.db.execute(
            select(Matchup)
            .where(and_(Matchup.season_id == season_id, Matchup.week == week))
        )
        matchups = result.scalars().all()

        if not matchups:
            logger.warning(f"No matchups found for season {season_id}, week {week}")
            return 0

        prediction_count = 0
        for matchup in matchups:
            try:
                # Check if prediction already exists
                if not regenerate:
                    existing = await self.db.execute(
                        select(MatchupRecap).where(
                            and_(
                                MatchupRecap.matchup_id == matchup.id,
                                MatchupRecap.recap_type == "prediction"
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        logger.debug(f"Prediction already exists for matchup {matchup.id}, skipping")
                        continue

                # Build context for prediction
                context = await self._build_prediction_context(matchup)

                # Generate prediction using Claude API
                prediction_text = await self._call_claude_api(
                    self._build_prediction_prompt(context),
                    "prediction"
                )

                # Store or update prediction
                await self._store_recap(
                    matchup_id=matchup.id,
                    predictions_text=prediction_text,
                    recap_type="prediction",
                    week=week,
                    season_id=season_id,
                    metadata=context.get("metadata", {}),
                    update_if_exists=regenerate
                )

                prediction_count += 1
                logger.info(f"Generated prediction for matchup {matchup.id}")

            except Exception as e:
                logger.error(f"Failed to generate prediction for matchup {matchup.id}: {e}")
                # Continue with other matchups

        await self.db.commit()
        logger.info(f"Generated {prediction_count} predictions for week {week}")
        return prediction_count

    async def _build_recap_context(self, matchup: Matchup) -> Dict[str, Any]:
        """Build context dictionary for recap generation.

        Args:
            matchup: Matchup object

        Returns:
            Context dictionary with all data needed for prompt
        """
        # Get roster details
        home_roster, away_roster = await self._get_rosters(matchup)
        home_user, away_user = await self._get_users(home_roster, away_roster)

        # Determine winner and loser
        if matchup.winner_roster_id == matchup.home_roster_id:
            winner_name = home_user.display_name or home_user.username
            loser_name = away_user.display_name or away_user.username
            winner_score = matchup.home_points
            loser_score = matchup.away_points
            winner_roster = home_roster
            loser_roster = away_roster
        else:
            winner_name = away_user.display_name or away_user.username
            loser_name = home_user.display_name or home_user.username
            winner_score = matchup.away_points
            loser_score = matchup.home_points
            winner_roster = away_roster
            loser_roster = home_roster

        # Get top performers
        top_performers = await self._get_top_performers(matchup)

        # Get lineup mistakes
        lineup_mistakes = await self._identify_lineup_mistakes(matchup)

        # Get H2H history
        h2h_summary = await self._get_h2h_summary(home_user, away_user)

        # Calculate standings delta
        standings_delta = await self._calculate_standings_delta(matchup)

        context = {
            "winner": winner_name,
            "loser": loser_name,
            "winner_score": winner_score,
            "loser_score": loser_score,
            "week": matchup.week,
            "season": await self._get_season_year(matchup.season_id),
            "match_type": matchup.match_type,
            "top_performers": top_performers,
            "lineup_mistakes": lineup_mistakes,
            "h2h_summary": h2h_summary,
            "standings_delta": standings_delta,
            "metadata": {
                "home_team": home_user.display_name or home_user.username,
                "away_team": away_user.display_name or away_user.username,
                "home_score": matchup.home_points,
                "away_score": matchup.away_points,
                "h2h_history": h2h_summary,
                "standings_impact": standings_delta,
            }
        }

        return context

    async def _build_prediction_context(self, matchup: Matchup) -> Dict[str, Any]:
        """Build context dictionary for prediction generation.

        Args:
            matchup: Matchup object

        Returns:
            Context dictionary
        """
        # Get roster details
        home_roster, away_roster = await self._get_rosters(matchup)
        home_user, away_user = await self._get_users(home_roster, away_roster)

        # Get current records (wins-losses-ties)
        home_record = f"{home_roster.settings.get('wins', 0)}-{home_roster.settings.get('losses', 0)}-{home_roster.settings.get('ties', 0)}"
        away_record = f"{away_roster.settings.get('wins', 0)}-{away_roster.settings.get('losses', 0)}-{away_roster.settings.get('ties', 0)}"

        # Get H2H history
        h2h_summary = await self._get_h2h_summary(home_user, away_user)

        # Calculate projected scores (use max potential if available, otherwise estimate)
        home_projected = matchup.home_max_potential_points or 100.0
        away_projected = matchup.away_max_potential_points or 100.0

        # Get standings implications
        standings_implications = await self._calculate_prediction_implications(matchup, home_roster, away_roster)

        context = {
            "team1": home_user.display_name or home_user.username,
            "team2": away_user.display_name or away_user.username,
            "team1_record": home_record,
            "team2_record": away_record,
            "projected_score1": home_projected,
            "projected_score2": away_projected,
            "week": matchup.week,
            "season": await self._get_season_year(matchup.season_id),
            "h2h_summary": h2h_summary,
            "standings_implications": standings_implications,
            "metadata": {
                "home_team": home_user.display_name or home_user.username,
                "away_team": away_user.display_name or away_user.username,
                "home_record": home_record,
                "away_record": away_record,
                "projected_scores": {
                    "home": home_projected,
                    "away": away_projected
                },
                "h2h_history": h2h_summary,
            }
        }

        return context

    async def _call_claude_api(
        self, prompt: str, generation_type: str, max_retries: int = 3
    ) -> str:
        """Call Claude API with retry logic, or generate mock text if in mock mode.

        Args:
            prompt: Prompt to send to Claude
            generation_type: 'recap' or 'prediction' (for logging)
            max_retries: Maximum number of retry attempts

        Returns:
            Generated text from Claude or mock text
        """
        # Mock mode: Generate realistic placeholder text
        if self.mock_mode:
            logger.debug(f"Generating mock {generation_type}")
            return self._generate_mock_text(prompt, generation_type)

        # Real API mode
        for attempt in range(max_retries):
            try:
                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=200,  # Keep recaps concise
                    temperature=0.8,  # Add some personality
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                # Extract text from response
                generated_text = response.content[0].text
                return generated_text.strip()

            except Exception as e:
                logger.warning(f"Claude API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise

        raise Exception(f"Failed to generate {generation_type} after {max_retries} attempts")

    def _generate_mock_text(self, prompt: str, generation_type: str) -> str:
        """Generate mock/placeholder text for testing without API key.

        Args:
            prompt: The prompt (used to extract context)
            generation_type: 'recap' or 'prediction'

        Returns:
            Mock generated text
        """
        import random

        # Extract key info from prompt
        lines = prompt.split('\n')
        matchup_line = [l for l in lines if 'Matchup:' in l or 'vs' in l]
        matchup_info = matchup_line[0] if matchup_line else "Team A vs Team B"

        if generation_type == "recap":
            templates = [
                f"What a thriller! {matchup_info.split('Matchup:')[-1].strip()} in a hard-fought battle. The winner capitalized on some questionable lineup decisions by the opponent. This result shakes up the playoff race.",
                f"Dominant performance! {matchup_info.split('Matchup:')[-1].strip()}. Key players showed up when it mattered most, while the losing squad left points on the bench. Playoff implications are significant.",
                f"Close one! {matchup_info.split('Matchup:')[-1].strip()} came down to Monday night. Some lineup mistakes cost the loser dearly. The standings got a lot more interesting after this one.",
                f"Statement win! {matchup_info.split('Matchup:')[-1].strip()}. The victor rode strong performances from their stars while the opponent's bench outscored their starters. Division race heating up!",
            ]
            return random.choice(templates)
        else:  # prediction
            templates = [
                f"This matchup features {matchup_info.split('vs')[0].strip() if 'vs' in matchup_info else 'two competitive teams'}. Projected scores favor a close contest. Key players to watch on both sides. Could determine playoff seeding.",
                f"Intriguing clash between {matchup_info.split('vs')[0].strip() if 'vs' in matchup_info else 'these squads'}. The projections are tight. Both teams need this win for playoff positioning. Expect a nail-biter.",
                f"Battle of playoff hopefuls! {matchup_info}. Close projected scores suggest we're in for a competitive game. Division standings could shift significantly based on this result.",
                f"Must-win territory for both teams. {matchup_info}. Projections show a toss-up. Star performances will decide this one. Huge implications for the playoff race.",
            ]
            return random.choice(templates)

    def _build_recap_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for weekly recap generation."""
        return f"""You are a snarky fantasy football analyst writing a matchup recap for a dynasty league.

Matchup: {context['winner']} ({context['winner_score']:.2f} pts) defeated {context['loser']} ({context['loser_score']:.2f} pts)
Week {context['week']}, {context['season']} season, {context['match_type']} matchup

Head-to-Head History:
{context['h2h_summary']}

Top Performers:
{context['top_performers']}

Lineup Mistakes:
{context['lineup_mistakes']}

Standings Impact:
{context['standings_delta']}

Write 3-4 sentences: highlight the outcome, call out the biggest lineup mistake (if any), mention a standout player, and explain playoff implications. Be snarky and fun. Under 100 words."""

    def _build_prediction_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for matchup prediction generation."""
        return f"""You are previewing this week's matchup in a dynasty league.

Matchup: {context['team1']} vs {context['team2']}
Week {context['week']}, {context['season']} season

Head-to-Head History:
{context['h2h_summary']}

Current Records:
{context['team1']}: {context['team1_record']}
{context['team2']}: {context['team2_record']}

Projected Scores:
{context['team1']}: {context['projected_score1']:.2f} pts
{context['team2']}: {context['projected_score2']:.2f} pts

Standings Context:
{context['standings_implications']}

Write 2-3 sentences: predict the winner, highlight what's at stake (playoff positioning, division race). Keep it engaging. Under 75 words."""

    async def _store_recap(
        self,
        matchup_id: int,
        week: int,
        season_id: int,
        recap_type: str,
        recap_text: Optional[str] = None,
        predictions_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        update_if_exists: bool = False
    ):
        """Store or update a recap in the database."""
        if update_if_exists:
            # Try to update existing
            result = await self.db.execute(
                select(MatchupRecap).where(
                    and_(
                        MatchupRecap.matchup_id == matchup_id,
                        MatchupRecap.recap_type == recap_type
                    )
                )
            )
            existing_recap = result.scalar_one_or_none()

            if existing_recap:
                if recap_text:
                    existing_recap.recap_text = recap_text
                if predictions_text:
                    existing_recap.predictions_text = predictions_text
                existing_recap.recap_metadata = metadata
                existing_recap.generated_at = datetime.utcnow()
                return

        # Create new recap
        new_recap = MatchupRecap(
            matchup_id=matchup_id,
            recap_text=recap_text,
            predictions_text=predictions_text,
            week=week,
            season_id=season_id,
            recap_type=recap_type,
            recap_metadata=metadata
        )
        self.db.add(new_recap)

    async def _get_rosters(self, matchup: Matchup) -> Tuple[Roster, Roster]:
        """Get home and away rosters for a matchup."""
        home_result = await self.db.execute(
            select(Roster).where(Roster.id == matchup.home_roster_id)
        )
        away_result = await self.db.execute(
            select(Roster).where(Roster.id == matchup.away_roster_id)
        )
        return home_result.scalar_one(), away_result.scalar_one()

    async def _get_users(self, home_roster: Roster, away_roster: Roster) -> Tuple[User, User]:
        """Get users for home and away rosters."""
        home_user_result = await self.db.execute(
            select(User).where(User.user_id == home_roster.owner_id)
        )
        away_user_result = await self.db.execute(
            select(User).where(User.user_id == away_roster.owner_id)
        )
        return home_user_result.scalar_one(), away_user_result.scalar_one()

    async def _get_season_year(self, season_id: int) -> int:
        """Get season year from season_id."""
        result = await self.db.execute(
            select(Season.year).where(Season.id == season_id)
        )
        return result.scalar_one()

    async def _get_top_performers(self, matchup: Matchup) -> str:
        """Get top 3 scoring players from the matchup."""
        result = await self.db.execute(
            select(MatchupPlayerPoint, Player)
            .join(Player, Player.player_id == MatchupPlayerPoint.player_id, isouter=True)
            .where(MatchupPlayerPoint.matchup_id == matchup.id)
            .order_by(MatchupPlayerPoint.points.desc())
            .limit(3)
        )

        performers = result.all()
        if not performers:
            return "No player data available"

        lines = []
        for mpp, player in performers:
            player_name = player.full_name if player else f"Player {mpp.player_id}"
            lines.append(f"- {player_name}: {mpp.points:.2f} pts")

        return "\n".join(lines)

    async def _identify_lineup_mistakes(self, matchup: Matchup) -> str:
        """Identify bench players who outscored starters."""
        # Get all player points for this matchup
        result = await self.db.execute(
            select(MatchupPlayerPoint, Player)
            .join(Player, Player.player_id == MatchupPlayerPoint.player_id, isouter=True)
            .where(MatchupPlayerPoint.matchup_id == matchup.id)
            .order_by(MatchupPlayerPoint.roster_id, MatchupPlayerPoint.points.desc())
        )

        all_players = result.all()

        # Group by roster
        rosters_players = {}
        for mpp, player in all_players:
            if mpp.roster_id not in rosters_players:
                rosters_players[mpp.roster_id] = {"starters": [], "bench": []}

            player_name = player.full_name if player else f"Player {mpp.player_id}"
            player_position = player.position if player else "UNKNOWN"

            if mpp.is_starter:
                rosters_players[mpp.roster_id]["starters"].append((player_name, player_position, mpp.points))
            else:
                rosters_players[mpp.roster_id]["bench"].append((player_name, player_position, mpp.points))

        # Find biggest mistakes (bench > starter at same position)
        mistakes = []
        for roster_id, players in rosters_players.items():
            for bench_player, bench_pos, bench_points in players["bench"]:
                for starter_name, starter_pos, starter_points in players["starters"]:
                    if bench_pos == starter_pos and bench_points > starter_points:
                        mistakes.append(
                            f"Started {starter_name} ({starter_points:.2f} pts), benched {bench_player} ({bench_points:.2f} pts)"
                        )
                        break  # Only report worst mistake per bench player

        if not mistakes:
            return "No significant lineup mistakes"

        # Return top 2 mistakes
        return "\n".join(mistakes[:2])

    async def _get_h2h_summary(self, user1: User, user2: User) -> str:
        """Get head-to-head history summary between two users."""
        # Query all matchups between these two users
        result = await self.db.execute(
            select(Matchup)
            .join(Roster, Matchup.home_roster_id == Roster.id)
            .where(
                and_(
                    Roster.owner_id.in_([user1.user_id, user2.user_id]),
                    Matchup.away_roster_id.in_(
                        select(Roster.id).where(Roster.owner_id.in_([user1.user_id, user2.user_id]))
                    )
                )
            )
        )

        matchups = result.scalars().all()

        if not matchups:
            return "First meeting between these teams"

        user1_wins = sum(1 for m in matchups if m.winner_roster_id and await self._is_roster_owner(m.winner_roster_id, user1.user_id))
        user2_wins = len(matchups) - user1_wins

        user1_name = user1.display_name or user1.username
        user2_name = user2.display_name or user2.username

        return f"{len(matchups)} previous meetings, series {user1_name} leads {user1_wins}-{user2_wins}"

    async def _is_roster_owner(self, roster_id: int, user_id: str) -> bool:
        """Check if a roster belongs to a user."""
        result = await self.db.execute(
            select(Roster.owner_id).where(Roster.id == roster_id)
        )
        owner_id = result.scalar_one_or_none()
        return owner_id == user_id

    async def _calculate_standings_delta(self, matchup: Matchup) -> str:
        """Calculate how this matchup affected standings."""
        # Simplified version - would need full standings calculation
        return "Standings impact calculation not yet implemented"

    async def _calculate_prediction_implications(
        self, matchup: Matchup, home_roster: Roster, away_roster: Roster
    ) -> str:
        """Calculate what's at stake for predictions."""
        # Simplified version
        home_wins = home_roster.settings.get('wins', 0)
        away_wins = away_roster.settings.get('wins', 0)

        if home_wins >= 6 or away_wins >= 6:
            return "Playoff positioning on the line"
        elif home_wins <= 2 or away_wins <= 2:
            return "Battle to avoid bottom of standings"
        else:
            return "Mid-pack battle for playoff positioning"
