from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.api.deps import verify_cron_secret
from app.services.sync_service import SyncService
from app.config import get_settings, LEAGUES

router = APIRouter()
settings = get_settings()


@router.post("/sync/league", dependencies=[Depends(verify_cron_secret)])
async def sync_league_data(db: AsyncSession = Depends(get_db)):
    """Admin endpoint to sync current season data from Sleeper API for all configured leagues.

    Requires CRON_SECRET bearer token authentication.
    """
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


@router.post("/sync/history", dependencies=[Depends(verify_cron_secret)])
async def sync_all_history(db: AsyncSession = Depends(get_db)):
    """Admin endpoint to sync all historical seasons from Sleeper API for all configured leagues.

    Walks each league's previous_league_id chain to find and sync every season
    from its inception to the current year.

    Requires CRON_SECRET bearer token authentication.
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


@router.post("/cron/sync", dependencies=[Depends(verify_cron_secret)])
async def cron_sync_league(db: AsyncSession = Depends(get_db)):
    """Secure cron endpoint for scheduled data syncs.

    Requires Bearer token authentication via Authorization header.
    Use this endpoint for automated syncs from GitHub Actions or Railway Cron.

    Example:
        curl -X POST https://your-api.com/api/cron/sync \\
             -H "Authorization: Bearer YOUR_CRON_SECRET"
    """
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
