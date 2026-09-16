"""Pydantic schemas for the Task API."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    goal: str = Field(..., min_length=5, max_length=2000, description="Natural language goal")
    priority: int = Field(default=0, ge=0, le=10)


class TaskResponse(BaseModel):
    id: uuid.UUID
    goal: str
    status: str
    priority: int
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TaskLogResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    step_number: int
    action: Optional[str] = None
    details: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
