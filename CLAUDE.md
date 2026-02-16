# Insight2Dynasty - Project Guidelines

## Project Overview
Insight2Dynasty is a fantasy football dynasty league website that integrates with the Sleeper platform. It provides comprehensive analytics, historical data, and league information for dynasty league members.

**Sleeper League ID**: 1313933992642220032

## Technology Stack

### Frontend
- **Framework**: React 18 + Vite + TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Query (API caching) + Context API
- **Routing**: React Router v6
- **UI Components**: Headless UI or shadcn/ui

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: MySQL 8.0+
- **Migrations**: Alembic
- **Validation**: Pydantic

### External APIs
- **Sleeper API**: https://docs.sleeper.com/
  - Read-only access
  - Rate limit: < 1000 calls/minute
  - Base URL: https://api.sleeper.app/v1

## Project Structure

```
Insight2DynastyLeague/
├── frontend/                 # React + Vite application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page components (6 main pages)
│   │   ├── hooks/           # Custom React hooks
│   │   ├── services/        # API client services
│   │   ├── types/           # TypeScript type definitions
│   │   ├── App.tsx          # Root component
│   │   └── main.tsx         # Entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/            # API route handlers
│   │   │   ├── routes/     # Endpoint definitions
│   │   │   └── deps.py     # Dependency injection
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── services/       # Business logic
│   │   │   └── sleeper_client.py  # Sleeper API integration
│   │   ├── database.py     # Database connection
│   │   ├── config.py       # Configuration management
│   │   └── main.py         # FastAPI app entry point
│   ├── alembic/            # Database migrations
│   ├── requirements.txt
│   └── .env                # Environment variables (not in git)
│
├── docker-compose.yml      # Local MySQL setup
├── .gitignore
├── README.md
└── CLAUDE.md              # This file
```

## Database Schema

### Core Tables
1. **leagues** - League configuration and settings
2. **users** - League members (owners)
3. **rosters** - Team rosters by season
4. **matchups** - Weekly matchup results
5. **players** - Player data cached from Sleeper
6. **transactions** - Trade history, waiver claims
7. **seasons** - Season metadata (year, divisions, playoff structure)
8. **drafts** - Draft metadata
9. **draft_picks** - Individual draft selections
10. **season_awards** - Season winners (champion, division, consolation)

### Important Notes
- Division structure changed from 4 divisions to 2 divisions
- Track this in the `seasons` table
- `season_awards` table handles variable number of division winners

## API Endpoints

### Backend API Structure
All endpoints under `/api` prefix:

- **Standings**: `/api/standings`, `/api/standings/{season}`
- **Players**: `/api/players`, `/api/players/{player_id}`
- **Matchups**: `/api/matchups/head-to-head/{owner1}/{owner2}`
- **Owners**: `/api/owners`, `/api/owners/{owner_id}`
- **Drafts**: `/api/drafts`, `/api/drafts/{year}`
- **League History**: `/api/league-history`, `/api/league-history/{season}`
- **Sync**: `/api/sync/league` (admin endpoint)

## Frontend Pages

1. **Home/Standings** - Current season standings, playoff bracket, recent transactions
2. **Player Statistics** - Searchable player table with filters
3. **Head-to-Head History** - Owner vs owner comparison
4. **Owner Records** - Historical records and season breakdowns
5. **Draft Results** - Year-by-year draft boards
6. **League History** - Champions, division winners, consolation bracket winners

## Development Workflow

### Getting Started
1. Start MySQL: `docker-compose up -d`
2. Run migrations: `cd backend && alembic upgrade head`
3. Start backend: `cd backend && uvicorn app.main:app --reload`
4. Start frontend: `cd frontend && npm run dev`

### Environment Variables
- Backend: `backend/.env` (see `backend/.env.example`)
- Frontend: `frontend/.env` (see `frontend/.env.example`)

### Data Sync
- Manual sync: `POST /api/sync/league`
- Sync pulls data from Sleeper API and updates MySQL
- Run sync after setup to populate initial data

## Coding Guidelines

### Python (Backend)
- Use async/await for all database operations
- Follow FastAPI best practices
- Pydantic models for request/response validation
- Type hints everywhere
- Use dependency injection for database sessions

### TypeScript (Frontend)
- Strict TypeScript configuration
- Define types for all API responses
- Use React Query for all API calls
- Component-based architecture
- Tailwind for all styling

### General
- Keep components small and focused
- Reuse components where possible
- Handle loading and error states
- Mobile-first responsive design
- Clear, descriptive variable names

## Data Sync Strategy
- Initial sync: Pull all historical data from Sleeper
- Daily sync during season: Update current week matchups
- Weekly sync: Update player data
- Store all data locally to reduce API calls
- Sleeper API is read-only - we cache everything in MySQL

## Testing & Verification
1. Backend API docs: http://localhost:8000/docs
2. Frontend dev server: http://localhost:5173
3. Test each page loads correctly
4. Verify data sync works
5. Check responsive design on mobile

## Deployment
- TBD - Focus on local development first
- Backend: Needs Python 3.11+ environment
- Frontend: Static build via `npm run build`
- Database: MySQL 8.0+ required

## Resources
- [Sleeper API Docs](https://docs.sleeper.com/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Query Docs](https://tanstack.com/query/latest)
- [Tailwind CSS Docs](https://tailwindcss.com/)
