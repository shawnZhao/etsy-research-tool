from sqlalchemy import String, Integer, Float, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class Listing(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "listings"

    listing_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    shop_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    category: Mapped[str] = mapped_column(String(500), nullable=True)
    category_path: Mapped[dict] = mapped_column(JSONB, default=list)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    images: Mapped[dict] = mapped_column(JSONB, default=list)
    favorites: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=0)
    views_est: Mapped[int] = mapped_column(Integer, default=0)
    etsy_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
