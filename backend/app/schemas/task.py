"""Pydantic schemas for Task API requests and responses."""

from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel, Field


# --- Request Schemas ---

class TaskCreate(BaseModel):
    goal: str = Field(..., min_length=5, max_length=2000, description="Natural language goal")
    priority: int = Field(default=0, ge=0, le=10)


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    error_message: Optional[str] = None


# --- Response Schemas ---

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
    action: str
    details: dict
    screenshot_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    tasks: list[TaskResponse]
    total: int
