"""Task ORM models — compatible with both SQLite and PostgreSQL."""

import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.models.database import Base, utcnow


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    priority = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="task", cascade="all, delete-orphan")


class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(Uuid(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    action = Column(String(100))
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    task = relationship("Task", back_populates="logs")
