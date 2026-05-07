# Source Adapter 接入规范

本文档定义 Sundarr 多源搜索的接入方式。目标是通过代码型 Source Adapter 接入真实媒体网站，实现即时搜索、统一解析和失败隔离。

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
Phase 0-7 已实现 Source Adapter 抽象、ExampleSource、Search Pipeline、sources API 和 Web Console 管理入口。
Phase 0-7 未实现真实网站代码型 Adapter SDK 的完整开发体验。
Phase 0-7 未实现通过 Web Console 配置复杂网站爬虫。
真实媒体源接入需要作为后续独立大阶段设计和验收。
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

## 2. Source 类型

近期主线只保留代码型源。

### 2.1 代码型源

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

### 2.2 文档型网站实验

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

### 2.3 不作为近期主线的源类型

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
  "type": "movie",
  "year": 2014,
  "season": null,
  "episode": null,
  "limit": 20
}
```

字段规则：

```text
keyword 必填。
type 可选，允许 movie / tv / anime / unknown。
year 可选。
season / episode 可选。
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
  "raw_content": "share url: https://pan.example.invalid/s/abc code: 1234",
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

## 5. BaseSource 接口

```python
class BaseSource:
    id: str
    name: str
    source_type: str
    enabled: bool

    async def search(self, query: SearchQuery) -> list[RawSearchItem]:
        raise NotImplementedError
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

## 6. Source 配置字段

所有 source 必须具备基础字段：

```text
id
name
type
enabled
trust_level
legal_note
adapter_module
config_json
created_at
updated_at
```

代码型源配置示例：

```json
{
  "id": "site_a",
  "name": "站点 A",
  "type": "code",
  "enabled": true,
  "trust_level": 1,
  "legal_note": "用户自行确认来源合法性",
  "adapter_module": "sundarr.app.sources.adapters.site_a",
  "config_json": {
    "base_url": "https://example.invalid",
    "timeout_seconds": 10,
    "rate_limit_per_minute": 20,
    "user_agent": "Sundarr"
  }
}
```

配置只保存开关、基础 URL、超时、限流、User-Agent 等参数，不保存可执行 Python 代码。

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
已安装代码型 Adapter
Adapter 启用 / 禁用
Adapter 非代码参数
Adapter 测试搜索
Adapter 最后错误和耗时
```

Web Console 不允许：

```text
在线编辑代码型 Source Adapter
上传执行 Python 代码
在配置或数据库中保存可执行 Python 代码
配置复杂网站爬虫
绕过 Source Adapter 接口直接改搜索服务逻辑
```

代码型源必须通过代码实现和部署。

---

## 10. 新增真实网站 Source 步骤

```text
新增 Python Adapter 类。
继承 BaseSource。
实现 search(query)。
按需实现详情页解析、分页和站点级限流。
输出 RawSearchItem。
添加 fixture 测试。
注册 adapter。
在 Web Console 启用并执行测试搜索。
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
Web Console 可管理已安装代码型 Adapter。
代码型源不能通过 Web Console 在线编辑。
配置和数据库不保存可执行 Python 代码。
```
