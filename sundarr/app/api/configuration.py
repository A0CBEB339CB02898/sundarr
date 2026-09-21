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
    issues.sort(key=lambda item: (item.get("severity") != "required", item["id"]))
    issue_ids = sorted(item["id"] for item in issues)
    fingerprint = "ready" if not issue_ids else sha256("\n".join(issue_ids).encode("utf-8")).hexdigest()[:20]
    ready = not any(item.get("severity") == "required" for item in issues)
    return {"ready": ready, "fingerprint": fingerprint, "issues": issues}


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
    connections = {item.id: item for item in session.query(SmbConnection).all()}
    if not connections:
        return [{
            "id": "smb-connection-missing",
            "category": "sync",
            "severity": "required",
            "title": "尚未配置 SMB 连接",
            "message": "先添加远程或本地 NAS 的 SMB 连接，才能建立媒体库同步链路。",
            "action_label": "配置存储",
            "action_path": "/app/storage",
        }]
    local_libraries = {item.id: item for item in session.query(MediaLibrary).all()}
    if not local_libraries:
        return [{
            "id": "local-library-missing",
            "category": "sync",
            "severity": "required",
            "title": "尚未创建本地媒体库",
            "message": "选择已配置的 SMB 连接和目标目录，创建本地媒体库。",
            "action_label": "创建本地媒体库",
            "action_path": "/app/libraries",
        }]
    remote_libraries = {item.id: item for item in session.query(RemoteMediaLibrary).all()}
    if not remote_libraries:
        return [{
            "id": "remote-library-missing",
            "category": "sync",
            "severity": "required",
            "title": "尚未创建远程媒体库",
            "message": "绑定远程 SMB 目录，作为同步来源。",
            "action_label": "创建远程媒体库",
            "action_path": "/app/remote-libraries",
        }]
    bindings = session.query(SyncBinding).all()
    if not bindings:
        return [{
            "id": "sync-binding-missing",
            "category": "sync",
            "severity": "required",
            "title": "尚未建立同步绑定",
            "message": "连接远程媒体库和本地媒体库，Worker 才能创建同步任务。",
            "action_label": "建立同步绑定",
            "action_path": "/app/remote-libraries",
        }]
    warnings: list[dict[str, str]] = []
    executable_binding_count = 0

    for remote in remote_libraries.values():
        if remote.enabled and not remote.target_library_id:
            warnings.append({
                "id": f"remote-library-unbound:{remote.id}",
                "category": "sync",
                "severity": "recommended",
                "title": f"远程媒体库“{remote.name}”未绑定目标",
                "message": "该远程媒体库仍可浏览，但 Worker 不会为它自动创建同步任务。",
                "action_label": "绑定目标媒体库",
                "action_path": "/app/remote-libraries",
            })

    for connection in connections.values():
        if connection.enabled and connection.last_test_ok is False:
            warnings.append({
                "id": f"smb-connection-test-failed:{connection.id}",
                "category": "sync",
                "severity": "recommended",
                "title": f"SMB 连接“{connection.name}”最近测试失败",
                "message": "如果该连接参与同步，相关链路将无法执行；未使用的连接不会阻断其他有效链路。",
                "action_label": "检查存储连接",
                "action_path": "/app/storage",
            })

    for binding in bindings:
        blockers = _binding_blockers(binding, remote_libraries, local_libraries, connections)
        if not blockers:
            executable_binding_count += 1
            continue
        warnings.append({
            "id": f"sync-binding-unavailable:{binding.id}",
            "category": "sync",
            "severity": "recommended",
            "title": f"同步绑定“{binding.name}”当前不可执行",
            "message": "；".join(blockers) + "。",
            "action_label": "检查同步绑定",
            "action_path": "/app/remote-libraries",
        })

    if executable_binding_count:
        return warnings

    return [{
        "id": "sync-chain-unavailable",
        "category": "sync",
        "severity": "required",
        "title": "没有可执行的媒体库同步链路",
        "message": "至少需要一条已启用且连接、来源和目标均可用的同步绑定。",
        "action_label": "检查同步配置",
        "action_path": "/app/remote-libraries",
    }, *warnings]


def _binding_blockers(
    binding: SyncBinding,
    remote_libraries: dict[str, RemoteMediaLibrary],
    local_libraries: dict[str, MediaLibrary],
    connections: dict[str, SmbConnection],
) -> list[str]:
    blockers: list[str] = []
    if not binding.enabled:
        blockers.append("同步绑定已禁用")

    remote = remote_libraries.get(binding.remote_library_id)
    local = local_libraries.get(binding.local_library_id)
    if remote is None:
        blockers.append("远程媒体库不存在")
    if local is None:
        blockers.append("本地媒体库不存在")
    if remote is None or local is None:
        return blockers

    if not remote.enabled:
        blockers.append("远程媒体库已禁用")
    if not local.enabled:
        blockers.append("本地媒体库已禁用")
    if remote.target_library_id != local.id:
        blockers.append("远程媒体库未绑定到该目标")
    if binding.media_type != remote.media_type or binding.media_type != local.media_type:
        blockers.append("媒体类型不一致")
    if remote.last_test_ok is False:
        blockers.append("远程媒体库最近测试失败")
    if local.last_test_ok is False:
        blockers.append("本地媒体库最近测试失败")

    for label, connection_id in (("来源", remote.connection_id), ("目标", local.connection_id)):
        connection = connections.get(connection_id)
        if connection is None:
            blockers.append(f"{label} SMB 连接不存在")
        elif not connection.enabled:
            blockers.append(f"{label} SMB 连接已禁用")
        elif connection.last_test_ok is False:
            blockers.append(f"{label} SMB 连接最近测试失败")
    return blockers
