from sqlalchemy import Float, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin
import uuid
import datetime


class SEOAudit(Base, UUIDMixin):
    __tablename__ = "seo_audits"

    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False, index=True)
    title_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    tag_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    description_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    suggestions: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    benchmarks: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
