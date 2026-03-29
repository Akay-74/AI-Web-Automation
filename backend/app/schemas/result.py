"""Pydantic schemas for Result API responses."""

from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel


class ResultResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    data_type: str
    data: dict
    summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResultListResponse(BaseModel):
    results: list[ResultResponse]
