from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.routes import (
    standings, players, owners, matchups, drafts, league_history,
    sync, player_records, rookie_records, taxi_squads, seasons,
    transactions, trade_grades, draft_grades, playoffs, power_rankings,
    matchup_recaps, newsletter, roster_analysis, trade_calculator,
    draft_picks, team_records, free_agents, search, leagues,
)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Fantasy Football Dynasty League API integrating with Sleeper",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global routes (no league scope)
app.include_router(leagues.router, prefix="/api", tags=["Leagues"])
app.include_router(sync.router, prefix="/api", tags=["Sync"])
app.include_router(players.router, prefix="/api", tags=["Players"])

# League-scoped routes — all live under /api/{league_slug}/...
_LEAGUE_PREFIX = "/api/{league_slug}"

app.include_router(standings.router, prefix=_LEAGUE_PREFIX, tags=["Standings"])
app.include_router(owners.router, prefix=_LEAGUE_PREFIX, tags=["Owners"])
app.include_router(matchups.router, prefix=_LEAGUE_PREFIX, tags=["Matchups"])
app.include_router(drafts.router, prefix=_LEAGUE_PREFIX, tags=["Drafts"])
app.include_router(league_history.router, prefix=_LEAGUE_PREFIX, tags=["League History"])
app.include_router(player_records.router, prefix=_LEAGUE_PREFIX, tags=["Player Records"])
app.include_router(rookie_records.router, prefix=_LEAGUE_PREFIX, tags=["Rookie Records"])
app.include_router(taxi_squads.router, prefix=_LEAGUE_PREFIX, tags=["Taxi Squads"])
app.include_router(seasons.router, prefix=_LEAGUE_PREFIX, tags=["Seasons"])
app.include_router(transactions.router, prefix=_LEAGUE_PREFIX, tags=["Transactions"])
app.include_router(trade_grades.router, prefix=_LEAGUE_PREFIX, tags=["Trade Grades"])
app.include_router(draft_grades.router, prefix=_LEAGUE_PREFIX, tags=["Draft Grades"])
app.include_router(playoffs.router, prefix=_LEAGUE_PREFIX, tags=["Playoffs"])
app.include_router(power_rankings.router, prefix=_LEAGUE_PREFIX, tags=["Power Rankings"])
app.include_router(matchup_recaps.router, prefix=_LEAGUE_PREFIX, tags=["Matchup Recaps"])
app.include_router(newsletter.router, prefix=_LEAGUE_PREFIX, tags=["Newsletter"])
app.include_router(roster_analysis.router, prefix=_LEAGUE_PREFIX, tags=["Roster Analysis"])
app.include_router(trade_calculator.router, prefix=_LEAGUE_PREFIX, tags=["Trade Calculator"])
app.include_router(draft_picks.router, prefix=_LEAGUE_PREFIX, tags=["Draft Picks"])
app.include_router(team_records.router, prefix=_LEAGUE_PREFIX, tags=["Team Records"])
app.include_router(free_agents.router, prefix=_LEAGUE_PREFIX, tags=["Free Agents"])
app.include_router(search.router, prefix=_LEAGUE_PREFIX, tags=["Search"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Insight2Dynasty API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint for Railway and monitoring."""
    return {
        "status": "healthy",
        "service": "Insight2Dynasty API",
        "version": settings.APP_VERSION
    }
