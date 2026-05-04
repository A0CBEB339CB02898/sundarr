from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.transfer import TransferCreateRequest, TransferResponse
from sundarr.app.services.transfer_service import transfer_service

router = APIRouter(tags=["transfers"])


@router.post("/transfers", response_model=TransferResponse)
async def create_transfer(request: TransferCreateRequest, db: Session = Depends(get_db)) -> TransferResponse:
    try:
        return transfer_service.create_transfer(db, request)
    except ValueError as exc:
        raise _transfer_error(exc) from exc


@router.get("/transfers/{task_id}", response_model=TransferResponse)
async def get_transfer(task_id: str, db: Session = Depends(get_db)) -> TransferResponse:
    task = transfer_service.get_transfer(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="搬运任务不存在。")
    return task


def _transfer_error(exc: ValueError) -> HTTPException:
    messages = {
        "RESOURCE_LINK_NOT_FOUND": "资源链接不存在。",
    }
    return HTTPException(status_code=404, detail=messages.get(str(exc), "搬运任务请求无效。"))
