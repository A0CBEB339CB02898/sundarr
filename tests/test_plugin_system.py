"""
插件系统测试脚本

验证插件注册、加载和查询功能。
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sundarr.app.plugins.base import LoadedPlugin, PluginManifest, PluginType
from sundarr.app.plugins.registry import PluginRegistry, plugin_registry


def test_plugin_registry():
    """测试插件注册中心"""
    print("测试插件注册中心...")

    # 清除现有插件
    plugin_registry.clear()

    # 创建测试插件清单
    manifest = PluginManifest(
        id="test-source",
        name="测试搜索源",
        version="1.0.0",
        plugin_type=PluginType.SOURCE,
        description="用于测试的搜索源插件",
        author="测试",
        homepage_url="https://example.com",
        plugin_api_version="1.0",
        entry="test_source:create_source",
        config_schema={},
    )

    # 创建测试插件实例
    loaded = LoadedPlugin(
        manifest=manifest,
        module=None,
        instance=None,
        status="loaded",
    )

    # 注册插件
    plugin_registry.register_external(loaded)

    # 验证插件已注册
    assert plugin_registry.has_plugin("test-source"), "插件应该已注册"
    assert plugin_registry.is_plugin_loaded("test-source"), "插件应该已加载"

    # 按类型获取插件
    source_plugins = plugin_registry.get_plugins_by_type(PluginType.SOURCE)
    assert len(source_plugins) == 1, "应该有 1 个搜索源插件"
    assert source_plugins[0].manifest.id == "test-source", "插件 ID 应该匹配"

    # 获取所有插件
    all_plugins = plugin_registry.get_all_plugins()
    assert len(all_plugins) == 1, "应该有 1 个插件"

    # 获取插件统计
    stats = plugin_registry.get_plugin_count()
    assert stats["total"] == 1, "总插件数应该为 1"
    assert stats["loaded"] == 1, "已加载插件数应该为 1"
    assert stats["source"] == 1, "搜索源插件数应该为 1"

    # 注销插件
    plugin_registry.unregister("test-source")
    assert not plugin_registry.has_plugin("test-source"), "插件应该已注销"

    print("[OK] 插件注册中心测试通过")


def test_plugin_types():
    """测试插件类型"""
    print("测试插件类型...")

    # 验证所有插件类型
    assert PluginType.SOURCE == "source", "SOURCE 应该为 'source'"
    assert PluginType.CATALOG_PROVIDER == "catalog_provider", "CATALOG_PROVIDER 应该匹配"
    assert PluginType.WATCHLIST_PROVIDER == "watchlist_provider", "WATCHLIST_PROVIDER 应该匹配"
    assert PluginType.TRANSFER_DRIVER == "transfer_driver", "TRANSFER_DRIVER 应该匹配"
    assert PluginType.NOTIFICATION == "notification", "NOTIFICATION 应该为 'notification'"

    print("[OK] 插件类型测试通过")


def test_plugin_manifest():
    """测试插件清单"""
    print("测试插件清单...")

    manifest = PluginManifest(
        id="test-plugin",
        name="测试插件",
        version="1.0.0",
        plugin_type=PluginType.SOURCE,
        description="用于测试的插件",
        author="测试",
        homepage_url="https://example.com",
        plugin_api_version="1.0",
        entry="test:create",
        config_schema={"api_key": {"type": "string", "required": True}},
        dependencies=["dep-1", "dep-2"],
    )

    assert manifest.id == "test-plugin", "插件 ID 应该匹配"
    assert manifest.name == "测试插件", "插件名称应该匹配"
    assert manifest.version == "1.0.0", "插件版本应该匹配"
    assert manifest.plugin_type == PluginType.SOURCE, "插件类型应该匹配"
    assert manifest.dependencies == ["dep-1", "dep-2"], "依赖列表应该匹配"

    print("[OK] 插件清单测试通过")


def test_loaded_plugin():
    """测试已加载插件"""
    print("测试已加载插件...")

    manifest = PluginManifest(
        id="test-plugin",
        name="测试插件",
        version="1.0.0",
        plugin_type=PluginType.SOURCE,
        description="用于测试的插件",
        author="测试",
        homepage_url="https://example.com",
        plugin_api_version="1.0",
        entry="test:create",
        config_schema={},
    )

    # 测试已加载状态
    loaded = LoadedPlugin(
        manifest=manifest,
        module=None,
        instance=None,
        status="loaded",
        commit_hash="abc123",
        repo_path="/tmp/test",
    )

    assert loaded.is_loaded, "应该已加载"
    assert loaded.is_enabled, "应该已启用"
    assert not loaded.has_error, "不应该有错误"
    assert loaded.commit_hash == "abc123", "commit hash 应该匹配"

    # 测试错误状态
    error_loaded = LoadedPlugin(
        manifest=manifest,
        module=None,
        instance=None,
        status="error",
        error_message="加载失败",
    )

    assert not error_loaded.is_loaded, "不应该已加载"
    assert not error_loaded.is_enabled, "不应该已启用"
    assert error_loaded.has_error, "应该有错误"
    assert error_loaded.error_message == "加载失败", "错误消息应该匹配"

    print("[OK] 已加载插件测试通过")


def test_multiple_plugins():
    """测试多插件管理"""
    print("测试多插件管理...")

    # 清除现有插件
    plugin_registry.clear()

    # 创建多个测试插件
    plugins = [
        LoadedPlugin(
            manifest=PluginManifest(
                id=f"source-{i}",
                name=f"搜索源 {i}",
                version="1.0.0",
                plugin_type=PluginType.SOURCE,
                description=f"搜索源 {i}",
                author="测试",
                homepage_url="https://example.com",
                plugin_api_version="1.0",
                entry=f"source_{i}:create",
                config_schema={},
            ),
            module=None,
            instance=None,
            status="loaded",
        )
        for i in range(3)
    ]

    # 注册插件
    for plugin in plugins:
        plugin_registry.register_external(plugin)

    # 验证插件数量
    assert len(plugin_registry.get_all_plugins()) == 3, "应该有 3 个插件"
    assert len(plugin_registry.get_plugins_by_type(PluginType.SOURCE)) == 3, "应该有 3 个搜索源插件"

    # 验证统计信息
    stats = plugin_registry.get_plugin_count()
    assert stats["total"] == 3, "总插件数应该为 3"
    assert stats["external"] == 3, "外部插件数应该为 3"
    assert stats["source"] == 3, "搜索源插件数应该为 3"

    print("[OK] 多插件管理测试通过")


def main():
    """运行所有测试"""
    print("=" * 50)
    print("插件系统测试")
    print("=" * 50)
    print()

    try:
        test_plugin_types()
        print()
        test_plugin_manifest()
        print()
        test_loaded_plugin()
        print()
        test_plugin_registry()
        print()
        test_multiple_plugins()

        print()
        print("=" * 50)
        print("[OK] 所有测试通过")
        print("=" * 50)
        return 0

    except AssertionError as e:
        print()
        print("=" * 50)
        print(f"[FAIL] 测试失败：{e}")
        print("=" * 50)
        return 1

    except Exception as e:
        print()
        print("=" * 50)
        print(f"[ERROR] 测试异常：{e}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
