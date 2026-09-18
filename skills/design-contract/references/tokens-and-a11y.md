# Design Tokens 与可访问性

## tokens 是契约

`/frontend` 只消费 token，禁止硬编码。所以：**你没定义的值，前端就没法用**——他要么回来找你，要么硬编码（然后这个值永远留在代码里）。

tokens 的完整性直接决定实现质量。缺一个中间色阶，就会出现一个硬编码。

## 三层结构

```
① 原始层（primitive）—— 纯粹的值，不带语义
   blue-500: #3b82f6      gray-100: #f3f4f6
   space-4: 16px          radius-md: 6px

② 语义层（semantic）—— 指向原始层，带业务语义
   color-primary: {blue-500}
   color-danger: {red-500}
   color-text-secondary: {gray-500}
   color-surface: {white}

③ 组件层（component，可选）—— 指向语义层
   button-primary-bg: {color-primary}
   card-padding: {space-4}
```

**前端消费语义层，不消费原始层。** 原因：主题切换、品牌调整时只改语义层的指向，组件代码一行不动。

```
❌ 前端写 color-blue-500     → 换主题时蓝色变绿色，语义错乱
✅ 前端写 color-primary      → 换主题只改 primary 指向哪个原始色
```

组件层是否需要看项目规模：组件多、变体多时有用；小项目直接用语义层。

## 六类 tokens

### 颜色

**语义化命名，不是颜色名：**

```
✅ color-primary / color-danger / color-warning / color-success / color-info
✅ color-text-primary / color-text-secondary / color-text-disabled
✅ color-surface / color-surface-raised / color-border
❌ color-red / color-light-gray / color-blue-2
```

每个语义色要成套（用于不同场景）：

```
color-danger          主色（按钮背景、图标）
color-danger-hover    悬停态
color-danger-subtle   浅色背景（警告框底色）
color-danger-text     在浅色背景上的文字色（要保证对比度）
```

**只给一个 `color-danger` 是不够的**——前端画警告框时需要浅底色，他会自己调透明度，然后各处不一致。

### 间距

**一套节奏，不要零散数值：**

```
✅ space-1: 4px    space-2: 8px    space-3: 12px
   space-4: 16px   space-6: 24px   space-8: 32px   space-12: 48px
❌ 出现 13px、17px、22px
```

4 或 8 的倍数是常见基准。**零散数值的代价**：视觉节奏乱，且前端遇到 13px 只能硬编码。

### 字体

**字号、字重、行高成套定义**，不要分开给：

```
✅ text-heading-1: { size: 32px, weight: 700, lineHeight: 1.25 }
   text-body:      { size: 14px, weight: 400, lineHeight: 1.6 }
   text-caption:   { size: 12px, weight: 400, lineHeight: 1.5 }
❌ font-size-lg: 32px（前端要自己猜行高与字重）
```

行高用无单位倍数（`1.6`）而非固定 px——字号变化时行高自动跟随。

### 圆角、阴影、动效

```
radius-sm/md/lg/full
shadow-card / shadow-dropdown / shadow-modal    ← 按用途命名，不按大小
duration-fast: 150ms / duration-base: 250ms
easing-standard: cubic-bezier(0.4, 0, 0.2, 1)
```

阴影**按用途命名**（`shadow-modal`）而不是按大小（`shadow-lg`）：弹窗的阴影该多大是设计决策，前端不该判断。

### 断点（必须进 tokens）

```
breakpoint-sm: 640px
breakpoint-md: 768px
breakpoint-lg: 1024px
breakpoint-xl: 1280px
```

**断点不进 tokens 的后果**：各页面用不同断点，同一个屏宽下有的页面已切换布局有的还没切。

## 对比度：设计阶段必须验

**WCAG AA 要求**：

| 内容 | 最低对比度 |
|---|---|
| 正文（< 18pt 且非粗体） | **4.5:1** |
| 大字（≥ 18pt，或 ≥ 14pt 粗体） | **3:1** |
| UI 组件边界、图标 | **3:1** |
| 纯装饰、禁用状态 | 无要求 |

### 怎么算

对比度 = (L1 + 0.05) / (L2 + 0.05)，L 是相对亮度。**不用手算**——用工具（浏览器 DevTools 的对比度检查、在线对比度计算器、设计工具插件）。

