import asyncio
import re
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.session import get_db
from app.models.shop import Shop
from app.models.listing import Listing
from app.etsy.client import EtsyClient
from app.tasks.sync_tasks import sync_shop

router = APIRouter(prefix="/shops", tags=["shops"])


class TrackShopRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2000)


class CompareShopsRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1, max_length=20)


def _extract_shop_id(url_or_id: str) -> str:
    """Extract shop identifier from an Etsy shop URL, or return the raw string.

    Handles:
      - https://www.etsy.com/shop/ShopName  → "ShopName"
      - https://etsy.com/shop/12345        → "12345"
      - 12345 (raw numeric id)             → "12345"
      - anything else                       → stripped raw string
    """
    # etsy.com/shop/NAME pattern
    match = re.search(r'etsy\.com/shop/([^/?\s]+)', url_or_id)
    if match:
        return match.group(1)
    return url_or_id.strip()


def _parse_shop_id(shop_id: str) -> UUID:
    """Parse a shop UUID string, raising 422 on invalid format."""
    try:
        return UUID(shop_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid shop ID: {shop_id}")


# ---------------------------------------------------------------------------
# POST /shops/track
# ---------------------------------------------------------------------------
@router.post("/track")
async def track_shop(req: TrackShopRequest):
    """Track a new shop for analysis. Accepts an Etsy shop URL or numeric ID."""
    shop_identifier = _extract_shop_id(req.url.strip())
    if not shop_identifier:
        raise HTTPException(status_code=422, detail="Could not extract shop identifier from URL")

    try:
        numeric_id = int(shop_identifier)
    except ValueError:
        # Resolve shop name to numeric ID via Etsy API
        client = EtsyClient()
        try:
            found = await client.find_shop(shop_identifier)
        finally:
            await client.close()
        if found is None:
            raise HTTPException(
                status_code=404, detail=f"Shop not found: {shop_identifier}"
            )
        numeric_id = found.get("shop_id")
        if not numeric_id:
            raise HTTPException(
                status_code=404, detail=f"Could not resolve shop ID for: {shop_identifier}"
            )

    loop = asyncio.get_event_loop()
    task = await loop.run_in_executor(None, sync_shop.delay, numeric_id)
    return {"task_id": task.id}


# ---------------------------------------------------------------------------
# GET /shops/
# ---------------------------------------------------------------------------
@router.get("/")
async def list_shops(db: AsyncSession = Depends(get_db)):
    """List all tracked shops, most recently updated first (max 50)."""
    stmt = select(Shop).order_by(Shop.last_updated.desc()).limit(50)
    result = await db.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /shops/{shop_id}
# ---------------------------------------------------------------------------
@router.get("/{shop_id}")
async def get_shop(shop_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single shop by its UUID."""
    sid = _parse_shop_id(shop_id)
    stmt = select(Shop).where(Shop.id == sid)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Shop not found")
    return record


# ---------------------------------------------------------------------------
# GET /shops/{shop_id}/tags
# ---------------------------------------------------------------------------
@router.get("/{shop_id}/tags")
async def get_shop_tags(shop_id: str, db: AsyncSession = Depends(get_db)):
    """Get the top tags used by a shop."""
    sid = _parse_shop_id(shop_id)
    stmt = select(Shop).where(Shop.id == sid)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Shop not found")
    return record.tags_used or []


# ---------------------------------------------------------------------------
# GET /shops/{shop_id}/listings
# ---------------------------------------------------------------------------
@router.get("/{shop_id}/listings")
async def get_shop_listings(
    shop_id: str,
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    """Get a shop's listings with pagination (20 per page)."""
    sid = _parse_shop_id(shop_id)
    stmt = select(Shop).where(Shop.id == sid)
    result = await db.execute(stmt)
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=404, detail="Shop not found")

    per_page = 20
    offset = (page - 1) * per_page

    count_stmt = (
        select(func.count())
        .select_from(Listing)
        .where(Listing.shop_id == shop.shop_id)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    items_stmt = (
        select(Listing)
        .where(Listing.shop_id == shop.shop_id)
        .order_by(Listing.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    items_result = await db.execute(items_stmt)
    items = items_result.scalars().all()

    return {"items": items, "total": total}


# ---------------------------------------------------------------------------
# GET /shops/{shop_id}/trend
# ---------------------------------------------------------------------------
@router.get("/{shop_id}/trend")
async def get_shop_trend(shop_id: str, db: AsyncSession = Depends(get_db)):
    """Get shop listing frequency and trend data."""
    sid = _parse_shop_id(shop_id)
    stmt = select(Shop).where(Shop.id == sid)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Shop not found")
    return record.listing_frequency or {"weekly": 0, "monthly": 0, "trend": []}


# ---------------------------------------------------------------------------
# POST /shops/compare
# ---------------------------------------------------------------------------
@router.post("/compare")
async def compare_shops(req: CompareShopsRequest, db: AsyncSession = Depends(get_db)):
    """Compare multiple shops by their UUIDs."""
    try:
        uuid_ids = [UUID(i) for i in req.ids]
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid shop ID in list: {e}")
    stmt = select(Shop).where(Shop.id.in_(uuid_ids))
    result = await db.execute(stmt)
    return result.scalars().all()
