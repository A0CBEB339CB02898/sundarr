# 示例搜索源插件

这是一个 Sundarr 搜索源插件的示例模板，用于展示如何创建自定义搜索源。

## 功能特性

- 支持多源搜索
- 支持配置管理
- 支持测试搜索
- 支持详情获取

## 文件结构

```
source-plugin-template/
├── sundarr_plugin.toml      # 插件清单
├── my_source/
│   ├── __init__.py
│   ├── adapter.py           # 源适配器实现
│   └── parser.py            # HTML/JSON 解析器
├── README.md                # 使用说明
└── tests/
    └── test_adapter.py      # 测试文件
```

## 快速开始

### 1. 安装插件

开发测试可使用 `PluginLoader.load_from_local()` 加载目录；正式使用通过 `/plugins/repositories` 配置可信 Git 仓库。Web Console 仓库管理页面属于 Phase 10.2，当前尚未完成。

### 2. 配置插件

当前可通过插件 API 配置参数。Web Console 动态配置表单属于 Phase 10.2。

### 3. 使用插件

当前需要显式调用插件加载 API；启动自动加载 locked current_commit 属于 Phase 10.1。

## 开发指南

### 插件清单格式

插件清单文件 `sundarr_plugin.toml` 定义了插件的元数据和配置：

```toml
id = "my-source"
name = "我的搜索源"
version = "1.0.0"
plugin_type = "source"
description = "这是一个示例搜索源"
author = "Your Name"
homepage_url = "https://github.com/yourname/my-source"
adapter_api_version = "1.0"
entry = "my_source.adapter:create_source"

[config_schema]
api_key = { type = "string", required = true, label = "API Key", secret = true }
timeout = { type = "integer", default = 30, label = "超时时间（秒）" }
```

### 入口函数

入口函数必须返回一个 `SourceModel` 实例或 `SourceModel` 列表：

```python
def create_source() -> SourceModel:
    """创建搜索源实例"""
    return SourceModel(
        id="my-source",
        name="我的搜索源",
        description="这是一个示例搜索源",
        homepage_url="https://example.com",
        search_function=search,
        test_function=test_search,
        fetch_detail_function=fetch_detail,
    )
```

### 搜索函数

搜索函数必须是异步函数，接收 `SearchQuery` 参数，返回 `RawSearchItem` 列表：

```python
async def search(query: SearchQuery) -> List[RawSearchItem]:
    """搜索资源"""
    # 实现搜索逻辑
    pass
```

### 测试函数

测试函数用于验证插件是否正常工作：

```python
async def test_search(query: str) -> List[SourceTestEvent]:
    """测试搜索"""
    # 实现测试逻辑
    pass
```

## 配置字段类型

支持的配置字段类型：

- `string`: 字符串
- `integer`: 整数
- `boolean`: 布尔值
- `select`: 下拉选择（需要 `options` 字段）
- `password`: 密码输入（显示为 ***）

## 最佳实践

1. **错误处理**：所有函数都应该有完善的错误处理
2. **超时设置**：网络请求应该设置合理的超时时间
3. **日志记录**：使用标准日志记录关键操作
4. **配置验证**：在启动时验证配置参数
5. **测试覆盖**：编写完整的测试用例
6. **无导入副作用**：测试和插件 import 阶段不得访问实时网络或创建长期资源
7. **可清理资源**：Phase 10.1 后，长期连接和注册必须绑定 PluginActivation cleanup

## 示例代码

参考 `my_source/adapter.py` 中的实现。

## 许可证

MIT License
