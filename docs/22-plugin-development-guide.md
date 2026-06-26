# 插件开发指南

## 概述

本指南介绍如何为 Sundarr 开发插件，包括插件类型选择、开发流程、最佳实践等。

## 插件类型选择

根据您的需求选择合适的插件类型：

| 插件类型 | 用途 | 示例 |
|---------|------|------|
| **source** | 扩展搜索能力 | SeedHub、Bilibili、夸克网盘搜索 |
| **cloud_provider** | 支持不同网盘 | 夸克、阿里云盘、百度网盘 |
| **notification** | 支持通知渠道 | 钉钉、飞书、企业微信 |
| **crawler** | 监控外部数据源 | 豆瓣想看列表、RSS 订阅 |
| **link_validator** | 验证链接有效性 | 夸克链接验证、阿里云盘链接验证 |
| **link_extractor** | 提取资源链接 | 网页链接提取、磁力链接提取 |
| **task_processor** | 处理特定任务 | 直链下载、离线下载 |

## 开发流程

### 1. 创建插件目录

```bash
mkdir my-plugin
cd my-plugin
```

### 2. 创建插件清单

创建 `sundarr_plugin.toml` 文件：

```toml
id = "my-plugin"
name = "我的插件"
version = "1.0.0"
plugin_type = "source"
description = "这是一个示例插件"
author = "Your Name"
homepage_url = "https://github.com/yourname/my-plugin"
adapter_api_version = "1.0"
entry = "my_plugin.adapter:create_plugin"

[config_schema]
api_key = { type = "string", required = true, label = "API Key", secret = true }
```

### 3. 实现插件功能

创建插件实现文件：

```python
# my_plugin/adapter.py

from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import SourceModel

async def search(query: SearchQuery) -> list[RawSearchItem]:
    """搜索资源"""
    # 实现搜索逻辑
    return []

def create_plugin() -> SourceModel:
    """创建插件实例"""
    return SourceModel(
        id="my-plugin",
        name="我的插件",
        description="这是一个示例插件",
        homepage_url="https://github.com/yourname/my-plugin",
        search_function=search,
    )
```

### 4. 测试插件

创建测试文件：

```python
# tests/test_adapter.py

import asyncio
from my_plugin.adapter import search, create_plugin

def test_search():
    """测试搜索功能"""
    query = SearchQuery(keyword="测试", limit=5)
    results = asyncio.run(search(query))
    assert isinstance(results, list)

def test_create_plugin():
    """测试插件创建"""
    plugin = create_plugin()
    assert plugin.id == "my-plugin"
```

### 5. 发布插件

将插件代码推送到 Git 仓库：

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourname/my-plugin.git
git push -u origin main
```

## 插件类型详解

### Source 插件

搜索源插件用于扩展 Sundarr 的搜索能力。

**接口要求**:
- 实现 `search(query: SearchQuery) -> List[RawSearchItem]` 函数
- 实现 `test_search(keyword: str) -> List[SourceTestEvent]` 函数（可选）
- 实现 `fetch_detail(detail_url: str) -> RawSearchItem` 函数（可选）

**示例**:

```python
from sundarr.app.schemas.search import RawSearchItem, SearchQuery
from sundarr.app.sources.base import SourceModel, SourceTestEvent

async def search(query: SearchQuery) -> list[RawSearchItem]:
    """搜索资源"""
    # 实现搜索逻辑
    return [
        RawSearchItem(
            source_id="my-source",
            source_type="web",
            raw_title="资源标题",
            raw_url="https://example.com/detail/1",
            raw_content="资源描述",
            published_at=datetime.now(),
            fetched_at=datetime.now(),
            metadata={"quality": "1080p"},
        )
    ]

def create_source() -> SourceModel:
    """创建搜索源实例"""
    return SourceModel(
        id="my-source",
        name="我的搜索源",
        description="这是一个搜索源插件",
        homepage_url="https://github.com/yourname/my-source",
        search_function=search,
    )
```

### Cloud Provider 插件

网盘 Provider 插件用于支持从不同网盘下载资源。

**接口要求**:
- 实现 `get_auth_qrcode() -> CloudAuthResult` 函数（可选）
- 实现 `validate_cookie(cookie: str) -> bool` 函数
- 实现 `extract_direct_link(share_url: str, password: Optional[str]) -> DirectLink` 函数
- 实现 `list_files(folder_url: str, password: Optional[str]) -> AsyncGenerator[Dict[str, Any], None]` 函数

**示例**:

```python
from sundarr.app.plugins.types.cloud_provider import CloudProviderPlugin, DirectLink

class QuarkProvider(CloudProviderPlugin):
    """夸克网盘 Provider"""
    
    @property
    def provider_name(self) -> str:
        return "quark"
    
    async def validate_cookie(self, cookie: str) -> bool:
        """验证 Cookie 是否有效"""
        # 实现验证逻辑
        return True
    
    async def extract_direct_link(
        self, 
        share_url: str, 
        password: Optional[str] = None
    ) -> DirectLink:
        """提取直链"""
        # 实现提取逻辑
        return DirectLink(
            url="https://example.com/file.mp4",
            filename="file.mp4",
            file_size=1024,
            content_type="video/mp4",
        )

