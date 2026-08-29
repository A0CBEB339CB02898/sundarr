"""插件仓库、配置和 Activation 诊断 API。"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.plugin import PluginConfig, PluginRepository
from ..plugins.manager import plugin_manager
from ..schemas.plugin import PluginConfigUpdate, PluginRepositoryCreate, PluginRepositoryUpdate


router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("/repositories", response_model=list[dict[str, Any]])
def list_repositories(session: Session = Depends(get_db)):
    """获取全部插件仓库及其多插件 ID。"""

    repositories = session.query(PluginRepository).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "repo_url": item.repo_url,
            "branch": item.branch,
            "current_commit": item.current_commit,
            "previous_commit": item.previous_commit,
            "auto_update": item.auto_update,
            "enabled": item.enabled,
            "status": item.status,
            "last_error": item.last_error,
            "plugin_ids": [config.plugin_id for config in item.configs],
            "last_checked_at": item.last_checked_at,
            "last_loaded_at": item.last_loaded_at,
        }
        for item in repositories
    ]


@router.post("/repositories", response_model=dict[str, Any])
async def add_repository(data: PluginRepositoryCreate, session: Session = Depends(get_db)):
    try:
        result = await plugin_manager.add_repository(
            session,
            repo_url=data.repo_url,
            branch=data.branch,
            name=data.name,
            auto_update=data.auto_update,
            configs=data.configs,
            disabled_plugin_ids=set(data.disabled_plugin_ids),
        )
        return _result_response("插件仓库已添加", result)
    except Exception as exc:
        repository = session.query(PluginRepository).filter(PluginRepository.repo_url == data.repo_url).first()
        detail = repository.last_error if repository and repository.last_error else "插件仓库添加失败，请查看仓库诊断"
        raise HTTPException(status_code=400, detail=detail) from exc


@router.put("/repositories/{repo_id}", response_model=dict[str, Any])
async def update_repository(
    repo_id: str,
    data: PluginRepositoryUpdate,
    session: Session = Depends(get_db),
):
    try:
        result = await plugin_manager.update_repository(session, repo_id, data.new_commit)
        return _result_response("插件仓库已更新", result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_repository_error(session, repo_id, "插件仓库更新失败")) from exc


@router.post("/repositories/{repo_id}/rollback", response_model=dict[str, Any])
async def rollback_repository(repo_id: str, session: Session = Depends(get_db)):
    try:
        result = await plugin_manager.rollback_repository(session, repo_id)
        return _result_response("插件仓库已回滚", result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=_repository_error(session, repo_id, "插件仓库回滚失败")) from exc


@router.delete("/repositories/{repo_id}", response_model=dict[str, Any])
async def delete_repository(repo_id: str, session: Session = Depends(get_db)):
    try:
        await plugin_manager.remove_repository(session, repo_id)
        return {"status": "success", "message": "插件仓库已删除"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="插件仓库删除失败，请查看服务日志") from exc


@router.get("/plugins", response_model=list[dict[str, Any]])
def list_plugins(session: Session = Depends(get_db)):
    return plugin_manager.list_plugins(session)


@router.get("/plugins/{plugin_id}", response_model=dict[str, Any])
def get_plugin(plugin_id: str, session: Session = Depends(get_db)):
    plugin = next((item for item in plugin_manager.list_plugins(session) if item["id"] == plugin_id), None)
    if plugin is None:
        raise HTTPException(status_code=404, detail="插件不存在")
    plugin["config"] = plugin_manager.get_plugin_config(session, plugin_id)
    return plugin


@router.get("/plugins/{plugin_id}/config", response_model=dict[str, Any])
def get_plugin_config(plugin_id: str, session: Session = Depends(get_db)):
    try:
        return {"plugin_id": plugin_id, "config_data": plugin_manager.get_plugin_config(session, plugin_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/plugins/{plugin_id}/config", response_model=dict[str, Any])
async def update_plugin_config(
    plugin_id: str,
    data: PluginConfigUpdate,
    session: Session = Depends(get_db),
):
    try:
        await plugin_manager.update_plugin_config(session, plugin_id, data.config_data)
        return {"status": "success", "message": "插件配置已更新"}
    except ValueError as exc:
        row = session.query(PluginConfig).filter(PluginConfig.plugin_id == plugin_id).first()
        detail = row.last_error if row and row.last_error else str(exc)
        raise HTTPException(status_code=400, detail=detail) from exc
    except Exception as exc:
        row = session.query(PluginConfig).filter(PluginConfig.plugin_id == plugin_id).first()
        detail = row.last_error if row and row.last_error else "插件配置应用失败"
        raise HTTPException(status_code=400, detail=detail) from exc


@router.post("/plugins/{plugin_id}/enable", response_model=dict[str, Any])
async def enable_plugin(plugin_id: str, session: Session = Depends(get_db)):
    try:
        await plugin_manager.enable_plugin(session, plugin_id)
        return {"status": "success", "message": "插件已启用"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        row = session.query(PluginConfig).filter(PluginConfig.plugin_id == plugin_id).first()
        detail = row.last_error if row and row.last_error else "插件启用失败"
        raise HTTPException(status_code=400, detail=detail) from exc


@router.post("/plugins/{plugin_id}/disable", response_model=dict[str, Any])
async def disable_plugin(plugin_id: str, session: Session = Depends(get_db)):
    try:
        await plugin_manager.disable_plugin(session, plugin_id)
        return {"status": "success", "message": "插件已禁用"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/activations", response_model=list[dict[str, Any]])
def list_activations():
    return plugin_manager.activation_diagnostics()


@router.get("/activations/{plugin_id}", response_model=dict[str, Any])
def get_activation(plugin_id: str):
    diagnostic = plugin_manager.activation_diagnostic(plugin_id)
    if diagnostic is None:
        raise HTTPException(status_code=404, detail="当前进程没有该插件的 active Activation")
    return diagnostic


@router.get("/stats", response_model=dict[str, int])
def get_stats(session: Session = Depends(get_db)):
    plugins = plugin_manager.list_plugins(session)
    return {
        "total": len(plugins),
        "active": sum(item["status"] == "active" for item in plugins),
        "disabled": sum(item["status"] == "disabled" for item in plugins),
        "error": sum(item["status"] == "error" for item in plugins),
    }


@router.post("/load-all", response_model=dict[str, Any])
async def load_all_repositories(session: Session = Depends(get_db)):
    stats = await plugin_manager.load_all_repositories(session)
    return {"status": "success", "message": "插件仓库恢复完成", "stats": stats}


def _result_response(message: str, result: Any) -> dict[str, Any]:
    return {
        "status": "success",
        "message": message,
        "repository_id": result.repository_id,
        "commit": result.commit_hash,
        "plugin_ids": list(result.plugin_ids),
    }


def _repository_error(session: Session, repo_id: str, fallback: str) -> str:
    repository = session.get(PluginRepository, repo_id)
    return repository.last_error if repository and repository.last_error else fallback
