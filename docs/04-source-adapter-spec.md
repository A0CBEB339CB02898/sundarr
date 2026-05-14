# Source Adapter 接入规范

本文档定义 Sundarr 多源搜索的接入方式。所有搜索源都通过 Source Adapter 代码实现，实现即时搜索、统一解析和失败隔离。

---

## 1. 设计目标

Source Adapter 必须满足：

```text
多源可扩展
输入统一
输出统一
错误隔离
超时可控
后续管线复用
真实网站可逐个接入
站点差异由 Adapter 封装
```

不得把具体网站逻辑写死在 Search Service 中。

当前实现边界：

```text
搜索源统一由 Source Adapter 代码定义，不再由用户通过 Web Console 创建 configurable / document source。
每个真实搜索源通常使用一个 Python 文件实现。
Search Service 只调度统一接口，不写具体站点规则。
当前第一个真实搜索源为 `SeedHubSource`，参考 seedhub-cli 的 `/s/{keyword}/` 列表搜索、`/movies/{id}/` 详情页解析和 `/link_start/` 跳转页链接解析方式。
Sources 页面以列表展示已安装搜索源，详情弹窗提供测试入口和步骤日志。
```

原因：

```text
真实媒体源不是简单 URL 配置或本地文档维护问题。
它通常需要站点规则、分页、请求头、登录态、限流、解析规则、失败隔离、合法性边界和反爬处理。
这些能力超出当前 MVP 的 Source Adapter 骨架和 Sources 页面范围。
```

正确结构：

```text
Source Adapter
  -> RawSearchItem
  -> Parser
  -> Cloud Link Extractor
  -> Normalizer
  -> Deduper
  -> Ranker
  -> Resource Library
```

---

## 2. Source Adapter

适合真实媒体网站。

特点：

```text
通过 Python Adapter 实现
支持分页、特殊请求、复杂解析
支持进入详情页二次解析
支持站点级限流、超时和错误处理
不允许 Web Console 在线编辑代码
```

每个真实网站通常需要一个 Adapter，但 Adapter 复用统一 SDK、HTTP 工具、链接提取器、测试夹具和错误处理。

### 2.1 文档型网站实验

后续可以单独验证“文档型网站是否存在可通用读取模式”。

实验目标：

```text
判断文档型网站是否能通过统一模板读取。
判断是否值得抽象为专用 Adapter 模板。
明确哪些平台必须走专用 connector 或代码型 Adapter。
```

该实验不包含：

```text
要求用户维护本地 CSV / Markdown / plain text。
承诺通用在线文档读取。
承诺处理所有在线文档平台的登录、权限和导出格式。
```

### 2.2 不作为近期主线的源类型

```text
simple HTML configurable source
本地文档/表格源
通用在线文档读取
Web Console 配置复杂爬虫
```

---

## 3. SearchQuery

所有 Source Adapter 使用统一输入。

```json
{
  "keyword": "interstellar",
  "result_type": "all",
  "limit": 20
}
```

字段规则：

```text
keyword 必填。
result_type 可选，允许 all / magnet / quark / aliyun / baidu / xunlei / unknown。
limit 由 Search Service 统一限制最大值。
```

Adapter 不应修改 SearchQuery。

---

## 4. RawSearchItem

所有 Source Adapter 必须输出统一 RawSearchItem。

```json
{
  "source_id": "example_site",
  "source_type": "code",
  "raw_title": "Interstellar 2014 1080p",
  "raw_url": "https://example.invalid/detail/123",
  "raw_content": "share url: https://pan.quark.cn/s/abc code: 1234",
  "published_at": null,
  "fetched_at": "2026-05-04T10:00:00Z",
  "metadata": {}
}
```

字段规则：

```text
source_id 必填。
source_type 必填。
raw_title 必填；没有标题时使用可读的短文本。
raw_url 可为空，但应尽量提供来源页面。
raw_content 必填，用于链接提取。
published_at 可为空。
fetched_at 必填。
metadata 可保存 source 特有信息，但后续管线不能依赖特定 source 的 metadata 才能工作。
```

---

## 5. SourceModel 接口

```python
from dataclasses import dataclass
from collections.abc import Awaitable, Callable

SearchFunction = Callable[[SearchQuery], Awaitable[list[RawSearchItem]]]

@dataclass(frozen=True)
class SourceModel:
    id: str
    name: str
    description: str
    homepage_url: str
    search_function: SearchFunction
    test_function: SourceTestFunction | None = None
```

规则：