def create_provider() -> QuarkProvider:
    """创建 Provider 实例"""
    return QuarkProvider()
```

### Notification 插件

通知渠道插件用于支持通过不同渠道发送通知。

**接口要求**:
- 实现 `channel_name` 属性
- 实现 `config_schema` 属性
- 实现 `send(message: NotificationMessage) -> bool` 函数
- 实现 `test() -> bool` 函数

**示例**:

```python
from sundarr.app.plugins.types.notification import NotificationPlugin, NotificationMessage

class DingTalkNotification(NotificationPlugin):
    """钉钉通知"""
    
    @property
    def channel_name(self) -> str:
        return "dingtalk"
    
    @property
    def config_schema(self) -> dict:
        return {
            "webhook_url": {
                "type": "string",
                "required": True,
                "label": "Webhook URL",
                "secret": True,
            }
        }
    
    async def send(self, message: NotificationMessage) -> bool:
        """发送通知"""
        # 实现发送逻辑
        return True
    
    async def test(self) -> bool:
        """测试通知"""
        # 实现测试逻辑
        return True

def create_notification() -> DingTalkNotification:
    """创建通知实例"""
    return DingTalkNotification()
```

## 最佳实践

### 1. 错误处理

所有函数都应该有完善的错误处理：

```python
async def search(query: SearchQuery) -> list[RawSearchItem]:
    """搜索资源"""
    try:
        # 实现搜索逻辑
        results = []
        return results
    except Exception as e:
        logger.error(f"搜索失败：{e}")
        return []
```

### 2. 超时设置

网络请求应该设置合理的超时时间：

```python
import asyncio

async def fetch_with_timeout(url: str, timeout: int = 30) -> str:
    """带超时的请求"""
    try:
        async with asyncio.timeout(timeout):
            # 实现请求逻辑
            return ""
    except asyncio.TimeoutError:
        logger.error(f"请求超时：{url}")
        return ""
```

### 3. 日志记录

使用标准日志记录关键操作：

```python
import logging

logger = logging.getLogger(__name__)

async def search(query: SearchQuery) -> list[RawSearchItem]:
    """搜索资源"""
    logger.info(f"执行搜索：{query.keyword}")
    
    # 实现搜索逻辑
    
    logger.info(f"搜索完成，找到 {len(results)} 个结果")
    return results
```

### 4. 配置验证

在启动时验证配置参数：

```python
def validate_config(config: dict) -> bool:
    """验证配置"""
    if not config.get("api_key"):
        raise ValueError("API Key 不能为空")
    
    if config.get("timeout", 30) < 1:
        raise ValueError("超时时间必须大于 0")
    
    return True
```

### 5. 测试覆盖

编写完整的测试用例：

```python
import pytest
from my_plugin.adapter import search, create_plugin

@pytest.mark.asyncio
async def test_search():
    """测试搜索功能"""
    query = SearchQuery(keyword="测试", limit=5)
    results = await search(query)
    assert isinstance(results, list)

def test_create_plugin():
    """测试插件创建"""
    plugin = create_plugin()
    assert plugin.id == "my-plugin"
    assert plugin.name == "我的插件"
```

### 6. 文档齐全

提供完整的 README 和使用说明：

```markdown
# 我的插件

## 功能特性

- 支持多源搜索
- 支持配置管理

## 安装方法

1. 在 Web Console 中添加插件仓库地址
2. 配置插件参数

## 使用方法

插件会自动注册到 Sundarr，可以在搜索页面使用。

## 配置说明

- `api_key`: API Key（必填）
- `timeout`: 超时时间（默认 30 秒）

## 常见问题

### Q: 如何获取 API Key？

A: 访问 https://example.com 获取 API Key。
```

## 调试技巧

### 1. 查看日志

查看插件加载和运行日志：

```bash
tail -f ~/.sundarr/logs/sundarr.log | grep plugin
```

### 2. 测试插件

使用测试脚本验证插件功能：

```bash
cd my-plugin
python tests/test_adapter.py
```

### 3. 检查配置

在 Web Console 中检查插件配置是否正确。

### 4. 查看错误

查看插件状态和错误信息：

```bash
curl http://localhost:8000/plugins/plugins/my-plugin
```

## 常见问题

### Q: 插件加载失败怎么办？

A: 检查以下几点：
1. 插件清单文件 `sundarr_plugin.toml` 是否正确
2. 插件入口函数是否正确
3. 依赖项是否已安装
4. 配置参数是否正确

### Q: 如何更新插件？

A: 在 Web Console 中进入插件管理页面，找到要更新的插件仓库，点击 **更新**。

### Q: 如何调试插件？

A: 查看日志文件，使用测试脚本验证插件功能。

### Q: 插件 ID 冲突怎么办？

A: 修改插件清单中的 `id` 字段，使用不同的 ID。

## 参考

- [插件系统概述](20-plugin-system.md)
- [插件清单规范](20-plugin-manifest-spec.md)
- [插件 API 文档](21-plugin-api-spec.md)
- [示例插件](examples/source-plugin-template/)
