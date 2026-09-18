# 状态归属与数据层

## 状态归属判定树

```
这个状态是服务端数据吗？
├─ 是 → 数据获取层（react-query / swr / RTK Query）
│        绝不复制进本地 state
└─ 否 ↓
   只有一个组件用吗？
   ├─ 是 → 组件内 useState
   └─ 否 ↓
      跨路由需要保留吗？（分享链接、刷新、前进后退）
      ├─ 是 → URL 查询参数（首选）
      └─ 否 ↓
         几个兄弟组件用吗？
         ├─ 是 → 提到最近共同父组件
         └─ 全应用都要 → 全局 store / context
```

**核心原则：能放低就不要放高。** 放高的代价是更大的重渲染范围和更强的耦合。

## 为什么服务端数据不能复制进本地 state

```jsx
❌ const [tickets, setTickets] = useState([])
   const [loading, setLoading] = useState(false)
   const [error, setError] = useState(null)

   useEffect(() => {
     setLoading(true)
     fetch(`/api/tickets?status=${filter}`)
       .then(r => r.json())
       .then(d => { setTickets(d.items); setLoading(false) })
       .catch(e => { setError(e); setLoading(false) })
   }, [filter])
```

这段代码有**五个 bug**，且都是上线后偶发：

| Bug | 触发场景 |
|---|---|
| **请求竞态** | 快速切换筛选：请求 A（慢）后发但先返回请求 B（快）→ 显示了旧筛选的数据 |
| **卸载后 setState** | 请求未返回时用户已离开页面 → 内存泄漏警告 |
| **重复请求** | 两个组件都需要这份数据 → 发两次请求 |
| **无缓存** | 来回切 tab 每次都重新加载 → 体验差且浪费 |
| **无失效机制** | 别处修改了数据，这里还显示旧的 |

```jsx
✅ const { data, isLoading, error } = useQuery({
     queryKey: ['tickets', filter],      // filter 变化自动重新获取，且自动处理竞态
     queryFn: () => api.getTickets(filter),
   })
```

`queryKey` 是关键：它让缓存、去重、竞态处理全部自动化。同一个 key 的并发请求会被去重，key 变化时旧请求的响应会被丢弃。

### 变更后的缓存失效

```jsx
const mutation = useMutation({
  mutationFn: api.createExport,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['exports'] })   // 让列表重新获取
  },
})
```

**失效范围要精确**：`invalidateQueries(['exports'])` 会失效所有以 `exports` 开头的 key。范围过大 = 不必要的请求；范围过小 = 数据不同步。

### 乐观更新要配回滚

```jsx
useMutation({
  mutationFn: api.toggleStar,
  onMutate: async (id) => {
    await queryClient.cancelQueries({ queryKey: ['tickets'] })
    const prev = queryClient.getQueryData(['tickets'])
    queryClient.setQueryData(['tickets'], optimisticUpdate)
    return { prev }                                    // 保存快照
  },
  onError: (err, id, ctx) => {
    queryClient.setQueryData(['tickets'], ctx.prev)    // 失败回滚
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['tickets'] }),
})
```

**没有回滚的乐观更新比不做乐观更新更糟**：用户以为成功了，实际失败，界面显示的是假象。

## URL 作为状态容器

筛选、分页、排序、tab、展开的详情 ID —— **这些都该在 URL 里**。

```jsx
✅ const [params, setParams] = useSearchParams()
   const status = params.get('status') ?? 'open'
   const page = Number(params.get('page') ?? 1)
```

收益：可分享（发给同事就是同一个视图）、可刷新（不丢状态）、可前进后退（浏览器按钮符合预期）、可埋点（URL 本身记录了用户在看什么）。

放组件 state 里则这四项全部失去。用户刷新页面后回到默认筛选，是很常见也很烦人的体验问题。

**注意**：URL 参数变化要防抖（输入框搜索时不要每个字符都改 URL，会污染历史记录）。用 `replace: true` 避免每次都产生新的历史条目。

## 派生状态不要存

```jsx
❌ const [items, setItems] = useState([])
   const [count, setCount] = useState(0)
   const [hasSelection, setHasSelection] = useState(false)
   // 三处状态要手动保持同步，必然有不同步的时刻

✅ const [items, setItems] = useState([])
   const count = items.length
   const hasSelection = items.some(i => i.selected)
   // 单一数据源，不可能不同步
```

只在计算确实昂贵时才用 `useMemo`（几千条数据的复杂变换）。**几十条数据的 `filter`/`map` 不需要 memo**——memo 本身也有成本。

## 表单状态

| 场景 | 方案 |
|---|---|
| 简单表单（几个字段，无复杂校验） | 受控组件 + `useState` |
| 复杂表单（多字段、跨字段校验、动态字段） | 表单库（react-hook-form 等） |
| 需要与服务端校验结合 | 表单库 + 提交后映射后端 `field` 到对应输入 |

**后端返回的 `field` 要能定位到具体输入框并高亮**——契约里的 `INVALID_PARAM` 带 `field`，就是为了这个。只显示一句「参数错误」浪费了这个信息。

**失败后保留用户输入。** 提交失败清空表单是最容易招致投诉的实现。

## 重渲染优化的正确顺序

```
① 先修状态归属 —— 状态放得过高是重渲染的首要原因
② 再看是否每次渲染都创建新对象/函数传给子组件
③ 最后才考虑 memo / useCallback / useMemo
```

**顺序反了通常没效果**：给子组件加 `memo` 但每次传的 props 里有新建的对象/函数，memo 完全无效。

```jsx
❌ <Child onSelect={() => handle(id)} config={{ mode: 'a' }} />
   // 每次渲染都是新的函数和新的对象，memo 失效

✅ const onSelect = useCallback(() => handle(id), [id])
   const config = useMemo(() => ({ mode: 'a' }), [])
```

先用 React DevTools Profiler 确认哪个组件真的在过度渲染，再动手。

## 竞态的其它来源

数据层解决了查询竞态，但这两处仍需手动处理：

**① 快速连续提交**

```jsx
✅ <button disabled={mutation.isPending} onClick={submit}>
     {mutation.isPending ? '提交中…' : '提交'}
   </button>
```

**按钮 loading + disabled 是防重复提交的最低要求**。光靠后端幂等不够——用户会看到多次失败反馈。

**② 依赖顺序的多步操作**

```jsx
✅ const step1 = useMutation(...)
   const step2 = useMutation(...)
   const run = async () => {
     const r1 = await step1.mutateAsync(input)
     await step2.mutateAsync(r1.id)        // 严格顺序
   }
```

不要用两个独立的 `useEffect` 串联步骤——执行顺序不可靠。

## 自测清单

- [ ] 无 `useEffect + fetch` 手写数据获取
- [ ] 服务端数据未复制进本地 state
- [ ] 筛选/分页/排序/tab 在 URL 里
- [ ] 无派生状态被单独存储
- [ ] 变更后有对应的缓存失效，范围精确
- [ ] 乐观更新配了回滚
- [ ] 提交按钮有 loading + disabled
- [ ] 表单失败后保留用户输入
- [ ] 后端 `field` 能定位到具体输入并高亮
- [ ] 快速切换筛选时无旧数据闪现（竞态验证）
