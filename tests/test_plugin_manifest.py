"""通用插件 Manifest 解析测试。"""

from pathlib import Path

import pytest

from sundarr.app.plugins.base import PluginType
from sundarr.app.plugins.loader import PluginLoader


def write_manifest(repo_path: Path, content: str) -> Path:
    """在临时仓库写入插件清单。"""

    repo_path.mkdir(parents=True)
    manifest_path = repo_path / "sundarr_plugin.toml"
    manifest_path.write_text(content, encoding="utf-8")
    return manifest_path


def make_loader(tmp_path: Path) -> PluginLoader:
    return PluginLoader(repos_dir=tmp_path / "cache")


def test_parse_flat_v1_source_manifest(tmp_path: Path) -> None:
    repo_path = tmp_path / "flat-v1"
    write_manifest(
        repo_path,
        """
id = "legacy-source"
name = "旧版搜索源"
version = "1.0.0"
plugin_type = "source"
adapter_api_version = "1.0"
entry = "legacy.adapter:create_source"
dependencies = []

[config_schema]
timeout = { type = "integer", default = 30 }
""",
    )

    manifests = make_loader(tmp_path).parse_manifests(repo_path)

    assert len(manifests) == 1
    manifest = manifests[0]
    assert manifest.id == "legacy-source"
    assert manifest.plugin_type == PluginType.SOURCE
    assert manifest.manifest_version == 1
    assert manifest.plugin_api_version == "1.0"
    assert manifest.adapter_api_version == "1.0"
    assert manifest.requires == []
    assert manifest.provides == []


def test_parse_v2_multi_plugin_manifest(tmp_path: Path) -> None:
    repo_path = tmp_path / "multi-v2"
    write_manifest(
        repo_path,
        """
manifest_version = 2

[[plugins]]
id = "douban-catalog"
name = "豆瓣目录"
version = "0.1.0"
plugin_type = "catalog_provider"
plugin_api_version = "1.0"
entry = "douban.catalog:activate"

[plugins.runtime]
requires = ["core.http.v1", "core.catalog_registry.v1"]
provides = ["catalog.search.v1", "catalog.detail.v1"]

[plugins.config_schema.cookie]
type = "password"
secret = true

[[plugins]]
id = "douban-watchlist"
name = "豆瓣想看"
version = "0.1.0"
plugin_type = "watchlist_provider"
plugin_api_version = "1.0"
entry = "douban.watchlist:activate"

[plugins.runtime]
requires = ["core.http.v1", "core.watchlist_registry.v1"]
provides = ["watchlist.pull.v1"]
""",
    )

    manifests = make_loader(tmp_path).parse_manifests(repo_path)

    assert [manifest.id for manifest in manifests] == [
        "douban-catalog",
        "douban-watchlist",
    ]
    assert [manifest.plugin_type for manifest in manifests] == [
        PluginType.CATALOG_PROVIDER,
        PluginType.WATCHLIST_PROVIDER,
    ]
    assert all(manifest.manifest_version == 2 for manifest in manifests)
    assert manifests[0].requires == [
        "core.http.v1",
        "core.catalog_registry.v1",
    ]
    assert manifests[0].provides == [
        "catalog.search.v1",
        "catalog.detail.v1",
    ]
    assert manifests[0].config_schema["cookie"]["secret"] is True


@pytest.mark.parametrize(
    "plugin_type",
    [
        "cloud_provider",
        "crawler",
        "link_validator",
        "link_extractor",
        "task_processor",
    ],
)
def test_flat_v1_rejects_removed_plugin_types(
    tmp_path: Path,
    plugin_type: str,
) -> None:
    repo_path = tmp_path / plugin_type
    write_manifest(
        repo_path,
        f"""
id = "legacy-plugin"
name = "旧占位插件"
version = "1.0.0"
plugin_type = "{plugin_type}"
adapter_api_version = "1.0"
entry = "legacy.adapter:create_plugin"
""",
    )

    with pytest.raises(ValueError, match="无效的插件类型"):
        make_loader(tmp_path).parse_manifests(repo_path)


def test_flat_v1_rejects_non_source_supported_type(tmp_path: Path) -> None:
    repo_path = tmp_path / "v1-catalog"
    write_manifest(
        repo_path,
        """
id = "legacy-catalog"
name = "错误的旧版目录插件"
version = "1.0.0"
plugin_type = "catalog_provider"
adapter_api_version = "1.0"
entry = "legacy.catalog:create_plugin"
""",
    )

    with pytest.raises(ValueError, match="flat v1 插件清单只支持 source"):
        make_loader(tmp_path).parse_manifests(repo_path)


