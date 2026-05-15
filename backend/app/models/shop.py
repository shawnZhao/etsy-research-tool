from sqlalchemy import String, Integer, Float, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class Shop(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "shops"

    shop_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    total_listings: Mapped[int] = mapped_column(Integer, default=0)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    avg_rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    tags_used: Mapped[dict] = mapped_column(JSONB, default=list)
    category_distribution: Mapped[dict] = mapped_column(JSONB, default=list)
    price_range: Mapped[dict] = mapped_column(JSONB, default=dict)
    listing_frequency: Mapped[dict] = mapped_column(JSONB, default=dict)
    etsy_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
