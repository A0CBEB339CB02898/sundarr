# 搜索处理管线规范

本文档定义从多源搜索到资源库入库的统一处理流程。

---

## 1. 管线目标

搜索管线必须把不同来源的结果统一处理为可排序、可入库、可创建搬运任务的资源候选。

标准流程：

```text
SearchQuery
-> Source Adapter
-> RawSearchItem
-> Parser
-> Cloud Link Extractor
-> Normalizer
-> Deduper
-> Ranker
-> Resource Library
-> API Response
```

---

## 2. 聚合搜索

Search Service 负责调度多个 source。

规则：

```text
只调用 enabled source。
多个 source 并发执行。
单个 source 失败不能影响整体搜索。
source timeout 和 global timeout 必须生效。
所有 source 输出必须转换为 RawSearchItem。
```

MVP 默认：

```text
source timeout = 10s
global timeout = 15s
max concurrent sources = 5
```

---

## 3. Parser

Parser 负责从 RawSearchItem 中提取可分析文本和字段。

MVP Parser：

```text
HTML text extraction
plain text extraction
Markdown extraction
CSV row extraction
```

Parser 不负责：

```text
最终去重
最终排序
转存
下载
入库事务管理
```

---

## 4. Cloud Link Extractor

Cloud Link Extractor 负责识别网盘 provider、url、code 和 confidence。

输出结构：

```json
{
  "provider": "quark",
  "url": "https://pan.example.invalid/s/xxxx",
  "code": null,
  "raw_text": "quark: https://pan.example.invalid/s/xxxx",
  "confidence": 0.95
}
```

MVP 必须处理：

```text
链接和提取码不在同一行
同一文本多个链接
一条资源多个 provider
标题、广告、说明混杂
提取码 / 密码 / 访问码 / code
```

---

## 5. Normalizer

Normalizer 负责把 RawSearchItem + extracted links 转成 ResourceCandidate。

规则：

```text
保留 raw_title。
保留 source_url。
无法识别字段填 null。
不得编造年份、类型、季集信息。
MVP 使用规则推断 media_type 和 target library。
低置信度字段必须保留 confidence 或 unknown。
```

标准字段：

```text
title
normalized_title
original_title
type
year
season
episodes
quality
language
subtitle
source_id
source_url
links
score
```

---

## 6. Deduper

Deduper 负责合并同一媒体资源的多个来源或版本。

依据：

```text
normalized_title
year
type
season
episodes
provider url
quality
size_bytes
```

MVP 可以使用启发式规则，不引入复杂推荐算法。

合并规则：

```text
同一 Resource 可保留多个 ResourceLink。
不同 quality 可作为同一资源的不同候选 link。
无法高置信合并时保留为独立候选。
```

---

## 7. Ranker

Ranker 负责统一排序。

初始评分：

```text
final_score =
  title_score      * 0.40 +
  source_weight    * 0.20 +
  freshness_score  * 0.15 +
  link_valid_score * 0.15 +
  quality_score    * 0.10
```

规则：

```text
source 不决定最终排序。
ranker 不做合法性判断。
ranker 输出 score 和 explanation。
```

---

## 8. Resource Library 入库

Search Service 必须把搜索结果沉淀到 Resource Library。

入库对象：

```text
resources
resource_links
transfer history relation if needed later
```

规则：

```text
同一 link 不重复插入。
资源重复时更新 updated_at 和 score。
保留 source_id 和 source_url。
不要把搜索缓存当作资源库事实来源。
```

---

## 9. 缓存

Redis 可用于搜索缓存。

建议：

```text
普通关键词缓存 10 分钟
热门关键词缓存 1 小时
失败 source 熔断 5 分钟
```

缓存不替代 PostgreSQL 资源库。

---

## 10. 验收标准

搜索管线完成时必须满足：

```text
可并发调用多个 source。
source 失败不影响整体返回。
RawSearchItem 可转 ResourceCandidate。
可提取至少一种 provider 链接。
可基础去重。
可基础排序。
搜索结果可入库。
API 返回结果包含 candidate explanation 或 score 字段。
```
