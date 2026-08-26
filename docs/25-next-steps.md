# 下一步执行清单

更新时间：2026-08-26。完整路线见 `docs/24-implementation-roadmap.md`。

## 当前目标

完成 Phase 10.1 Python Plugin Activation Runtime。当前不新增更多插件类型，不开发 Alist 或网盘直链下载。

## 执行顺序

1. 已实现 `PluginContext` 的能力提供、能力依赖和清理回调注册。
2. 已实现 `PluginActivation` 的状态和并发幂等、逆序释放。
3. 已为生命周期异常、重复释放和资源清理增加 8 项单元测试。
4. 下一步为 manifest 增加 `requires/provides`，接入 Source 注册动作与候选健康检查。
5. 随后实现注册中心原子切换和失败回滚。
6. 最后接入应用启动时自动激活 enabled 仓库的锁定 commit。

## Phase 10.0 完成定义

状态：已完成。

```text
默认 pytest 无收集副作用且全部通过。
前端构建通过。
数据库迁移图只有预期 head，干净数据库可 upgrade head。
start / status / stop 不误杀外部进程。
PID 文件指向真实监听或执行服务进程。
停止后端口、PID 文件和子进程全部释放。
```

## 当前插件交付边界

只实现 SOURCE 插件需要的最小生命周期：

```text
已完成：PluginContext、PluginActivation、ActivationStatus、LIFO cleanup callbacks。
下一单元：manifest requires/provides、Source 注册动作、候选加载和健康检查。
后续单元：原子切换、失败回滚、启动加载 locked current_commit。
失败保留旧 Activation
```

该交付单元不包含插件市场、Cloud Provider、通知、Crawler、Cordis 后端改写或在线编辑 Python 代码。

## 当前已知阻塞

```text
工作区存在用户未提交的插件迁移链修复。
当前运行时没有配置外部插件仓库，因此搜索源为 0。
当前 Windows 主机没有 Docker，Compose 运行验收需要其他 Docker 环境。
真实 SMB 完整搬运需要专用测试目录和用户已有测试环境。
```
