# Sundarr 搜索源开发技能

用于后续为 Sundarr 新增代码型搜索源。搜索源不再由用户在 Web Console 中配置，统一通过代码注册表加载。

## 目标结构

每个真实网站通常一个 Python 文件：

```text
sundarr/app/sources/base.py        # BaseSource 和 SourceDescriptor
sundarr/app/sources/registry.py    # 注册已安装搜索源
sundarr/app/sources/seedhub.py     # 示例：SeedHubSource
```

新增搜索源时：

1. 在 `sundarr/app/sources/<source_id>.py` 中新增类，继承 `BaseSource`。
2. 实现 `id`、`name`、`source_type = "code"`、`enabled`、`description`、`legal_note`。
3. 实现 `async def search(self, query: SearchQuery) -> list[RawSearchItem]`。
4. 在 `sundarr/app/sources/registry.py` 的 `get_registered_sources()` 中注册实例。
5. 添加 fixture / 单元测试，不让默认 pytest 依赖真实网站实时可用性。

## Adapter 职责

Adapter 只负责站点访问和转换为 `RawSearchItem`：

```text
负责：搜索页面、详情页、站点字段解析、站点级超时、合法性说明。
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
