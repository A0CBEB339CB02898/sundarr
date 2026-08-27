"""
插件系统基础抽象

定义插件类型、清单和已加载插件的数据结构。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from datetime import datetime


class PluginType(str, Enum):
    """
    插件类型枚举

    每种类型对应一种特定的功能扩展点：
    - SOURCE: 搜索源插件（如影视资源站、Bilibili 等）
    - CATALOG_PROVIDER: 媒体目录插件
    - WATCHLIST_PROVIDER: 外部想看列表插件
    - TRANSFER_DRIVER: 后续搬运驱动扩展点，当前不允许激活
    - NOTIFICATION: 后续通知扩展点，当前不允许激活
    """

    SOURCE = "source"
    CATALOG_PROVIDER = "catalog_provider"
    WATCHLIST_PROVIDER = "watchlist_provider"
    TRANSFER_DRIVER = "transfer_driver"
    NOTIFICATION = "notification"


@dataclass
class PluginManifest:
    """
    插件清单 - 声明式配置

    描述插件的元数据、配置和入口点。存储在 sundarr_plugin.toml 文件中。

    Attributes:
        id: 插件唯一标识符（如 "quark-provider"）
        name: 插件显示名称（如 "夸克网盘 Provider"）
        version: 插件版本号（如 "1.0.0"）
        plugin_type: 插件类型
        description: 插件描述
        author: 作者
        homepage_url: 项目主页 URL
        plugin_api_version: 插件 API 版本（必须与 Sundarr 版本兼容）
        entry: 入口点（"module:function" 格式）
        config_schema: 配置字段声明（JSON Schema 格式）
        manifest_version: 清单格式版本；flat v1 为 1，通用清单为 2
        requires: 激活前需要的 Core 能力
        provides: 激活成功后提供的插件能力
        dependencies: flat v1 遗留兼容字段
    """

    id: str
    name: str
    version: str
    plugin_type: PluginType
    entry: str
    plugin_api_version: str
    description: str = ""
    author: str = ""
    homepage_url: str = ""
    config_schema: Dict[str, Any] = field(default_factory=dict)
    manifest_version: int = 1
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    @property
    def adapter_api_version(self) -> str:
        """兼容旧 API 字段名；新代码统一使用 plugin_api_version。"""

        return self.plugin_api_version


@dataclass
class LoadedPlugin:
    """
    已加载插件 - 加载结果

    描述插件的加载状态和实例信息。

    Attributes:
        manifest: 插件清单
        module: Python 模块对象
        instance: 插件实例（具体类型取决于 plugin_type）
        status: 加载状态（"loaded", "error", "disabled"）
        error_message: 错误消息（如果 status 为 "error"）
        commit_hash: Git commit hash（如果是从 Git 仓库加载）
        repo_path: 本地仓库路径（如果是从 Git 仓库加载）
        loaded_at: 加载时间
    """

    manifest: PluginManifest
    module: Any
    instance: Any
    status: str
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None
    repo_path: Optional[str] = None
    loaded_at: datetime = field(default_factory=datetime.now)

    @property
    def is_loaded(self) -> bool:
        """检查插件是否已成功加载"""
        return self.status == "loaded"

    @property
    def is_enabled(self) -> bool:
        """检查插件是否启用（已加载且未禁用）"""
        return self.status == "loaded"

    @property
    def has_error(self) -> bool:
        """检查插件是否有错误"""
        return self.status == "error"


# 类型别名
SearchFunction = Callable[..., Coroutine[Any, Any, List[Any]]]
TestFunction = Callable[..., Coroutine[Any, Any, Any]]
FetchDetailFunction = Callable[..., Coroutine[Any, Any, Any]]
