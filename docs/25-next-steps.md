# 下一步执行清单

更新时间：2026-08-27。完整路线见 `docs/24-implementation-roadmap.md`。

## 当前目标

完成 Phase 10.1 媒体发现中心的设计和最小 MVP 闭环。Python 插件生命周期在 204 项测试通过的稳定节点暂停，后续恢复。

## 当前决策顺序

```text
1. 已确认媒体身份使用内部 UUID + 多个外部平台 ID
2. 已确认 TMDb 为主目录数据提供方，豆瓣想看为可选独立接入
3. 当前确认发现数据的持久化和缓存边界
4. 页面信息架构、筛选项和详情入口
5. MediaSubject、ResourceOffer、Artifact 与任务的关系
6. 最小 API 和 Web Console 验收范围
```

## 已确认边界

```text
媒体发现中心属于当前 MVP。
TMDb 负责 MVP 的目录、搜索、筛选、热门、分类、详情和海报。
豆瓣想看是可选独立接入，失败不得阻断媒体发现中心。
提供筛选、热门、分类、详情、关注列表和发现型海报墙。
不做本地媒体库海报墙。
不做播放器和观影进度。
不做完整本地媒体管理。
```

## 暂停点

```text
PluginContext、PluginActivation、ActivationStatus 已实现。
LIFO cleanup、失败续跑和并发幂等释放已测试。
manifest requires/provides、Source 注册、健康检查、原子切换和启动加载待恢复。
```

## 环境限制

```text
当前运行时没有配置外部插件仓库，因此搜索源为 0。
当前 Windows 主机没有 Docker，Compose 运行验收需要其他 Docker 环境。
真实 SMB 完整搬运需要专用测试目录和用户已有测试环境。
```
