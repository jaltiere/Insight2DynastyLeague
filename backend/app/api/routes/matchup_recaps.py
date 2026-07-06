from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from app.database import get_db
from app.api.deps import get_league_id, get_league_config, verify_cron_secret
from app.services.sleeper_client import sleeper_client
from app.models.matchup_recap import MatchupRecap
from app.models.matchup import Matchup
from app.models.roster import Roster
from app.models.user import User
from app.models.season import Season
from app.schemas.matchup_recap import (
    MatchupRecapResponse,
    WeekRecapsResponse,
    CurrentWeekMatchupsResponse,
    NewsletterRecapResponse
)
from app.services.matchup_recap_service import MatchupRecapService
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/matchup-recaps/current", response_model=CurrentWeekMatchupsResponse)
async def get_current_week_matchups(
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current week matchups with predictions."""
    # Get current NFL state to determine current week
    nfl_state = await sleeper_client.get_nfl_state()
    current_week = nfl_state.get("week", 1)
    current_season = int(nfl_state.get("season", 2024))
    season_type = nfl_state.get("season_type", "regular")

    # Handle offseason - return empty matchups
    if season_type == "off" or current_week == 0:
        return CurrentWeekMatchupsResponse(
            week=0,
            season=current_season,
            matchups=[]
        )

    # Get current season from database
    result = await db.execute(
        select(Season)
        .where(Season.year == current_season, Season.group_id == league_id)
        .order_by(Season.id.desc())
    )
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail="Current season not found")

    # Get matchups for current week
    result = await db.execute(
        select(Matchup).where(
            and_(Matchup.season_id == season.id, Matchup.week == current_week)
        )
    )
    matchups = result.scalars().all()

    # Get recaps for these matchups
    matchup_responses = []
    for matchup in matchups:
        recap_response = await _build_matchup_recap_response(matchup, "prediction", db)
        matchup_responses.append(recap_response)

    return CurrentWeekMatchupsResponse(
        week=current_week,
        season=current_season,
        matchups=matchup_responses
    )


@router.get("/matchup-recaps/previous", response_model=WeekRecapsResponse)
async def get_previous_week_recaps(
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get previous week matchups with recaps."""
    # Get current NFL state
    nfl_state = await sleeper_client.get_nfl_state()
    current_week = nfl_state.get("week", 1)
    current_season = int(nfl_state.get("season", 2024))
    season_type = nfl_state.get("season_type", "regular")

    # Handle offseason - show championship week from previous season
    if season_type == "off" or current_week == 0:
        # Get most recent completed season
        result = await db.execute(
            select(Season)
            .where(Season.year == current_season - 1, Season.group_id == league_id)
            .order_by(Season.id.desc())
        )
        season = result.scalar_one_or_none()

        if not season:
            return WeekRecapsResponse(week=0, season=current_season, recaps=[])

        # Get the last week of matchups from that season
        result = await db.execute(
            select(Matchup).where(Matchup.season_id == season.id).order_by(Matchup.week.desc()).limit(6)
        )
        matchups = result.scalars().all()

        if not matchups:
            return WeekRecapsResponse(week=0, season=current_season - 1, recaps=[])

        last_week = matchups[0].week if matchups else 0

        # Get all matchups from that week
        result = await db.execute(
            select(Matchup).where(
                and_(Matchup.season_id == season.id, Matchup.week == last_week)
            )
        )
        matchups = result.scalars().all()

        recap_responses = []
        for matchup in matchups:
            recap_response = await _build_matchup_recap_response(
                matchup,
                "playoff" if matchup.match_type == "playoff" else "weekly",
                db
            )
            recap_responses.append(recap_response)

        return WeekRecapsResponse(
            week=last_week,
            season=current_season - 1,
            recaps=recap_responses
        )

    if current_week < 2:
        # No previous week
        return WeekRecapsResponse(week=0, season=current_season, recaps=[])

    previous_week = current_week - 1

    # Get current season from database
    result = await db.execute(
        select(Season)
        .where(Season.year == current_season, Season.group_id == league_id)
        .order_by(Season.id.desc())
    )
    season = result.scalar_one_or_none()

    if not season:
        raise HTTPException(status_code=404, detail="Current season not found")

    # Get matchups for previous week
    result = await db.execute(
        select(Matchup).where(
            and_(Matchup.season_id == season.id, Matchup.week == previous_week)
        )
    )
    matchups = result.scalars().all()

    # Get recaps for these matchups
    recap_responses = []
    for matchup in matchups:
        recap_response = await _build_matchup_recap_response(
            matchup,
            "playoff" if matchup.match_type == "playoff" else "weekly",
            db
        )
        recap_responses.append(recap_response)

    return WeekRecapsResponse(
        week=previous_week,
        season=current_season,
        recaps=recap_responses
    )


@router.get("/matchup-recaps/week/{week}", response_model=WeekRecapsResponse)
async def get_week_recaps(
    week: int,
    season: Optional[int] = None,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get recaps for a specific week."""
    # Determine season
    if season is None:
        nfl_state = await sleeper_client.get_nfl_state()
        season = int(nfl_state.get("season"))

    # Get season from database
    result = await db.execute(
        select(Season)
        .where(Season.year == season, Season.group_id == league_id)
        .order_by(Season.id.desc())
    )
    season_obj = result.scalar_one_or_none()

    if not season_obj:
        raise HTTPException(status_code=404, detail="Season not found")

    # Get matchups for week
    result = await db.execute(
        select(Matchup).where(
            and_(Matchup.season_id == season_obj.id, Matchup.week == week)
        )
    )
    matchups = result.scalars().all()

    # Get recaps
    recap_responses = []
    for matchup in matchups:
        recap_response = await _build_matchup_recap_response(
            matchup,
            "playoff" if matchup.match_type == "playoff" else "weekly",
            db
        )
        recap_responses.append(recap_response)

    return WeekRecapsResponse(
        week=week,
        season=season,
        recaps=recap_responses
    )


@router.get("/matchup-recaps/newsletter/{week}", response_model=NewsletterRecapResponse)
async def get_newsletter_recaps(
    week: int,
    season: Optional[int] = None,
    league_id: str = Depends(get_league_id),
    db: AsyncSession = Depends(get_db),
):
    """Get recaps formatted for newsletter inclusion."""
    # Get season
    if season is None:
        nfl_state = await sleeper_client.get_nfl_state()
        season = int(nfl_state.get("season"))

    # Get previous week recaps
    previous_week_result = await db.execute(
        select(Season)
        .where(Season.year == season, Season.group_id == league_id)
        .order_by(Season.id.desc())
    )
    season_obj = previous_week_result.scalar_one_or_none()

    if not season_obj:
        raise HTTPException(status_code=404, detail="Season not found")

    # Get completed matchups (week - 1)
    completed_result = await db.execute(
        select(Matchup).where(
            and_(Matchup.season_id == season_obj.id, Matchup.week == week - 1)
        )
    )
    completed_matchups = completed_result.scalars().all()

    # Get upcoming matchups (week)
    upcoming_result = await db.execute(
        select(Matchup).where(
            and_(Matchup.season_id == season_obj.id, Matchup.week == week)
        )
    )
    upcoming_matchups = upcoming_result.scalars().all()

    # Build responses
    completed_responses = []
    for matchup in completed_matchups:
        recap_response = await _build_matchup_recap_response(
            matchup,
            "playoff" if matchup.match_type == "playoff" else "weekly",
            db
        )
        completed_responses.append(recap_response)

    upcoming_responses = []
    for matchup in upcoming_matchups:
        recap_response = await _build_matchup_recap_response(matchup, "prediction", db)
        upcoming_responses.append(recap_response)

    return NewsletterRecapResponse(
        week=week,
        season=season,
        completed_matchups=completed_responses,
        upcoming_matchups=upcoming_responses,
        summary=f"Week {week} Newsletter"
    )


@router.post("/matchup-recaps/regenerate/{week}", dependencies=[Depends(verify_cron_secret)])
async def regenerate_recaps(
    week: int,
    season: Optional[int] = None,
    force: bool = Query(False, description="Force regeneration even during offseason"),
    league_id: str = Depends(get_league_id),
    league_config: dict = Depends(get_league_config),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to regenerate recaps for a week (requires CRON_SECRET)."""
    # Block if recaps are disabled for this league
    if not league_config.get("recaps_enabled", False):
        return {
            "status": "skipped",
            "message": f"Recaps are disabled for this league.",
            "week": week,
            "season": season,
        }

    # Get NFL state to check season status
    nfl_state = await sleeper_client.get_nfl_state()
    season_type = nfl_state.get("season_type", "regular")
    current_week = nfl_state.get("week", 0)

    # Block recap regeneration during offseason unless forced
    if not force and (season_type == "off" or current_week == 0):
        return {
            "status": "skipped",
            "message": "Recap generation skipped - NFL is in offseason. Use ?force=true to override.",
            "week": week,
            "season": season
        }

    # Get season
    if season is None:
        season = int(nfl_state.get("season"))

    result = await db.execute(
        select(Season)
        .where(Season.year == season, Season.group_id == league_id)
        .order_by(Season.id.desc())
    )
    season_obj = result.scalar_one_or_none()

    if not season_obj:
        raise HTTPException(status_code=404, detail="Season not found")

    # Regenerate recaps
    recap_service = MatchupRecapService(db, settings.ANTHROPIC_API_KEY)
    recap_count = await recap_service.generate_weekly_recaps(season_obj.id, week)

    return {
        "status": "success",
        "message": f"Regenerated {recap_count} recaps for week {week}",
        "week": week,
        "season": season
    }


@router.post("/matchup-recaps/regenerate-predictions/{week}", dependencies=[Depends(verify_cron_secret)])
async def regenerate_predictions(
    week: int,
    season: Optional[int] = None,
    regenerate: bool = Query(True, description="Force regenerate existing predictions"),
    force: bool = Query(False, description="Force generation even during offseason"),
    league_id: str = Depends(get_league_id),
    league_config: dict = Depends(get_league_config),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to regenerate predictions for upcoming week (requires CRON_SECRET)."""
    # Block if recaps are disabled for this league
    if not league_config.get("recaps_enabled", False):
        return {
            "status": "skipped",
            "message": f"Recaps are disabled for this league.",
            "week": week,
            "season": season,
        }

    # Get NFL state to check season status
    nfl_state = await sleeper_client.get_nfl_state()
    season_type = nfl_state.get("season_type", "regular")
    current_week = nfl_state.get("week", 0)

    # Block prediction regeneration during offseason unless forced
    if not force and (season_type == "off" or current_week == 0):
        return {
            "status": "skipped",
            "message": "Prediction generation skipped - NFL is in offseason. Use ?force=true to override.",
            "week": week,
            "season": season
        }

    # Get season
    if season is None:
        season = int(nfl_state.get("season"))

    result = await db.execute(
        select(Season)
        .where(Season.year == season, Season.group_id == league_id)
        .order_by(Season.id.desc())
    )
    season_obj = result.scalar_one_or_none()

    if not season_obj:
        raise HTTPException(status_code=404, detail="Season not found")

    # Generate predictions
    recap_service = MatchupRecapService(db, settings.ANTHROPIC_API_KEY)
    prediction_count = await recap_service.generate_current_week_predictions(
        season_obj.id, week, regenerate=regenerate
    )

    return {
        "status": "success",
        "message": f"Generated {prediction_count} predictions for week {week}",
        "week": week,
        "season": season
    }


async def _build_matchup_recap_response(
    matchup: Matchup,
    recap_type: str,
    db: AsyncSession
) -> MatchupRecapResponse:
    """Build a MatchupRecapResponse from a matchup and its recap."""

    async def _team_name(roster_db_id: int) -> str:
        """Resolve a display name, tolerating missing rosters/owners.

        Sleeper allows ownerless rosters (user_id NULL), so a strict
        scalar_one() here would 500 the whole recap page.
        """
        roster_result = await db.execute(
            select(Roster).where(Roster.id == roster_db_id)
        )
        roster = roster_result.scalar_one_or_none()
        if not roster:
            return "Unknown Team"

        user = None
        if roster.user_id:
            user_result = await db.execute(
                select(User).where(User.id == roster.user_id)
            )
            user = user_result.scalar_one_or_none()

        if user:
            return user.display_name or user.username
        return roster.team_name or "Unknown Team"

    home_team = await _team_name(matchup.home_roster_id)
    away_team = await _team_name(matchup.away_roster_id)

    # Get recap
    recap_result = await db.execute(
        select(MatchupRecap).where(
            and_(
                MatchupRecap.matchup_id == matchup.id,
                MatchupRecap.recap_type == recap_type
            )
        )
    )
    recap = recap_result.scalar_one_or_none()

    # Get season year
    season_result = await db.execute(
        select(Season.year).where(Season.id == matchup.season_id)
    )
    season_year = season_result.scalar_one()

    # Build metadata with match type info
    metadata = recap.recap_metadata if recap else {}
    if metadata is None:
        metadata = {}

    # Add playoff bracket information
    metadata['match_type'] = matchup.match_type
    if matchup.week >= 17:
        # Determine playoff bracket position based on match_type and matchup_id
        if matchup.match_type == 'playoff':
            if matchup.matchup_id == 1:
                metadata['bracket_label'] = '🏆 Championship'
            elif matchup.matchup_id == 2:
                metadata['bracket_label'] = '🥉 3rd Place'
        elif matchup.match_type == 'consolation':
            # Consolation games have higher matchup_ids (4, 5, etc.)
            if matchup.matchup_id == 4:
                metadata['bracket_label'] = '🎖️ Consolation Championship'
            elif matchup.matchup_id == 5:
                metadata['bracket_label'] = '🎯 9th Place'

    return MatchupRecapResponse(
        matchup_id=matchup.id,
        week=matchup.week,
        season=season_year,
        home_team=home_team,
        away_team=away_team,
        home_score=matchup.home_points,
        away_score=matchup.away_points,
        recap_text=recap.recap_text if recap else None,
        predictions_text=recap.predictions_text if recap else None,
        recap_type=recap_type,
        recap_metadata=metadata,
        generated_at=recap.generated_at if recap else None
    )