def test_v2_rejects_reserved_transfer_driver(tmp_path: Path) -> None:
    repo_path = tmp_path / "future-driver"
    write_manifest(
        repo_path,
        """
manifest_version = 2

[[plugins]]
id = "future-driver"
name = "未来搬运驱动"
version = "0.1.0"
plugin_type = "transfer_driver"
plugin_api_version = "1.0"
entry = "future.driver:activate"

[plugins.runtime]
provides = ["transfer.execute.v1"]
""",
    )

    with pytest.raises(ValueError, match="当前版本尚不能激活插件类型"):
        make_loader(tmp_path).parse_manifests(repo_path)


def test_v2_rejects_duplicate_plugin_id(tmp_path: Path) -> None:
    repo_path = tmp_path / "duplicates"
    write_manifest(
        repo_path,
        """
manifest_version = 2

[[plugins]]
id = "same-plugin"
name = "插件一"
version = "0.1.0"
plugin_type = "source"
plugin_api_version = "1.0"
entry = "one.adapter:activate"
[plugins.runtime]
provides = ["source.search.v1"]

[[plugins]]
id = "same-plugin"
name = "插件二"
version = "0.1.0"
plugin_type = "source"
plugin_api_version = "1.0"
entry = "two.adapter:activate"
[plugins.runtime]
provides = ["source.search.v1"]
""",
    )

    with pytest.raises(ValueError, match="重复 plugin_id"):
        make_loader(tmp_path).parse_manifests(repo_path)


@pytest.mark.parametrize(
    ("fragment", "message"),
    [
        ("manifest_version = 3", "不支持的 manifest_version"),
        ('plugin_api_version = "2.0"', "不支持的 plugin_api_version"),
        ("provides = []", "至少一个 runtime.provides"),
    ],
)
def test_v2_rejects_unsupported_contracts(
    tmp_path: Path,
    fragment: str,
    message: str,
) -> None:
    repo_path = tmp_path / message
    if fragment.startswith("manifest_version"):
        content = f"{fragment}\n"
    else:
        plugin_api_version = (
            fragment
            if fragment.startswith("plugin_api_version")
            else 'plugin_api_version = "1.0"'
        )
        provides = (
            fragment
            if fragment.startswith("provides")
            else 'provides = ["source.search.v1"]'
        )
        content = f"""
manifest_version = 2

[[plugins]]
id = "example-source"
name = "示例搜索源"
version = "0.1.0"
plugin_type = "source"
{plugin_api_version}
entry = "example.adapter:activate"

[plugins.runtime]
{provides}
"""
    write_manifest(repo_path, content)

    with pytest.raises(ValueError, match=message):
        make_loader(tmp_path).parse_manifests(repo_path)


@pytest.mark.parametrize(
    ("plugin_id", "entry", "message"),
    [
        ("Invalid_ID", "example.adapter:activate", "无效的插件 id"),
        ("example-source", "../example.py:activate", "无效的插件 entry"),
    ],
)
def test_v2_rejects_invalid_identity_or_entry(
    tmp_path: Path,
    plugin_id: str,
    entry: str,
    message: str,
) -> None:
    repo_path = tmp_path / message
    write_manifest(
        repo_path,
        f"""
manifest_version = 2

[[plugins]]
id = "{plugin_id}"
name = "无效插件"
version = "0.1.0"
plugin_type = "source"
plugin_api_version = "1.0"
entry = "{entry}"
[plugins.runtime]
provides = ["source.search.v1"]
""",
    )

    with pytest.raises(ValueError, match=message):
        make_loader(tmp_path).parse_manifests(repo_path)


def test_current_single_plugin_loader_rejects_v2_until_activation_is_ready(
    tmp_path: Path,
) -> None:
    repo_path = tmp_path / "v2-not-active"
    write_manifest(
        repo_path,
        """
manifest_version = 2

[[plugins]]
id = "example-source"
name = "示例搜索源"
version = "0.1.0"
plugin_type = "source"
plugin_api_version = "1.0"
entry = "example.adapter:activate"
[plugins.runtime]
provides = ["source.search.v1"]
""",
    )

    with pytest.raises(NotImplementedError, match="类型专用 Activation 尚未接入"):
        make_loader(tmp_path)._parse_manifest(repo_path)
