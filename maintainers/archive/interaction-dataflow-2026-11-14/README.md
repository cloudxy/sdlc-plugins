# 交互、数据流与定向交付经验归纳

2026-11-14。来源为本次 VSC 维护会话及其现存私有设计/执行记录；按用户要求固化到 SDLC 对应角色的既有 Skill。这里保存来源与适用范围，不进入角色默认运行时上下文，不复制作品、媒体、凭据、联系方式或正式库测试记录。

## 来源、教训与归属

| 来源与已知范围 | 提炼的方法 | 对应角色 / Skill |
|---|---|---|
| 会话早期报告5项失败已在旧版复现；本次未重现这些旧失败 | 旧失败须固定基线归因，不等于豁免；用户要求先修时执行该决定 | QA / coverage-matrix；SRE / deliver；QC / release-gate |
| `service-operations/feedback.md`：个人/管理查询、分类落库、状态语义及26条获准正式测试反馈；本次未重放这些写入 | 服务端身份界定个人数据；先筛选再分页，计数/详情/回执同范围；历史未知保持未知；正式种子有授权、标记、编号及保留决定 | backend / impl-evidence；DBA / schema；QA / coverage-matrix |
| `design/sidebar-sky-20261113.md`：帮助/设置等宽、设置文字；focusout 先关闭导致点击丢失；旧实现只验展开/收起 | 已接受比例和标签保留；菜单必须走到子项实际操作；空 relatedTarget 不证明离开；指针/键盘/焦点序列回归 | designer / design-contract；frontend / impl-evidence；debug |
| `design/codex-authorization-20261113.md`：先仅登记授权，后接通实际生成；当前通道绿灯和校验不一致 | 凭证、登录、选择、服务端支持、真实成功逐层区分；通道身份贯穿登记/校验/分派/结果；保留另一模式配置，不混用计费凭据 | architect / architecture；backend、frontend / impl-evidence |
| 同一记录：CLI 升级短暂缺失、权限/参数错误、工具自身401、旧文件不能算新产物 | 分层归因、脱敏诊断、按安装版本核参数、输出归属与路径边界；既有图可验证UI时不重复付费生成，不擅自重试/回退 | backend / impl-evidence 的 provider-authorization |
| 同一记录：贯穿绿线与进度条可并存，机制为结构宿主 focus-visible；查看拼图覆盖右侧生成结果 | 假设用可区分探测证伪；只修宿主焦点轮廓；参考/拼图/生成/历史独立状态与下载对象 | debug；frontend / impl-evidence |
| `design/ai-character-library-design-20261114.md`：生成历史归位、沿原IndexedDB、不截断30条、更多菜单实测溢出 | 页面归位不迁移权威；成员版本精确；真实窗口验证菜单与浮条，不只验短卡片 | architect；designer；frontend；QA |
| `design/official-assets-design-20261114.md` 与本次 `official-assets-redesign-20261114/verification.json`：原站实际观察、源码辅助核对、桌面及375px本机页面 | 各来源自动/手动加载契约分别建模；首批/追加/筛选重置不同，批量不是API上限；自然比例与原能力保留；当前分类及浮条可达 | designer；frontend；QA |
| 同一次实现：参考库按源默认60，姿势明确改单张96，追加60；仅适用于该契约 | 数值作为该案例参数保存，通用Skill要求按来源记录和验证，不硬编码所有库相同批量 | designer；frontend；QA |
| 原推送钩子发现旧最小DOM没有 getAttribute；补齐后相关6组检查通过 | 最后一轮变更后核受影响旧用例；标准DOM夹具准确，不在生产代码绕接口或删断言 | QA；frontend；SRE |
| 浏览器被其他操作者切换、多项Git工作同时进行 | 新观察后再操作；必要时短暂专用标签；干净副本针对固定提交运行原定向钩子；保留无关工作 | QA；SRE |
| 用户明确“以后不能全量测试，只在修改影响范围内”；这覆盖旧的全量默认 | 当前任务按影响选择相关结构/链接/场景与必要回归；遇到超出范围的义务报告缺口，不能静默跑全量或绕门禁 | QA；SRE；QC |

50%宽度、60/96数量、具体供应商/CLI版本和端口均为案例事实，不作为全产品默认。真实测试发生在各原始任务；本次只做方法应用评测与相关维护检查，不据历史成功保证当前生产能力。

## 消费方式

专业方法位于既有 Skill 及按条件加载的 references。未改角色身份、权限、注册表任务、宿主工具能力或生成后的 agent 文件。新增三个参考分别从 designer、frontend、backend 的既有入口可发现；架构、DBA、QA、SRE、QC 与 debug 在原责任位置补最小规则。

## 场景评测与检查

输入及事先判据在 `evaluation/inputs.json` 和 `criteria.json`。A/B 由原有设计角色继续执行；它继承了先前上下文，不称fresh盲测。C–F 由维护执行者应用候选Skill推演，不称独立复核。没有新旧方法对照，不报告相对改进；本次结论记 evaluated。

维护检查只覆盖此次方法、发现路径、方法台账及版本生成一致性。用户的定向验证限制优先于仓库AGENTS的历史全脚本默认；未运行所有 test_*.py 或完整 check-sdlc 夹具集。实际命令与结果另见 `checks/results.json`。无生产请求、种子写入、图片生成、数据库结构或部署改动。
