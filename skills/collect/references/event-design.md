# 埋点事件设计

埋点是产品的「感官」。设计得好，北极星、漏斗、分群、增长实验都能直接算；设计得差，每次复盘都在吵口径。

## 1. 先从指标倒推，不从按钮正推

```
指标（metrics.yaml id）→ 需要观察的用户行为 → 事件 → 属性
```

| 指标 | 需要观察的行为 | 事件 | 关键属性 |
|---|---|---|---|
| 首份报表查看率 | 导入完成、首次看到报表 | `dataset_imported`、`report_viewed` | `dataset_id`、`row_count`、`is_first_view` |

**没有指标（或具名分析）要用的事件不加。**

## 2. 命名规范

| 规则 | 例 | 反例 |
|---|---|---|
| `object_action`，动作用过去式 | `report_viewed`、`invite_sent` | `clickShareBtn`、`view_report_page` |
| 对象用产品领域词（与 domain-model 统一语言一致） | `report`、`dataset` | `page2`、`modal_a` |
| snake_case，全小写 | `order_paid` | `OrderPaid` |
| 一个行为一个事件，差异用属性表达 | `report_shared` + `channel: link|wechat|email` | `report_shared_link`、`report_shared_wechat` |
| 不以 UI 位置命名 | `export_started` + `entry: toolbar|menu` | `toolbar_export_click` |

## 3. 属性

| 类别 | 内容 | 放哪 |
|---|---|---|
| 公共属性（每个事件都有） | `event_time`（客户端/服务端各一）、`anonymous_id`、`user_id`、`session_id`、`platform`、`app_version`、`page`、`tenant_id`（ToB） | 产品 tracking-plan 统一定义 |
| 事件属性 | 与该行为相关的参数：对象 id、数量、结果、来源 | 每个事件单独定义 |
| 业务结果 | `result: success|failed` + `error_code`（不是另起失败事件，除非失败是独立行为） | 事件属性 |

每个属性写清：类型、允许值（枚举列出）、是否必填、示例。

## 4. 身份打通

| 场景 | 规则 |
|---|---|
| 未登录浏览 | 只有 `anonymous_id`（设备/浏览器生成，持久化） |
| 注册 / 登录成功 | 服务端发 `user_signed_up` / `user_logged_in`，携带 `anonymous_id` 与 `user_id`，建立映射 |
| 跨设备 | 以 `user_id` 为准；`anonymous_id` 只用于登录前行为归并 |
| 登出 | 生成新的 `anonymous_id`，避免下一位用户行为串号 |
| ToB 多租户 | `tenant_id` 作为公共属性；同一人多租户以 `(tenant_id, user_id)` 区分 |

## 5. 客户端 vs 服务端

| 放服务端 | 放客户端 |
|---|---|
| 支付、订单、状态变更、权限变更、邮件发送——**以数据库事实为准的结果** | 曝光、点击、滚动、停留、前端报错——**只有前端知道的行为** |
| 不受广告拦截、重试、离线影响 | 需要处理离线队列、批量上报、去重 |

同一行为两端都发时，明确哪个是指标口径来源，另一个只做诊断。

## 6. 采样、频率与性能

- 高频事件（滚动、鼠标移动、心跳）默认不采；确需时采样并在属性里写 `sample_rate`。
- 批量上报、页面卸载时 `sendBeacon`；不阻塞交互。
- 曝光事件定义「有效曝光」（可见面积 ≥50% 且 ≥1 秒）。

## 7. 隐私与合规

- 事件属性禁止明文 PII（手机号、邮箱、证件号、精确地址）；需要时用不可逆哈希或服务端关联。
- 同意状态：未同意分析类 Cookie / 隐私政策前，不发非必要事件，或打 `consent: false` 并在数仓侧隔离。
- 未成年人、敏感类目按法规单独处理。

## 8. tracking.md 里每个事件的最小描述

```yaml
- id: EV-1
  event: report_viewed
  journey: J-1 第 3 步
  trigger: 报表首屏图表渲染完成（非路由进入）
  placement: client
  properties:
    report_id: {type: string, required: true}
    is_first_view: {type: boolean, required: true}
    load_ms: {type: integer, required: true}
  metric: report_first_view_rate
  owner: pm
  validation: 打开任一报表，网络面板看到 1 次 report_viewed，is_first_view 首次为 true、刷新后为 false
```

## 反模式

| 反模式 | 后果 | 修正 |
|---|---|---|
| 「页面浏览」代替关键行为 | 进入页面 ≠ 看到价值 | 以价值出现的时刻为触发 |
| 前端发「支付成功」 | 与订单表对不上 | 服务端发，以订单状态为准 |
| 一个按钮一个事件 | 事件爆炸、口径分裂 | 行为事件 + 属性 |
| 上线后补埋点 | 本次上线效果永远不可评估 | define 阶段写进 tracking.md 与 FR |
