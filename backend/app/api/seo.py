import asyncio
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.seo_audit import SEOAudit
from app.tasks.seo_tasks import run_seo_audit

router = APIRouter(prefix="/seo", tags=["seo"])


class AuditRequest(BaseModel):
    listing_url: str = Field(..., min_length=1, max_length=2000)


def _extract_listing_id(url_or_id: str) -> int:
    """Extract listing ID from an Etsy listing URL or raw numeric string.

    Handles:
      - https://www.etsy.com/listing/123456789/...  -> 123456789
      - https://etsy.com/listing/123456789           -> 123456789
      - 123456789 (raw numeric ID)                   -> 123456789
    """
    match = re.search(r'etsy\.com/listing/(\d+)', url_or_id)
    if match:
        return int(match.group(1))
    try:
        return int(url_or_id)
    except (ValueError, TypeError):
        raise ValueError(f"Could not extract listing ID from: {url_or_id}")


# ---------------------------------------------------------------------------
# POST /seo/audit
# ---------------------------------------------------------------------------
@router.post("/audit")
async def audit_listing(req: AuditRequest):
    """Audit a listing's SEO. Accepts an Etsy listing URL or numeric ID."""
    try:
        listing_id = _extract_listing_id(req.listing_url.strip())
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Could not extract listing ID from URL"
        )

    loop = asyncio.get_event_loop()
    task = await loop.run_in_executor(None, run_seo_audit.delay, listing_id)
    return {"task_id": task.id}


# ---------------------------------------------------------------------------
# GET /seo/audits/{audit_id}
# ---------------------------------------------------------------------------
@router.get("/audits/{audit_id}")
async def get_audit(audit_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single SEO audit by its UUID."""
    try:
        aid = UUID(audit_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid audit ID: {audit_id}")

    stmt = select(SEOAudit).where(SEOAudit.id == aid)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Audit not found")
    return record


# ---------------------------------------------------------------------------
# GET /seo/audits
# ---------------------------------------------------------------------------
@router.get("/audits")
async def list_audits(
    listing_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List SEO audits, optionally filtered by listing UUID."""
    stmt = select(SEOAudit)
    if listing_id:
        try:
            lid = UUID(listing_id)
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"Invalid listing ID: {listing_id}"
            )
        stmt = stmt.where(SEOAudit.listing_id == lid)
    stmt = stmt.order_by(SEOAudit.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /seo/benchmarks
# ---------------------------------------------------------------------------
@router.get("/benchmarks")
async def get_benchmarks():
    """Get static benchmark scores for SEO comparison."""
    return {
        "avg_title_score": 65,
        "avg_tag_score": 60,
        "avg_description_score": 55,
        "avg_overall_score": 61,
    }
