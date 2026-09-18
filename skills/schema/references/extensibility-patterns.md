# 可扩展性模式：为已知的变化留口子，而不是为想象留口子

**原则**：只为 `feature-map.md` Next / Later 里出现的、或 `strategy.md` 明确的业务多样性（多种内容类型、多种支付渠道、多地区、多角色）设计扩展点。每个扩展点都要回答：**新增一种变体要改什么、代价多大**。

## 模式速查

| 变化类型 | 推荐模式 | 新增一种变体的代价 | 不适用时 |
|---|---|---|---|
| 同一实体有多种「类型」，差异在少量配置 | **类型表 + JSON 配置 + 生成列索引** | 加一行类型 + 适配代码，无迁移 | 类型之间差异大、各自有大量需要查询的字段 |
| 类型差异大，各自有需要查询 / 约束的字段 | **公共主表 + 每类型扩展表（1:1）** | 新建一张扩展表（加法迁移） | 类型数量多且频繁增加 |
| 一个对象可以挂在多种目标上（评论、标签、点赞、附件） | **多态关联：`target_type + target_id`**（或每目标一张关联表） | 新目标类型零迁移 | 需要数据库级外键保证时 → 每目标一张关联表 |
| 需要知道「某个时间点的样子」 | **版本表 / 时态表**（`valid_from`、`valid_to`、`version`） | 无 | 只需要「谁改了什么」→ 审计日志即可 |
| 状态流程可能增加状态 | **VARCHAR 状态 + 流转表 / 应用层状态机** | 加状态值 + 流转规则，无 DDL | — |
| 租户 / 用户可自定义字段 | **自定义字段定义表 + 值存 JSON（必要时生成列）** | 定义一行 | 需要跨租户统计分析这些字段 → 数仓侧展开 |
| 计数、热度、排行 | **计数器表 / 分桶计数 + 异步汇总** | 无 | 强一致计数 → 事务内更新（热点注意） |
| 多语言内容 | **翻译表 `(entity_id, locale, field, value)` 或每实体翻译子表** | 新语言零迁移 | 只有两种语言且固定 → 列也可以 |
| 未来可能分片 | **所有大表带分片键（`tenant_id` / `user_id`）并在唯一键与索引最左** | 无（今天就付出，成本低） | 数据量确定很小的配置表 |
| 多币种 / 多地区 | 金额 + 币种同行；时间统一 UTC；地区作为维度列 | 无 | — |

## 模式细节

### 类型表 + JSON 配置 + 生成列

```sql
CREATE TABLE source_types (
  code VARCHAR(32) PRIMARY KEY,          -- file | api | database
  name VARCHAR(64) NOT NULL,
  config_schema JSON NOT NULL            -- 该类型配置的 JSON Schema，应用层校验
);

CREATE TABLE data_sources (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id BIGINT UNSIGNED NOT NULL,
  type_code VARCHAR(32) NOT NULL,
  config JSON NOT NULL,
  api_base_url VARCHAR(255) GENERATED ALWAYS AS (config->>'$.base_url') VIRTUAL,  -- 需要查询的字段做生成列
  INDEX idx_ds_tenant_type (tenant_id, type_code),
  INDEX idx_ds_api_url (api_base_url)
);
```

纪律：JSON 里只放**不参与关系约束**的配置；需要唯一性、外键、频繁过滤的字段拿出来做列或生成列；JSON Schema 在应用层校验并有版本。

### 公共主表 + 扩展表

```
assets（id, tenant_id, kind, name, status, created_at …）   -- 所有类型共有、列表页要用的字段
asset_skill_ext（asset_id PK/FK, entry_file, examples JSON）
asset_plugin_ext（asset_id PK/FK, manifest_version, bundled_count）
```

列表查询只打主表；详情按 `kind` 加载对应扩展表。新类型 = 新扩展表，主表不动。

### 多态关联的两种写法

| 写法 | 优点 | 缺点 |
|---|---|---|
| `comments(target_type, target_id)` | 新目标零迁移 | 无外键；删除目标要应用层清理；索引 `(target_type, target_id, created_at)` |
| `report_comments`、`dataset_comments` 各一张 | 有外键、清晰 | 新目标要加表 |

目标类型 ≤3 且稳定 → 各一张；目标类型会持续增加 → 多态 + 清理任务 + 对账。

### 版本 / 时态

```
report_versions（report_id, version, definition JSON, published_at, published_by）
reports（id, current_version, …）
```

分享链接、审计、回滚都指向具体 `version`——这就是「快照 vs 引用」在版本维度上的落地。

## 反模式：EAV（实体-属性-值）

```
entity_attributes(entity_id, attr_name, attr_value VARCHAR)
```

看起来「无限可扩展」，代价是：类型丢失、无法约束、查询要 N 次自连接、索引失效、数仓难以使用。**只在「用户自定义字段且几乎不查询」时考虑**，并优先用 JSON 列替代。

## 路线压力测试的写法

对每个 Next / Later 项：

| 未来需求 | 需要的 DDL | 加法 / 破坏性 | 代价 | 结论 |
|---|---|---|---|---|

判定规则：
- **Next 项出现破坏性变更** → 现在就调整模型（今天改几乎免费）。
- **Later 项出现破坏性变更** → 可以接受，但写下触发条件与迁移路径（expand-contract 三步）。
- **为 Later 项提前引入复杂度** → 只在代价极低时做（例如今天就带上 `tenant_id` / 分片键）。

## 自检

- [ ] 每个扩展点都对应一条已知变化（feature-map / strategy），不是「以防万一」？
- [ ] 写清了新增一种变体的代价？
- [ ] JSON 里没有需要约束或频繁过滤的字段？
- [ ] 没有引入 EAV 作为通用扩展方案？
- [ ] 路线压力测试覆盖所有 Next 项，破坏性项已处理或写明触发条件？
