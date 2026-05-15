from sqlalchemy.orm import DeclarativeBase
import uuid
from sqlalchemy import UUID, Column, DateTime, func


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
