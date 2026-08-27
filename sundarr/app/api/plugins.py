"""
插件管理 API

提供插件仓库管理、插件配置管理等 API 端点。
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.plugin import PluginConfig, PluginRepository
from ..plugins.base import PluginType
from ..plugins.manager import plugin_manager
from ..plugins.registry import plugin_registry
from ..schemas.plugin import (
    PluginConfigUpdate,
    PluginInfo,
    PluginRepositoryCreate,
    PluginRepositoryUpdate,
    PluginStats,
)

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("/repositories", response_model=List[Dict[str, Any]])
def list_repositories(
    session: Session = Depends(get_db),
):
    """获取所有插件仓库"""
    repos = session.query(PluginRepository).all()
    return [
        {
            "id": repo.id,
            "name": repo.name,
            "repo_url": repo.repo_url,
            "branch": repo.branch,
            "current_commit": repo.current_commit,
            "previous_commit": repo.previous_commit,
            "auto_update": repo.auto_update,
            "enabled": repo.enabled,
            "status": repo.status,
            "last_error": repo.last_error,
            "last_checked_at": repo.last_checked_at.isoformat() if repo.last_checked_at else None,
            "last_loaded_at": repo.last_loaded_at.isoformat() if repo.last_loaded_at else None,
        }
        for repo in repos
    ]


@router.post("/repositories", response_model=Dict[str, Any])
def add_repository(
    data: PluginRepositoryCreate,
    session: Session = Depends(get_db),
):
    """添加插件仓库"""
    try:
        loaded = plugin_manager.add_repository(
            session=session,
            repo_url=data.repo_url,
            branch=data.branch,
            name=data.name,
            auto_update=data.auto_update,
        )
        return {
            "status": "success",
            "message": f"仓库已添加：{loaded.manifest.name}",
            "plugin_id": loaded.manifest.id,
            "commit": loaded.commit_hash,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/repositories/{repo_id}", response_model=Dict[str, Any])
def update_repository(
    repo_id: str,
    data: PluginRepositoryUpdate,
    session: Session = Depends(get_db),
):
    """更新仓库到最新或指定 commit"""
    try:
        loaded = plugin_manager.update_repository(
            session=session,
            repo_id=repo_id,
            new_commit=data.new_commit,
        )
        return {
            "status": "success",
            "message": f"仓库已更新：{loaded.manifest.name}",
            "new_commit": loaded.commit_hash,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/repositories/{repo_id}/rollback", response_model=Dict[str, Any])
def rollback_repository(
    repo_id: str,
    session: Session = Depends(get_db),
):
    """回滚仓库到上一个版本"""
    try:
        loaded = plugin_manager.rollback_repository(
            session=session,
            repo_id=repo_id,
        )
        return {
            "status": "success",
            "message": f"仓库已回滚：{loaded.manifest.name}",
            "new_commit": loaded.commit_hash,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/repositories/{repo_id}", response_model=Dict[str, Any])
def delete_repository(
    repo_id: str,
    session: Session = Depends(get_db),
):
    """删除仓库"""
    try:
        plugin_manager.remove_repository(
            session=session,
            repo_id=repo_id,
        )
        return {
            "status": "success",
            "message": "仓库已删除",
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plugins", response_model=List[Dict[str, Any]])
def list_plugins(
    plugin_type: Optional[PluginType] = None,
    include_disabled: bool = False,
):
    """获取所有插件"""
    if plugin_type:
        plugins = plugin_registry.get_plugins_by_type(
            plugin_type,
            include_disabled=include_disabled,
        )
    else:
        plugins = plugin_registry.get_all_plugins(
            include_disabled=include_disabled,
        )

    return [
        {
            "id": p.manifest.id,
            "name": p.manifest.name,
            "version": p.manifest.version,
            "plugin_type": p.manifest.plugin_type.value,
            "description": p.manifest.description,
            "author": p.manifest.author,
            "homepage_url": p.manifest.homepage_url,
            "status": p.status,
            "error_message": p.error_message,
            "commit_hash": p.commit_hash,
            "repo_path": p.repo_path,
        }
        for p in plugins
    ]


@router.get("/plugins/{plugin_id}", response_model=Dict[str, Any])
def get_plugin(plugin_id: str):
    """获取插件详情"""
    plugin = plugin_registry.get_plugin(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="插件不存在")

    return {
        "id": plugin.manifest.id,
        "name": plugin.manifest.name,
        "version": plugin.manifest.version,
        "plugin_type": plugin.manifest.plugin_type.value,
        "description": plugin.manifest.description,
        "author": plugin.manifest.author,
        "homepage_url": plugin.manifest.homepage_url,
        "manifest_version": plugin.manifest.manifest_version,
        "plugin_api_version": plugin.manifest.plugin_api_version,
        "adapter_api_version": plugin.manifest.adapter_api_version,
        "entry": plugin.manifest.entry,
        "config_schema": plugin.manifest.config_schema,
        "requires": plugin.manifest.requires,
        "provides": plugin.manifest.provides,
        "dependencies": plugin.manifest.dependencies,
        "status": plugin.status,
        "error_message": plugin.error_message,
        "commit_hash": plugin.commit_hash,
        "repo_path": plugin.repo_path,
    }


@router.put("/plugins/{plugin_id}/config", response_model=Dict[str, Any])
def update_plugin_config(
    plugin_id: str,
    data: PluginConfigUpdate,
    session: Session = Depends(get_db),
):
    """更新插件配置"""
    try:
        plugin_manager.update_plugin_config(
            session=session,
            plugin_id=plugin_id,
            config_data=data.config_data,
        )
        return {
            "status": "success",
            "message": "插件配置已更新",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/plugins/{plugin_id}/enable", response_model=Dict[str, Any])
def enable_plugin(
    plugin_id: str,
    session: Session = Depends(get_db),
):
    """启用插件"""
    plugin_manager.enable_plugin(session, plugin_id)
    return {
        "status": "success",
        "message": "插件已启用",
    }


@router.post("/plugins/{plugin_id}/disable", response_model=Dict[str, Any])
def disable_plugin(
    plugin_id: str,
    session: Session = Depends(get_db),
):
    """禁用插件"""
    plugin_manager.disable_plugin(session, plugin_id)
    return {
        "status": "success",
        "message": "插件已禁用",
    }


@router.get("/stats", response_model=Dict[str, int])
def get_stats():
    """获取插件统计信息"""
    return plugin_manager.get_plugin_stats()


@router.post("/load-all", response_model=Dict[str, Any])
def load_all_repositories(
    session: Session = Depends(get_db),
):
    """加载所有已配置的仓库"""
    try:
        stats = plugin_manager.load_all_repositories(session)
        return {
            "status": "success",
            "message": f"加载完成：总计 {stats['total']}，成功 {stats['loaded']}，失败 {stats['error']}",
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
