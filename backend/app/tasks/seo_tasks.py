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
from app.services.seo_service import SEOService
from app.db.session import async_session
from app.models.listing import Listing
from app.models.seo_audit import SEOAudit
from sqlalchemy import select

RETRYABLE_EXCEPTIONS = (EtsyRateLimitError, EtsyServerError, OSError)


def _get_category_hot_tags(category: str) -> list[str]:
    """Return trending tags for a given category."""
    tags_by_category = {
        "necklace": [
            "necklace", "gold necklace", "personalized necklace",
            "name necklace", "dainty necklace", "custom necklace",
            "charm necklace", "layered necklace",
        ],
        "earrings": [
            "earrings", "gold earrings", "stud earrings",
            "hoop earrings", "dangle earrings", "pearl earrings",
            "statement earrings", "minimalist earrings",
        ],
        "rings": [
            "rings", "gold ring", "stacking rings",
            "engagement ring", "birthstone ring", "signet ring",
            "adjustable ring", "minimalist ring",
        ],
        "bracelet": [
            "bracelet", "gold bracelet", "beaded bracelet",
            "personalized bracelet", "charm bracelet", "tennis bracelet",
            "bangle set", "friendship bracelet",
        ],
        "home": [
            "home decor", "wall art", "custom sign",
            "boho decor", "farmhouse decor", "minimalist decor",
        ],
        "art": [
            "wall art", "print", "custom print",
            "digital art", "original art",
        ],
        "clothing": [
            "clothing", "custom shirt", "vintage clothing",
            "personalized sweatshirt", "boho dress", "handmade top",
        ],
        "vintage": [
            "vintage", "retro", "antique",
            "mid century", "vintage decor",
        ],
    }

    if category:
        for key, value in tags_by_category.items():
            if key in category.lower():
                return value

    return ["handmade", "gift", "personalized", "custom", "small business"]


async def _get_or_create_listing(db, item: dict):
    """Upsert a single listing from Etsy API item data.

    Creates a new Listing record or updates an existing one by listing_id.
    Only mutable fields are updated on existing records.
    """
    listing_id_etsy = item.get("listing_id")
    if not listing_id_etsy:
        return None

    # Check if listing already exists
    stmt = select(Listing).where(Listing.listing_id == listing_id_etsy)
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

    shop_id = item.get("shop_id") or 0

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
        listing = record
    else:
        listing = Listing(
            listing_id=listing_id_etsy,
            shop_id=shop_id,
            **fields,
        )
        db.add(listing)

    return listing


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_seo_audit(self, listing_id: int):
    """Fetch listing from Etsy, run SEO audit, and store results."""

    async def _run():
        client = EtsyClient()
        try:
            async with async_session() as db:
                service = SEOService()

                # 1. Fetch listing from Etsy API
                item = await client.get_listing(listing_id)

                # 2. Upsert listing
                listing = await _get_or_create_listing(db, item)
                if listing is None:
                    return {"error": "Could not create listing record"}

                await db.flush()

                # 3. SEO scoring
                core_keywords = service.extract_core_keywords(
                    listing.title or "", listing.tags or []
                )
                category = listing.category or ""
                hot_tags = _get_category_hot_tags(category)

                title_score, title_suggestions = service.score_title(
                    listing.title or "", core_keywords
                )
                tag_score, tag_suggestions = service.score_tags(
                    listing.tags or [], listing.title or "", hot_tags
                )
                desc_score, desc_suggestions = service.score_description(
                    listing.description or "", core_keywords
                )
                overall = service.compute_overall_score(
                    title_score, tag_score, desc_score
                )

                suggestions = title_suggestions + tag_suggestions + desc_suggestions
                benchmarks = {
                    "avg_title_score": 65,
                    "avg_tag_score": 60,
                    "avg_description_score": 55,
                    "avg_overall_score": 61,
                }

                # 4. Create SEOAudit record
                audit = SEOAudit(
                    listing_id=listing.id,
                    title_score=title_score,
                    tag_score=tag_score,
                    description_score=desc_score,
                    overall_score=overall,
                    suggestions=suggestions,
                    benchmarks=benchmarks,
                )
                db.add(audit)
                await db.commit()

                return {"audit_id": str(audit.id), "overall_score": overall}
        finally:
            await client.close()

    try:
        return asyncio.run(_run())
    except RETRYABLE_EXCEPTIONS as exc:
        raise self.retry(exc=exc)
    except (EtsyAuthError, EtsyNotFoundError) as exc:
        return {"error": str(exc), "listing_id": listing_id}
