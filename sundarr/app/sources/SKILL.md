# Sundarr 搜索源开发技能

用于为 Sundarr 外部 Python 插件仓库新增代码型搜索源。搜索源不在 Core 内逐站点新增文件，也不由 Web Console 编辑代码。

## 目标结构

每个真实网站通常位于独立 `sundarr-sources` 仓库的一个插件目录：

```text
sundarr/app/sources/base.py        # Core 中的 SourceModel 协议
sundarr/app/sources/registry.py    # Core 运行时注册入口
sundarr-sources/sources/<id>/      # 外部仓库中的真实站点 Adapter
```

新增搜索源时：

1. 在外部搜索源仓库中新增 Adapter 模块和 `sundarr_plugin.toml`。
2. 实现 `id`、`name`、`description` 和 `async def search(self, query: SearchQuery) -> list[RawSearchItem]`。
3. 入口返回 `SourceModel` 或 `list[SourceModel]`，由 PluginLoader 和 PluginRegistry 注册。
4. 不直接修改 Core 注册表；仓库、配置、启停和锁定 commit 由插件管理模块负责。
5. 添加 fixture / 单元测试，不让默认 pytest 依赖真实网站实时可用性。

## Adapter 职责

Adapter 只负责站点访问和转换为 `RawSearchItem`：

```text
负责：搜索页面、详情页、站点字段解析、站点级超时。
不负责：最终去重、排序、入库、创建 Transfer、保存到网盘。
```

`RawSearchItem.raw_content` 必须包含可被统一链接提取器识别的原始文本。当前统一提取器支持：

```text
magnet
quark
aliyun
baidu
xunlei
提取码 / 密码 / 访问码 / code
```

## 合规边界

搜索源不得：

```text
绕过登录、验证码、会员、风控或付费限制。
分发、托管或缓存资源文件本体。
把 cookie、token、密码或个人凭据提交到仓库。
在数据库或配置中保存可执行 Python 代码。
```

如果目标站点要求登录、验证码或明显反爬绕过，应停止实现并更新文档说明风险。

## 测试要求

新增搜索源时至少覆盖：

```text
解析列表页详情链接。
解析详情页标题和 raw_content。
链接提取器能识别目标 provider。
SearchService 能隔离该源失败。
重复真实链接只返回一次。
```

默认测试必须使用静态 HTML fixture 或 mock，不访问真实网站。真实网站连通性只能作为显式手动集成验收。
