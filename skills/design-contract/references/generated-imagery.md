# 生成图（designer 侧用法）

出图能力与做法见 [sdlc-workflow:imagery](../../imagery/SKILL.md)（提示词纪律、授权、证据与闸门都在那里）。本文件只回答设计线的三个问题：**什么时候值得生成一张图、风格锚点从哪里来、生成完怎么落进工件。**

派单包 `imagery` 非空才生成；为空就是"这一趟不需要图"，不要自己加。

## 什么时候值得生成

| 任务 | 允许的 kind | 值得的情形 | 不值得的情形 |
|---|---|---|---|
| `explore` | `ref` | 视觉语言有真实不确定性（暖/冷中性、插画感/摄影感、密度给人的观感），一张探针图比三段形容词快 | 方向已经清楚；或者只是想让 `design-directions.md` 看起来更丰满 |
| `specify` | `illustration` `empty-state` `hero` `icon` | 空态/错误态/引导时刻需要一张图来承担说明；官网需要一张让人记住的 hero；图标要成一家子 | admin 后台的功能界面（antd 基座上，差异来自契约质量，不是配图）；任何能用文字或组件讲清的地方 |

`ref` 只是探针：**方向本身仍然是原型代码 + 它的渲染**。`check-sdlc.sh` 判"方向有没有渲染产物"时会忽略 `assets/refs/` 与 `assets/generated/`，所以拿生成图顶替原型渲染不会通过，只会浪费一轮。

## 风格锚点从哪里来

提示词里的"风格"必须是**已经决定过的东西**，不是临时发挥：

1. `<product_root>/design-system.md` 的实际取值：强调色 hex、中性底色的冷暖、圆角与阴影的克制程度、字体气质。
2. 本次选定的方向（`design-directions.md` 的 `选定：D<n>`）：`explore` 阶段则是你正在试的那一个方向。
3. [visual-direction.md](visual-direction.md) 的五个 AI 默认簇——它们同样是**出图**的默认脸。生成图落进那五簇里（暖奶油+赤陶色、近黑底+单荧光、SaaS 卡片套件…）就是没为这个产品做选择，重写提示词再来一次。

一张图只承担一件事：`--purpose` 写不出来，就是还没想清楚要它干什么。

## 生成完怎么落进工件

```
python3 PLUGIN_ROOT/scripts/image/generate.py --root <feature_dir> \
  --kind empty-state --name empty-orders \
  --purpose "订单空态：说明还没有数据以及下一步做什么" \
  --declared-in 02-shape/edge-states.md \
  --prompt-file <feature_dir>/prompts/empty-orders.txt --aspect 4:3
python3 PLUGIN_ROOT/scripts/image/check.py --root <feature_dir>
```

- 提示词先写成文件（它会原文存进证据，是这项工作可被审查的部分）。
- **先看图再引用**：Read 那个 PNG，看构图、留白、有没有多余文字、对比度够不够压文案。
- 在 `--declared-in` 的那份工件里引用它，并写清是 AI 生成：
  `![订单空态（AI 生成，证据 evidence/images/empty-orders.json）](assets/generated/empty-orders.png)`
- `edge-states.md` 里配图不能替代该状态的文案与行为约定；`design-directions.md` 里参考图旁边要写清它试的是什么、结论是什么。
- 之后改了声明源那份工件，图会被判 stale：重新看一遍，确认仍然对，再重新生成或重新声明。

## 交回来之前

- [ ] 每张图都有 `purpose`，且不是"配图"这类空话？
- [ ] 风格锚点能指回 `design-system.md` 或选定方向？
- [ ] 图里没有生成的文字、没有真人肖像、没有他人商标？
- [ ] 方向与原型的**真实渲染**一张都没少（生成图是额外的，不是替代）？
- [ ] `check.py --root <feature_dir>` 退出 0？
