<!-- sdlc:unfilled — 写入本次的真实内容后删除本行；带这一行的文件在闸门里等于没交 -->
# 联调记录 · T-<nn> <旅程切片>

> 作者：frontend 帽（与 backend 同一切片）｜泳道：L<n>｜日期：<YYYY-MM-DD>｜构建：<commit>
> 切片：J-<n> 第 <a>–<b> 步｜对照：选定原型 `02-shape/prototypes/<d>-*.png` · `02-shape/edge-states.md`
> **真实后端，不用 mock。** 截图必须打开看过。

## 1. 环境

```
$ <app.start 命令>
<关键输出>
exit: 0
base_url: <http://localhost:5173>
```

## 2. 走查

| 步骤 | 操作 | 期望（spec / flows） | 实际 | 截图 |
|---|---|---|---|---|
| J-1.1 | 上传 sample-5000.xlsx | 进度可见，完成后进入报表 | 符合 | ![](screens/T-01/j1-1-1440.png) |
| J-1.2 | 等待报表 | 30s 内首屏；签名时刻渐显 | 22s；渐显存在 | ![](screens/T-01/j1-2-1440.png) |

截图命令：

```
$ bash PLUGIN_ROOT/scripts/ui-evidence.sh <url> 03-impl/screens/T-<nn> 375,1440
<输出>
exit: 0
```

## 3. 状态抽查（至少：空 / 错误 / 权限）

| 状态 | 如何触发 | 结果 | 截图 |
|---|---|---|---|

## 4. 与原型对照

| 差异 | 原因 | 处理（已修 / 交 designer 确认 / 技术限制交 architect） |
|---|---|---|

## 5. 契约偏差

| 接口 / 字段 | 契约 | 实际 | 处理（回 architect / 已修） |
|---|---|---|---|

## 6. 埋点（tracking: yes）

| EV-n | 是否触发 | 属性是否正确 | 方法 |
|---|---|---|---|

## 7. 结论

切片可演示：<是 / 否 + 缺什么>
