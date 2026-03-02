from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.sync_service import SyncService
from app.config import get_settings

router = APIRouter()
settings = get_settings()


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


@router.post("/cron/sync")
async def cron_sync_league(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db)
):
    """Secure cron endpoint for scheduled data syncs.

    Requires Bearer token authentication via Authorization header.
    Use this endpoint for automated syncs from GitHub Actions or Railway Cron.

    Example:
        curl -X POST https://your-api.com/api/cron/sync \\
             -H "Authorization: Bearer YOUR_CRON_SECRET"
    """
    # Validate authorization
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>"
        )

    token = authorization.replace("Bearer ", "")
    if token != settings.CRON_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid cron secret"
        )

    # Perform sync
    try:
        sync_service = SyncService(db)
        result = await sync_service.sync_league()
        return {
            "status": "success",
            "message": "Scheduled sync completed",
            **result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scheduled sync failed: {str(e)}"
        )
