from decimal import Decimal

from sqlalchemy import String, Integer, Float, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class Keyword(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "keywords"

    keyword: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    search_volume_est: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    competition_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0.0")
    avg_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, server_default="0")
    listing_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    top_category: Mapped[str] = mapped_column(String(255), nullable=True)
    related_tags: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    trend_direction: Mapped[str] = mapped_column(String(20), default="stable", server_default="stable")
    trend_data: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    etsy_raw: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
