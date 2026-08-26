"""插件 Activation 生命周期基础设施。"""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable, Iterable, Mapping
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any

from .base import PluginManifest


CleanupCallback = Callable[[], None | Awaitable[None]]


class ActivationStatus(str, Enum):
    """一次插件 Activation 的运行状态。"""

    CANDIDATE = "candidate"
    VALIDATING = "validating"
    WAITING = "waiting"
    ACTIVE = "active"
    FAILED = "failed"
    DISPOSING = "disposing"
    DISPOSED = "disposed"


class MissingCapabilityError(RuntimeError):
    """插件需要的 Core 能力尚未提供。"""

    def __init__(self, plugin_id: str, missing: Iterable[str]) -> None:
        self.plugin_id = plugin_id
        self.missing = tuple(sorted(set(missing)))
        names = "、".join(self.missing)
        super().__init__(f"插件 {plugin_id} 缺少必需能力：{names}")


class PluginContextClosedError(RuntimeError):
    """插件上下文已封闭，不能再增加副作用。"""


class PluginContext:
    """插件访问 Core 能力和登记可逆副作用的唯一入口。"""

    def __init__(
        self,
        plugin_id: str,
        *,
        capabilities: Mapping[str, Any] | None = None,
        plugin_config: Mapping[str, Any] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.plugin_id = plugin_id
        self.logger = logger or logging.getLogger(f"sundarr.plugin.{plugin_id}")
        self.plugin_config = MappingProxyType(dict(plugin_config or {}))
        self._core_capabilities = dict(capabilities or {})
        self._provided_capabilities: dict[str, Any] = {}
        self._cleanup_callbacks: list[CleanupCallback] = []
        self._sealed = False
        self._disposed = False
        self._dispose_lock = asyncio.Lock()
        self._cleanup_errors: list[Exception] = []

    @property
    def provided_capabilities(self) -> Mapping[str, Any]:
        """返回插件已声明能力的只读快照。"""

        return MappingProxyType(dict(self._provided_capabilities))

    @property
    def cleanup_count(self) -> int:
        """返回尚未执行的清理回调数量。"""

        return len(self._cleanup_callbacks)

    def has_capability(self, name: str) -> bool:
        """检查 Core 或当前插件是否提供指定能力。"""

        return name in self._provided_capabilities or name in self._core_capabilities

    def missing_capabilities(self, required: Iterable[str]) -> tuple[str, ...]:
        """返回当前缺失的必需能力。"""

        return tuple(sorted({name for name in required if not self.has_capability(name)}))

    def require(self, name: str) -> Any:
        """取得指定能力；不存在时立即失败。"""

        if name in self._provided_capabilities:
            return self._provided_capabilities[name]
        if name in self._core_capabilities:
            return self._core_capabilities[name]
        raise MissingCapabilityError(self.plugin_id, [name])

    def provide(self, name: str, value: Any) -> None:
        """声明当前插件提供的能力。"""

        self._ensure_open()
        if not name:
            raise ValueError("能力名称不能为空")
        if name in self._core_capabilities or name in self._provided_capabilities:
            raise ValueError(f"能力名称冲突：{name}")
        self._provided_capabilities[name] = value

    def register_cleanup(self, callback: CleanupCallback) -> CleanupCallback:
        """登记清理回调，并返回原回调便于调用方保存。"""

        self._ensure_open()
        if not callable(callback):
            raise TypeError("清理回调必须可调用")
        self._cleanup_callbacks.append(callback)
        return callback

    def seal(self) -> None:
        """封闭上下文，禁止 Activation 生效后继续增加副作用。"""

        self._sealed = True

    async def dispose(self) -> list[Exception]:
        """按 LIFO 顺序执行一次清理；单项失败不阻断后续清理。"""

        async with self._dispose_lock:
            if self._disposed:
                return list(self._cleanup_errors)
            self._disposed = True
            self._sealed = True
            while self._cleanup_callbacks:
                callback = self._cleanup_callbacks.pop()
                try:
                    result = callback()
                    if inspect.isawaitable(result):
                        await result
                except Exception as exc:
                    self._cleanup_errors.append(exc)
                    self.logger.exception("插件清理回调执行失败：plugin_id=%s", self.plugin_id)
            return list(self._cleanup_errors)

    def _ensure_open(self) -> None:
        if self._sealed or self._disposed:
            raise PluginContextClosedError(f"插件 {self.plugin_id} 的上下文已封闭")


class PluginActivation:
    """表示某个插件版本的一次候选、激活和释放过程。"""

    def __init__(
        self,
        *,
        manifest: PluginManifest,
        context: PluginContext,
        repository_id: str | None = None,
        commit_hash: str | None = None,
        required_capabilities: Iterable[str] = (),
    ) -> None:
        if context.plugin_id != manifest.id:
            raise ValueError("PluginContext.plugin_id 必须与 manifest.id 一致")
        self.manifest = manifest
        self.context = context
        self.repository_id = repository_id
        self.commit_hash = commit_hash
        self.required_capabilities = tuple(dict.fromkeys(required_capabilities))
        self.instance: Any = None
        self.status = ActivationStatus.CANDIDATE
        self.error: str | None = None
        self.activated_at: datetime | None = None
        self.disposed_at: datetime | None = None
        self.cleanup_errors: list[Exception] = []
        self._dispose_lock = asyncio.Lock()

    @property
    def plugin_id(self) -> str:
        return self.manifest.id

    @property
    def provided_capabilities(self) -> Mapping[str, Any]:
        return self.context.provided_capabilities

    def begin_validation(self) -> None:
        """校验依赖并进入 validating；缺失依赖时进入 waiting。"""

        self._require_status(ActivationStatus.CANDIDATE, ActivationStatus.WAITING)
        missing = self.context.missing_capabilities(self.required_capabilities)
        if missing:
            self.status = ActivationStatus.WAITING
            error = MissingCapabilityError(self.plugin_id, missing)
            self.error = str(error)
            raise error
        self.error = None
        self.status = ActivationStatus.VALIDATING

    def activate(self, instance: Any) -> None:
        """把已通过校验的候选标记为 active。"""

        self._require_status(ActivationStatus.VALIDATING)
        self.instance = instance
        self.context.seal()
        self.status = ActivationStatus.ACTIVE
        self.activated_at = datetime.now()

    async def fail(self, error: BaseException | str) -> None:
        """标记候选失败，并清理候选阶段产生的全部副作用。"""

        if self.status in {ActivationStatus.DISPOSING, ActivationStatus.DISPOSED}:
            return
        self.error = str(error)
        self.cleanup_errors = await self.context.dispose()
        self.status = ActivationStatus.FAILED

    async def dispose(self) -> None:
        """幂等释放 Activation。"""

        async with self._dispose_lock:
            if self.status == ActivationStatus.DISPOSED:
                return
            self.status = ActivationStatus.DISPOSING
            self.cleanup_errors = await self.context.dispose()
            self.status = ActivationStatus.DISPOSED
            self.disposed_at = datetime.now()

    def _require_status(self, *allowed: ActivationStatus) -> None:
        if self.status not in allowed:
            names = "、".join(item.value for item in allowed)
            raise RuntimeError(
                f"插件 {self.plugin_id} 当前状态 {self.status.value} 不允许此操作，要求状态：{names}"
            )
