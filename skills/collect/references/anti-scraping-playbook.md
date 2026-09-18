# 反爬实战手册

## 反爬检测方式（按普遍程度排序）

### 1. 频率限制
最常见。N 秒内超过 M 次请求 → 429 或 IP 临时封禁。

**检测**：连续请求后返回 429，或响应时间突然变长（服务端故意延迟）。
**应对**：DOWNLOAD_DELAY + AUTOTHROTTLE + CONCURRENT_REQUESTS_PER_DOMAIN 降档。

### 2. User-Agent 检测
非浏览器 UA（如 `python-requests/2.x` 或 Scrapy 默认 UA）直接 403。

**检测**：浏览器能访问但爬虫 403。
**应对**：UA 轮换中间件 + 真实浏览器 UA 池。

### 3. IP 封禁
同一 IP 大量请求后 → 整个 IP 被封（403/超时/连接重置）。

**检测**：换 UA 仍然 403。换 IP 能访问。
**应对**：代理池（住宅 > 数据中心）。Scrapy 配置 `HttpProxyMiddleware`。

### 4. JS 渲染
数据不在 HTML 源码中，而是 JS 动态加载。直接爬 HTML 拿不到数据。

**检测**：`view-source:` 能看到 HTML 但没有数据；浏览器 DevTools Network 面板有 XHR 请求返回数据。
**应对**：优先找 API 端点（DevTools → Network → XHR），直接调 API 比渲染快得多。无法找到 API → Splash/Playwright。

### 5. CAPTCHA
登录或高频请求后出现验证码。

**检测**：页面含验证码图片或滑块。
**应对**：2captcha / anti-captcha（按次计费）。能绕过则绕过（登录 Cookie 保持），验证码是最后手段。

### 6. 指纹检测
TLS 指纹 / Canvas 指纹 / WebDriver 属性检测。爬虫的 TLS 握手与浏览器不同。

**检测**：UA、IP、Cookie 都正常但仍被拦截。
**应对**：curl_cffi（模拟浏览器 TLS 指纹）或 Playwright（真实浏览器环境）。

## 实战模式

### 模式 A：静态 HTML + CSS 选择器（最简单）

```python
def parse(self, response):
    for product in response.css('div.product-item'):
        yield {
            'name': product.css('h2::text').get(),
            'price': product.css('.price::text').re_first(r'[\d.]+'),
            'url': product.css('a::attr(href)').get(),
        }
```

### 模式 B：JSON API 直接调用（最稳定）

先用 DevTools Network 面板找 API 端点，然后直接调：

```python
def parse(self, response):
    # 不解析 HTML，直接调 API
    yield scrapy.Request(
        'https://api.example.com/products?page=1',
        callback=self.parse_api,
        headers={'Authorization': 'Bearer ...'},
    )

def parse_api(self, response):
    data = json.loads(response.text)
    for item in data['products']:
        yield { ... }
```

### 模式 C：JS 渲染页面（Playwright/Splash）

```python
# settings.py 开启 PLAYWRIGHT_ENABLED = True
# meta 传入 playwright 配置
def start_requests(self):
    yield Request(
        url,
        meta={'playwright': True, 'playwright_page_methods': [
            PageMethod('wait_for_selector', '.product-item'),
        ]},
    )
```

### 模式 D：登录 + Cookie

```python
def start_requests(self):
    yield Request(
        login_url,
        callback=self.after_login,
        method='POST',
        body=form_data,
    )

def after_login(self, response):
    # Cookie 已设置，继续爬
    yield Request(target_url, callback=self.parse)
```

## 监控与告警

| 指标 | 阈值 | 动作 |
|---|---|---|
| 连续 3 次零条目 | 告警 | 检查是否被封 |
| 成功率 < 80% | 告警 | 检查反爬升级 |
| 响应时间 P95 > 10s | 告警 | 降低并发或检查网络 |
| 429 频率 > 20% | 告警 | 立即降速 |
