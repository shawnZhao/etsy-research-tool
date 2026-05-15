from sqlalchemy import String, Integer, Float, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class Keyword(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "keywords"

    keyword: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    search_volume_est: Mapped[int] = mapped_column(Integer, default=0)
    competition_score: Mapped[float] = mapped_column(Float, default=0.0)
    avg_price: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    listing_count: Mapped[int] = mapped_column(Integer, default=0)
    top_category: Mapped[str] = mapped_column(String(255), nullable=True)
    related_tags: Mapped[dict] = mapped_column(JSONB, default=list)
    trend_direction: Mapped[str] = mapped_column(String(20), default="stable")
    trend_data: Mapped[dict] = mapped_column(JSONB, default=list)
    etsy_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
