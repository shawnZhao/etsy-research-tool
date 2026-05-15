from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.keyword import Keyword
from app.tasks.keyword_tasks import search_and_analyze_keyword

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.post("/search")
async def search_keyword(keyword: str, db: AsyncSession = Depends(get_db)):
    task = search_and_analyze_keyword.delay(keyword)
    return {"task_id": task.id, "status": "processing"}


@router.get("/")
async def list_keywords(
    sort: str = "last_updated",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
):
    col = getattr(Keyword, sort, Keyword.last_updated)
    if order == "asc":
        stmt = select(Keyword).order_by(col.asc()).limit(100)
    else:
        stmt = select(Keyword).order_by(col.desc()).limit(100)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{keyword_id}")
async def get_keyword(keyword_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Keyword).where(Keyword.id == keyword_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record


@router.get("/{keyword_id}/related")
async def get_related_tags(keyword_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Keyword).where(Keyword.id == keyword_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record.related_tags or []


@router.post("/compare")
async def compare_keywords(ids: list[str], db: AsyncSession = Depends(get_db)):
    from uuid import UUID
    uuid_ids = [UUID(i) for i in ids]
    stmt = select(Keyword).where(Keyword.id.in_(uuid_ids))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{keyword_id}/trend")
async def get_trend(keyword_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Keyword).where(Keyword.id == keyword_id)
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return record.trend_data or []
