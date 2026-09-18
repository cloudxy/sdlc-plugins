# auto_agents SRE pitfalls（仅实战已验证）

收录门槛（两条同时满足才进本文件）：

1. **实战**：本仓库 git 历史里真实炸过 / 演练踩过，不是通用建议。
2. **已验证**：有提交 SHA，或有测试/脚本注释记录「实测」。

未在本仓发生过的条目（HTTP/2 git push、未观测的僵尸端口、Power Market 未落地路径）**不写**。推测与「应该会」不进。

---

## P-SRE-01 · npm 11 lockfile 在 CI npm 10 下 `npm ci` 全炸

**症状**：本机 Node 25 / npm 11 生成 lockfile 后，CI（Node 20，npm@10）与 Docker `npm ci` 报传递依赖缺失（当时是 `yaml@2.9.0`）。

**原因**：npm 11 与 npm 10 解析传递依赖图不同。CI `actions/setup-node` 钉 Node 20 → npm@10。本机新 npm 写出的 lockfile CI 读不懂。

**证据**：`4a54127`（2026-09-02）`fix(ci): lockfile 用 npm@10 重生成——npm 11 (Node 25) 与 npm 10 (Node 20 CI) 传递依赖解析不同，yaml@2.9.0 在 npm 11 lockfile 中缺失导致 CI/Docker npm ci 全炸`。

**规则**：前端 lockfile 只用 npm@10 生成（与 CI Node 20 对齐）。根 `package.json` 注释 D2 已写。本机 Node 25 改依赖后必须用 npm@10 重写 lockfile，不能「我这边 install 过了」。

---

## P-SRE-02 · macOS ARM64 `uv.lock` 在 Linux x86_64 `uv sync --frozen` 解析失败

**症状**：本机构建过的 Docker/uv 流程在 CI `ubuntu-latest` 上 `uv sync --frozen` 炸；另一次只 COPY `pyproject.toml` 时 `readme` 字段指向不在 context 的 `README.md` 同样炸。

**原因**：uv lock 在 ARM64 与 x86_64 上解析结果不同；workspace 成员元数据构建还要求包目录和 README 在 context 里。本机绿 ≠ CI 绿。

**证据**：

- `c881c32`（2026-09-02）Docker 构建阶段只 COPY `pyproject.toml`，readme 引用的 README.md 不在 context → `uv sync --frozen` 炸。
- `b50be93`（2026-09-02）`fix(docker): uv export + pip install 替代 workspace 构建——绕过 macOS ARM64 lockfile 在 Linux x86_64 的 uv sync --frozen 解析差异`。
- `c3a7d4d` 改为完整源码 COPY 再 `uv sync`。HEAD `Dockerfile` 是 `uv sync --package auto-agents-backend --no-dev`，**没有** `--frozen`，可复现性弱于曾用的 export 绕过。

**规则**：跨平台镜像必须在 CI 构建，不能只信本机 ARM。若恢复 `--frozen`，先在 linux/amd64 上验证，不要假设 lockfile 跨 arch 可互换。

---

## P-SRE-03 · Dockerfile 前端 Stage 仍 COPY 已删除的 per-app lockfile

**症状**：CI `frontend-build` 走根 workspaces + 根 `package-lock.json`；`Dockerfile` Stage1 仍 `COPY frontend/admin/package-lock.json`（official 同）。工作区与 git **都没有**这两个文件。

**原因**：workspaces 落地后 per-app lockfile 被删，T11 改过 Dockerfile 但没改前端 COPY。CI 前端 job 与 Docker 前端 Stage 不是同一条管线，会再次静默分叉。

**证据**：

- `902de6d`（2026-09-03）根 `package-lock.json` + workspaces。
- `9d0627b` / `34914ac`（2026-09-03）`delete mode` `frontend/{admin,official}/package-lock.json`。
- `df5db02`（2026-09-05）T11 仍改 Dockerfile，L10/L16 COPY 未动。
- 本轮：`git ls-files '*package-lock.json'` 仅根文件；`ls frontend/admin/package-lock.json` No such file。

**规则**：Docker 前端构建必须与 CI `npm ci`（根 lockfile + shared 先 build）同源。admin `package.json` 未声明 `@auto-agents/frontend-shared`，只 COPY admin 目录即使有 lockfile 也解析不了 shared。改 lockfile 布局时 Dockerfile 是同一张检查单。

---

## P-SRE-04 · 浅健康恒 200，依赖挂了编排器仍当活

**症状**：进程僵死或不退出时 compose `restart` 不触发；`/api/v1/health` 恒 200，HEALTHCHECK 全绿，服务其实连不上 MySQL/Redis。代码注释指向 2026-08 冻结事故。

**原因**：编排器按 HTTP 状态码判定。body 里写 `unhealthy` 但状态码 200 = 浅探测。僵死不退出 ≠ 崩溃，`restart: unless-stopped` 覆盖不了。

**证据**：

