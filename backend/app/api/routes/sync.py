from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.sleeper_client import sleeper_client

router = APIRouter()


@router.post("/sync/league")
async def sync_league_data(db: AsyncSession = Depends(get_db)):
    """Admin endpoint to sync data from Sleeper API."""
    # TODO: Implement full sync logic
    # This will:
    # 1. Fetch league info
    # 2. Fetch all rosters
    # 3. Fetch all users
    # 4. Fetch matchups for all weeks
    # 5. Fetch all drafts and picks
    # 6. Update database

    return {"message": "Sync endpoint - to be implemented", "status": "pending"}
