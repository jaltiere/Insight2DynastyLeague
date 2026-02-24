# Insight2Dynasty

A modern fantasy football dynasty league website integrating with the Sleeper platform.

## Features

- **Current Standings** - Real-time league standings and playoff brackets
- **Player Statistics** - Comprehensive searchable player database
- **Head-to-Head History** - Owner vs owner matchup records
- **Owner Records** - Historical performance and season breakdowns
- **Draft Results** - Year-by-year draft boards with all picks
- **League History** - Champions, division winners, and consolation bracket winners

## Tech Stack

### Frontend
- React 18 + Vite + TypeScript
- Tailwind CSS
- React Query
- React Router v6

### Backend
- FastAPI (Python 3.11+)
- SQLAlchemy 2.0
- MySQL 8.0+
- Alembic (migrations)

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Insight2DynastyLeague
   ```

2. **Start MySQL database**
   ```bash
   docker-compose up -d
   ```

3. **Set up Backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

   # Copy environment template and configure
   cp .env.example .env
   # Edit .env with your settings

   # Run migrations
   alembic upgrade head

   # Start the server
   uvicorn app.main:app --reload
   ```

4. **Set up Frontend**
   ```bash
   cd frontend
   npm install

   # Copy environment template
   cp .env.example .env

   # Start dev server
   npm run dev
   ```

5. **Sync data from Sleeper**
   ```bash
   curl -X POST http://localhost:8000/api/sync/league
   ```

6. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Project Structure

```
Insight2DynastyLeague/
├── frontend/          # React + Vite application
├── backend/           # FastAPI application
├── docker-compose.yml # MySQL setup
├── CLAUDE.md         # Development guidelines
└── README.md         # This file
```

## Server Management

### Starting the Servers

**MySQL database:**
```bash
docker-compose up -d
```

**Backend (FastAPI):**
```bash
cd backend
# Activate virtual environment first
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

uvicorn app.main:app --reload
```
The backend runs at http://localhost:8000. The `--reload` flag enables auto-restart on code changes.

**Frontend (Vite):**
```bash
cd frontend
npm run dev
```
The frontend runs at http://localhost:5173.

### Restarting Servers

- **Backend**: Press `Ctrl+C` in the terminal running uvicorn, then re-run `uvicorn app.main:app --reload`
- **Frontend**: Press `Ctrl+C` in the terminal running Vite, then re-run `npm run dev`
- **MySQL**: `docker-compose down && docker-compose up -d`

## Database Migrations

Migrations are managed with Alembic from the `backend/` directory.

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Check current migration version
alembic current

# View migration history
alembic history

# Create a new migration after model changes
alembic revision --autogenerate -m "Description of changes"

# Roll back the last migration
alembic downgrade -1

# Roll back all migrations
alembic downgrade base
```

Always run `alembic upgrade head` after pulling new code that includes migration files.

## Data Sync from Sleeper

The app syncs data from the Sleeper API into the local MySQL database. The backend server must be running for all sync commands.

### Weekly Sync (During the Season)

Run this once per week after games are completed to update matchup results, rosters, transactions, and standings:

```bash
curl -X POST http://localhost:8000/api/sync/league
```

Or visit http://localhost:8000/docs and use the interactive Swagger UI to trigger the `/api/sync/league` endpoint.

**What it syncs:**
- League configuration and settings
- Users (owners)
- Current season data
- Rosters (current player assignments)
- Matchups (all weeks with scores)
- Drafts and draft picks
- NFL player data
- Transactions (trades, waivers, free agent adds/drops)

**Recommended schedule during the season:**
- Run after Tuesday waivers clear each week to capture final scores and transactions
- Can be run multiple times safely — it upserts (inserts or updates) all data

### New Season / League Rollover

When the Sleeper league rolls over to a new season (typically after the NFL draft in late April/early May), Sleeper creates a new league ID that is linked to the previous season. To pick up the new season:

1. **Sync current league data** — the sync automatically follows the league chain, so no config change is needed:
   ```bash
   curl -X POST http://localhost:8000/api/sync/league
   ```

2. **If the league ID has changed** (check Sleeper), update `SLEEPER_LEAGUE_ID` in `backend/.env`:
   ```
   SLEEPER_LEAGUE_ID=<new_league_id>
   ```
   Then restart the backend server and re-run the sync.

3. **Sync full history** to backfill any gaps or to re-sync all historical seasons:
   ```bash
   curl -X POST http://localhost:8000/api/sync/history
   ```
   This walks the `previous_league_id` chain from the current league all the way back to the first season and syncs every season.

4. **Run any new database migrations** in case schema changes were made for the new season:
   ```bash
   cd backend
   alembic upgrade head
   ```

### First-Time Setup Sync

After initial installation, run both syncs to populate all data:

```bash
# Sync current season
curl -X POST http://localhost:8000/api/sync/league

# Sync all historical seasons
curl -X POST http://localhost:8000/api/sync/history
```

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines, architecture documentation, and coding standards.

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

## License

Private project for dynasty league use.
