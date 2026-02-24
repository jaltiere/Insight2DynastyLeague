from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.routes import standings, players, owners, matchups, drafts, league_history, sync, player_records, rookie_records, taxi_squads, seasons, transactions

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

# Include routers
app.include_router(standings.router, prefix="/api", tags=["Standings"])
app.include_router(players.router, prefix="/api", tags=["Players"])
app.include_router(owners.router, prefix="/api", tags=["Owners"])
app.include_router(matchups.router, prefix="/api", tags=["Matchups"])
app.include_router(drafts.router, prefix="/api", tags=["Drafts"])
app.include_router(league_history.router, prefix="/api", tags=["League History"])
app.include_router(sync.router, prefix="/api", tags=["Sync"])
app.include_router(player_records.router, prefix="/api", tags=["Player Records"])
app.include_router(rookie_records.router, prefix="/api", tags=["Rookie Records"])
app.include_router(taxi_squads.router, prefix="/api", tags=["Taxi Squads"])
app.include_router(seasons.router, prefix="/api", tags=["Seasons"])
app.include_router(transactions.router, prefix="/api", tags=["Transactions"])


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
