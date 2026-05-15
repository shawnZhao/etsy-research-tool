import math
from collections import Counter
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.keyword import Keyword


class KeywordService:
    CATEGORY_WEIGHTS: dict[str, float] = {
        "jewelry": 1.2,
        "home_and_living": 0.9,
        "clothing": 1.1,
        "craft_supplies": 0.8,
        "art_and_collectibles": 0.7,
        "accessories": 1.0,
        "paper_and_party_supplies": 0.6,
        "weddings": 1.3,
        "toys_and_games": 0.8,
        "vintage": 0.9,
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    def estimate_search_volume(self, listing_count: int, category: str) -> int:
        """Estimate search volume from listing count and category weight."""
        normalized = category.lower().strip().replace(" & ", "_and_").replace(" ", "_")
        weight = self.CATEGORY_WEIGHTS.get(normalized, 0.85)
        return int(listing_count * weight / 100)

    def calculate_competition(
        self, total_listings: int, avg_review_count: float, prices: list[float]
    ) -> float:
        """Calculate competition score 0-100 from listing metrics."""
        if not prices or total_listings == 0:
            return 0.0

        review_factor = min(avg_review_count / 1000, 1.0)

        if len(prices) > 1:
            mean_price = sum(prices) / len(prices)
            variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
            std_dev = math.sqrt(variance)
            if mean_price > 0:
                cv = std_dev / mean_price
                price_dispersion = min(cv, 1.0)
            else:
                price_dispersion = 0
        else:
            price_dispersion = 0

        score = (
            0.5 * review_factor
            + 0.5 * (1 - price_dispersion)
        ) * 100
        return round(score, 1)

    def extract_related_tags(
        self, tags_list: list[list[str]], seed_keyword: str
    ) -> list[dict]:
        """Extract related tags from search results, excluding the seed keyword."""
        seed_lower = seed_keyword.lower()
        seed_tokens = set(seed_lower.split())
        counter: Counter[str] = Counter()
        for tags in tags_list:
            for tag in tags:
                tag_lower = tag.lower()
                tag_tokens = set(tag_lower.split())
                if tag_lower == seed_lower or seed_tokens == tag_tokens:
                    continue
                counter[tag_lower] += 1
        top = counter.most_common(20)
        return [{"tag": tag, "count": count} for tag, count in top]

    def compute_trend(self, keyword_record: Keyword, current_volume: int) -> dict:
        """Update trend data with new volume reading. Returns updated trend fields."""
        trend_data = list(keyword_record.trend_data or [])
        trend_data.append({
            "date": datetime.now(timezone.utc).isoformat(),
            "volume": current_volume,
        })
        if len(trend_data) >= 3:
            recent = [p["volume"] for p in trend_data[-3:]]
            if recent[-1] > recent[0] * 1.1:
                direction = "up"
            elif recent[-1] < recent[0] * 0.9:
                direction = "down"
            else:
                direction = "stable"
            return {"trend_data": trend_data[-10:], "trend_direction": direction}
        return {"trend_data": trend_data, "trend_direction": "stable"}

    async def get_or_create_keyword(self, keyword: str) -> Keyword:
        """Get existing keyword record or create a new one."""
        normalized = keyword.lower().strip()
        stmt = select(Keyword).where(Keyword.keyword == normalized)
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()
        if record is not None:
            return record
        record = Keyword(keyword=normalized)
        self.db.add(record)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            result = await self.db.execute(stmt)
            record = result.scalar_one()
        return record
