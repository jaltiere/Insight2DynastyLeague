import os

# Set test DATABASE_URL before any app modules are imported
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

import pytest
from typing import AsyncGenerator
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.main import app
from app.models import (
    League, User, Season, Roster, Matchup, Player,
    Draft, DraftPick, SeasonAward,
)


@pytest.fixture(scope="session")
def engine():
    """Create a single async engine for all tests (SQLite in-memory)."""
    eng = create_async_engine("sqlite+aiosqlite://", echo=False)

    # Enable foreign key enforcement in SQLite
    @event.listens_for(eng.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return eng


@pytest.fixture(autouse=True)
async def tables(engine):
    """Create all tables before each test, drop after for isolation."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for tests."""
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create an httpx AsyncClient with the FastAPI app using the test DB."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Factory functions – create test data with sensible defaults
# ---------------------------------------------------------------------------

async def create_league(db: AsyncSession, **overrides) -> League:
    defaults = {
        "id": "test_league_001",
        "name": "Test Dynasty League",
        "sport": "nfl",
        "season": "2024",
        "status": "in_season",
        "settings": {},
        "scoring_settings": {},
        "roster_positions": [],
    }
    defaults.update(overrides)
    league = League(**defaults)
    db.add(league)
    await db.flush()
    return league


async def create_user(db: AsyncSession, **overrides) -> User:
    defaults = {
        "id": "user_001",
        "username": "testuser",
        "display_name": "Test User",
        "avatar": "avatar_123",
        "is_active": True,
    }
    defaults.update(overrides)
    user = User(**defaults)
    db.add(user)
    await db.flush()
    return user


async def create_season(db: AsyncSession, league: League, **overrides) -> Season:
    defaults = {
        "league_id": league.id,
        "year": 2024,
        "num_divisions": 2,
        "playoff_structure": {},
        "regular_season_weeks": 14,
        "playoff_weeks": 3,
    }
    defaults.update(overrides)
    season = Season(**defaults)
    db.add(season)
    await db.flush()
    return season


async def create_roster(
    db: AsyncSession, season: Season, user: User, **overrides
) -> Roster:
    defaults = {
        "roster_id": 1,
        "season_id": season.id,
        "user_id": user.id,
        "team_name": "Test Team",
        "division": 1,
        "wins": 10,
        "losses": 4,
        "ties": 0,
        "points_for": 1500,
        "points_against": 1200,
        "players": [],
        "starters": [],
        "reserve": [],
        "taxi": [],
        "settings": {},
    }
    defaults.update(overrides)
    roster = Roster(**defaults)
    db.add(roster)
    await db.flush()
    return roster


async def create_matchup(
    db: AsyncSession,
    season: Season,
    home_roster: Roster,
    away_roster: Roster,
    **overrides,
) -> Matchup:
    defaults = {
        "season_id": season.id,
        "week": 1,
        "matchup_id": 1,
        "home_roster_id": home_roster.id,
        "away_roster_id": away_roster.id,
        "home_points": 120.5,
        "away_points": 110.3,
        "winner_roster_id": home_roster.id,
    }
    defaults.update(overrides)
    matchup = Matchup(**defaults)
    db.add(matchup)
    await db.flush()
    return matchup


async def create_player(db: AsyncSession, **overrides) -> Player:
    defaults = {
        "id": "player_001",
        "first_name": "Patrick",
        "last_name": "Mahomes",
        "full_name": "Patrick Mahomes",
        "position": "QB",
        "team": "KC",
        "number": 15,
        "age": 28,
        "height": "6'3\"",
        "weight": 225,
        "college": "Texas Tech",
        "years_exp": 7,
        "status": "Active",
        "injury_status": None,
        "stats": {},
    }
    defaults.update(overrides)
    player = Player(**defaults)
    db.add(player)
    await db.flush()
    return player


async def create_draft(db: AsyncSession, season: Season, **overrides) -> Draft:
    defaults = {
        "id": "draft_001",
        "season_id": season.id,
        "year": season.year,
        "type": "snake",
        "status": "complete",
        "rounds": 4,
        "settings": {},
        "draft_order": {},
    }
    defaults.update(overrides)
    draft = Draft(**defaults)
    db.add(draft)
    await db.flush()
    return draft


async def create_draft_pick(db: AsyncSession, draft: Draft, **overrides) -> DraftPick:
    defaults = {
        "draft_id": draft.id,
        "pick_no": 1,
        "round": 1,
        "pick_in_round": 1,
        "roster_id": 1,
        "player_id": None,
        "pick_metadata": {},
    }
    defaults.update(overrides)
    pick = DraftPick(**defaults)
    db.add(pick)
    await db.flush()
    return pick


async def create_season_award(
    db: AsyncSession, season: Season, user: User, **overrides
) -> SeasonAward:
    defaults = {
        "season_id": season.id,
        "user_id": user.id,
        "award_type": "champion",
        "award_detail": None,
        "roster_id": 1,
        "final_record": "12-2-0",
        "points_for": 1800,
    }
    defaults.update(overrides)
    award = SeasonAward(**defaults)
    db.add(award)
    await db.flush()
    return award
