# vendor/

上游原件的存放处。**本仓库不分发任何上游内容**：这里只提交 `install.sh`、本说明和每个来源的锁文件 `<来源>.lock.json`。

首次使用（或锁文件更新后）运行：

```bash
bash vendor/install.sh            # 安装全部可安装来源；许可证受限的来源默认跳过
bash vendor/install.sh --check    # 检查是否已安装且与锁文件一致
```

`install.sh` 按锁文件从上游源头下载**同一个 commit 的同一批文件**，算出的树摘要与锁文件一致才落盘，否则什么都不写。依赖 bash、python3，以及 git（或 curl + tar）。

| 来源 | 上游 | 许可证 | 本插件怎么用 |
|---|---|---|---|
| `anthropic-skills` | anthropics/skills：frontend-design、skill-creator、claude-api/agent-design | Apache-2.0 | frontend-design 被 design-contract 引用；其余为维护者参考 |
| `agentskills` | agentskills/agentskills：规范与写作指南 | Apache-2.0 | 维护者参考 |
| `svg-diagram` | bybit-exchange/svg-diagram 运行时子集 | MIT | 已收纳，待绘图检查接入 |
| `anthropic-docx` | anthropics/skills 的 docx | All rights reserved | 维护者参考；默认不下载，`--accept-restricted` 表示你接受其上游条款 |
| `claude-code` | anthropics/claude-code 的 4 份插件文档 | All rights reserved | 同上 |

规则：

- 这里的内容**不会自动变成能力**。宿主不扫描 `vendor/`；插件只通过引用使用它（技能链接、派单输入、脚本调用）。
- 不要手改、不要复制到别处。健康检查会核对内容与锁文件是否一致、引用是否合规、有没有副本。
- 锁文件由维护者机器上的 plugin-updater 每日更新（只在选定文件的内容变化时改写），随后由维护者提交。