- `df5db02`（2026-09-05）`ops: compose 加固+深健康探测(/health/deep 503 语义)+看门狗+部署回滚文档（T11）`；新增 `health.py` `/deep`、compose HEALTHCHECK、`scripts/watchdog.sh`、`backend/tests/test_health_api.py`（依赖失败必须 503）。
- `docker-compose.yml` L87–90 注释：旧浅探测恒 200。
- 复盘路径 `docs/ops/incident-2026-08-backend-freeze.md` **不在 git**（见 P-SRE-08）。

**规则**：给 Docker/K8s/watchdog 用的探针必须依赖失败 → 非 2xx。`/db` `/redis` `/storage` 失败仍 200 只给人看，编排禁止打它们。liveness 不要在依赖挂时无限杀 API（watchdog 默认 `WATCHDOG_RESTART=0` 就是这条）。

---

## P-SRE-05 · watchdog：bash 3.2 UTF-8 崩 + `RESTART=0` 仍 kill（B4 实测）

**症状**：看门狗「安全缺省只告警」在真实执行路径上：(1) 中文日志行 `set -u` 直接崩；(2) `WATCHDOG_RESTART=0` 仍然 `kill -9`，宿主机直跑杀了没人拉起，把僵死升级成宕机。无冷却时 7 秒 3 轮告警轰炸。

**原因**：

- bash 3.2（macOS 默认）在 UTF-8 下把紧跟变量的全角标点首字节 `0xef` 并入变量名 → unbound。dry-run 不走 `log ALERT` 那一行，所以 dry-run 绿、真跑红。
- kill 没闸在 `RESTART=1` 上。

**证据**：`9c5bd00`（看门狗 kill 闭环**实测**修复）。`scripts/watchdog.sh` L50–51、L161–163、L183–191 注释写明演练踩中。

**规则**：macOS 运维脚本按 bash 3.2 写：无关联数组、无 `${var,,}`、中文语境一律 `${VAR}`。安全缺省必须在真路径上 dry-run **和** 一次真实失败轮都测过。dry-run 绿不算。

---

## P-SRE-06 · `run.py` 宿主管道关闭后不排水 → 子进程僵死

**症状**：`python run.py all | head` 或终端已退出后，backend 看起来还在，实际 uvicorn access log 写满管道，事件循环堵住。

**原因**：`_stream` 线程停消费 stdout 后，子进程同步写日志阻塞。`start_new_session=True` 只解决信号组，不解决管道背压。

**证据**：`384b848` `fix(run): logger request_id 默认 extra + run.py 排水防僵死（T3 伴生）`。现行 `run.py` L36–40：`BrokenPipeError` 时继续空转排水，不让线程死。

**规则**：编排器转发子进程 stdout 时，写失败不能停读。僵尸「端口还在、健康 000」先 `lsof` 再查是不是管道堵死，不要只 SIGTERM（可能被忽略）。

---

## P-SRE-07 · Dynaconf `.env` 不做 `${VAR}` 展开 → 启动即拒

**症状**：prod 模板曾写 `"${PROD_XXX}"` 形式占位，进程起来后 JWT/Webhook 守卫当成字面量，启动失败。

**原因**：Dynaconf `load_dotenv` 不跑 shell 展开。看起来像「用了环境变量」，实际密钥是美元括号字符串。

**证据**：`config/prod/.env.example` 头注释「P1-1 修复配套」+「旧模板即此问题导致启动即拒」。`README.md` 敏感信息节同样警示。

**规则**：`.env` 里必须是部署脚本写入的真实值。密钥生成与注入发生在 compose/K8s/CI secret，不发生在 dotenv 插值。prod 模板禁止 `${}` 占位。

---

## P-SRE-08 · `docs/` gitignore 把 runbook 和复盘吞掉

**症状**：compose、Dockerfile、watchdog 都写「见 `docs/ops/deploy.md` / `incident-2026-08-backend-freeze.md`」。工作区无 `docs/`。`git check-ignore -v docs/ops/deploy.md` → `.gitignore:76:docs/`。T11 提交说明含「部署回滚文档」，diff 只有 5 个非 docs 文件。

**原因**：运维真源放进默认 gitignore 的树。本地写了等于没入库。值班、CI、新克隆都 404。

**证据**：`.gitignore` L76；`docker-compose.yml` L9；`scripts/watchdog.sh` L68 `RUNBOOK=...`；`df5db02` stat 无 docs。本轮 `ls docs` → No such file。

**规则**：发布/回滚/事故复盘必须在**可提交路径**（如 `deploy/README.md`）。hint/runbook 字段禁止指向 gitignore 路径。文件头写「gitignore 已登记」不等于真的 ignore（对照 litellm：头自称已 ignore，`git ls-files` 仍跟踪 —— 那是另一起密钥事故，处理是轮换+剔除，不在本条展开）。

---

## 不收录（未达门槛）

| 候选 | 为什么不进 |
|------|------------|
| git HTTP/2 framing layer | 技能通用 gotcha，本仓无对应提交 |
| Power Market CACHE_DIR / SOURCES merge | 设计已写，代码零落地，没有实战失败 |
| 平台 Redis 无 volume 丢队列 | 代码事实，尚未以事故形式炸过 |
| MySQL 扁平键 vs 嵌套键 | 配置漂移已在诊断里写；无「按 prod 模板发布即连不上」的提交 |
