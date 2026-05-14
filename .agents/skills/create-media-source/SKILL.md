---
name: create-media-source
description: Use when creating, debugging, testing, or extending Sundarr code-based media source adapters such as SeedHub under sundarr/app/sources/.
---

# 创建媒体源

## 适用场景

当用户要求新增、修复或调试代码型媒体源 Adapter 时使用本 skill。典型目标是让 `sundarr/app/sources/<source>.py` 能稳定返回 `RawSearchItem`，并通过 `SearchService` 归一化为可用的搜索候选。

## 当前架构入口

媒体源是代码型 Adapter，不通过 Web Console 在线编辑代码。

关键文件：

`sundarr/app/sources/<source>.py`

`sundarr/app/sources/registry.py`

`sundarr/app/sources/base.py`

`sundarr/app/services/search_service.py`

`sundarr/app/parsers/link_extractor.py`

`tests/test_search.py`

`tests/test_sources.py`

## 创建步骤

1. 先确认站点搜索入口、详情页 URL 规则、链接承载位置和是否需要跳转解析。
2. 在 `sundarr/app/sources/` 新增或修改 Adapter，至少提供 `id`、`name`、`description`、`homepage_url`、`search()` 和 `test_search()`。
3. `search()` 返回 `RawSearchItem`，`raw_content` 必须包含 `extract_cloud_links()` 能识别的原始链接文本。
4. 在 `registry.py` 注册 `SourceModel`，保证 `/sources` 和 `/search` 使用同一实现。
5. 为搜索 URL、列表解析、详情解析、跳转链接清洗和支持链接识别补充单元测试。

## 调试流程

1. 先直接调用源 Adapter，确认列表页能解析详情页数量。

```powershell
python -c "from sundarr.app.sources.seedhub import SeedHubSource; s=SeedHubSource(); html=s._fetch(s._search_url('keyword')); print(len(s._parse_detail_urls(html)))"
```

2. 再直接调用 `source.search()`，确认源层不抛异常且返回 `RawSearchItem`。

```powershell
python -c "import asyncio; from sundarr.app.sources.seedhub import SeedHubSource; from sundarr.app.schemas.search import SearchQuery; s=SeedHubSource(); items=asyncio.run(s.search(SearchQuery(keyword='keyword', limit=20))); print(len(items)); print([(i.raw_title, i.raw_url) for i in items])"
```

3. 最后通过 `SearchService` 冒烟，确认不会被 10 秒源超时拦截，且结果能归一化。

```powershell
python -c "import asyncio; from sundarr.app.services.search_service import SearchService; from sundarr.app.services.link_validator import LinkValidator; from sundarr.app.sources.registry import get_registered_sources; from sundarr.app.schemas.search import SearchQuery; svc=SearchService(sources=get_registered_sources(), validator=LinkValidator(enable_network=False)); r=asyncio.run(svc.search(SearchQuery(keyword='keyword', result_type='all', limit=20))); print(r.count, [(sr.source_id, sr.count, sr.error) for sr in r.source_results])"
```

## 排查重点

1. 如果源层能返回但 `/search` 无结果，检查 `raw_content` 是否能被 `extract_cloud_links()` 识别。
2. 如果 `source_results.error` 是 `SEARCH_SOURCE_TIMEOUT`，检查是否在事件循环里执行了同步网络请求，详情页和跳转解析应使用 `asyncio.to_thread()` 并发执行。
3. 如果遇到 `InvalidURL`，优先清洗站点跳转链接中的非必要查询参数，尤其是包含空格、中文、emoji 的标题参数。
4. 支持的新网盘域名必须同步考虑 `link_extractor.py`、源内直接链接提取和 `_contains_supported_link()` 的一致性。
5. 真实站点 HTML 的终端输出可能因 PowerShell 编码显示为乱码，必要时用 `text.encode('unicode_escape').decode()` 判断程序内字符串是否正确。

## 测试要求

最小回归：

```powershell
pytest tests/test_search.py tests/test_sources.py
```

完整回归：

```powershell
pytest
```

验收时至少记录：

`source.search()` 返回数量。

`SearchService` 的 `source_results` 中该源 `error` 为 `None`。

本次新增或修复的解析边界已被单元测试覆盖。

## SeedHub 经验

SeedHub 的 `/link_start/` 跳转链接会携带 `movie_title`，其中可能包含空格、中文或 emoji。请求前只保留必要的 `redirect_to` 参数，避免 `InvalidURL` 中断整个搜索。

SeedHub 详情页和跳转链接数量较多，串行请求容易超过 `SearchService` 的 10 秒源超时。详情页抓取和跳转解析应并发执行，并且异常只跳过当前详情或链接，不应让整个源失败。
