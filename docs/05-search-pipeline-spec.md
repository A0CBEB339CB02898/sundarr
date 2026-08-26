# 搜索处理管线规范

本文档定义从多源实时搜索到标准化候选结果、收藏标记和前端展示的统一处理流程。

状态：Core 管线、收藏标记和两阶段详情接口已实现；当前缺少已配置并自动恢复的外部真实 Source。

---

## 1. 管线目标

搜索管线必须把不同来源的结果统一处理为可排序、可去重、可展示的搜索结果。当前搜索页只展示结果，不直接创建 Transfer。

标准流程：

```text
SearchQuery
-> Source Adapter
-> RawSearchItem
-> Parser
-> Cloud Link Extractor
-> Normalizer
-> Deduper
-> Link Validator
-> Ranker
-> Favorite Marker
-> API Response
```

---

## 2. 聚合搜索

Search Service 负责调度多个 source。

规则：

```text
只调用代码中的 SourceModel 实例；搜索源不再单独启用或禁用。
多个 source 并发执行。
单个 source 失败不能影响整体搜索。
source timeout 和 global timeout 必须生效。
所有 source 输出必须转换为 RawSearchItem。
Search Service 可按 result_type 过滤链接类型。
API Response 必须同时返回全局去重结果和每个 source 的独立结果分组，供 Web Console 横向 tab 展示。
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

Cloud Link Extractor 负责识别磁力 / 网盘 provider、url、code 和 confidence。

输出结构：

```json
{
  "provider": "quark",
  "url": "https://pan.quark.cn/s/xxxx",
  "code": null,
  "raw_text": "quark: https://pan.quark.cn/s/xxxx",
  "confidence": 0.95
}
```

MVP 必须处理：

```text
magnet
quark
aliyun
baidu
xunlei
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
year
links
is_favorited
```

ResourceCandidate 只表示实时搜索候选资源，不默认入库。

Link 级字段：

```text
id
provider
name
url
code
quality
valid
validation_status
validation_message
checked_at
source_id
source_url
is_favorited
```

规则：

```text
quality 属于具体 ResourceLink，表示该链接的版本/画质标签，不属于 Resource。
name 属于具体 ResourceLink，用于前端展示该链接对应的资源版本名称；无法从源站精确获取时，可由资源标题和 quality 兜底生成。
type 获取不稳定，不作为 MVP 最小搜索结果字段。
score / explanation 只属于搜索排序内部过程，不作为前端主展示或持久化事实字段。
```

---

## 6. Deduper

Deduper 负责合并同一媒体资源的多个来源或版本。

依据：

```text
normalized_title
year
provider url
quality
```

MVP 可以使用启发式规则，不引入复杂推荐算法。

合并规则：

```text
同一 Resource 可保留多个 ResourceLink。
同一真实链接只保留一次，标题可任选较早或评分较高的结果展示。
不同 quality 可作为同一资源的不同候选 link。
无法高置信合并时保留为独立候选。
```

持久化边界：

```text
/search 只做实时搜索与聚合，不自动写入 resources / resource_links。
只有用户主动收藏资源或收藏链接时，才写入 Resource / ResourceLink。
实时搜索结果返回前可以查询收藏库，为 ResourceCandidate / ResourceLinkResult 附加 is_favorited 标记。
收藏库不作为 /search 的替代数据源；用户点击搜索时始终调用 Source Adapter。
```

收藏刷新策略：

```text
收藏资源刷新：基于 title / original_title / year 重新触发实时搜索，返回最新候选结果供用户选择。
收藏链接刷新：只重新检测该链接的 valid / checked_at，不重新搜索所有媒体源。
刷新必须由用户显式触发，MVP 不做后台自动刷新。
```

---

## 6.5 Link Validator

Link Validator 负责在搜索返回前同步检测链接有效性。

规则：

```text
磁力、thunder、ed2k 等下载协议链接只做格式级有效性判断，不承诺资源活性。
已识别网盘链接优先使用 provider 公开接口或页面信号检测。
当前支持 quark / aliyun / baidu / xunlei / uc / 115 / 123pan / tianyi。
无法识别 provider 或 provider 没有明确检测信号时使用轻量 HEAD / GET 兜底。
404 / 410 视为 invalid。
401 / 403 / 405 / 429 视为 unknown，避免把登录、权限或限流误判为失效。
需要提取码但分享存在时视为 valid。
需要登录、验证码或风控校验时视为 unknown。
检测失败不影响搜索结果展示。
```

输出字段：

```text
valid
validation_status
validation_message
checked_at
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

## 8. 收藏标记与入库边界

Search Service 不把搜索结果自动沉淀到 Resource Library。

收藏库写入只发生在用户动作中：

```text
用户收藏资源 -> upsert resources，并设置 favorited_at。
用户收藏链接 -> upsert 最小 resources 父记录，upsert resource_links，并设置 link.favorited_at。
用户取消收藏资源 -> 清空 resource.favorited_at；如无收藏链接引用，后续可清理。
用户取消收藏链接 -> 删除 resource_links 或清空 link.favorited_at；MVP 建议直接删除该收藏链接记录。
```

搜索返回前可以读取收藏库：

```text
按 normalized_title / original_title / year 标记 ResourceCandidate.is_favorited。
按 provider + normalized(url) 标记 ResourceLinkResult.is_favorited。
收藏库只提供标记，不替代实时搜索源结果。
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

缓存不替代 Source Adapter 实时搜索，也不替代收藏库。

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
搜索结果默认不自动入库。
API 返回结果可标记资源和链接是否已收藏。
用户主动收藏资源或链接后，可在收藏库中读取。
```
