"""
插件相关数据库模型

定义插件仓库、插件配置和插件日志的数据库模型。
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from ..core.database import Base
from .mixins import TimestampMixin


class PluginRepository(Base, TimestampMixin):
    """
    插件仓库配置

    存储 Git 仓库的配置信息，用于加载外部插件。

    Attributes:
        id: 仓库 ID（主键）
        name: 仓库显示名称
        repo_url: Git 仓库 URL
        branch: 分支名称
        current_commit: 当前使用的 commit hash
        previous_commit: 上一个 commit hash（用于回滚）
        auto_update: 是否自动更新
        enabled: 是否启用
        status: 状态（"pending", "loaded", "error"）
        last_error: 最后一次错误信息
        last_checked_at: 最后一次检查时间
        last_loaded_at: 最后一次加载时间
    """

    __tablename__ = "plugin_repositories"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    repo_url = Column(String, nullable=False, unique=True)
    branch = Column(String, default="main")
    current_commit = Column(String)
    previous_commit = Column(String)
    auto_update = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    status = Column(String, default="pending")  # pending, loaded, error
    last_error = Column(Text)
    last_checked_at = Column(DateTime)
    last_loaded_at = Column(DateTime)

    # 关联
    configs = relationship("PluginConfig", back_populates="repository")

    def __repr__(self):
        return f"<PluginRepository(id={self.id}, name={self.name}, status={self.status})>"


class PluginConfig(Base, TimestampMixin):
    """
    插件配置

    存储插件的运行时配置。

    Attributes:
        id: 配置 ID（主键）
        plugin_id: 插件 ID
        plugin_type: 插件类型
        config_data: 配置数据（JSON）
        enabled: 是否启用
        status: 状态（"active", "disabled", "error"）
        repository_id: 关联的仓库 ID
    """

    __tablename__ = "plugin_configs"

    id = Column(String, primary_key=True, index=True)
    plugin_id = Column(String, nullable=False, unique=True, index=True)
    plugin_type = Column(String, nullable=False)
    config_data = Column(Text, default="{}")  # JSON 字符串
    enabled = Column(Boolean, default=True)
    status = Column(String, default="active")  # active, disabled, error
    repository_id = Column(String, ForeignKey("plugin_repositories.id"))

    # 关联
    repository = relationship("PluginRepository", back_populates="configs")

    def __repr__(self):
        return f"<PluginConfig(id={self.id}, plugin_id={self.plugin_id}, enabled={self.enabled})>"


class PluginLog(Base, TimestampMixin):
    """
    插件日志

    存储插件运行时的日志信息。

    Attributes:
        id: 日志 ID（主键）
        plugin_id: 插件 ID
        level: 日志级别（"info", "warn", "error", "debug"）
        message: 日志消息
        details: 详细信息（JSON）
        timestamp: 时间戳
    """

    __tablename__ = "plugin_logs"

    id = Column(String, primary_key=True, index=True)
    plugin_id = Column(String, nullable=False, index=True)
    level = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text)  # JSON 字符串
    timestamp = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<PluginLog(id={self.id}, plugin_id={self.plugin_id}, level={self.level})>"
