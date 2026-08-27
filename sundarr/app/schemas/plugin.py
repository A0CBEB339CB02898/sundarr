"""
插件 API Schema

定义插件 API 的请求和响应模型。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PluginRepositoryCreate(BaseModel):
    """创建插件仓库请求"""

    repo_url: str = Field(..., description="Git 仓库 URL")
    branch: str = Field("main", description="分支名称")
    name: Optional[str] = Field(None, description="仓库显示名称")
    auto_update: bool = Field(False, description="是否自动更新")


class PluginRepositoryUpdate(BaseModel):
    """更新插件仓库请求"""

    new_commit: Optional[str] = Field(None, description="新的 commit hash")


class PluginConfigUpdate(BaseModel):
    """更新插件配置请求"""

    config_data: Dict[str, Any] = Field(..., description="配置数据")


class PluginInfo(BaseModel):
    """插件信息"""

    id: str
    name: str
    version: str
    plugin_type: str
    description: str
    author: str
    homepage_url: str
    status: str
    error_message: Optional[str] = None
    commit_hash: Optional[str] = None
    repo_path: Optional[str] = None


class PluginStats(BaseModel):
    """插件统计信息"""

    total: int
    builtin: int
    external: int
    loaded: int
    error: int
    disabled: int
    source: int
    catalog_provider: int
    watchlist_provider: int
    transfer_driver: int
    notification: int
