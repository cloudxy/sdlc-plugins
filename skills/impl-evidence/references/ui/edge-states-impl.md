# 六态实现与 a11y 落地

## 为什么六态不是可选项

只做 happy path 的实现，用户会遇到：白屏、原始报错信息、无限转圈、点了没反应。这些不是「边缘情况」——**加载态每次访问都出现，空态在新用户那里是首屏**。

对照 `/designer` 的 `edge-states.md` 逐屏核对。设计没覆盖的回去要，不要自己编。

## 加载态

### 骨架屏 vs spinner

| 场景 | 用 |
|---|---|
| 首次加载已知结构的内容（列表、卡片、表格） | **骨架屏**——占位形状与真实内容一致，避免布局跳动 |
| 结构未知或极短耗时 | spinner |
| 局部操作（按钮提交） | 按钮内 loading + disabled |
| 后台刷新（数据已有，在更新） | **保留旧数据 + 轻量指示**，不要变骨架 |

**首次加载与刷新必须区分**：

```jsx
const { data, isLoading, isFetching } = useQuery(...)

if (isLoading) return <Skeleton />          // 首次，无数据
return (
  <>
    {isFetching && <RefreshIndicator />}    // 刷新，有旧数据
    <List items={data.items} />
  </>
)
```

刷新时整屏变骨架是常见错误——用户看着已有内容突然消失，体验上像是崩了。

### 避免闪烁

极快返回的请求（< 200ms）显示 loading 反而是负面体验（一闪而过的骨架）。处理：延迟显示 loading（200–300ms 后才显示），或对已缓存数据直接渲染。

## 空态

**两种空态完全不同，必须分开：**

| 类型 | 判据 | 文案与操作 |
|---|---|---|
| **本来就没有** | 无筛选条件且结果为空 | 说明这是什么、为什么有用、**给创建入口** |
| **筛选后没有** | 有筛选条件且结果为空 | 说明当前筛选无匹配、**给清除筛选按钮** |

```jsx
if (items.length === 0) {
  return hasActiveFilter
    ? <EmptyFiltered onClear={clearFilters} />     // 「当前筛选无匹配，清除筛选」
    : <EmptyInitial onCreate={openCreate} />       // 「还没有工单，创建第一个」
}
```

混在一起用「暂无数据」是最偷懒也最没用的实现：新用户不知道该干什么，老用户不知道是筛选问题还是真的没了。

第三种容易漏的：**搜索无结果** —— 除了「无匹配」，最好给建议（检查拼写、尝试更宽的条件）。

## 错误态

### 按 code 分支，不按 message

```jsx
✅ function renderError(err) {
     switch (err.code) {
       case 'ROW_LIMIT_EXCEEDED':
         return <Alert>单次最多导出 {err.detail.limit} 条
                  <Button onClick={focusFilter}>缩小筛选范围</Button></Alert>
       case 'EXPORT_IN_PROGRESS':
         return <Alert>已有导出任务进行中
                  <Link to={`/exports/${err.detail?.export_id}`}>查看</Link></Alert>
       case 'FORBIDDEN_SCOPE':
         return <Alert>只能导出自己负责的工单</Alert>
       case 'RATE_LIMITED':
         return <Alert>操作过于频繁，请 {err.retryAfter} 秒后重试</Alert>
       default:
         return <Alert>操作失败，请稍后重试
                  <Detail>错误编号 {err.trace_id}</Detail>
                  <Button onClick={retry}>重试</Button></Alert>
     }
   }
```

三条纪律：

- **不用 `message` 做判断**——文案会改、会国际化，用它做逻辑会静默失效
- **`default` 分支必须有**——后端可能新增错误码，没有 default 就是白屏
- **5xx 展示 `trace_id`**——用户报障时这是唯一能定位日志的线索

### 错误态要给下一步

「出错了」是无用的错误态。每个错误要回答**用户现在能做什么**：重试、改条件、换账号、联系管理员、或明确「这个需要等待」。

### 错误的显示位置

| 错误范围 | 显示在哪 |
|---|---|
| 整页数据加载失败 | 页面级错误态（替换内容区） |
| 某个区块失败 | 区块内错误态，其余部分正常 |
| 表单字段校验 | 字段旁，且用 `aria-describedby` 关联 |
| 操作失败（提交、删除） | Toast 或就近提示，**保留用户输入** |

**局部失败不要整页报错**——列表加载成功但侧栏统计失败时，列表应该照常显示。

## 权限态

无权限时**隐藏还是禁用**取决于产品意图，问 `/designer`：

| 方式 | 何时用 |
|---|---|
| 完全隐藏 | 用户不该知道这个功能存在 |
| 显示但禁用 + 说明 | 用户应该知道有这功能，可以去申请权限 |

