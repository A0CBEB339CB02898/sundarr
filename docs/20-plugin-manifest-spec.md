# 插件清单规范

插件清单文件名为 `sundarr_plugin.toml`。当前稳定范围只包括 Python SOURCE 插件。更新时间：2026-08-26。

---

## 1. 当前支持格式

```toml
id = "my-source"
name = "我的搜索源"
version = "1.0.0"
plugin_type = "source"
description = "示例搜索源。"
author = "Sundarr Team"
homepage_url = "https://github.com/example/my-source"
adapter_api_version = "1.0"
entry = "my_source.adapter:create_source"

dependencies = []

[config_schema]
timeout = { type = "integer", default = 30, label = "超时时间（秒）", min = 1, max = 300 }
```

字段：

```text
id                    全局唯一，小写字母、数字和连字符，3-50 字符。
name                  简体中文或明确的站点显示名。
version               插件自身语义化版本。
plugin_type           当前必须为 source。
description           简短用途说明。
author                可选作者信息。
homepage_url          可选项目主页。
adapter_api_version   当前使用 "1.0"。
entry                 module:function。
dependencies          当前兼容字段；Phase 10.1 后由 requires 取代能力依赖语义。
config_schema         Web/API 可管理的非代码配置声明。
```

---

## 2. 入口协议

当前入口函数无参数调用，返回：

```python
SourceModel
list[SourceModel]
```

禁止在 import 或入口阶段：

```text
执行未受控的长期网络循环。
创建无法释放的线程或定时器。
访问 Sundarr 数据库、SMB 凭据或 Worker 私有对象。
修改全局注册中心。
```

Phase 10.1 引入 PluginContext 后，将增加兼容的 Activation 入口形式；旧 v1 无参数入口在明确迁移期内继续支持。

---

## 3. 配置字段

支持：

```text
string
integer
boolean
select
password
```

字段属性：

```text
type
required
label
secret
default
placeholder
min / max
options
```

敏感字段必须标记 `secret = true`，API 和日志不得回显明文。

---

## 4. Phase 10.1 生命周期扩展

目标格式：

```toml
[runtime]
requires = ["source_registry", "http_client"]
provides = ["source:my-source"]
```

语义：

```text
requires 中任一能力缺失时不激活插件。
provides 只在候选 Activation 验证成功并切换后可见。
禁用、更新、回滚或删除时撤销 provides 并执行 cleanup。
```

在 Core 完成该字段实现前，清单可以不写 `[runtime]`，插件也不得假定依赖注入已经存在。

---

## 5. 校验规则

```text
清单路径必须位于锁定 commit 的仓库目录内。
entry module 不得通过路径或符号链接越界。
plugin_type 和 adapter_api_version 必须受当前 Core 支持。
SOURCE 列表中的每个 SourceModel.id 必须全局唯一。
RawSearchItem.source_id 必须与对应 SourceModel.id 一致。
配置必须通过 config_schema；数据库不得保存可执行代码。
```

---

## 6. 当前不支持

以下仅是未来扩展概念，不是当前可用 SDK：

```text
cloud_provider
notification
crawler
link_validator
link_extractor
task_processor
```

不得用这些类型绕过 Cloud Direct Download 的非 MVP 边界。

---

## 7. 参考

```text
docs/20-plugin-system.md
docs/21-plugin-api-spec.md
docs/22-plugin-development-guide.md
examples/source-plugin-template/
```
