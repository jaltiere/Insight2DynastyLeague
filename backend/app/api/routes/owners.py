from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter()


@router.get("/owners")
async def get_all_owners(db: AsyncSession = Depends(get_db)):
    """Get all owner records."""
    # TODO: Implement all owners endpoint
    return {"message": "All owners endpoint - to be implemented"}


@router.get("/owners/{owner_id}")
async def get_owner_details(owner_id: str, db: AsyncSession = Depends(get_db)):
    """Get individual owner history."""
    # TODO: Implement owner details
    return {"message": f"Owner {owner_id} details - to be implemented"}
