from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.sync_service import SyncService
from app.config import get_settings, LEAGUES

router = APIRouter()
settings = get_settings()


@router.post("/sync/league")
async def sync_league_data(db: AsyncSession = Depends(get_db)):
    """Admin endpoint to sync current season data from Sleeper API for all configured leagues."""
    results = []
    errors = []
    for league in LEAGUES:
        try:
            svc = SyncService(
                db,
                league_id=league["id"],
                recaps_enabled=league.get("recaps_enabled", False),
            )
            result = await svc.sync_league()
            results.append({"league": league["slug"], **result})
        except Exception as e:
            errors.append({"league": league["slug"], "error": str(e)})

    if errors and not results:
        raise HTTPException(status_code=500, detail=f"All syncs failed: {errors}")
    return {"leagues": results, "errors": errors}


@router.post("/sync/history")
async def sync_all_history(db: AsyncSession = Depends(get_db)):
    """Admin endpoint to sync all historical seasons from Sleeper API for all configured leagues.

    Walks each league's previous_league_id chain to find and sync every season
    from its inception to the current year.
    """
    results = []
    errors = []
    for league in LEAGUES:
        try:
            svc = SyncService(db, league_id=league["id"])
            result = await svc.sync_all_history()
            results.append({"league": league["slug"], **result})
        except Exception as e:
            errors.append({"league": league["slug"], "error": str(e)})

    if errors and not results:
        raise HTTPException(status_code=500, detail=f"All history syncs failed: {errors}")
    return {"leagues": results, "errors": errors}


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

    # Perform sync for all configured leagues
    results = []
    errors = []
    for league in LEAGUES:
        try:
            svc = SyncService(
                db,
                league_id=league["id"],
                recaps_enabled=league.get("recaps_enabled", False),
            )
            result = await svc.sync_league()
            results.append({"league": league["slug"], **result})
        except Exception as e:
            errors.append({"league": league["slug"], "error": str(e)})

    if errors and not results:
        raise HTTPException(status_code=500, detail=f"All syncs failed: {errors}")
    return {
        "status": "success",
        "message": "Scheduled sync completed",
        "leagues": results,
        "errors": errors,
    }
