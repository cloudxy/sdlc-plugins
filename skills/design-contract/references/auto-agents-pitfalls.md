# auto-agents designer pitfalls

> 只收录本仓库已复现的设计坑：有代码/测试/工单注释，不是通用 UX 理论。
> 卡片：pitfall / evidence / prevent。未达此线的不写。

---

## P-DES-01 失败装空

**pitfall：** 公开列表 `catch` 后 `setItems([])`，再渲染「暂无已发布…」。网络失败、接口 5xx、目录真没有、搜索无命中，用户看到同一块空白。访客得出「这个产品没有货」，而不是「现在加载失败」。

**evidence：**

- `frontend/official/src/components/home/SkillsSection.tsx`：`.catch(() => setItems([]))`，注释写「后端不可达时静默空态，不影响首页其余部分」。失败时节标题还在、卡片区空白。
- `frontend/official/src/pages/SkillsSquare.tsx`：`catch { setItems([]) }` 后 `Empty description="暂无已发布技能"`。无 `q` 的空目录与有 `q` 的零命中同一句。
- `frontend/official/src/pages/Capabilities.tsx`：`catch(() => setItems([]))` 后 `暂无已发布${TYPE_LABELS[type]}`。
- 审查 QA-09：首页技能精选失败装空未进 Wave 0；spec FR-28 把「失败不得装成没有产品」冻在 Wave 1 市场，首页仍漏。

**prevent：** 空态判据拆开：无筛选且 200 空 = 目录空；有 `q`/筛选且 200 空 = 清除筛选；`catch` / 5xx / 离线 = 错误态 + 重试，文案禁止「暂无已发布」。首页精选与市场列表用同一条规则。

---

## P-DES-02 权限未知当成「无权限」

**pitfall：** 把「权限列表还没回来 / 拉失败」设计成与「该角色没有这些码」相同的 UI（菜单滤光、按钮全隐）。刷新或后端瞬断时，熟练用户以为功能丢了；再叠加租户叶子 `tenantOnly` 只滤顶层时，平台超管会看见不该进的租户项。

**evidence：**

- `frontend/admin/src/hooks/usePermission.ts`：注释记录「缓存空 → filterMenu 全滤光 → 侧边栏消失」；现改为缓存空显示全量菜单（安全改到 API）。
- `frontend/admin/src/hooks/usePermission.test.tsx`：`bea13b5` 回归「补拉失败菜单全量兜底而非全滤光」；F-T10-1：兜底曾只滤顶层 `tenantOnly`，叶子上的成员/用量在超管无租户时仍出现。

**prevent：** 权限三态分开画：**未知**（保留壳或上次菜单，不要空白 Sider）、**拒绝**（发现性禁用+说明 / 平台专属隐藏）、**通过**。未知不是空数组。`tenantOnly` 必须滤到叶子。403 文案说谁能看，不说「抱歉」。

---

## P-DES-03 CTA 标签与出口不是同一件事

**pitfall：** 按钮写「联系升级 / 联系销售 / 即可登录」，实际送到「再开一家免费企业」或留在无法登录的成功页。用户按标签理解后果，出口却是另一条任务。这是欺骗性 CTA，不是文案风格问题。

**evidence：**

- `frontend/official/src/pages/Pricing.tsx`：免费档 `免费注册`、专业档 `联系升级`、企业档 `联系销售`，三档 `cta.href` 都是 `/register`。
- `frontend/official/src/pages/Register.tsx`：成功 Toast「注册成功，即可登录开始第一次采集」；主按钮 `href="/register"`「再注册一家」，次「返回官网」。无后台登录链。
- spec FR-04 / FR-05、ops S-05/S-07：激活断链与空头定价按此复现。

**prevent：** 按钮文案 = 按下之后发生的动作。免费档才进注册；付费档必须是另一出口（或标「预告不可购买」）。注册成功主按钮必须是「登录管理后台」。同一动作从按钮到 Toast 到落地页用同一个动词。

---

## P-DES-04 筛选空与目录空同一句「暂无」

**pitfall：** 表格/卡片只有一种 `Empty`。新用户不知道下一步；老用户不知道是筛错了还是真没有。和 P-DES-01 叠加时，第三种（失败）也被吞进同一句。

**evidence：**

- `SkillsSquare.tsx`：`items.length === 0` → 唯一 `暂无已发布技能`（含 `?q=` 搜索）。
- `frontend/admin/src/components/spider/TaskList.tsx`：无 `emptyText`；有状态/爬虫筛选时，空表与「还没有采集任务」不可分。
- `frontend/admin/src/pages/Capabilities.tsx`：专家团 `暂无专家团`，同页已有「组建专家团」，空态不指向该按钮。
- 反例（可学）：`PlanList`「去采集向导创建一个」；`TemplateTab` 指向「收藏」；`NewApiOps` 降级空 vs 真无渠道两套 `emptyText`。

**prevent：** 两种空态两套文案+主按钮：本来没有 = 邀请创建；筛选后没有 = 列出当前筛选 +「清除筛选」。有主按钮的页，空态必须指向它。治理台不要把仓库路径写进 `emptyText`。

---

## P-DES-05 不可信技能正文必须当纯文本，不能随「详情升级」改成 Markdown

**pitfall：** 市场详情从 Modal 升级成独立 URL 时，容易把 SKILL.md 改成 Markdown/HTML 渲染。第三方正文是不可信内容；一改渲染路径，XSS 夹具就会从「可见文本」变成可执行节点。

**evidence：**

- `frontend/official/src/pages/SkillsSquare.tsx`：注释约定「SKILL.md 为不可信内容，一律以纯文本渲染」；`<pre data-testid="skill-md">`。
- `frontend/official/src/pages/SkillsSquare.test.tsx`：`XSS_PAYLOAD = '<script>alert("xss")</script>…'`，断言只成为转义文本。
- spec T-27：技能广场纯文本防 XSS 是已有能力，Wave 1 迁到能力市场，禁止直接删光。审查 QA-05：FR-17…31 尚无 XSS GWT。

**prevent：** 商店详情合同写死：不可信正文 = 纯文本节点，禁止 markdown/HTML。迁 `/capabilities/:type/:slug` 时把 `SkillsSquare.test.tsx` 的 XSS 夹具一起迁，而不是「先做漂亮详情再补安全」。未上架/黑名单深链走 404，不在详情里解释原因。
