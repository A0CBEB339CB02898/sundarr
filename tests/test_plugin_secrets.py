import pytest
from cryptography.fernet import Fernet

from sundarr.app.plugins import secrets


SCHEMA = {
    "token": {"type": "password", "required": True, "secret": True},
    "language": {"type": "string", "default": "zh-CN"},
}


def test_sensitive_plugin_config_is_encrypted_at_rest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(secrets.PLUGIN_CONFIG_KEY_ENV, Fernet.generate_key().decode("ascii"))

    stored = secrets.encode_plugin_config({"token": "live-secret", "language": "zh-CN"}, SCHEMA)

    assert stored.startswith(secrets.ENCRYPTED_PREFIX)
    assert "live-secret" not in stored
    assert secrets.decode_plugin_config(stored) == {"token": "live-secret", "language": "zh-CN"}


def test_non_sensitive_plugin_config_keeps_readable_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(secrets.PLUGIN_CONFIG_KEY_ENV, raising=False)

    stored = secrets.encode_plugin_config({"language": "zh-CN"}, SCHEMA)

    assert stored == '{"language":"zh-CN"}'
    assert secrets.decode_plugin_config(stored) == {"language": "zh-CN"}


def test_wrong_plugin_config_key_returns_safe_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(secrets.PLUGIN_CONFIG_KEY_ENV, Fernet.generate_key().decode("ascii"))
    stored = secrets.encode_plugin_config({"token": "live-secret"}, SCHEMA)
    monkeypatch.setenv(secrets.PLUGIN_CONFIG_KEY_ENV, Fernet.generate_key().decode("ascii"))

    with pytest.raises(secrets.PluginConfigDecryptionError, match="数据库外加密主密钥"):
        secrets.decode_plugin_config(stored)


def test_local_key_file_is_created_outside_database(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    key_file = tmp_path / "runtime" / "plugin-config.key"
    monkeypatch.delenv(secrets.PLUGIN_CONFIG_KEY_ENV, raising=False)
    monkeypatch.setattr(secrets, "PLUGIN_CONFIG_KEY_FILE", key_file)

    stored = secrets.encode_plugin_config({"token": "file-secret"}, SCHEMA)

    assert key_file.exists()
    assert "file-secret" not in stored
    assert secrets.decode_plugin_config(stored)["token"] == "file-secret"
