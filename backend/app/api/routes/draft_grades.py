"""Draft grading API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.draft_grading import DraftGradingService

router = APIRouter()


@router.get("/draft-grades")
async def get_draft_grades(
    draft_type: Optional[str] = Query(
        None,
        description='Filter by draft type: "startup" or "rookie"',
    ),
    owner_id: Optional[str] = Query(
        None, description="Filter to drafts involving this owner"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Get graded drafts.

    Query params:
    - draft_type: "startup" (2020) or "rookie" (all others)
    - owner_id: Filter to drafts involving specific owner

    Returns list of graded drafts with owner performance breakdowns.
    """
    service = DraftGradingService(db)

    # Validate draft_type if provided
    if draft_type and draft_type not in ("startup", "rookie"):
        raise HTTPException(
            status_code=400,
            detail='draft_type must be "startup" or "rookie"',
        )

    grades = await service.grade_all_drafts(
        draft_type=draft_type,
        owner_id=owner_id,
    )
    return {"total": len(grades), "drafts": grades}


@router.get("/draft-grades/{draft_id}")
async def get_draft_grade(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get grade for a specific draft by ID."""
    service = DraftGradingService(db)
    grade = await service.grade_single_draft(draft_id)
    if not grade:
        raise HTTPException(
            status_code=404,
            detail=f"Draft {draft_id} not found or not complete",
        )
    return grade
