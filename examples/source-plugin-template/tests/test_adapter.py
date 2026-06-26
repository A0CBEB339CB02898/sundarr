"""
示例搜索源插件测试
"""

import asyncio
import sys
from pathlib import Path

# 添加插件目录到 Python 路径
plugin_dir = Path(__file__).parent.parent
sys.path.insert(0, str(plugin_dir))

# 添加项目根目录到 Python 路径
project_root = plugin_dir.parent.parent
sys.path.insert(0, str(project_root))

from sundarr.app.schemas.search import SearchQuery
from sundarr.app.sources.base import SourceModel

from my_source.adapter import create_source, fetch_detail, search, test_search


def test_create_source():
    """测试创建搜索源实例"""
    print("测试创建搜索源实例...")

    source = create_source()

    assert isinstance(source, SourceModel), "应该返回 SourceModel 实例"
    assert source.id == "my-source", "ID 应该为 'my-source'"
    assert source.name == "我的搜索源", "名称应该匹配"
    assert callable(source.search_function), "搜索函数应该是可调用的"
    assert callable(source.test_function), "测试函数应该是可调用的"
    assert callable(source.fetch_detail_function), "详情函数应该是可调用的"

    print("[OK] 创建搜索源实例测试通过")


def test_search_function():
    """测试搜索函数"""
    print("测试搜索函数...")

    query = SearchQuery(keyword="测试", limit=5)
    results = asyncio.run(search(query))

    assert isinstance(results, list), "应该返回列表"
    assert len(results) > 0, "应该有搜索结果"

    for item in results:
        assert item.raw_title, "结果应该有标题"
        assert item.raw_url, "结果应该有 URL"
        assert item.source_id == "my-source", "source_id 应该匹配"

    print("[OK] 搜索函数测试通过")


def test_fetch_detail_function():
    """测试详情函数"""
    print("测试详情函数...")

    detail = asyncio.run(fetch_detail("https://example.com/detail/1"))

    assert detail.raw_title, "详情应该有标题"
    assert detail.raw_url == "https://example.com/detail/1", "URL 应该匹配"
    assert detail.source_id == "my-source", "source_id 应该匹配"

    print("[OK] 详情函数测试通过")


def test_test_search_function():
    """测试测试搜索函数"""
    print("测试测试搜索函数...")

    events = asyncio.run(test_search("测试"))

    assert isinstance(events, list), "应该返回事件列表"
    assert len(events) > 0, "应该有事件"

    for event in events:
        assert event.step, "事件应该有步骤"
        assert event.status, "事件应该有状态"
        assert event.message, "事件应该有消息"

    print("[OK] 测试搜索函数测试通过")


def main():
    """运行所有测试"""
    print("=" * 50)
    print("示例搜索源插件测试")
    print("=" * 50)
    print()

    try:
        test_create_source()
        print()
        test_search_function()
        print()
        test_fetch_detail_function()
        print()
        test_test_search_function()

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
