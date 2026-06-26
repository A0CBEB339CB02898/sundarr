"""
示例搜索源适配器

这是一个示例搜索源适配器，用于演示如何创建自定义搜索源。
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import SourceModel, SourceTestEvent

logger = logging.getLogger(__name__)


async def search(query: SearchQuery) -> List[RawSearchItem]:
    """
    搜索资源

    Args:
        query: 搜索查询对象

    Returns:
        搜索结果列表
    """
    logger.info(f"执行搜索：{query.keyword}")

    # 模拟搜索延迟
    await asyncio.sleep(0.1)

    # 返回示例结果
    return [
        RawSearchItem(
            source_id="my-source",
            source_type="web",
            raw_title=f"{query.keyword} - 示例资源 1",
            raw_url="https://example.com/detail/1",
            raw_content="这是一个示例资源的描述",
            published_at=datetime.now(),
            fetched_at=datetime.now(),
            metadata={
                "quality": "1080p",
                "poster_url": "https://example.com/poster/1.jpg",
                "description": "这是一个示例资源",
            },
        ),
        RawSearchItem(
            source_id="my-source",
            source_type="web",
            raw_title=f"{query.keyword} - 示例资源 2",
            raw_url="https://example.com/detail/2",
            raw_content="这是另一个示例资源的描述",
            published_at=datetime.now(),
            fetched_at=datetime.now(),
            metadata={
                "quality": "720p",
                "poster_url": "https://example.com/poster/2.jpg",
                "description": "这是另一个示例资源",
            },
        ),
    ]


async def fetch_detail(detail_url: str) -> RawSearchItem:
    """
    获取资源详情

    Args:
        detail_url: 详情页 URL

    Returns:
        资源详情
    """
    logger.info(f"获取详情：{detail_url}")

    # 模拟获取详情延迟
    await asyncio.sleep(0.1)

    # 返回示例详情
    return RawSearchItem(
        source_id="my-source",
        source_type="web",
        raw_title="示例资源详情",
        raw_url=detail_url,
        raw_content="这是资源详情的内容",
        published_at=datetime.now(),
        fetched_at=datetime.now(),
        metadata={
            "quality": "1080p",
            "poster_url": "https://example.com/poster/1.jpg",
            "description": "这是资源详情",
            "links": [
                {
                    "url": "https://pan.quark.cn/s/example",
                    "provider": "quark",
                    "password": None,
                }
            ],
        },
    )


async def test_search(keyword: str) -> List[SourceTestEvent]:
    """
    测试搜索

    Args:
        keyword: 搜索关键词

    Returns:
        测试事件列表
    """
    logger.info(f"测试搜索：{keyword}")

    events = []

    # 记录开始事件
    events.append(
        SourceTestEvent(
            step="search",
            status="start",
            message=f"开始测试搜索：{keyword}",
            data={"keyword": keyword},
        )
    )

    try:
        # 执行搜索
        query = SearchQuery(keyword=keyword, limit=5)
        results = await search(query)

        # 记录搜索结果事件
        events.append(
            SourceTestEvent(
                step="search",
                status="success",
                message=f"搜索完成，找到 {len(results)} 个结果",
                data={"count": len(results)},
            )
        )

        # 记录每个结果
        for i, result in enumerate(results):
            events.append(
                SourceTestEvent(
                    step="result",
                    status="success",
                    message=f"结果 {i+1}: {result.raw_title}",
                    data={
                        "title": result.raw_title,
                        "url": result.raw_url,
                        "quality": result.metadata.get("quality", "unknown"),
                    },
                )
            )

    except Exception as e:
        # 记录错误事件
        events.append(
            SourceTestEvent(
                step="search",
                status="error",
                message=f"搜索失败：{str(e)}",
                data={"error": str(e)},
            )
        )

    return events


def create_source() -> SourceModel:
    """
    创建搜索源实例

    Returns:
        搜索源实例
    """
    return SourceModel(
        id="my-source",
        name="我的搜索源",
        description="这是一个示例搜索源插件，用于演示如何创建自定义搜索源",
        homepage_url="https://github.com/sundarr/my-source",
        search_function=search,
        test_function=test_search,
        fetch_detail_function=fetch_detail,
    )
