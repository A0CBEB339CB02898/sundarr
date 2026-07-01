"""
SMB 连接池管理器

提供 SMB 连接的连接池机制，支持：
- 连接复用
- 自动重连
- 连接健康检查
- 错误恢复
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sundarr.app.storage.smb import SmbConfig, SmbWriter

logger = logging.getLogger(__name__)


@dataclass
class PooledConnection:
    """
    连接池中的连接

    Attributes:
        writer: SmbWriter 实例
        config: 连接配置
        created_at: 创建时间
        last_used_at: 最后使用时间
        last_checked_at: 最后检查时间
        use_count: 使用次数
        error_count: 错误次数
        is_healthy: 是否健康
    """

    writer: SmbWriter
    config: SmbConfig
    created_at: datetime = field(default_factory=datetime.now)
    last_used_at: datetime = field(default_factory=datetime.now)
    last_checked_at: datetime = field(default_factory=datetime.now)
    use_count: int = 0
    error_count: int = 0
    is_healthy: bool = True

    @property
    def idle_time(self) -> timedelta:
        """空闲时间"""
        return datetime.now() - self.last_used_at

    @property
    def age(self) -> timedelta:
        """存活时间"""
        return datetime.now() - self.created_at

    def mark_used(self):
        """标记为已使用"""
        self.last_used_at = datetime.now()
        self.use_count += 1

    def mark_error(self):
        """标记为错误"""
        self.error_count += 1
        self.is_healthy = False
        self.last_checked_at = datetime.now()

    def mark_healthy(self):
        """标记为健康"""
        self.error_count = 0
        self.is_healthy = True
        self.last_checked_at = datetime.now()


class SmbConnectionPool:
    """
    SMB 连接池

    管理 SMB 连接的创建、复用和回收。

    使用方式：
        pool = SmbConnectionPool(
            max_connections=10,
            max_idle_time=300,
            max_age=3600,
        )

        # 获取连接
        async with pool.get_connection(config) as writer:
            await writer.list_dir("/")

        # 测试连接
        is_ok = await pool.test_connection(config)
    """

    def __init__(
        self,
        max_connections: int = 10,
        max_idle_time: int = 300,  # 5 分钟
        max_age: int = 3600,  # 1 小时
        health_check_interval: int = 60,  # 1 分钟
        max_error_count: int = 3,
    ):
        """
        初始化连接池

        Args:
            max_connections: 最大连接数
            max_idle_time: 最大空闲时间（秒）
            max_age: 最大存活时间（秒）
            health_check_interval: 健康检查间隔（秒）
            max_error_count: 最大错误次数
        """
        self.max_connections = max_connections
        self.max_idle_time = timedelta(seconds=max_idle_time)
        self.max_age = timedelta(seconds=max_age)
        self.health_check_interval = timedelta(seconds=health_check_interval)
        self.max_error_count = max_error_count

        # 连接池：key 为配置的 hash，value 为连接列表
        self._pools: Dict[str, list[PooledConnection]] = defaultdict(list)

        # 锁
        self._lock = asyncio.Lock()

        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None

        # 延迟启动清理任务（在第一次使用时启动）
        self._cleanup_task_started = False

    def _config_key(self, config: SmbConfig) -> str:
        """
        生成配置的唯一标识

        Args:
            config: SMB 配置

        Returns:
            配置的唯一标识
        """
        # 使用 host, port, share, username, domain 作为 key
        # 不包含 password 和 base_path，因为这些可能不同
        return f"{config.host}:{config.port}:{config.share}:{config.username}:{config.domain}"

    def _start_cleanup_task(self):
        """启动清理任务"""
        if not self._cleanup_task_started and (self._cleanup_task is None or self._cleanup_task.done()):
            try:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                self._cleanup_task_started = True
            except RuntimeError:
                # 没有运行的事件循环，延迟启动
                pass

    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval.total_seconds())
                await self._cleanup_idle_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"连接池清理失败：{e}")

    async def _cleanup_idle_connections(self):
        """清理空闲连接"""
        async with self._lock:
            for key, connections in self._pools.items():
                # 移除过期和不健康的连接
                self._pools[key] = [
                    conn
                    for conn in connections
                    if conn.idle_time < self.max_idle_time
                    and conn.age < self.max_age
                    and conn.is_healthy
                    and conn.error_count < self.max_error_count
                ]

    def _get_connection_from_pool(self, config: SmbConfig) -> Optional[PooledConnection]:
        """
        从连接池获取连接

        Args:
            config: SMB 配置

        Returns:
            连接实例，如果没有可用连接则返回 None
        """
        key = self._config_key(config)
        connections = self._pools.get(key, [])

        # 移除不健康的连接
        connections = [
            conn
            for conn in connections
            if conn.is_healthy and conn.error_count < self.max_error_count
        ]

        if not connections:
            return None

        # 选择空闲时间最长的连接
        connections.sort(key=lambda c: c.last_used_at)
        return connections[0]

    def _add_connection_to_pool(self, config: SmbConfig, writer: SmbWriter) -> PooledConnection:
        """
        将连接添加到连接池

        Args:
            config: SMB 配置
            writer: SmbWriter 实例

        Returns:
            连接实例
        """
        key = self._config_key(config)
        conn = PooledConnection(writer=writer, config=config)
        self._pools[key].append(conn)
        return conn

    def _remove_connection_from_pool(self, conn: PooledConnection):
        """
        从连接池移除连接

        Args:
            conn: 连接实例
        """
        key = self._config_key(conn.config)
        if key in self._pools:
            self._pools[key] = [
                c for c in self._pools[key] if c is not conn
            ]

    async def get_connection(self, config: SmbConfig) -> SmbWriter:
        """
        获取 SMB 连接

        优先从连接池获取，如果没有可用连接则创建新连接。

        Args:
            config: SMB 配置

        Returns:
            SmbWriter 实例
        """
        # 确保清理任务已启动
        self._start_cleanup_task()

        async with self._lock:
            # 尝试从连接池获取
            conn = self._get_connection_from_pool(config)
            if conn:
                conn.mark_used()
                logger.debug(f"从连接池获取连接：{config.host}:{config.share}")
                return conn.writer

        # 创建新连接
        writer = SmbWriter(config)

        # 测试连接
        try:
            await writer.test_connection()
        except Exception as e:
            logger.error(f"创建连接失败：{e}")
            raise

        async with self._lock:
            # 检查连接数限制
            key = self._config_key(config)
            if len(self._pools.get(key, [])) >= self.max_connections:
                # 移除最旧的连接
                connections = self._pools[key]
                if connections:
                    connections.sort(key=lambda c: c.created_at)
                    self._remove_connection_from_pool(connections[0])

            # 添加到连接池
            conn = self._add_connection_to_pool(config, writer)
            conn.mark_used()

        logger.debug(f"创建新连接：{config.host}:{config.share}")
        return writer

    async def test_connection(self, config: SmbConfig) -> bool:
        """
        测试连接

        Args:
            config: SMB 配置

        Returns:
            连接是否正常
        """
        try:
            writer = SmbWriter(config)
            await writer.test_connection()
            return True
        except Exception as e:
            logger.error(f"测试连接失败：{e}")
            return False

    async def mark_connection_error(self, config: SmbConfig, writer: SmbWriter):
        """
        标记连接为错误

        Args:
            config: SMB 配置
            writer: SmbWriter 实例
        """
        async with self._lock:
            key = self._config_key(config)
            connections = self._pools.get(key, [])
            for conn in connections:
                if conn.writer is writer:
                    conn.mark_error()
                    logger.warning(f"连接标记为错误：{config.host}:{config.share}")
                    break

    async def mark_connection_healthy(self, config: SmbConfig, writer: SmbWriter):
        """
        标记连接为健康

        Args:
            config: SMB 配置
            writer: SmbWriter 实例
        """
        async with self._lock:
            key = self._config_key(config)
            connections = self._pools.get(key, [])
            for conn in connections:
                if conn.writer is writer:
                    conn.mark_healthy()
                    logger.debug(f"连接标记为健康：{config.host}:{config.share}")
                    break

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        获取连接池统计信息

        Returns:
            统计信息字典
        """
        async with self._lock:
            stats = {
                "total_connections": 0,
                "healthy_connections": 0,
                "unhealthy_connections": 0,
                "pools": {},
            }

            for key, connections in self._pools.items():
                healthy = [c for c in connections if c.is_healthy]
                unhealthy = [c for c in connections if not c.is_healthy]

                stats["total_connections"] += len(connections)
                stats["healthy_connections"] += len(healthy)
                stats["unhealthy_connections"] += len(unhealthy)
                stats["pools"][key] = {
                    "total": len(connections),
                    "healthy": len(healthy),
                    "unhealthy": len(unhealthy),
                    "avg_idle_time": sum(
                        (c.idle_time.total_seconds() for c in connections), 0
                    ) / len(connections) if connections else 0,
                }

            return stats

    async def close(self):
        """关闭连接池"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            self._pools.clear()

        logger.info("连接池已关闭")


# 全局连接池实例
smb_connection_pool = SmbConnectionPool()
