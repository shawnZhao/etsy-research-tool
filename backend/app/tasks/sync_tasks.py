import asyncio
from decimal import Decimal
from app.tasks.celery_app import celery_app
from app.etsy.client import EtsyClient
from app.etsy.exceptions import (
    EtsyRateLimitError,
    EtsyServerError,
    EtsyAuthError,
    EtsyNotFoundError,
)
from app.services.shop_service import ShopService
from app.db.session import async_session
from app.models.listing import Listing
from sqlalchemy import select

RETRYABLE_EXCEPTIONS = (EtsyRateLimitError, EtsyServerError, OSError)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_shop(self, shop_id: int):
    """Sync shop info, all listings, and analysis from Etsy API."""

    async def _run():
        client = EtsyClient()
        try:
            async with async_session() as db:
                service = ShopService(db)

                # 1. Fetch shop from Etsy API
                shop_data = await client.get_shop(shop_id)

                # 2. Upsert shop record
                shop = await service.upsert_shop(
                    shop_id=shop_data.get("shop_id", shop_id),
                    name=shop_data.get("shop_name", ""),
                    url=shop_data.get("url", ""),
                )
                shop.total_listings = shop_data.get("listing_active_count", 0)
                shop.total_reviews = shop_data.get("review_count", 0)
                review_avg = float(shop_data.get("review_average") or 0)
                shop.avg_rating = Decimal(str(round(review_avg, 2)))
                shop.etsy_raw = shop_data

                # 3. Fetch all listings with pagination
                offset = 0
                limit = 100
                while True:
                    page = await client.get_shop_listings(
                        shop_id, limit=limit, offset=offset
                    )
                    items = page.get("results", [])
                    for item in items:
                        await _upsert_listing(db, shop.shop_id, item)
                    offset += len(items)
                    if len(items) < limit:
                        break

                # 4. Run analysis
                shop.tags_used = await service.analyze_tags(shop)
                shop.category_distribution = await service.analyze_categories(shop)
                shop.price_range = await service.analyze_prices(shop)

                await db.commit()
                return {"shop_id": str(shop.id)}
        finally:
            await client.close()

    try:
        return asyncio.run(_run())
    except RETRYABLE_EXCEPTIONS as exc:
        raise self.retry(exc=exc)
    except (EtsyAuthError, EtsyNotFoundError) as exc:
        return {"error": str(exc), "shop_id": shop_id}


async def _upsert_listing(db, shop_id: int, item: dict):
    """Upsert a single listing from Etsy API item data.

    Creates a new Listing record or updates an existing one by listing_id.
    Only mutable fields are updated on existing records.
    """
    listing_id = item.get("listing_id")
    if not listing_id:
        return None

    # Check if listing already exists
    stmt = select(Listing).where(Listing.listing_id == listing_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    # Parse price — handle both dict (amount/divisor) and scalar formats
    price_data = item.get("price", {})
    if isinstance(price_data, dict):
        amount = float(price_data.get("amount", 0))
        divisor = float(price_data.get("divisor", 1))
        price_value = amount / max(divisor, 1)
    elif isinstance(price_data, (int, float)):
        price_value = float(price_data)
    else:
        price_value = 0.0
    price = Decimal(str(round(price_value, 2)))

    # Parse category from taxonomy_path (use last element)
    taxonomy_path = item.get("taxonomy_path", [])
    category = taxonomy_path[-1] if taxonomy_path else None

    # Parse currency — prefer top-level currency_code, fall back to price dict
    currency = item.get("currency_code", "")
    if not currency and isinstance(price_data, dict):
        currency = price_data.get("currency_code", "USD")
    if not currency:
        currency = "USD"

    # Parse images — extract full-size URLs
    images_data = item.get("images", [])
    images = []
    for img in images_data:
        img_url = img.get("url_fullxfull") or img.get("url_570xN") or ""
        if img_url:
            images.append(img_url)

    # Build field values
    fields = {
        "title": item.get("title", ""),
        "description": item.get("description", ""),
        "tags": item.get("tags", []),
        "price": price,
        "currency": currency,
        "category": category,
        "category_path": taxonomy_path,
        "url": item.get("url", ""),
        "images": images,
        "favorites": item.get("num_favorers", 0),
        "review_count": item.get("review_count", 0),
        "rating": Decimal(
            str(round(float(item.get("rating") or 0), 2))
        ),
        "etsy_raw": item,
    }

    if record is not None:
        # Update only mutable fields on existing record
        for key, value in fields.items():
            setattr(record, key, value)
    else:
        record = Listing(
            listing_id=listing_id,
            shop_id=shop_id,
            **fields,
        )
        db.add(record)

    return record
