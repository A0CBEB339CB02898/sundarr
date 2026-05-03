# Source Adapter 接入规范

本文档定义 Sundarr 多源搜索的接入方式。目标是让新媒体源接入方便、快捷、格式统一。

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
```

不得把具体网站逻辑写死在 Search Service 中。

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

MVP 支持三类源：

```text
configurable   配置型源
code           代码型源
document       文档/表格型源
```

### 2.1 配置型源

适合结构稳定、规则简单的网站或页面。

特点：

```text
通过配置描述搜索 URL、结果选择器、字段映射
无需写 Python 代码
可由 Web Console 管理
```

### 2.2 代码型源

适合需要复杂逻辑的源。

特点：

```text
通过 Python Adapter 实现
支持分页、特殊请求、复杂解析
不允许 Web Console 在线编辑代码
```

### 2.3 文档/表格型源

适合用户维护的合法资源表。

特点：

```text
支持 Markdown / plain text / CSV
后续可扩展在线文档和在线表格
可由 Web Console 管理
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
  "source_type": "configurable",
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
created_by_user
config_json
created_at
updated_at
```

配置型源示例：

```json
{
  "id": "example_site",
  "name": "Example Site",
  "type": "configurable",
  "enabled": true,
  "trust_level": 1,
  "legal_note": "User configured source",
  "config_json": {
    "base_url": "https://example.invalid",
    "search_url": "https://example.invalid/search?q={keyword}",
    "selectors": {
      "item": ".result-item",
      "title": ".title",
      "url": "a@href",
      "content": ".summary"
    }
  }
}
```

文档/表格型源示例：

```json
{
  "id": "my_csv",
  "name": "My CSV",
  "type": "document",
  "enabled": true,
  "trust_level": 1,
  "legal_note": "Personal maintained list",
  "config_json": {
    "format": "csv",
    "url": "https://example.invalid/resources.csv",
    "columns": {
      "title": "title",
      "link": "link",
      "code": "code",
      "quality": "quality",
      "year": "year"
    }
  }
}
```

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
配置型源
文档/表格型源
```

Web Console 不允许：

```text
在线编辑代码型 Source Adapter
上传执行 Python 代码
绕过 Source Adapter 接口直接改搜索服务逻辑
```

代码型源必须通过代码实现和部署。

---

## 10. 新增 Source 步骤

配置型源：

```text
在 Web Console 新增 source。
填写 search_url 和 selectors。
点击 test source。
确认 RawSearchItem 输出正常。
启用 source。
```

代码型源：

```text
新增 Python Adapter 类。
继承 BaseSource。
实现 search(query)。
输出 RawSearchItem。
添加单元测试。
注册 adapter。
```

文档/表格型源：

```text
在 Web Console 新增 document source。
填写 URL 或文件路径。
配置字段映射。
点击 test source。
确认 RawSearchItem 输出正常。
启用 source。
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
Web Console 可管理配置型源和文档/表格型源。
代码型源不能通过 Web Console 在线编辑。
```
