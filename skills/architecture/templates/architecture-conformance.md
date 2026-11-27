<!-- sdlc:unfilled — 写入真实内容后删除本行；未填写的模板不算交付 -->
# 架构符合性核验 · <功能名>

> 核验输入基准：contract `<path@rev>` · ADR `<ids@rev>` · security-review `<path@rev 或 N/A>`
> 被核验实现版本：代码 commit `<sha>`｜运行构建/环境 `<build_id + env 或 unknown>`｜日期：<YYYY-MM-DD>
> 综合结论：<all required obligations met / **blocked: deviation or unverified obligations remain**>

严格区分三层证据：① 静态源码属性；② 指定代码版本上的实跑检查；③ 已标识运行构建的真实行为。旧提交报告、无构建关联截图或仅配置声明均不构成当前运行证据（见 `references/conformance-task.md`）。

## 1. 架构义务逐项核验矩阵

| 义务 ID / 来源 | 期望约束（QAS / 边界 / 幂等 / `[SEC-n]`） | 代码版本与位置 | 执行命令、环境与原始证据路径 | 实测结果与证据层级 | 状态 (`met` / `deviation` / `unverified`) | 责任角色与处置动作 |
|---|---|---|---|---|---|---|
| <QAS-1 / SEC-1> | <例：跨租户访问 100% 拒绝> | `<sha + path>` | `<证据文件与退出码，缺失写 missing>` | <实跑负向用例通过（层级②）> | <met / deviation / unverified> | <backend 返工 / qa 补跑 / owner 例外审批> |

## 2. 结构原则与高阶红线核查

| 检查项 | 核查结果（`met` / `deviation` / `N/A`） | 证据位置或偏差说明 |
|---|---|---|
| 模块深度与单向依赖（DIP / LoD / 无浅层透传壳） | | <分层检查脚本输出、跨模块私有表直连核查> |
| 唯一事实源（DIE/SSOT：可见性谓词、限额、错误码无多处漂移） | | <列表/计数/导出谓词同源核查> |
| 进程无状态（无进程内可变全局变量/本地锁充当跨实例状态） | | <多 worker 共享状态存储核查> |
| 有界化与三态副作用（超时/限流/重试抖动/`In-Doubt` 对账恢复） | | <外部调用在事务外 + 超时降级测试记录> |

## 3. 基线晋升与未决阻断项

- **可回写产品 `architecture.md` 的已证实增量**：<仅列 `implemented` 或 `deployed` 证据齐备的事实行；无则写无>。
- **阻断项与移交**：任何必填义务处于 `deviation` 或 `unverified` 时，不得声明架构符合性通过或自行豁免；交经理维护未决义务并路由对应负责人返工或走正式风险审批。
