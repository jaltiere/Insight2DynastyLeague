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

### Production Deployment
- **Platform**: Railway (https://railway.app)
- **Frontend**: www.insight2dynasty.com (Static React app)
- **Backend**: api.insight2dynasty.com (FastAPI service)
- **Database**: Railway MySQL 8.0
- **CI/CD**: GitHub Actions for testing, Railway auto-deploy on push to main
- **Automated Sync**: GitHub Actions daily at 6 AM UTC
- **Domain Registrar**: GoDaddy

**Required Dependencies (Already in requirements.txt):**
- `cryptography>=42.0.0` - Required for MySQL 8.0 authentication (caching_sha2_password)

**Environment Variables:**

Backend (Railway):
- `DATABASE_URL` - Auto-populated by Railway MySQL plugin
- `SLEEPER_LEAGUE_ID` - 1313933992642220032
- `CORS_ORIGINS` - https://www.insight2dynasty.com,http://localhost:5173
- `CRON_SECRET` - Secure random string for scheduled sync and recap regeneration endpoints
- `ANTHROPIC_API_KEY` - Claude API key for AI-generated matchup recaps (optional; mock mode if empty)
- `DEBUG` - False (production)
- `APP_VERSION` - 1.0.0

Frontend (Railway):
- `VITE_API_BASE_URL` - https://api.insight2dynasty.com
  - **Important**: Variable name must be `VITE_API_BASE_URL` (not `VITE_API_URL`)
  - This matches the name in `frontend/src/services/api.ts`

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
11. **matchup_recaps** - AI-generated recaps and predictions per matchup

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
- **Matchup Recaps**: `/api/matchup-recaps/current`, `/api/matchup-recaps/previous`, `/api/matchup-recaps/week/{week}`
- **Recap Admin**: `/api/matchup-recaps/regenerate/{week}`, `/api/matchup-recaps/regenerate-predictions/{week}` (require CRON_SECRET)
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

## Git Workflow

**IMPORTANT**: All feature development and bug fixes MUST be done in feature branches, NOT directly on `main`.

### Branch Strategy
1. **main** - Production-ready code only
2. **feature/** - New features (e.g., `feature/add-player-stats-page`)
3. **bugfix/** - Bug fixes (e.g., `bugfix/cors-error`)
4. **hotfix/** - Urgent production fixes

### Workflow Rules
1. **Never commit directly to main** - All changes must go through pull requests
2. **Always pull latest main before creating a branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/feature-name
   # or
   git checkout -b bugfix/bug-description
   ```
3. **Work on your branch**, commit regularly with clear messages
4. **Push your branch** to GitHub:
   ```bash
   git push -u origin feature/feature-name
   ```
5. **Create a Pull Request** on GitHub for code review
6. **Merge only after review** - Use GitHub's merge button
7. **Delete branch after merge** to keep repository clean

### Commit Message Guidelines
- Use present tense: "Add feature" not "Added feature"
- Be descriptive: "Fix CORS error for port 5176" not "Fix bug"
- Reference issues if applicable: "Fix #123: Add player search"
- Include co-author line for AI assistance:
  ```
  Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
  ```

### Example Workflow
```bash
# Always start from latest main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/add-owner-stats

# Make changes and commit
git add .
git commit -m "Add owner career statistics endpoint"

# Push to GitHub
git push -u origin feature/add-owner-stats

# Create PR on GitHub, get review, merge
# After merge, switch back to main and pull
git checkout main
git pull origin main
```

### Creating Pull Requests

**GitHub CLI Location**: The `gh` CLI is installed but not in system PATH. Use the full path:
```bash
"/c/Program Files/GitHub CLI/gh.exe" pr create --title "Your Title" --body "Your description"
```

**Example PR Creation**:
```bash
"/c/Program Files/GitHub CLI/gh.exe" pr create \
  --title "Add new feature" \
  --body "Description of changes"
```

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
- **Mobile-first responsive design** - Always consider mobile users first

### Responsive Design Guidelines
- **Mobile-first approach**: Design for mobile screens first, then scale up for desktop
- **Responsive navigation**: Use hamburger menu for mobile (< 768px), horizontal nav for desktop
- **Touch-friendly targets**: Minimum 48x48px touch targets for buttons/links
- **Tailwind breakpoints**:
  - Mobile: default (< 640px)
  - Tablet: `md:` (≥ 768px)
  - Desktop: `lg:` (≥ 1024px)
- **Test on multiple devices**: Phone, tablet, desktop
- **Avoid horizontal scroll**: All content must fit within viewport width
- **Readable text sizes**: Minimum 14px on mobile, 16px on desktop

### General
- Keep components small and focused
- Reuse components where possible
- Handle loading and error states
- Always add optional chaining for nullable API data
- Clear, descriptive variable names

## AI-Generated Matchup Recaps

### Overview
The site generates AI-powered recaps for completed matchups and predictions for upcoming matchups using the Claude API (claude-haiku-4-5). Recaps include top performers, lineup mistakes, head-to-head history, and playoff implications.

### Key Files
- `backend/app/services/matchup_recap_service.py` - Core generation logic (context building, Claude API calls)
- `backend/app/api/routes/matchup_recaps.py` - REST endpoints for reading and regenerating recaps
- `backend/app/models/matchup_recap.py` - Database model (`matchup_recaps` table)
- `.github/workflows/weekly-recaps.yml` - Scheduled GitHub Actions workflow

### Environment Variables
- `ANTHROPIC_API_KEY` - Claude API key for recap generation. If empty/missing, the service runs in **mock mode** and generates placeholder text instead of calling the API.

### How Recaps Are Generated
- **Recaps** (completed matchups): Built from winner/loser scores, top 5 performers with team attribution, lineup mistakes (benched > starter), H2H history, and bracket context
- **Predictions** (upcoming matchups): Built from team records, projected scores, H2H history, and standings implications
- **Model**: `claude-haiku-4-5-20251001`, temperature 0.9, max 250 tokens

### Scheduling & Automation
Recaps are generated on a Tuesday/Thursday schedule during the NFL season:

| Day | Action | Trigger |
|-----|--------|---------|
| Tuesday | Generate previous week recaps + current week predictions | `scheduled-sync.yml` and `weekly-recaps.yml` |
| Thursday | Regenerate predictions (updated lineups) | `scheduled-sync.yml` and `weekly-recaps.yml` |

**Two workflows trigger generation:**
1. `scheduled-sync.yml` - Calls `/api/cron/sync` which includes recap generation inside `sync_service.py`
2. `weekly-recaps.yml` - Calls regenerate endpoints directly for dedicated recap generation

### Offseason Guards (Three Layers)
Recaps are **frozen during the NFL offseason** to prevent regeneration when no games are being played. The Sleeper API's `/state/nfl` endpoint is used to detect offseason (`season_type == "off"` or `week == 0`).

1. **Sync Service** (`sync_service.py`): Only generates recaps when `season_type in ("regular", "post")` and `current_week >= 2`
2. **Regenerate Endpoints** (`matchup_recaps.py`): Both `regenerate/{week}` and `regenerate-predictions/{week}` check NFL state and return `{"status": "skipped"}` during offseason
3. **GitHub Actions** (`weekly-recaps.yml`): Checks Sleeper NFL state first and skips all generation steps during offseason

### Manual Regeneration
Both regenerate endpoints accept a `?force=true` query parameter to bypass the offseason guard:

```bash
# Regenerate recaps for a specific week (e.g., championship week 17)
curl -X POST "https://api.insight2dynasty.com/api/matchup-recaps/regenerate/17?season=2025&force=true" \
  -H "Authorization: Bearer $CRON_SECRET"

# Regenerate predictions for a specific week
curl -X POST "https://api.insight2dynasty.com/api/matchup-recaps/regenerate-predictions/5?season=2025&force=true" \
  -H "Authorization: Bearer $CRON_SECRET"
```

You can also trigger the `weekly-recaps.yml` workflow manually from GitHub Actions (workflow_dispatch), but note this will be skipped during offseason unless the endpoints are called with `?force=true`.

### Week 1 Wednesday Game
The Thursday prediction sync won't run in time when Week 1 has a Wednesday night game. Manually trigger predictions the morning of the Wednesday game with a direct API call:

```bash
# Run before the first game of Week 1 (Wednesday or whenever it kicks off)
curl -X POST "https://api.insight2dynasty.com/api/matchup-recaps/regenerate-predictions/1?season=2026" \
  -H "Authorization: Bearer $CRON_SECRET"
```

No `?force=true` needed — the season will be active by then. Update the `season` param each year.

### Read Endpoints (No Auth Required)
- `GET /api/matchup-recaps/current` - Current week matchups with predictions (empty during offseason)
- `GET /api/matchup-recaps/previous` - Previous week recaps (shows championship week during offseason)
- `GET /api/matchup-recaps/week/{week}?season=YYYY` - Recaps for a specific week
- `GET /api/matchup-recaps/newsletter/{week}` - Recaps formatted for newsletter

### Database Storage
- Table: `matchup_recaps` with unique constraint on `(matchup_id, recap_type)`
- Recap types: `weekly`, `playoff`, `prediction`
- `generated_at` timestamp tracks when each recap was last generated
- No automatic expiration — recaps persist until explicitly regenerated

## Data Sync Strategy
- Initial sync: Pull all historical data from Sleeper
- Daily sync during season: Update current week matchups
- Weekly sync: Update player data
- Store all data locally to reduce API calls
- Sleeper API is read-only - we cache everything in MySQL

## Testing & Verification

### Development Testing
1. **Backend API docs**: http://localhost:8000/docs
2. **Frontend dev server**: http://localhost:5173
3. **Test each page loads correctly** on all screen sizes
4. **Verify data sync works** (initial sync + incremental sync)

### Responsive Design Testing
Test on multiple viewport sizes:
- **Mobile**: 375px, 390px, 414px (iPhone sizes)
- **Tablet**: 768px, 820px, 1024px (iPad sizes)
- **Desktop**: 1280px, 1440px, 1920px

**Browser DevTools:**
1. Open DevTools (F12) → Toggle device toolbar (Ctrl+Shift+M)
2. Test common devices: iPhone 12/13/14, iPad, Desktop
3. Check navigation menu (hamburger on mobile, horizontal on desktop)
4. Verify no horizontal scrolling
5. Test touch targets are at least 48x48px

**Production Testing:**
- Test on actual mobile devices (iOS Safari, Android Chrome)
- Test in different orientations (portrait and landscape)
- Check dark mode on all devices

### Unit Testing Requirements
- **All tests must pass before merging or shipping any feature.** Disabling, skipping, or deleting tests to make a build green is never acceptable. If a test is failing, fix the underlying code.
- **Always add or update unit tests** when adding new features, fixing bugs, or modifying API endpoints
- Backend tests live in `backend/tests/` using pytest with async support
- Use the factory helpers in `backend/tests/conftest.py` (`create_league`, `create_user`, `create_season`, `create_roster`, etc.) to set up test data
- Tests run against an in-memory SQLite database (no MySQL required)
- Run tests with: `cd backend && py -m pytest tests/ -v`
- Test both the happy path and edge cases (missing data, fallback behavior, 404s)
- When modifying an API response shape, update `test_*_response_has_all_fields` tests to include new fields

## Deployment

### Production Deployment (Railway)
✅ **Live at**: www.insight2dynasty.com

**Platform**: Railway
**Architecture**:
- Frontend: Static React app (www.insight2dynasty.com)
- Backend: FastAPI service (api.insight2dynasty.com)
- Database: Railway MySQL 8.0

**Deployment Process**:
1. Push to `main` branch
2. GitHub Actions runs tests (backend pytest, frontend build)
3. Railway auto-deploys both frontend and backend
4. Migrations run automatically via start command: `alembic upgrade head && uvicorn...`

**Custom Domain Setup**:
- Use CNAME records for subdomains (www, api)
- GoDaddy does not support CNAME for apex domain (@)
- Set up domain forwarding: `insight2dynasty.com` → `www.insight2dynasty.com`

**Automated Data Sync**:
- GitHub Actions workflow runs daily at 6 AM UTC
- Calls `/api/cron/sync` endpoint with Bearer token authentication
- Updates current season data automatically

**Configuration Files**:
- `railway.toml` - Railway deployment configuration
- `nixpacks.toml` - Nixpacks build configuration (sets working directory to backend)
- `.github/workflows/deploy.yml` - CI tests
- `.github/workflows/scheduled-sync.yml` - Tuesday/Thursday automated sync (includes recap generation)
- `.github/workflows/weekly-recaps.yml` - Dedicated recap generation workflow (Tuesday/Thursday)

**Important Notes**:
- Database migrations run as part of the start command (no separate migration step needed)
- Frontend env var must be `VITE_API_BASE_URL` (not `VITE_API_URL`)
- Backend requires `cryptography` package for MySQL 8.0 authentication
- Sync order matters: players must be synced before drafts (foreign key constraint)

For detailed deployment instructions, see [DEPLOYMENT.md](./docs/DEPLOYMENT.md).

### Common Deployment Issues

**1. Frontend Calling Wrong API**
- **Symptom**: Frontend shows empty data or "Standings -" with no season
- **Cause**: `VITE_API_BASE_URL` pointing to wrong domain
- **Fix**: Ensure `VITE_API_BASE_URL=https://api.insight2dynasty.com` in Railway frontend service

**2. CORS Errors**
- **Symptom**: Browser console shows CORS policy errors
- **Cause**: Backend `CORS_ORIGINS` doesn't include frontend domain
- **Fix**: Update backend `CORS_ORIGINS=https://www.insight2dynasty.com,http://localhost:5173`

**3. Undefined Filter Error**
- **Symptom**: `TypeError: Cannot read properties of undefined (reading 'filter')`
- **Cause**: Missing optional chaining when API data is loading
- **Fix**: Use `standings?.standings?.filter(...)` instead of `standings?.standings.filter(...)`

**4. Foreign Key Constraint During Sync**
- **Symptom**: `IntegrityError` when syncing draft picks
- **Cause**: Drafts synced before players exist
- **Fix**: Already fixed - players are now synced first in `sync_all_history()`

**5. MySQL Authentication Error**
- **Symptom**: `RuntimeError: 'cryptography' package is required`
- **Cause**: Missing cryptography package for MySQL 8.0 auth
- **Fix**: Already in requirements.txt - ensure Railway installed it

## Resources
- [Sleeper API Docs](https://docs.sleeper.com/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Query Docs](https://tanstack.com/query/latest)
- [Tailwind CSS Docs](https://tailwindcss.com/)
