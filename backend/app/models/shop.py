from decimal import Decimal

from sqlalchemy import String, Integer, Float, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDMixin, TimestampMixin


class Shop(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "shops"

    shop_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    total_listings: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0, server_default="0")
    tags_used: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    category_distribution: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    price_range: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    listing_frequency: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    etsy_raw: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
