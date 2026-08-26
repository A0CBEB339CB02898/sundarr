"""
SMB 连接池测试脚本

测试连接池的基本功能。
"""

import asyncio
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sundarr.app.storage.pool import SmbConnectionPool
from sundarr.app.storage.smb import SmbConfig


async def test_connection_pool():
    """测试连接池基本功能"""
    print("测试连接池基本功能...")

    # 创建连接池
    pool = SmbConnectionPool(
        max_connections=5,
        max_idle_time=60,
        max_age=300,
        health_check_interval=30,
        max_error_count=3,
    )

    # 创建测试配置
    config = SmbConfig(
        host="test-host",
        share="test-share",
        username="test-user",
        password="test-pass",
        port=445,
        domain="",
        base_path="/",
    )

    # 测试配置 key 生成
    key = pool._config_key(config)
    assert key == "test-host:445:test-share:test-user:", f"配置 key 应该为 'test-host:445:test-share:test-user:'，实际为 '{key}'"
    print("[OK] 配置 key 生成正常")

    # 测试连接池统计
    stats = await pool.get_connection_stats()
    assert stats["total_connections"] == 0, f"总连接数应该为 0，实际为 {stats['total_connections']}"
    assert stats["healthy_connections"] == 0, f"健康连接数应该为 0，实际为 {stats['healthy_connections']}"
    assert stats["unhealthy_connections"] == 0, f"不健康连接数应该为 0，实际为 {stats['unhealthy_connections']}"
    print("[OK] 连接池统计正常")

    # 关闭连接池
    await pool.close()
    print("[OK] 连接池关闭正常")


async def test_connection_pool_with_mock():
    """测试连接池与模拟连接"""
    print("测试连接池与模拟连接...")

    # 创建连接池
    pool = SmbConnectionPool(
        max_connections=3,
        max_idle_time=60,
        max_age=300,
        health_check_interval=30,
        max_error_count=3,
    )

    # 创建多个配置
    configs = [
        SmbConfig(
            host=f"host-{i}",
            share=f"share-{i}",
            username=f"user-{i}",
            password=f"pass-{i}",
            port=445,
            domain="",
            base_path="/",
        )
        for i in range(3)
    ]

    # 测试配置 key 唯一性
    keys = [pool._config_key(config) for config in configs]
    assert len(keys) == len(set(keys)), "配置 key 应该唯一"
    print("[OK] 配置 key 唯一性正常")

    # 测试连接池大小限制
    assert pool.max_connections == 3, f"最大连接数应该为 3，实际为 {pool.max_connections}"
    print("[OK] 连接池大小限制正常")

    # 关闭连接池
    await pool.close()
    print("[OK] 连接池关闭正常")


async def test_pooled_connection():
    """测试连接池中的连接"""
    print("测试连接池中的连接...")

    from sundarr.app.storage.pool import PooledConnection
    from datetime import datetime

    # 创建模拟配置
    config = SmbConfig(
        host="test-host",
        share="test-share",
        username="test-user",
        password="test-pass",
    )

    # 创建模拟 writer
    class MockWriter:
        pass

    writer = MockWriter()

    # 创建连接
    conn = PooledConnection(
        writer=writer,
        config=config,
    )

    # 测试初始状态
    assert conn.is_healthy, "连接应该初始为健康"
    assert conn.error_count == 0, f"错误计数应该为 0，实际为 {conn.error_count}"
    assert conn.use_count == 0, f"使用计数应该为 0，实际为 {conn.use_count}"
    print("[OK] 连接初始状态正常")

    # 测试标记使用
    conn.mark_used()
    assert conn.use_count == 1, f"使用计数应该为 1，实际为 {conn.use_count}"
    print("[OK] 连接标记使用正常")

    # 测试标记错误
    conn.mark_error()
    assert not conn.is_healthy, "连接应该标记为不健康"
    assert conn.error_count == 1, f"错误计数应该为 1，实际为 {conn.error_count}"
    print("[OK] 连接标记错误正常")

    # 测试标记健康
    conn.mark_healthy()
    assert conn.is_healthy, "连接应该标记为健康"
    assert conn.error_count == 0, f"错误计数应该为 0，实际为 {conn.error_count}"
    print("[OK] 连接标记健康正常")

    # 测试空闲时间
    idle_time = conn.idle_time
    assert idle_time.total_seconds() >= 0, "空闲时间应该大于等于 0"
    print("[OK] 连接空闲时间正常")

    # 测试存活时间
    age = conn.age
    assert age.total_seconds() >= 0, "存活时间应该大于等于 0"
    print("[OK] 连接存活时间正常")


async def main():
    """运行所有测试"""
    print("=" * 50)
    print("SMB 连接池测试")
    print("=" * 50)
    print()

    try:
        await test_connection_pool()
        print()
        await test_connection_pool_with_mock()
        print()
        await test_pooled_connection()

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
        print(f"[FAIL] 测试异常：{e}")
        print("=" * 50)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
