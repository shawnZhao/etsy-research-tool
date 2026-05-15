import asyncio
from app.tasks.celery_app import celery_app
from app.etsy.client import EtsyClient
from app.services.keyword_service import KeywordService
from app.db.session import async_session


@celery_app.task(bind=True, max_retries=3)
def search_and_analyze_keyword(self, keyword: str):
    """Search keyword on Etsy, analyze results, and store in DB."""

    async def _run():
        client = EtsyClient()
        try:
            async with async_session() as db:
                service = KeywordService(db)

                # 1. Search Etsy API
                results = await client.search_listings(keyword, limit=50)
                listings_data = results.get("results", [])
                total_count = results.get("count", 0)

                # 2. Extract prices and tags from search results
                prices = []
                all_tags = []
                for item in listings_data:
                    price_data = item.get("price", {})
                    if isinstance(price_data, dict):
                        amount = float(price_data.get("amount", 0)) / max(
                            float(price_data.get("divisor", 1)), 1
                        )
                    else:
                        amount = float(price_data) if price_data else 0
                    prices.append(amount)
                    all_tags.append(item.get("tags", []))

                # 3. Calculate analysis metrics
                record = await service.get_or_create_keyword(keyword)
                record.search_volume_est = service.estimate_search_volume(
                    total_count, "jewelry"
                )
                record.competition_score = service.calculate_competition(
                    total_listings=total_count,
                    avg_review_count=sum(
                        item.get("num_favorers", 0) for item in listings_data
                    ) / max(len(listings_data), 1),
                    prices=prices,
                )
                record.avg_price = sum(prices) / len(prices) if prices else 0
                record.listing_count = total_count
                record.related_tags = service.extract_related_tags(all_tags, keyword)
                record.etsy_raw = {"count": total_count, "sample": listings_data[:5]}

                trend = service.compute_trend(record, total_count)
                record.trend_data = trend["trend_data"]
                record.trend_direction = trend["trend_direction"]

                await db.commit()
                return {"keyword_id": str(record.id)}
        finally:
            await client.close()

    return asyncio.run(_run())
