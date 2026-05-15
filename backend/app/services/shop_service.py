import statistics
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.shop import Shop
from app.models.listing import Listing


class ShopService:
    """Service for shop analysis: tags, categories, prices, and shop management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_shop(self, shop_id: int, name: str, url: str) -> Shop:
        """Find existing shop by shop_id or create a new one. Flushes and returns."""
        stmt = select(Shop).where(Shop.shop_id == shop_id)
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is not None:
            record.name = name
            record.url = url
        else:
            record = Shop(shop_id=shop_id, name=name, url=url)
            self.db.add(record)
        await self.db.flush()
        return record

    async def analyze_tags(self, shop: Shop) -> list[dict]:
        """Count tag usage across all shop listings, return top 50."""
        stmt = select(Listing.tags).where(Listing.shop_id == shop.shop_id)
        result = await self.db.execute(stmt)
        counter: Counter = Counter()
        for row in result.all():
            tags = row[0] or []
            counter.update(tags)
        top = counter.most_common(50)
        return [{"tag": tag, "count": count} for tag, count in top]

    async def analyze_categories(self, shop: Shop) -> list[dict]:
        """Count category usage across shop listings, return top 10 with percentages."""
        stmt = select(Listing.category).where(
            Listing.shop_id == shop.shop_id,
            Listing.category.isnot(None),
        )
        result = await self.db.execute(stmt)
        counter: Counter = Counter()
        for row in result.all():
            cat = row[0]
            if cat:
                counter[cat] += 1
        total = sum(counter.values())
        if total == 0:
            return []
        top = counter.most_common(10)
        return [
            {"category": cat, "count": count, "pct": round(count / total * 100, 1)}
            for cat, count in top
        ]

    async def analyze_prices(self, shop: Shop) -> dict:
        """Analyze price distribution across shop listings: min, max, avg, median."""
        stmt = select(Listing.price).where(
            Listing.shop_id == shop.shop_id,
            Listing.price.isnot(None),
        )
        result = await self.db.execute(stmt)
        prices = [float(row[0]) for row in result.all() if row[0] is not None]
        if not prices:
            return {"min": 0, "max": 0, "avg": 0, "median": 0}
        return {
            "min": round(min(prices), 2),
            "max": round(max(prices), 2),
            "avg": round(sum(prices) / len(prices), 2),
            "median": round(statistics.median(prices), 2),
        }
