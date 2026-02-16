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

## Development

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines, architecture documentation, and coding standards.

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation.

## License

Private project for dynasty league use.
