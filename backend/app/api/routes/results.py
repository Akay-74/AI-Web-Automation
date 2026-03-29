"""Results API routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.result import Result
from app.schemas.result import ResultResponse, ResultListResponse

router = APIRouter(tags=["results"])


@router.get("/tasks/{task_id}/results", response_model=ResultListResponse)
async def get_task_results(task_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get extracted results for a task."""
    result = await db.execute(
        select(Result).where(Result.task_id == task_id).order_by(Result.created_at)
    )
    results = result.scalars().all()
    return ResultListResponse(results=results)


@router.get("/results/{result_id}", response_model=ResultResponse)
async def get_result(result_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single result by ID."""
    result = await db.execute(select(Result).where(Result.id == result_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Result not found")
    return item
