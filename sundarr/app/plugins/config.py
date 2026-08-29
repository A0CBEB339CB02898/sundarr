"""插件 Manifest 配置 Schema 的最小校验器。"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import logging
from typing import Any


class PluginConfigValidationError(ValueError):
    """插件配置不符合 Manifest 声明。"""


_SUPPORTED_TYPES = {"string", "password", "integer", "boolean", "select"}
REDACTED_VALUE = "***"


def validate_plugin_config(
    schema: Mapping[str, Any],
    config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """校验配置、应用默认值，并返回与输入隔离的字典。"""

    if not isinstance(schema, Mapping):
        raise PluginConfigValidationError("config_schema 必须是映射")
    if config is None:
        config = {}
    if not isinstance(config, Mapping):
        raise PluginConfigValidationError("插件配置必须是映射")

    unknown = sorted(set(config) - set(schema))
    if unknown:
        raise PluginConfigValidationError(
            f"插件配置包含未声明字段：{'、'.join(str(item) for item in unknown)}"
        )

    result: dict[str, Any] = {}
    for field_name, raw_field_schema in schema.items():
        if not isinstance(field_name, str) or not field_name:
            raise PluginConfigValidationError("config_schema 字段名必须是非空字符串")
        if not isinstance(raw_field_schema, Mapping):
            raise PluginConfigValidationError(
                f"配置字段 {field_name} 的 schema 必须是映射"
            )

        field_type = raw_field_schema.get("type")
        if field_type not in _SUPPORTED_TYPES:
            raise PluginConfigValidationError(
                f"配置字段 {field_name} 使用了不支持的类型：{field_type}"
            )

        if field_name in config:
            value = deepcopy(config[field_name])
        elif "default" in raw_field_schema:
            value = deepcopy(raw_field_schema["default"])
        elif raw_field_schema.get("required", False):
            raise PluginConfigValidationError(f"缺少必填插件配置：{field_name}")
        else:
            continue

        _validate_field_value(field_name, field_type, value, raw_field_schema)
        result[field_name] = value

    return result


def redact_plugin_config(
    schema: Mapping[str, Any],
    config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """按 Manifest 声明脱敏配置，未知字段也不对外回显。"""

    result: dict[str, Any] = {}
    values = config or {}
    for field_name, field_schema in schema.items():
        if field_name not in values or not isinstance(field_schema, Mapping):
            continue
        if field_schema.get("type") == "password" or field_schema.get("secret") is True:
            result[field_name] = REDACTED_VALUE
        else:
            result[field_name] = deepcopy(values[field_name])
    return result


def redact_plugin_error(
    error: BaseException | str,
    schema: Mapping[str, Any],
    config: Mapping[str, Any] | None,
    *,
    max_length: int = 1000,
) -> str:
    """替换错误中的已知敏感配置值，并限制持久化诊断长度。"""

    message = str(error)
    values = config or {}
    for field_name, field_schema in schema.items():
        if not isinstance(field_schema, Mapping):
            continue
        if field_schema.get("type") != "password" and field_schema.get("secret") is not True:
            continue
        value = values.get(field_name)
        if isinstance(value, str) and value:
            message = message.replace(value, REDACTED_VALUE)
    return message[:max_length]


class SensitiveValueLogFilter(logging.Filter):
    """在 LogRecord 进入 handler 前替换已知敏感配置值。"""

    def __init__(self, values: list[str]) -> None:
        super().__init__()
        self._values = tuple(item for item in values if item)

    def filter(self, record: logging.LogRecord) -> bool:
        rendered = record.getMessage()
        for value in self._values:
            rendered = rendered.replace(value, REDACTED_VALUE)
        record.msg = rendered
        record.args = ()
        return True


def build_sensitive_log_filter(
    schema: Mapping[str, Any],
    config: Mapping[str, Any],
) -> SensitiveValueLogFilter | None:
    """根据 secret/password 声明创建日志脱敏过滤器。"""

    values: list[str] = []
    for field_name, field_schema in schema.items():
        if not isinstance(field_schema, Mapping):
            continue
        is_secret = field_schema.get("type") == "password" or field_schema.get("secret") is True
        value = config.get(field_name)
        if is_secret and isinstance(value, str) and value:
            values.append(value)
    return SensitiveValueLogFilter(values) if values else None


def _validate_field_value(
    field_name: str,
    field_type: str,
    value: Any,
    field_schema: Mapping[str, Any],
) -> None:
    if field_type in {"string", "password"}:
        if not isinstance(value, str):
            raise PluginConfigValidationError(
                f"插件配置 {field_name} 必须是字符串"
            )
        return

    if field_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise PluginConfigValidationError(f"插件配置 {field_name} 必须是整数")
        minimum = field_schema.get("min")
        maximum = field_schema.get("max")
        if minimum is not None and value < minimum:
            raise PluginConfigValidationError(
                f"插件配置 {field_name} 不能小于 {minimum}"
            )
        if maximum is not None and value > maximum:
            raise PluginConfigValidationError(
                f"插件配置 {field_name} 不能大于 {maximum}"
            )
        return

    if field_type == "boolean":
        if not isinstance(value, bool):
            raise PluginConfigValidationError(
                f"插件配置 {field_name} 必须是布尔值"
            )
        return

    options = field_schema.get("options")
    if not isinstance(options, list) or not options:
        raise PluginConfigValidationError(
            f"select 配置字段 {field_name} 必须声明非空 options"
        )
    if value not in options:
        raise PluginConfigValidationError(
            f"插件配置 {field_name} 不在允许的选项中"
        )
