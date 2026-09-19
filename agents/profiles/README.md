# Per-role source files (edit these, not `agents/<role>.md`)

Hermes / OpenClaw / this repo's `.claude/` all split **who / how it talks / what it learned / what the project needs**. Same split here.

| File | What | Who edits | Hermes analogue |
|---|---|---|---|
| `IDENTITY.md` | 分身：帽子、职责、拒绝清单、红线 | 人 | 角色契约（Hermes 把这块塞进 SOUL；本仓库 `.claude/IDENTITY.md` 单独抽） |
| `SOUL.md` | 性格：语气、软偏好 | 人 | `SOUL.md` |
| `../../<role>.md` | 宿主分身：frontmatter + 组装后的 system prompt | **只由** `render-role-agents.py` 生成 | Hermes `prompt_builder` 的产出，不是手写源 |
| `skills/<proc>/SKILL.md` | 做法（how），按工件命名 | 人 | 与 IDENTITY 分开；solo 入口是 `$<proc>`（`$pm` 等别名已删） |
| `<feature>/memory/<role>.md` | 记忆：facts，≤2200 字 | 该角色在交卷时写 | `MEMORY.md` |
| 仓库 `AGENTS.md` | 上下文：项目约定 | 人 | `AGENTS.md`（`agents_md: true` 注入，不进 SOUL） |

ZCode/Grok **不**在 `agents/*.md` 里展开 `@import` / `@include`（AGENTS.md 同样不展开）。所以 SOUL/IDENTITY 不能靠运行时引入；工厂是编译期引入。改身份或性格：只编辑本目录，再跑 `python3 scripts/render-role-agents.py`。不要手改 `agents/<role>.md`。已有 `IDENTITY.md` / `SOUL.md` **不会被覆盖**；生成器不再保存或恢复另一套身份种子。

审查角色（reviewer / qc）没有运行时 memory 文件。

Task routes, permitted companions, source-write capabilities and partial-stage checks are generated from workflow/registry.json. SOUL expresses tone only; professional methods and technical requirements belong to the task skill. Update sources and re-render all agents; do not maintain a second task/permission list in profiles.
