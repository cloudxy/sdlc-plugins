# 角色源文件

这里维护 19 个角色的身份和表达风格。角色名称、任务与写入权限以 [workflow/registry.json](../../workflow/registry.json) 为准；各宿主加载的是编译后的角色文件。

## 文件职责

| 位置 | 内容 | 维护方式 |
|---|---|---|
| `<role>/IDENTITY.md` | 角色使命、职责、拒绝清单与红线 | 修改对应角色的源文件 |
| `<role>/SOUL.md` | 语气和软偏好 | 只描述风格；专业步骤放进技能 |
| [../_lib/](../_lib/) | 共享的 Loop、Tools、Skills、Memory、Contract | 修改共享行为源文件 |
| [../../skills/](../../skills/) | 专业做法与交付标准 | 根据任务选用技能；独立入口用技能名 |
| [../../adapters/](../../adapters/) | 宿主工具档、可选 MCP 白名单与宿主说明 | 修改宿主源配置后重新生成 |
| 业务项目的 `<feature>/memory/<role>.md` | 该角色核实过的运行时事实（≤2200 字） | 产出角色交卷时写；reviewer / qc 没有运行时 memory 文件 |
| 业务项目的 `AGENTS.md` | 项目约定 | 由项目维护，不并入 SOUL |

## 生成与核对

在仓库根目录执行：

```bash
python3 scripts/render-role-agents.py
python3 scripts/render-role-agents.py --check
```

生成器读取本目录、共享行为栈和注册表，输出：

- `agents/<role>.md`：ZCode、Claude Code、Grok 的角色。
- `adapters/codex/agents/sdlc-workflow-<role>.toml`：Codex 角色。
- `adapters/kimi/agents/sdlc-workflow-<role>.md`：Kimi 角色。

这些输出不手改。已有的 `IDENTITY.md` 和 `SOUL.md` 不会被生成器覆盖，也没有另一套身份种子需要同步。任务路由、可搭配技能与写入能力来自注册表，不在 profiles 中另存一份权限表。

共享内容在编译时组装，不依赖宿主运行时展开 `@import` / `@include`。修改注册表或宿主清单源时，还需运行 `python3 scripts/workflow.py render`；项目链接与宿主限制见[宿主路由](../../skills/sdlc/references/hosts.md)。

方法源变更须登记台账并完成适用验证，具体要求见[维护者指南](../../maintainers/README.md)。
