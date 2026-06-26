# 插件清单规范

## 概述

插件清单文件 `sundarr_plugin.toml` 是插件的配置文件，定义了插件的元数据、配置和入口点。

## 文件格式

插件清单使用 TOML 格式，包含以下部分：

1. **基本元数据**: 插件 ID、名称、版本等
2. **插件类型**: 插件的功能类型
3. **入口点**: 插件的入口函数
4. **配置字段声明**: 插件的配置参数

## 基本元数据

```toml
id = "my-plugin"
name = "我的插件"
version = "1.0.0"
plugin_type = "source"
description = "这是一个示例插件"
author = "Your Name"
homepage_url = "https://github.com/yourname/my-plugin"
adapter_api_version = "1.0"
```

### 字段说明

- **id**: 插件的唯一标识符，必须全局唯一
  - 格式：小写字母、数字、连字符
  - 示例：`quark-provider`, `dingtalk-notification`
  - 长度：3-50 字符

- **name**: 插件的显示名称
  - 示例：`夸克网盘 Provider`, `钉钉通知`

- **version**: 插件版本号
  - 格式：语义化版本（Semantic Versioning）
  - 示例：`1.0.0`, `1.2.3-beta.1`

- **plugin_type**: 插件类型
  - 可选值：`source`, `cloud_provider`, `notification`, `crawler`, `link_validator`, `link_extractor`, `task_processor`

- **description**: 插件的简短描述
  - 长度：不超过 200 字符

- **author**: 插件作者
  - 示例：`Sundarr Team`

- **homepage_url**: 插件项目主页 URL
  - 示例：`https://github.com/sundarr/my-plugin`

- **adapter_api_version**: 适配器 API 版本
  - 当前版本：`1.0`
  - 必须与 Sundarr 版本兼容

## 入口点

```toml
entry = "my_plugin.adapter:create_plugin"
```

### 入口点格式

入口点格式为 `module:function`，其中：

- **module**: Python 模块路径
  - 示例：`my_plugin.adapter`, `quark_provider.main`

- **function**: 模块中的函数名
  - 该函数必须返回插件实例
  - 对于 `source` 类型，返回 `SourceModel` 或 `List[SourceModel]`
  - 对于其他类型，返回相应的插件实例

### 入口函数规范

入口函数必须：

1. 无参数调用
2. 返回插件实例
3. 不抛出异常（或抛出明确的错误信息）

```python
def create_plugin():
    """创建插件实例"""
    return MyPlugin()
```

## 配置字段声明

```toml
[config_schema]
api_key = { type = "string", required = true, label = "API Key", secret = true }
timeout = { type = "integer", default = 30, label = "超时时间（秒）", min = 1, max = 300 }
```

### 字段类型

- **string**: 字符串
- **integer**: 整数
- **boolean**: 布尔值
- **select**: 下拉选择
- **password**: 密码输入（显示为 ***）

### 字段属性

- **type**: 字段类型（必填）
- **required**: 是否必填（默认为 `false`）
- **label**: 字段显示名称
- **secret**: 是否为敏感信息（显示为 ***）
- **default**: 默认值
- **placeholder**: 输入提示
- **min**: 最小值（仅 integer）
- **max**: 最大值（仅 integer）
- **options**: 选项列表（仅 select）

### 示例

```toml
[config_schema]
# 字符串字段
api_key = { type = "string", required = true, label = "API Key", secret = true }

# 整数字段
timeout = { type = "integer", default = 30, label = "超时时间（秒）", min = 1, max = 300 }

# 布尔字段
enable_proxy = { type = "boolean", default = false, label = "启用代理" }

# 下拉选择字段
proxy_type = { type = "select", label = "代理类型", options = ["HTTP", "HTTPS", "SOCKS5"] }

# 密码字段
password = { type = "password", label = "密码", secret = true }
```

## 依赖声明

```toml
dependencies = ["other-plugin", "another-plugin"]
```

### 依赖说明

- **dependencies**: 依赖的其他插件 ID 列表
- 插件系统会自动解析依赖关系
- 如果依赖的插件不存在或加载失败，当前插件也会加载失败

## 完整示例

```toml
# 插件清单示例

id = "quark-provider"
name = "夸克网盘 Provider"
version = "1.0.0"
plugin_type = "cloud_provider"
description = "夸克网盘直链下载支持"
author = "Sundarr Team"
homepage_url = "https://github.com/sundarr/quark-provider"
adapter_api_version = "1.0"
entry = "quark_provider.adapter:create_provider"

# 依赖
dependencies = []

# 配置字段声明
[config_schema]
cookie = { type = "password", required = true, label = "Cookie", secret = true, placeholder = "请输入夸克网盘 Cookie" }
timeout = { type = "integer", default = 30, label = "超时时间（秒）", min = 1, max = 300 }
```

## 验证规则

插件清单必须满足以下规则：

1. **id**: 必须全局唯一，格式为小写字母、数字、连字符，长度 3-50 字符
2. **version**: 必须符合语义化版本格式
3. **plugin_type**: 必须是支持的插件类型之一
4. **adapter_api_version**: 必须与 Sundarr 版本兼容
5. **entry**: 必须是有效的 `module:function` 格式

## 常见错误

### 1. ID 冲突

```
ValueError: 插件 ID 冲突：my-plugin 已被内置插件占用
```

**解决方案**: 修改插件清单中的 `id` 字段，使用不同的 ID。

### 2. 版本格式错误

```
ValueError: 无效的版本号：1.0
```

**解决方案**: 使用语义化版本格式，如 `1.0.0`。

### 3. 插件类型错误

```
ValueError: 无效的插件类型：unknown
```

**解决方案**: 使用支持的插件类型之一。

### 4. 入口点错误

```
ModuleNotFoundError: No module named 'my_plugin'
```

**解决方案**: 检查模块路径是否正确，确保模块存在。

### 5. 依赖缺失

```
ValueError: 依赖插件不存在：other-plugin
```

**解决方案**: 安装依赖的插件，或修改依赖声明。

## 最佳实践

1. **使用有意义的 ID**: ID 应该简洁明了，易于识别
2. **语义化版本**: 使用语义化版本号，便于版本管理
3. **详细的描述**: 提供清晰的插件描述和配置说明
4. **合理的配置**: 只声明必要的配置字段，设置合理的默认值
5. **错误处理**: 在入口函数中处理可能的错误
6. **文档齐全**: 提供完整的 README 和使用说明

## 参考

- [插件系统概述](20-plugin-system.md)
- [插件 API 文档](21-plugin-api-spec.md)
- [插件开发指南](22-plugin-development-guide.md)
