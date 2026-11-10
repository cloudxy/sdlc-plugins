# sdlc-eval 实际场景答复

## case_id: maintenance-without-client

不必专门登录 Claude CLI，也不必为了凑固定调用数或重复次数重跑。Skill 评测仍然需要实际任务证据，但不绑定某个模型、客户端或模型对照方案。

按你描述的已有证据，可以记录“三个真实场景的当前版本答复均满足各自既定标准”。来源审查、脚本回归和场景评测应分别记载，避免把一种检查当成另一种检查的替代品。还应列出此次共享账号暂停规则涉及的条件分支，说明三个场景实际覆盖哪些分支；没有运行的分支记为未测试。

评测记录应保留：

- 被评 Skill 的版本或树哈希、具体规则改动及评测范围。
- 三个场景各自的输入、输入快照、事先确定的判定标准、完整实际答复、逐项判定及对应证据；注明评判方式和评判者，不能由产出方补造评分。
- 实际采用的评测方式，以及实际可得的模型、设置、工具、资源用量等信息。未知或未采集的字段如实写明，不能推测填充。
- 来源审查、脚本回归的结果与证据路径，以及失败、无效、未运行或未覆盖的项目。
- 限制：Claude CLI 未登录；未做冻结旧版与新版的受控比较；结论仅覆盖这三个场景和实际检查的条件分支。

因此，可以结束这次已完成的场景评测记录；“改写后优于旧版”“整体质量提高”仍无前后对照证据，不能写成已证实。若后续需要作出这类质量提升结论，再安排冻结旧、新方法、保持任务输入和执行条件可比的评测。无需仅因某个客户端不可用而否定已有的有效场景证据。

### 实际读取路径

- `/Users/xuyun/Documents/sdlc-workflow/skills/sdlc-eval/SKILL.md`
- `/Users/xuyun/Documents/sdlc-workflow/skills/sdlc-eval/references/controlled-comparisons.md`
- `/private/tmp/sdlc-mt-lessons-20261110/scenarios/sdlc-eval.json`

## case_id: evaluation-required-control

不能直接宣布 Skill 评测通过。现在能确认的是健康检查和 Python 脚本回归通过；尚未执行任何使用该 Skill 的任务场景，Skill 的实际行为仍未验证。“不对模型使用做要求”允许选择合适的评测方式，并没有取消 Skill 修改后的场景评测要求。

可行的下一步是：

1. 列出采集断点规则此次改变的条件分支，选择能够覆盖这些变化及关键边界的实际任务场景，预先明确输入和逐项判定标准。
2. 用当前可用的评测方式执行这些场景。例如进行隔离的下一轮答复评测，让执行者读取修改后的 Skill、面对场景给出完整实际答复，再由独立评判者依据标准检查。无需指定模型、客户端或固定调用数。
3. 保存 Skill 版本、实际输入、完整产出、使用方式、逐项判定与证据。只记录实际观察到的信息；失败、无效、未运行和未覆盖项目均如实保留。
4. 若发现问题，修正后验证相关场景，并完成适用的回归检查。仅在证据满足已声明的标准后，给出限定于实际评测范围的结论。

目前应记录为：“机械回归通过；Skill 场景评测未执行，待完成。”若暂时没有可用的场景评测方式，就保留待评测状态，不能把脚本通过或环境限制记成 Skill 评测通过。

### 实际读取路径

- `/Users/xuyun/Documents/sdlc-workflow/skills/sdlc-eval/SKILL.md`
- `/Users/xuyun/Documents/sdlc-workflow/skills/sdlc-eval/references/controlled-comparisons.md`
- `/private/tmp/sdlc-mt-lessons-20261110/scenarios/sdlc-eval.json`
