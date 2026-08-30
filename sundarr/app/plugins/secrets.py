"""插件配置敏感载荷的数据库外密钥加密。"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from ..config import PROJECT_ROOT


ENCRYPTED_PREFIX = "fernet:v1:"
PLUGIN_CONFIG_KEY_ENV = "SUNDARR_PLUGIN_CONFIG_KEY"
PLUGIN_CONFIG_KEY_FILE = PROJECT_ROOT / ".sundarr" / "plugin-config.key"


class PluginConfigDecryptionError(ValueError):
    """插件配置无法使用当前数据库外密钥解密。"""


def encode_plugin_config(config: Mapping[str, Any], schema: Mapping[str, Any] | None = None) -> str:
    """序列化配置；存在已赋值敏感字段时加密整个载荷。"""

    serialized = json.dumps(dict(config), ensure_ascii=False, separators=(",", ":"))
    if not _contains_sensitive_value(config, schema or {}):
        return serialized
    encrypted = Fernet(_load_key()).encrypt(serialized.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{encrypted}"


def decode_plugin_config(value: str | Mapping[str, Any] | None) -> dict[str, Any]:
    """读取明文兼容载荷或 v1 加密载荷。"""

    if isinstance(value, Mapping):
        return dict(value)
    serialized = value or "{}"
    if serialized.startswith(ENCRYPTED_PREFIX):
        token = serialized.removeprefix(ENCRYPTED_PREFIX)
        try:
            serialized = Fernet(_load_key()).decrypt(token.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise PluginConfigDecryptionError("插件配置无法解密，请检查数据库外加密主密钥") from exc
    try:
        decoded = json.loads(serialized)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("插件配置不是有效 JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError("插件配置 JSON 必须是对象")
    return decoded


def config_requires_encryption(
    stored_value: str | Mapping[str, Any] | None,
    config: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> bool:
    """判断旧明文敏感配置是否需要迁移。"""

    return (
        isinstance(stored_value, str)
        and not stored_value.startswith(ENCRYPTED_PREFIX)
        and _contains_sensitive_value(config, schema)
    )


def _contains_sensitive_value(config: Mapping[str, Any], schema: Mapping[str, Any]) -> bool:
    for field_name, field_schema in schema.items():
        if not isinstance(field_schema, Mapping):
            continue
        is_sensitive = field_schema.get("type") == "password" or field_schema.get("secret") is True
        if is_sensitive and config.get(field_name) not in (None, ""):
            return True
    return False


def _load_key() -> bytes:
    configured = os.environ.get(PLUGIN_CONFIG_KEY_ENV, "").strip()
    if configured:
        key = configured.encode("ascii")
        _validate_key(key)
        return key
    return _load_or_create_file_key(PLUGIN_CONFIG_KEY_FILE)


def _load_or_create_file_key(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        key = path.read_bytes().strip()
    except FileNotFoundError:
        generated = Fernet.generate_key()
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            key = path.read_bytes().strip()
        else:
            with os.fdopen(descriptor, "wb") as file_handle:
                file_handle.write(generated)
            key = generated
    try:
        path.chmod(0o600)
    except OSError:
        pass
    _validate_key(key)
    return key


def _validate_key(key: bytes) -> None:
    try:
        Fernet(key)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{PLUGIN_CONFIG_KEY_ENV} 或插件配置密钥文件不是有效 Fernet 密钥") from exc
