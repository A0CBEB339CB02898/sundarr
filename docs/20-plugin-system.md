# Sundarr 插件系统

## 概述

Sundarr 插件系统提供统一的插件注册、发现和管理机制，支持多种插件类型，帮助用户扩展 Sundarr 的功能。

### 支持的插件类型

- **Source (搜索源)**: 扩展 Sundarr 的搜索能力，支持从多个网站搜索资源
- **Cloud Provider (网盘 Provider)**: 支持从不同网盘下载资源
- **Notification (通知渠道)**: 支持通过不同渠道发送通知
- **Crawler (爬虫)**: 支持监控外部数据源（如豆瓣想看列表）
- **Link Validator (链接验证器)**: 验证资源链接的有效性
- **Link Extractor (链接提取器)**: 从网页中提取资源链接
- **Task Processor (任务处理器)**: 处理不同类型的任务

## 快速开始

### 1. 安装插件

#### 方式一：从 Git 仓库安装（推荐）

在 Web Console 中添加插件仓库地址：

1. 进入 **插件管理** 页面
2. 点击 **添加仓库**
3. 输入 Git 仓库 URL 和分支名称
4. 点击 **确定**

#### 方式二：从本地目录安装

将插件目录复制到 `~/.sundarr/plugins/repos/` 目录下。

### 2. 配置插件

1. 在 **插件管理** 页面找到已安装的插件
2. 点击 **配置**
3. 填写配置参数
4. 点击 **保存**

### 3. 使用插件

配置完成后，插件会自动注册到 Sundarr，可以在相应功能中使用。

## 插件管理

### Web Console 管理

Sundarr 提供了专业的 Web Console 来管理插件：

- **插件仓库管理**: 添加、更新、回滚、删除插件仓库
- **插件列表**: 查看所有已安装的插件及其状态
- **插件配置**: 配置插件的运行参数
- **插件统计**: 查看插件的使用情况

### API 管理

Sundarr 提供了完整的 API 来管理插件：

```
# 获取所有插件
GET /plugins/plugins

# 获取插件详情
GET /plugins/plugins/{plugin_id}

# 添加插件仓库
POST /plugins/repositories

# 更新插件仓库
PUT /plugins/repositories/{repo_id}

# 启用插件
POST /plugins/plugins/{plugin_id}/enable

# 禁用插件
POST /plugins/plugins/{plugin_id}/disable

# 更新插件配置
PUT /plugins/plugins/{plugin_id}/config
```

## 插件开发

### 开发流程

1. 创建插件目录结构
2. 编写插件清单文件 `sundarr_plugin.toml`
3. 实现插件功能
4. 测试插件
5. 发布插件

### 目录结构

```
my-plugin/
├── sundarr_plugin.toml      # 插件清单
├── my_plugin/
│   ├── __init__.py
│   └── adapter.py           # 插件实现
├── README.md                # 使用说明
└── tests/
    └── test_adapter.py      # 测试文件
```

### 插件清单格式

插件清单文件 `sundarr_plugin.toml` 定义了插件的元数据和配置：

```toml
id = "my-plugin"
name = "我的插件"
version = "1.0.0"
plugin_type = "source"  # 插件类型：source, cloud_provider, notification 等
description = "这是一个示例插件"
author = "Your Name"
homepage_url = "https://github.com/yourname/my-plugin"
adapter_api_version = "1.0"
entry = "my_plugin.adapter:create_plugin"

[config_schema]
api_key = { type = "string", required = true, label = "API Key", secret = true }
timeout = { type = "integer", default = 30, label = "超时时间（秒）" }
```

### 配置字段类型

支持的配置字段类型：

- `string`: 字符串
- `integer`: 整数
- `boolean`: 布尔值
- `select`: 下拉选择（需要 `options` 字段）
- `password`: 密码输入（显示为 ***）

### 开发示例

参考 `examples/source-plugin-template/` 目录中的示例代码。

## 最佳实践

1. **错误处理**: 所有函数都应该有完善的错误处理
2. **超时设置**: 网络请求应该设置合理的超时时间
3. **日志记录**: 使用标准日志记录关键操作
4. **配置验证**: 在启动时验证配置参数
5. **测试覆盖**: 编写完整的测试用例

## 故障排查

### 插件加载失败

如果插件加载失败，请检查：

1. 插件清单文件 `sundarr_plugin.toml` 是否正确
2. 插件入口函数是否正确
3. 依赖项是否已安装
4. 配置参数是否正确

### 插件运行错误

如果插件运行出错，请查看：

1. 日志文件中的错误信息
2. Web Console 中的插件状态
3. 插件配置是否正确

### 插件冲突

如果插件 ID 冲突，请修改插件清单中的 `id` 字段。

## 常见问题

### Q: 如何更新插件？

A: 在 Web Console 中进入插件管理页面，找到要更新的插件仓库，点击 **更新**。

### Q: 如何回滚插件？

A: 在 Web Console 中进入插件管理页面，找到要回滚的插件仓库，点击 **回滚**。

### Q: 如何禁用插件？

A: 在 Web Console 中进入插件管理页面，找到要禁用的插件，点击 **禁用**。

### Q: 如何删除插件？

A: 在 Web Console 中进入插件管理页面，找到要删除的插件仓库，点击 **删除**。

## 参考文档

- [插件清单规范](docs/20-plugin-manifest-spec.md)
- [插件 API 文档](docs/21-plugin-api-spec.md)
- [插件开发指南](docs/22-plugin-development-guide.md)

## 示例插件

- [搜索源插件模板](examples/source-plugin-template/)
- [夸克网盘插件](examples/quark-provider/)
- [阿里云盘插件](examples/aliyun-provider/)
- [钉钉通知插件](examples/dingtalk-notification/)
- [飞书通知插件](examples/feishu-notification/)
