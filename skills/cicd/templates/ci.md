<!-- sdlc:unfilled — 写入真实内容后删除本行；未填写的模板不算交付 -->
# CI 门禁接线记录 · <功能/项目名>

> 任务：`sre/deliver/ci`（`06-deliver/ci.md`）｜作者：`sre`｜日期：<YYYY-MM-DD>
> 权威配置源：`sdlc.config.yaml` · `<PLUGIN_ROOT>/scripts/check-sdlc.sh`｜变更流水线文件：`<路径列表>`
> **边界声明：CI 仅运行确定性 G-script 门禁（不替代 G-fresh 独立审查，也不代表已执行生产部署）。**

## 1. 门禁到流水线步骤 1:1 映射与不可绕过分支保护（Cheapest First，严禁「这次特殊先合」）

> **硬防线**：分支保护规则必须将聚合状态检查设为 **Required 且开启管理员同样受限（Include administrators / Do not allow bypassing）**，从机制上封死「这次特殊先合」手工强行合并与 `continue-on-error` 软化退出码；本地 Agent 仍严格保持只跑受影响目标的定向测试，不跑无关全量套件。

| 顺序 | 权威来源 (`sdlc.config.yaml` / 插件) | CI Job / Step 名称 | 触发阶段与退出码语义 | 产出证据构件（`gates[]` 可采信日志） |
|---|---|---|---|---|
| 1 | `gates.lint` | `lint` | PR 必过；非 0 立即阻断合并（无 warning 洗白） | `artifacts/gate-lint.log` |
| 2 | `gates.test`（受影响 `unit` + **`contract-test`**） | `test-targeted` · `contract-test` | PR 必过（按变更影响定向路由）；非 0 立即阻断合并 | `artifacts/gate-test.log` · `gate-contract.log` |
| 3 | `gates.sast`（静态安全扫描 `SAST`） | `sast` | PR 必过（扫描变更及依赖面）；高危/中危规则命中非 0 阻断 | `artifacts/gate-sast.log` |
| 4 | `gates.build` | `build` | PR 必过；非 0 立即阻断合并 | `artifacts/gate-build.log` |
| 5 | `gates.migration` / `gates.e2e` | `migration` · `e2e` | PR 必过；非 0 立即阻断合并 | `artifacts/gate-migration.log` · `gate-e2e.log` |
| 6 | `check-sdlc.sh --require` | `sdlc-gate` | PR 必过；违规数 = 退出码 | `artifacts/gate-check-sdlc.log` |
| 7 | `gates.dast`（**Staging `DAST` 动态扫描钩子**） | `staging-dast` | 存在 Web/API 暴露面时在部署预发（Staging）后自动触发；非 0 阻断晋级生产（纯离线库填 `N/A + 无 Web/API 面理由`） | `artifacts/gate-staging-dast.log` |

## 2. 变更路径定向路由与 Monorepo 依赖图（Changed-Path Routing）

| 变更面 | 路由规则（`gate-router` 计算传递闭包，兼顾本地定向速度与 CI 严密性） | 分支保护不可绕过与防死锁策略 |
|---|---|---|
| 单包 / 模块代码变更 | 运行该模块及传递下游消费者的定向 `lint + unit + contract-test + SAST`，不盲跑无关子项目全量套件 | 统一由不可绕过的 `ci-gate-summary` 汇总（管理员禁止强合）；合法跳过的子 Job 显式汇报 skipped-pass，任何子门禁失败则汇总必红 |
| 公共底座变更（`migrations/` · `auth/` · 共享契约 · 锁文件 · CI 配置） | 自动升级受影响集成、契约兼容性门禁与 Staging `DAST` 扫描范围 | 同上 |
| `.sdlc/<feature>/` 发现规则 | 特性分支仅校验活动 feature 已完成阶段（`--hat <done>`）；`main` 按 `delivery_goal` 校验承诺阶段；跳过已归档与纯方案 feature | — |

## 3. 工具链固定、供应链证明（SBOM / 签名）与客户端/包发布门控

| 项 | 配置与安全边界 |
|---|---|
| Runner 与 Action 固定 | Runner 镜像与第三方 Action 固定不可变 SHA/Digest：`<例：actions/checkout@11bd7190...>`；目标架构：`<linux/amd64 / macos-arm64>` |
| 凭据与签名密钥 | 仅通过 CI Secret Vault / OIDC 引用名注入（`<SECRET_NAMES>`），`sdlc.config.yaml` 与脚本 `0` 明文密钥 |
| SBOM 与来源签名 | 构建产物生成 `<CycloneDX / SPDX>` SBOM，并通过 `<Cosign OIDC / SLSA / Apple Notarization>` 签名绑定源码树摘要 |
| 移动端 / 桌面端 / 包仓库发布（若适用） | PR 仅跑编译、ABI/SemVer 检查与打包预演；不可逆商店/包推送隔离在显式 Release Tag + `qc` 准出审批之后，且已核对服务端 N-2 兼容 |

## 4. 验证记录与证据复用条件

- **配置语法/本地静态校验**：`<actionlint / workflow lint 命令 + exit: 0>`
- **真实流水线运行记录**：`<Run URL + 日志摘要>`（若当前沙箱/权限未触发远端运行，必须明确写「**未在远端 CI 实跑**」及待验证边界，严禁伪造 URL）
- **`gates[]` 绿灯复用红线**：仅当 `commit/tree SHA`、工作区干净态、锁文件与依赖版本、`sdlc.config.yaml`、门禁脚本版本、目标 OS/架构及外部夹具契约**全部一致**时方可复用；任一漂移必须重跑。
