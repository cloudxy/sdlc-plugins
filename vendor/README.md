# 上游原件与锁文件

本目录只提交本说明、[install.sh](install.sh) 与 `<来源>.lock.json`。上游原件由使用者从源头下载到 `vendor/<来源>/`，不纳入本仓库版本控制。

## 安装与检查

在仓库根目录执行，依赖 Bash、Python 3，以及 Git（首选）或 curl + tar：

```bash
bash vendor/install.sh                 # 安装可用来源，默认跳过许可证受限的来源
bash vendor/install.sh svg-diagram     # 只安装一个来源
bash vendor/install.sh --check         # 只读核对已安装内容与锁文件
```

安装器按锁文件的 `commit` 和 `included_paths` 下载，校验 `tree_digest` 后才替换对应来源。下载失败或摘要不一致时，该来源保持原状；多个来源逐个处理。已有内容与锁文件不同时，默认保留并报错；确认可以覆盖后才使用 `--force <来源>`。

`--accept-restricted` 表示接受对应上游条款并允许下载受限来源。`--check` 对未安装的可选受限来源提示跳过；退出码 `0` 表示检查通过，`1` 表示有来源缺失或不一致，`2` 表示用法或环境错误。

## 当前来源

许可证与文件用途按仓库锁文件列示，使用时同时查阅对应上游条款。

| 锁文件 | 上游 | 锁定许可证 | 当前用途 |
|---|---|---|---|
| [anthropic-skills](anthropic-skills.lock.json) | `anthropics/skills` | Apache-2.0 | frontend-design 是设计与 UI 实现的必读引用；skill-creator、agent-design 等为维护者参考 |
| [agentskills](agentskills.lock.json) | `agentskills/agentskills` | Apache-2.0 | 技能规范与写作指南，供维护者参考 |
| [svg-diagram](svg-diagram.lock.json) | `bybit-exchange/svg-diagram` | MIT | SVG 运行时资料与检查工具，已由注册表及 `scripts/diagram/lint.py` 接入 |
| [anthropic-docx](anthropic-docx.lock.json) | `anthropics/skills` 的 docx | All rights reserved | 维护者参考，默认不下载 |
| [claude-code](claude-code.lock.json) | `anthropics/claude-code` 的插件文档 | All rights reserved | 维护者参考，默认不下载 |

## 维护边界

- 宿主不扫描 `vendor/`。只有技能引用、注册表 `reads` 或脚本调用才会使用这里的内容；文件的 `purpose` 区分 runtime 与 maintainer。
- 不手改下载的原件，也不复制到技能目录。健康检查核对摘要、运行时引用、许可证分类与副本。
- 锁文件记录上游提交、路径、文件摘要和用途。维护者的 plugin-updater 可更新锁文件；使用者只需安装器，无须配置 updater。
- 上游更新后，需核对实际改动并运行适用检查；改写进本地方法的内容按[维护流程](../maintainers/README.md)记录来源与评测。
- 下载的上游 README 保持原件；本次项目文档维护只编辑版本控制内的本地说明。
