"""系统配置就绪状态 API。"""

from __future__ import annotations

from hashlib import sha256
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import MediaLibrary, RemoteMediaLibrary, SmbConnection, SyncBinding
from ..plugins.manager import plugin_manager


router = APIRouter(prefix="/configuration", tags=["configuration"])


@router.get("/readiness", response_model=dict[str, Any])
def configuration_readiness(session: Session = Depends(get_db)) -> dict[str, Any]:
    """返回当前可执行的配置缺口，不包含任何配置值。"""

    issues = _plugin_issues(session)
    issues.extend(_sync_setup_issues(session))
    issue_ids = sorted(item["id"] for item in issues)
    fingerprint = "ready" if not issue_ids else sha256("\n".join(issue_ids).encode("utf-8")).hexdigest()[:20]
    return {"ready": not issues, "fingerprint": fingerprint, "issues": issues}


def _plugin_issues(session: Session) -> list[dict[str, str]]:
    plugins = plugin_manager.list_plugins(session)
    issues: list[dict[str, str]] = []
    catalog_plugins = [item for item in plugins if item["plugin_type"] == "catalog_provider"]
    for plugin in plugins:
        missing_fields = plugin.get("missing_required_config") or []
        if not missing_fields:
            continue
        config_schema = plugin.get("config_schema") or {}
        missing_labels = [
            str((config_schema.get(field_name) or {}).get("label") or field_name)
            for field_name in missing_fields
        ]
        issues.append({
            "id": f"plugin-required-config:{plugin['id']}",
            "category": "plugin",
            "severity": "required",
            "title": f"{plugin['name']} 缺少必填配置",
            "message": f"需要配置：{'、'.join(missing_labels)}。保存后再启用插件。",
            "action_label": "配置插件",
            "action_path": f"/app/plugins?plugin_id={quote(plugin['id'])}",
        })
    if not catalog_plugins:
        issues.append({
            "id": "catalog-provider-missing",
            "category": "plugin",
            "severity": "required",
            "title": "媒体发现尚未配置",
            "message": "添加并配置至少一个 CATALOG_PROVIDER，发现页才会显示真实目录数据。",
            "action_label": "管理插件",
            "action_path": "/app/plugins",
        })
    elif not any(item["enabled"] and not item.get("configuration_required") for item in catalog_plugins):
        if not any(item.get("configuration_required") for item in catalog_plugins):
            issues.append({
                "id": "catalog-provider-disabled",
                "category": "plugin",
                "severity": "required",
                "title": "目录 Provider 尚未启用",
                "message": "启用一个已配置的 CATALOG_PROVIDER，发现页才会请求真实目录数据。",
                "action_label": "管理插件",
                "action_path": "/app/plugins",
            })
    return issues


def _sync_setup_issues(session: Session) -> list[dict[str, str]]:
    if session.query(SmbConnection).count() == 0:
        return [{
            "id": "smb-connection-missing",
            "category": "sync",
            "severity": "required",
            "title": "尚未配置 SMB 连接",
            "message": "先添加远程或本地 NAS 的 SMB 连接，才能建立媒体库同步链路。",
            "action_label": "配置存储",
            "action_path": "/app/storage",
        }]
    if session.query(MediaLibrary).count() == 0:
        return [{
            "id": "local-library-missing",
            "category": "sync",
            "severity": "required",
            "title": "尚未创建本地媒体库",
            "message": "选择已配置的 SMB 连接和目标目录，创建本地媒体库。",
            "action_label": "创建本地媒体库",
            "action_path": "/app/libraries",
        }]
    if session.query(RemoteMediaLibrary).count() == 0:
        return [{
            "id": "remote-library-missing",
            "category": "sync",
            "severity": "required",
            "title": "尚未创建远程媒体库",
            "message": "绑定远程 SMB 目录，作为同步来源。",
            "action_label": "创建远程媒体库",
            "action_path": "/app/remote-libraries",
        }]
    if session.query(SyncBinding).count() == 0:
        return [{
            "id": "sync-binding-missing",
            "category": "sync",
            "severity": "required",
            "title": "尚未建立同步绑定",
            "message": "连接远程媒体库和本地媒体库，Worker 才能创建同步任务。",
            "action_label": "建立同步绑定",
            "action_path": "/app/remote-libraries",
        }]
    return []
