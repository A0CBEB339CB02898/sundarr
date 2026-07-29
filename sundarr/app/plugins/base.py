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
    - CLOUD_PROVIDER: 网盘 Provider 插件（如夸克、阿里云盘等）
    - NOTIFICATION: 通知渠道插件（如钉钉、飞书等）
    - CRAWLER: 爬虫插件（如豆瓣监控等）
    - LINK_VALIDATOR: 链接验证器插件
    - LINK_EXTRACTOR: 链接提取器插件
    - TASK_PROCESSOR: 任务处理器插件
    """

    SOURCE = "source"
    CLOUD_PROVIDER = "cloud_provider"
    NOTIFICATION = "notification"
    CRAWLER = "crawler"
    LINK_VALIDATOR = "link_validator"
    LINK_EXTRACTOR = "link_extractor"
    TASK_PROCESSOR = "task_processor"


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
        adapter_api_version: 适配器 API 版本（必须与 Sundarr 版本兼容）
        entry: 入口点（"module:function" 格式）
        config_schema: 配置字段声明（JSON Schema 格式）
        dependencies: 依赖的其他插件 ID 列表
    """

    id: str
    name: str
    version: str
    plugin_type: PluginType
    description: str
    author: str
    homepage_url: str
    adapter_api_version: str
    entry: str
    config_schema: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)


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
