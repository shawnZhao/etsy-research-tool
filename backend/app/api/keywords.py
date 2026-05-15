import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.keyword import Keyword
from app.tasks.keyword_tasks import search_and_analyze_keyword

router = APIRouter(prefix="/keywords", tags=["keywords"])

ALLOWED_SORT_COLUMNS = {
    "last_updated",
    "search_volume_est",
    "competition_score",
    "avg_price",
    "listing_count",
    "keyword",
    "trend_direction",
}


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=500)


def _parse_keyword_id(keyword_id: str) -> UUID:
    try:
        return UUID(keyword_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid keyword ID: {keyword_id}")


@router.post("/search")
async def search_keyword(req: SearchRequest):
    loop = asyncio.get_event_loop()
    task = await loop.run_in_executor(
        None, search_and_analyze_keyword.delay, req.keyword.strip()
    )
    return {"task_id": task.id}


@router.get("/")
async def list_keywords(
    sort: str = "last_updated",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    if sort not in ALLOWED_SORT_COLUMNS:
        sort = "last_updated"
    if order not in ("asc", "desc"):
        order = "desc"
    col = getattr(Keyword, sort)
    if order == "asc":
        stmt = select(Keyword).order_by(col.asc()).limit(100)
    else:
        stmt = select(Keyword).order_by(col.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{keyword_id}")
async def get_keyword(keyword_id: str, db: AsyncSession = Depends(get_db)):
    kid = _parse_keyword_id(keyword_id)
    stmt = select(Keyword).where(Keyword.id == kid)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record


@router.get("/{keyword_id}/related")
async def get_related_tags(keyword_id: str, db: AsyncSession = Depends(get_db)):
    kid = _parse_keyword_id(keyword_id)
    stmt = select(Keyword).where(Keyword.id == kid)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record.related_tags or []


@router.post("/compare")
async def compare_keywords(ids: list[str], db: AsyncSession = Depends(get_db)):
    try:
        uuid_ids = [UUID(i) for i in ids]
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid keyword ID in list: {e}")
    stmt = select(Keyword).where(Keyword.id.in_(uuid_ids))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{keyword_id}/trend")
async def get_trend(keyword_id: str, db: AsyncSession = Depends(get_db)):
    kid = _parse_keyword_id(keyword_id)
    stmt = select(Keyword).where(Keyword.id == kid)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record.trend_data or []
