# QA共享控件规则：范围澄清复核

结论：实际QA末节已消除本轮指出的范围歧义。该结论只针对文字规则及其对既有B/D场景的适用性，不是运行页面验收、fresh独立结论或旧新收益比较。

本轮只读输入：

- `/Users/xuyun/Documents/sdlc-workflow/skills/coverage-matrix/references/e2e-and-exploratory.md` 的“共享控件跨页面的样式走查”末节。
- `/private/tmp/sdlc-service-style-20261114/scenario-output.md` 中既有B、D应用输出。

## B：仅统一跨页导航菜单

修正文明确：内容操作限于本次相关且已授权的动作；仅影响导航呈现时，核对导航目标即可。因此B不再需要执行周边绿色主按钮、红色危险按钮或其他业务写入来凑路径。

原有“保留已声明主次、危险或主题变体”同时保留，与B的变体表一致：同一变体对照自身契约，批准的亮/暗色差不被误判为缺陷。既有B输出无需改变其范围或增加审批。

## D：页面当前不可用

修正文把路径执行限定为“本次影响跨入口菜单或点击路径且实际页面可用”，并明确页面不可用时保留待验、不抢占浏览器、不扩大测试范围。

因此D可以继续提交静态分析、设计契约和定向脚本，实际页面与点击路径保持未执行；不能把单张旧截图或DOM通过升级为本轮视觉通过。后续仅由有权操作者重新确认实际页面后执行相关路径，与既有D输出一致。

## 剩余事项与证据边界

在本轮核对的B/D范围内，未发现仍需修正的强制流程或范围冲突。该澄清也未取消真实UI证据要求：页面暂不可用意味着待验，不意味着免验或通过。

未重复四案，未读取其他评测结论，未操作浏览器或运行UI/全站/全量测试；只新增本文件，保留此前scenario-output及所有仓库文件。

```json
{
  "role_id": "product-designer",
  "role_sha256": "5cc053b12adc07548075cd3bf3d80203052d4ad2a573c8ef1e489174a25278dd",
  "context_id": null,
  "context_sha256": null,
  "dispatch_id": null,
  "instance_id": null,
  "result_refs": ["/private/tmp/sdlc-service-style-20261114/scenario-refinement.md"],
  "memory_proposals": []
}
```

未提供正式context/dispatch/instance字段；只读由行为约束执行，宿主工具并非强制只读。