### 要验的组合

不是只验「黑字白底」，要验**所有实际出现的组合**：

```
color-text-primary   on color-surface          ← 正文
color-text-secondary on color-surface          ← 次要文字（最容易不合格）
color-text-primary   on color-surface-raised   ← 卡片上的文字
color-danger-text    on color-danger-subtle    ← 警告框里的文字
white                on color-primary          ← 主按钮文字
color-border         on color-surface          ← 边界（3:1）
```

**`color-text-secondary` 是最常不合格的**：设计上想要「弱一点」，一弱就掉到 4.5:1 以下。灰色文字要谨慎。

**验不过怎么办**：调深文字色，或调浅背景色。不要因为「设计上更好看」保留不合格的组合——那会让 `/frontend` 面临「照 token 做但不合规」的两难。

## 不只靠颜色传达信息

色盲用户（约 8% 男性）分不清红绿。所有靠颜色传达的信息都要有第二个通道：

| 场景 | 只有颜色 | 加第二通道 |
|---|---|---|
| 表单错误 | 边框变红 | 红边框 + 错误图标 + 文字说明 |
| 状态标签 | 绿色=成功 红色=失败 | 加图标（✓ / ✕）或文字 |
| 图表系列 | 不同颜色的线 | 加不同线型或直接标注 |
| 必填标记 | 红色星号 | 星号本身是形状，可接受；但要有 `required` 语义 |

## 设计阶段能定的 a11y 项

| 项 | 设计阶段做什么 |
|---|---|
| 对比度 | tokens 组合已验证（上文） |
| 不只靠颜色 | 每个状态有图标或文字 |
| **焦点顺序** | flow 里标明 Tab 顺序（表单、弹窗尤其重要） |
| **焦点样式** | 定义 `focus` 态的视觉（不能只有 hover） |
| 触摸目标 | 交互元素 ≥ 44×44px（含内边距） |
| 文案清晰 | 错误提示说清「发生了什么 + 现在做什么」 |
| 图标标签 | 纯图标按钮给出 `aria-label` 的文案 |
| 标题层级 | 页面的 h1/h2/h3 结构（不跳级） |
| 动效可关闭 | 大幅动效要考虑 `prefers-reduced-motion` |

### 焦点顺序要写出来

```
弹窗「导出配置」的 Tab 顺序：
1. 关闭按钮（×）
2. 格式选择（单选组，方向键切换）
3. 列选择（多选，Tab 进入组，方向键移动，Space 勾选）
4. 取消按钮
5. 确认按钮
→ 焦点锁在弹窗内（Tab 到最后回到第 1 项）
→ Esc 关闭
→ 关闭后焦点回到触发它的「导出」按钮
```

不写的话，`/frontend` 通常就用 DOM 默认顺序——在复杂布局里这个顺序往往不符合视觉顺序。

### 图标按钮的 aria-label 文案

```
🗑  aria-label="删除工单"        （不是「删除」——要说删什么）
⋯   aria-label="更多操作"
↓   aria-label="下载导出文件"
```

**这是文案工作，归设计。** 前端自己编的 label 经常不准确或不一致。

## 完整性自检

- [ ] 三层结构清晰，前端消费的是语义层
- [ ] 颜色语义化命名，每个语义色成套（主色/hover/浅底/浅底上的文字）
- [ ] 间距成节奏，无零散数值
- [ ] 字体三要素成套（字号+字重+行高）
- [ ] 阴影按用途命名
- [ ] 动效有时长 + 缓动
- [ ] **断点已进 tokens**
- [ ] 所有实际颜色组合的对比度已验（含 text-secondary）
- [ ] 每个靠颜色传达的信息有第二通道
- [ ] 焦点顺序已在 flow 里标明
- [ ] `focus` 态视觉已定义（不只有 hover）
- [ ] 触摸目标 ≥ 44×44px
- [ ] 纯图标按钮的 aria-label 文案已给
- [ ] 新增 token 前确认过现有的真的不够用

**完整 WCAG 合规需要辅助技术实测（屏幕阅读器、键盘、放大）与专家评审。** 以上是设计阶段能覆盖的基线。
