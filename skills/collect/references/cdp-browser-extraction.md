# CDP Browser Extraction — 从受控浏览器提取网页数据与资产

浏览器内存可读，不等于有权把第三方作品入库。先遵守 [collect/SKILL.md](../SKILL.md) 的来源访问合同，以及停在别人的作品前：遇登录或权限门控不得绕过控制。下面只用于已经授权、页面已按合同打开的会话。

适用场景：在上述边界内，从已登录、有访问限制或内容虚拟化的网页提取本产品有权保存的结构化数据、图片与文档时，通过 Chrome DevTools Protocol（CDP）控制浏览器实例完成采集。

## 启动受控浏览器

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --user-data-dir="$HOME/.sdlc-chrome-profile" \
  --remote-debugging-port=9222 \
  --no-first-run --no-default-browser-check \
  "https://target.example.com"
```

专用 `--user-data-dir` 保证登录态持久化且不影响日常浏览器。CDP 端口 9222 仅供本机访问。首次需人工登录；后续同一 profile 复用会话。

## 连接方式

Python venv 需安装 `websockets` 包。通过 `ws://127.0.0.1:9222/devtools/page/<TARGET_ID>` 连接具体页面。

```python
import json, urllib.request, websockets

targets = json.load(urllib.request.urlopen('http://127.0.0.1:9222/json/list'))
page = next(t for t in targets if t['type'] == 'page' and 'target' in t['url'])
ws = await websockets.connect(page['webSocketDebuggerUrl'], max_size=64*1024*1024)
```

## 核心采集技巧

### 1. 从已授权会话里已渲染的 blob URL 提取图片

飞书、Notion 等虚拟化长文档的图片存在 blob URL 中，`Page.getResourceContent` 取不到。解决：**从资源树枚举 blob URL，再在页面上下文 fetch**。

```python
# 第一步：枚举全部 blob URL
r = await call('Page.getResourceTree')
resources = r['result']['frameTree']['resources']
blob_urls = [res['url'] for res in resources
             if res['url'].startswith('blob:') and 'image' in res.get('mimeType','')]

# 第二步：逐个 fetch → base64 落盘
for u in blob_urls:
    expr = f"(async()=>{{const r=await fetch('{u}');const b=await r.arrayBuffer();"
           f"const t=new Uint8Array(b);let s='';"
           f"for(let j=0;j<t.length;j+=32768)s+=String.fromCharCode.apply(null,t.subarray(j,j+32768));"
           f"return JSON.stringify({{n:b.byteLength,type:r.type,b64:btoa(s)}})}})()"
    r2 = await call('Runtime.evaluate', {'expression':expr,'awaitPromise':True,'returnByValue':True})
    # base64 decode → 写文件
```

在一次已授权会话里，页面已经渲染的 blob 曾一次观察到 124 张。这只说明当时内存里已有这些资源，不是绕过登录墙的通用手段，也不能据此入库未授权的第三方作品。

### 2. 网络捕获（API 逆向）

启用 Network 域 → 重载页面 → 收集 XHR/Fetch 请求 → 逐个取响应体。

```python
await call('Network.enable')
await call('Page.navigate', {'url': page_url})
# 等待 + 收集 requestWillBeSent / responseReceived 事件
# 对 XHR 请求：await call('Network.getResponseBody', {'requestId': rid})
```

### 3. 虚拟化文档文本提取

长文档只渲染可视区。存在来源块模型与续读游标时，必须读取完整块模型，见 [collect/SKILL.md](../SKILL.md)「Virtualized DOM slices are not the full document」。不得把滚动后拼接的 `innerText` 当作完整文档，也不得混入阅读器画廊、菜单或相关链接。

### 4. Service Worker 处理

部分站点注册 SW 阻挡 CDP 工具。注销方法：

```python
await call('ServiceWorker.unregister', {'scopeURL': 'https://target.com/'})
await call('Storage.clearDataForOrigin', {'origin': 'https://target.com', 'storageTypes': 'service_workers'})
await call('ServiceWorker.stopAllWorkers')
```

### 5. Shell 沙箱无外网

macOS 沙箱环境下 curl/wget 无外网。一切外部 HTTP 通过 CDP 页面上下文 fetch 完成。

### 6. 硬准出红线：UI 点击成功 ≠ 数据获取成功（DOM 交互与底层载荷回执解耦）

前端按钮可点击、Tab 切换动画完成或列表滚动未抛异常，**绝不代表底层数据获取成功**——现代单页应用常在点击成功后静默吞掉底层 XHR/Fetch 的 HTTP `403`/`429`/`5xx`，或返回 HTTP `200` 但携带业务风控/权限/会话过期 JSON（如 `{"code": 40301, "msg": "forbidden"}`、空壳错包）。采集器准出必须通过以下硬校验：

1. **网络层与业务层双回执绑定**：每次触发点击、筛选切换或翻页后，必须通过 `Network.responseReceived` + `Network.getResponseBody` 关联本次动作对应的底层 API 响应，同时校验 HTTP 状态码（`2xx`）、业务 JSON 状态码、Schema 完整性以及实体/地区上下文回显（与活跃断点/租约一致），严禁仅凭 DOM 点击无报错即推进采集断点。
2. **失败请求结构化入重试/死信队列**：一旦拦截到被成功点击掩盖的 HTTP `403`/`429`/`5xx` 或业务错误 JSON，严禁静默跳过或标为 `confirmed-empty`；必须将**结构化 `error_code`、`request_id`（服务端 `trace_id` 或 CDP `requestId`）及 `retryable`（`true/false`）标记**持久化写入重试/死信队列（`retry_queue` / `dlq`），并按 [collection-recovery.md](collection-recovery.md) 执行退避、会话暂停或告警。

## 图片后处理管道

1. **尺寸过滤**：<200×120 的多为 UI 图标，筛除
2. **MD5 去重**：内容哈希去重，避免同一图不同 URL
3. **语义命名**：按内容重命名（`video_upscale_sample.png` 优于 `blob_01.png`）
4. **本地存储**：一律落盘到项目 assets/ 目录，不保留 URL 引用

## 图标级比对（UI 一致性审计）

SVG 路径级比对只判断视觉或几何图标是否相同。路径相同或不同都不代表点击功能等价；功能等价必须对每个控件执行 click → observe，见 [debug/SKILL.md](../../debug/SKILL.md) 与 [findings/SKILL.md](../../findings/SKILL.md)。三遍视觉判读可能给出三个不同答案，路径字符串可以核对几何：

```python
# 从 DOM 提取每个按钮的 SVG path d 属性
paths = {label: [p.getAttribute('d') for p in btn.querySelectorAll('svg path')]
         for label, btn in buttons.items()}
# 精确字符串比较
```

视觉相似（"竖向圆角轮廓+内部细节"族）≠ 路径相同。报告里分开写「路径相同」「剪影相似」和每个控件 click → observe 的结果。

## 常见坑

| 坑 | 解法 |
|---|---|
| SVG 元素的 `offsetParent` 返回 null | 用 `getBoundingClientRect().width > 0` 判断可见性 |
| JS 模板字符串嵌 MD 内容 | 反引号打断模板字面量；改为服务端渲染 |
| `Page.captureScreenshot` 返回 200KB+ | 用 `clip` 参数截取区域；或设 `Emulation.setDeviceMetricsOverride` 缩小视口 |
| 登录墙 | 暂停受影响操作。只使用已经授权的会话，不得用 blob 资源池绕过登录或权限门控 |
