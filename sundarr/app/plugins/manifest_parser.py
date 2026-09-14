"""Plugin Manifest v1/v2 的纯解析和校验。"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .base import PluginManifest, PluginType

_PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")
_ENTRY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*$")
_SUPPORTED_PLUGIN_API_VERSION = "1.0"
_SUPPORTED_V2_PLUGIN_TYPES = {PluginType.SOURCE, PluginType.CATALOG_PROVIDER, PluginType.WATCHLIST_PROVIDER}


class PluginManifestParser:
    """不接触 Git 和动态导入的 Manifest 解析器。"""

    def parse_manifests(self, repo_path: Path) -> list[PluginManifest]:
        repo_path = Path(repo_path).resolve()
        manifest_path = (repo_path / "sundarr_plugin.toml").resolve()
        if not manifest_path.is_relative_to(repo_path):
            raise ValueError("插件清单路径不能超出仓库目录")
        if not manifest_path.is_file():
            raise FileNotFoundError(f"插件清单文件不存在：{manifest_path}")
        with manifest_path.open("rb") as file:
            data = tomllib.load(file)
        manifest_version = data.get("manifest_version")
        if manifest_version is None:
            return [self._parse_flat_v1_manifest(data)]
        if manifest_version != 2:
            raise ValueError(f"不支持的 manifest_version：{manifest_version}")
        plugin_items = data.get("plugins")
        if not isinstance(plugin_items, list) or not plugin_items:
            raise ValueError("通用 v2 插件清单必须包含至少一个 [[plugins]] 声明")
        manifests = [self._parse_v2_manifest_item(item) for item in plugin_items]
        plugin_ids = [manifest.id for manifest in manifests]
        duplicate_ids = sorted({item for item in plugin_ids if plugin_ids.count(item) > 1})
        if duplicate_ids:
            raise ValueError(f"插件清单存在重复 plugin_id：{'、'.join(duplicate_ids)}")
        return manifests

    def _parse_manifest(self, repo_path: Path) -> PluginManifest:
        manifests = self.parse_manifests(repo_path)
        if len(manifests) != 1 or manifests[0].manifest_version != 1:
            raise NotImplementedError("通用 v2 必须通过候选 Activation 流程加载，旧 flat v1 入口不执行 v2")
        return manifests[0]

    def _parse_flat_v1_manifest(self, data: Mapping[str, Any]) -> PluginManifest:
        self._require_manifest_fields(data, "id", "name", "version", "plugin_type", "entry")
        plugin_type = self._parse_plugin_type(data["plugin_type"])
        if plugin_type != PluginType.SOURCE:
            raise ValueError("flat v1 插件清单只支持 source 类型")
        plugin_api_version = str(data.get("adapter_api_version", "1.0"))
        self._validate_plugin_api_version(plugin_api_version)
        return PluginManifest(
            id=self._validate_plugin_id(data["id"]), name=str(data["name"]), version=str(data["version"]),
            plugin_type=plugin_type, entry=self._validate_entry(data["entry"]),
            plugin_api_version=plugin_api_version, description=str(data.get("description", "")),
            author=str(data.get("author", "")), homepage_url=str(data.get("homepage_url", "")),
            config_schema=dict(self._validate_mapping(data.get("config_schema", {}), "config_schema")),
            manifest_version=1,
            dependencies=self._validate_string_list(data.get("dependencies", []), "dependencies"),
        )

    def _parse_v2_manifest_item(self, data: Any) -> PluginManifest:
        if not isinstance(data, Mapping):
            raise ValueError("[[plugins]] 声明必须是 TOML table")
        self._require_manifest_fields(data, "id", "name", "version", "plugin_type", "plugin_api_version", "entry")
        plugin_type = self._parse_plugin_type(data["plugin_type"])
        if plugin_type not in _SUPPORTED_V2_PLUGIN_TYPES:
            raise ValueError(f"当前版本尚不能激活插件类型：{plugin_type.value}")
        plugin_api_version = str(data["plugin_api_version"])
        self._validate_plugin_api_version(plugin_api_version)
        runtime = self._validate_mapping(data.get("runtime", {}), "runtime")
        requires = self._validate_string_list(runtime.get("requires", []), "runtime.requires")
        provides = self._validate_string_list(runtime.get("provides", []), "runtime.provides")
        if not provides:
            raise ValueError("通用 v2 插件声明必须提供至少一个 runtime.provides 能力")
        return PluginManifest(
            id=self._validate_plugin_id(data["id"]), name=str(data["name"]), version=str(data["version"]),
            plugin_type=plugin_type, entry=self._validate_entry(data["entry"]),
            plugin_api_version=plugin_api_version, description=str(data.get("description", "")),
            author=str(data.get("author", "")), homepage_url=str(data.get("homepage_url", "")),
            config_schema=dict(self._validate_mapping(data.get("config_schema", {}), "config_schema")),
            manifest_version=2, requires=requires, provides=provides,
        )

    @staticmethod
    def _require_manifest_fields(data: Mapping[str, Any], *fields: str) -> None:
        for field in fields:
            if field not in data:
                raise ValueError(f"插件清单缺少必填字段：{field}")

    @staticmethod
    def _parse_plugin_type(value: Any) -> PluginType:
        try:
            return PluginType(str(value))
        except ValueError as error:
            raise ValueError(f"无效的插件类型：{value}") from error

    @staticmethod
    def _validate_plugin_id(value: Any) -> str:
        plugin_id = str(value)
        if not _PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            raise ValueError(f"无效的插件 id：{plugin_id}")
        return plugin_id

    @staticmethod
    def _validate_entry(value: Any) -> str:
        entry = str(value)
        if not _ENTRY_PATTERN.fullmatch(entry):
            raise ValueError(f"无效的插件 entry：{entry}")
        return entry

    @staticmethod
    def _validate_plugin_api_version(value: str) -> None:
        if value != _SUPPORTED_PLUGIN_API_VERSION:
            raise ValueError(f"不支持的 plugin_api_version：{value}")

    @staticmethod
    def _validate_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
        if not isinstance(value, Mapping):
            raise ValueError(f"插件清单字段 {field_name} 必须是 TOML table")
        return value

    @staticmethod
    def _validate_string_list(value: Any, field_name: str) -> list[str]:
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError(f"插件清单字段 {field_name} 必须是非空字符串数组")
        if len(value) != len(set(value)):
            raise ValueError(f"插件清单字段 {field_name} 不能包含重复值")
        return list(value)