```text
Adapter 只负责获取和转换 raw item。
Adapter 不负责去重。
Adapter 不负责最终排序。
Adapter 不负责入库。
Adapter 不负责下载或转存。
```

---

## 6. Source 注册方式

Source Adapter 事实来源是代码：

```text
sundarr/app/sources/registry.py
```

每个 source 实现通常提供一个具体类或模块级函数，但对搜索管线暴露为 `SourceModel` 实例：

```text
id
name
description
homepage_url
search_function
test_function
```

注册示例：

```python
from sundarr.app.sources.base import SourceModel
from sundarr.app.sources.seedhub import SeedHubSource


def get_registered_sources():
    seedhub = SeedHubSource()
    return [
        SourceModel(
            id=seedhub.id,
            name=seedhub.name,
            description=seedhub.description,
            homepage_url=seedhub.homepage_url,
            search_function=seedhub.search,
            test_function=seedhub.test_search,
        )
    ]
```

搜索源不通过数据库启用、禁用或保存合规说明、错误状态、信任等级等旧配置字段。`sources` 表仅作为代码 Adapter 的目录表，由项目初始化或 API 读取时同步 `id`、`name`、`description`、`homepage_url`，不得保存可执行代码或用户可编辑的爬虫规则。

不得在数据库、配置文件或 Web Console 中保存可执行 Python 代码。

### 6.1 外部 Git 搜索源仓库

后续真实搜索源支持放入独立 Git 仓库，由 Sundarr Core 受控加载。

设计原则：

```text
Sundarr Core 只提供 Source Adapter SDK、加载框架、搜索管线和 Web Console。
真实搜索源代码可以集中放在独立 Git 仓库中。
Sundarr 只保存仓库地址、分支和锁定 commit。
系统从本地缓存中的已锁定 commit 加载搜索源。
默认不在每次启动时无条件执行远程最新代码。
```

该模式详见 `docs/19-source-repository-plugin-spec.md`。

### 6.2 SourceModel 分层边界

外部仓库接入不把来源、commit、加载状态和配置 schema 直接塞入 `SourceModel`。

后续模型分层：

```text
SourceManifest：来自外部仓库清单，描述搜索源声明。
LoadedSource：系统加载结果，描述来源、commit、状态、错误和 SourceModel。
SourceModel：SearchService 调用的最小运行时执行协议。
```

当前 `SourceModel` 继续作为 Adapter API v1 的执行接口，以兼容现有搜索管线和内置源。

---

## 7. 错误隔离

Search Service 必须隔离单个 source 的失败。

规则：

```text
一个 source 超时，不影响其他 source。
一个 source 抛异常，不影响聚合搜索整体返回。
source 错误必须记录 source_id、error_code、duration。
连续失败的 source SHOULD 短期熔断。
```

错误码建议：

```text
SEARCH_SOURCE_TIMEOUT
SEARCH_SOURCE_FAILED
SOURCE_CONFIG_INVALID
SOURCE_PARSE_FAILED
```

---

## 8. 超时和并发

MVP 默认策略：

```text
source timeout: 10s
global search timeout: 15s
max concurrent sources: 5
```

规则：

```text
Search Service 控制全局并发。
Adapter 可以有自己的内部 timeout，但不能超过全局限制。
Adapter 不应无限重试。
```

---

## 9. Web Console 管理范围

Web Console 可以管理：

```text
已安装搜索源列表
Adapter 测试搜索
Adapter 测试过程日志和预览结果
```

Web Console 不允许：

```text
在线编辑 Source Adapter
创建、删除、启用或禁用搜索源
上传执行 Python 代码
在配置或数据库中保存可执行 Python 代码
配置复杂网站爬虫
绕过 Source Adapter 接口直接改搜索服务逻辑
```

Source Adapter 必须通过代码实现和部署。

---

## 10. 新增真实网站 Source 步骤

```text
新增 Python Adapter 类。
实现 id、name、description 和 async search(query)。
按需实现详情页解析、分页和站点级限流。
输出 RawSearchItem。
添加 fixture 测试。
在 registry.py 中注册 SourceModel。
在 Web Console 执行测试搜索。
```

---

## 11. 验收标准

Source Adapter 框架完成时必须满足：

```text
至少一个示例 source 可搜索。
所有 source 输出 RawSearchItem。
单个 source 失败不影响整体搜索。
source timeout 生效。
Search Service 能聚合多个 source。
Web Console 可查看已安装搜索源并执行测试搜索。
Source Adapter 不能通过 Web Console 在线编辑。
配置和数据库不保存可执行 Python 代码或用户可编辑爬虫规则。
```
