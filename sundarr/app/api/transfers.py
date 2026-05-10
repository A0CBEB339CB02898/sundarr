from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from sundarr.app.core.database import get_db
from sundarr.app.schemas.transfer import TransferCreateRequest, TransferLogResponse, TransferResponse
from sundarr.app.services.transfer_service import transfer_service

router = APIRouter(tags=["transfers"])


@router.post("/transfers", response_model=TransferResponse)
async def create_transfer(request: TransferCreateRequest, db: Session = Depends(get_db)) -> TransferResponse:
    try:
        return transfer_service.create_transfer(db, request)
    except ValueError as exc:
        raise _transfer_error(exc) from exc


@router.get("/transfers", response_model=list[TransferResponse])
async def list_transfers(limit: int = 30, db: Session = Depends(get_db)) -> list[TransferResponse]:
    return transfer_service.list_transfers(db, limit=limit)


@router.get("/transfers/{task_id}", response_model=TransferResponse)
async def get_transfer(task_id: str, db: Session = Depends(get_db)) -> TransferResponse:
    task = transfer_service.get_transfer(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="搬运任务不存在。")
    return task


@router.post("/transfers/{task_id}/cancel", response_model=TransferResponse)
async def cancel_transfer(task_id: str, db: Session = Depends(get_db)) -> TransferResponse:
    try:
        return transfer_service.cancel_transfer(db, task_id)
    except ValueError as exc:
        raise _transfer_error(exc) from exc


@router.post("/transfers/{task_id}/retry", response_model=TransferResponse)
async def retry_transfer(task_id: str, db: Session = Depends(get_db)) -> TransferResponse:
    try:
        return transfer_service.retry_transfer(db, task_id)
    except ValueError as exc:
        raise _transfer_error(exc) from exc


@router.post("/transfers/{task_id}/pause", response_model=TransferResponse)
async def pause_transfer(task_id: str, db: Session = Depends(get_db)) -> TransferResponse:
    try:
        return transfer_service.pause_transfer(db, task_id)
    except ValueError as exc:
        raise _transfer_error(exc) from exc


@router.post("/transfers/{task_id}/resume", response_model=TransferResponse)
async def resume_transfer(task_id: str, db: Session = Depends(get_db)) -> TransferResponse:
    try:
        return transfer_service.resume_transfer(db, task_id)
    except ValueError as exc:
        raise _transfer_error(exc) from exc


@router.get("/transfers/{task_id}/logs", response_model=list[TransferLogResponse])
async def list_transfer_logs(task_id: str, db: Session = Depends(get_db)) -> list[TransferLogResponse]:
    try:
        return transfer_service.list_transfer_logs(db, task_id)
    except ValueError as exc:
        raise _transfer_error(exc) from exc


@router.post("/transfers/{task_id}/delete")
async def delete_transfer(task_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        transfer_service.delete_transfer(db, task_id)
        return {"ok": True}
    except ValueError as exc:
        raise _transfer_error(exc) from exc


@router.post("/transfers/clear-completed")
async def clear_completed_transfers(db: Session = Depends(get_db)) -> dict:
    count = transfer_service.clear_completed(db)
    return {"ok": True, "deleted_count": count}


def _transfer_error(exc: ValueError) -> HTTPException:
    messages = {
        "RESOURCE_LINK_NOT_FOUND": "资源链接不存在。",
        "TRANSFER_TASK_NOT_FOUND": "搬运任务不存在。",
        "TRANSFER_TASK_NOT_CANCELLABLE": "当前任务状态不允许取消。",
        "TRANSFER_TASK_NOT_RETRYABLE": "当前任务状态不允许重试。",
        "TRANSFER_TASK_NOT_PAUSABLE": "当前任务状态不允许暂停。",
        "TRANSFER_TASK_NOT_RESUMABLE": "当前任务未处于暂停状态。",
    }
    status_code = (
        409
        if str(exc)
        in {
            "TRANSFER_TASK_NOT_CANCELLABLE",
            "TRANSFER_TASK_NOT_RETRYABLE",
            "TRANSFER_TASK_NOT_PAUSABLE",
            "TRANSFER_TASK_NOT_RESUMABLE",
        }
        else 404
    )
    return HTTPException(status_code=status_code, detail=messages.get(str(exc), "搬运任务请求无效。"))
