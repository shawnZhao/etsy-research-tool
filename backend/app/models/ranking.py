from sqlalchemy import Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin
import uuid
import datetime


class RankingSnapshot(Base, UUIDMixin):
    __tablename__ = "ranking_snapshots"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True)
    keyword_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("keywords.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_results: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    captured_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