**禁用必须说明原因**（tooltip 或旁注）。灰掉但不解释的按钮是用户困惑的主要来源。

前端权限判断是**体验优化，不是安全边界**——后端必须独立校验。前端隐藏了按钮但接口没校验，等于没有权限控制。

## 离线态

```jsx
const online = useOnlineStatus()   // navigator.onLine + online/offline 事件
```

最低要求：断网时给明确提示（不要让用户以为是应用卡了），恢复后自动重试或提示刷新。

数据层通常有内置支持（react-query 的 `networkMode`）——优先用库的能力而不是自己实现。

## 边界态

| 边界 | 处理 |
|---|---|
| 超长文本（标题、名称） | 截断 + tooltip 显示全文；**不要让它撑破布局** |
| 极多条目 | 虚拟滚动或分页；测试时用几千条数据 |
| 极少条目（1 条） | 检查布局是否塌陷（grid 只有一个元素时的表现） |
| 数字边界 | 0、负数、极大值（千分位、溢出）、小数精度 |
| 空字符串 vs null | 显示占位符（`—`）而不是空白 |
| 长单词/URL 不换行 | `overflow-wrap: break-word` |
| 头像/图片加载失败 | 有 fallback（首字母/默认图） |

**测试要用极端数据**：把标题填成 200 个字符，把列表塞 5000 条，把数字改成 999999999。这些在真实数据里迟早出现。

## a11y 落地清单

### 语义化

```jsx
❌ <div className="btn" onClick={submit}>提交</div>
   // 键盘 Tab 不到、Enter 不触发、屏幕阅读器不报「按钮」

✅ <button type="button" onClick={submit}>提交</button>
```

原生元素自带键盘行为、焦点管理、语义角色。**用 div 模拟需要手工补全 role、tabIndex、onKeyDown**，几乎总是补不全。

### 键盘可达

- 所有交互元素能 Tab 到达，顺序符合视觉顺序
- Enter / Space 能触发
- **焦点必须可见**——不要 `outline: none` 而不给替代样式
- 跳过重复内容的「跳到主内容」链接（长导航时）

### 焦点管理

```jsx
// 弹窗打开：焦点移入，锁在内部，Esc 关闭，关闭后归还
useEffect(() => {
  if (!open) return
  const prev = document.activeElement
  dialogRef.current?.focus()
  return () => prev?.focus()          // 关闭时归还焦点
}, [open])
```

不管焦点的弹窗会让键盘用户被困在背景内容里——他们 Tab 到的是弹窗后面看不见的元素。

### 表单

```jsx
✅ <label htmlFor="email">邮箱</label>
   <input id="email" aria-describedby="email-err" aria-invalid={!!err} />
   {err && <span id="email-err" role="alert">{err}</span>}
```

`placeholder` 不能代替 `label`（输入后消失，且屏幕阅读器支持不一致）。

### 图标与图片

```jsx
✅ <button aria-label="删除工单"><TrashIcon /></button>      // 纯图标按钮
✅ <img src="chart.png" alt="本周工单量趋势：周一 12 条至周日 45 条" />
✅ <DecorativeIcon aria-hidden="true" />                    // 纯装饰
```

纯图标按钮没有 `aria-label` 时，屏幕阅读器读出来是空的。

### 动态内容播报

```jsx
✅ <div aria-live="polite">{status}</div>       // 状态变化（加载完成、保存成功）
✅ <div role="alert">{error}</div>              // 错误，立即播报
```

异步操作完成后如果只是视觉上变了，屏幕阅读器用户不知道发生了什么。

### 对比度与颜色

- 正文 ≥ 4.5:1，大字（18pt+ 或 14pt 粗体）≥ 3:1
- **不只靠颜色传达信息**：错误除了变红要有图标或文字（色盲用户看不出红绿差异）
- tokens 里的颜色组合要实际验证对比度，不要假设设计稿一定合规

完整 WCAG 合规需要辅助技术实测（屏幕阅读器、键盘、放大镜）与专家评审。这份清单是基线。

## 六态自测方法

不要只勾选，要真的跑出来看：

| 态 | 怎么造出来 |
|---|---|
| 加载 | 浏览器 DevTools 限速到 Slow 3G |
| 空（初始） | 用新账号，或清空数据 |
| 空（筛选） | 填一个必然无匹配的筛选条件 |
| 错误 | DevTools 拦截请求返回各个错误码；或临时改 API 地址 |
| 权限 | 切到低权限账号 |
| 离线 | DevTools Network 勾 Offline |
| 边界 | 塞 200 字标题、5000 条列表、极大数字 |

**每个都实际看一遍**，截图或记录进证据。勾选而未实测的六态，上线后基本都有问题。
