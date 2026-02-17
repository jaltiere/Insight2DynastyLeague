from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.sync_service import SyncService

router = APIRouter()


@router.post("/sync/league")
async def sync_league_data(db: AsyncSession = Depends(get_db)):
    """Admin endpoint to sync data from Sleeper API.

    This endpoint performs a full sync of:
    - League configuration
    - Users (owners)
    - Current season data
    - Rosters
    - Matchups (all weeks)
    - Drafts and draft picks
    - NFL players
    """
    try:
        sync_service = SyncService(db)
        result = await sync_service.sync_league()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/sync/history")
async def sync_all_history(db: AsyncSession = Depends(get_db)):
    """Admin endpoint to sync all historical seasons from Sleeper API.

    Walks the previous_league_id chain to find and sync every season
    from the league's inception to the current year.
    """
    try:
        sync_service = SyncService(db)
        result = await sync_service.sync_all_history()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History sync failed: {str(e)}")
