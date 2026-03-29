"""User ORM model — compatible with both SQLite and PostgreSQL."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Uuid

from app.models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
