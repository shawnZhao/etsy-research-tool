from fastapi import APIRouter
from celery.result import AsyncResult
from app.tasks.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)
    response = {"task_id": task_id, "status": result.state}
    if result.state == "SUCCESS":
        response["result"] = result.result
    elif result.state == "FAILURE":
        response["error"] = str(result.info)
    return response
