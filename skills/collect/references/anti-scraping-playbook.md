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

### 模式 E：账号池（登录态采集的生产形态）

来源允许多账号访问、业务确有需要时，按批准的账号与共享访问预算设计账号池；不能用换号绕过来源限制：

- **存储**：Redis HASH（账号标识 → 凭据），凭据不进代码库
- **配额**：每账号每日上限；计数键带「账号 + 日期」，惰性初始化 + TTL
- **租约**：`SET ... NX EX` 只是领取原语；定义所有者 token、期限、续租/到期回收及旧持有者停止/提交校验。超出使用窗口仍在运行时，不能仅凭抢锁成功保证多机独占
- **失效**：用响应和会话证据区分凭据过期、权限拒绝与访问限制；停止依赖失效账号的操作，按授权路径恢复。保留任务或按协议移交，不自动换号重试
- **预算**：按来源约定和观测分开记录查询、点击等实际操作；不能由状态码或随机节奏推断平台机制。关键账本失效停止依赖操作，普通统计失败按契约降级

## 失败分类：不是所有失败都重试

一律重试会放大异常行为（多 Worker 共享账号时尤其如此）。先分类，再处置：

| 失败类别 | 特征 | 处置 |
|---|---|---|
| 验证码 / 访问限制 | 核对页面、响应与共享账号/IP；不能只凭状态码判定 | 保留任务；暂停受影响操作，按访问约定及明确恢复条件处理 |
| 任务数据错误 | 条目本身缺字段或非法 | 死信队列，人工介入；不重试 |
| 页面结构变化 | 选择器/接口字段大面积取空 | **零重试**，立即告警修解析——重试只会用请求量放大事故 |
| 资源故障 | 本地浏览器 / Redis / 网络不可用 | 上抛暂停，指数退避探测恢复；与目标站反爬无关，别计入风控 |
| 未知异常 | 未归类 | 保留现场与任务，先判断副作用及影响范围，再选择有界恢复；不默认重放页面动作 |

**切换以独立性为前提**：只有候选任务不依赖受限账号、会话、IP 或故障账本时才继续调度。部分交付与新鲜度取舍依批准需求确定，不能为了切类型继续而放大共享故障。暂停期限、当天淘汰和次日恢复均为项目策略。

**登录失效不暴力重登**：频繁重新登录本身就是风控信号。开一个有限时长窗口等待人工恢复（或换号），超时再休眠到次日。

## 浏览器自动化的拟人要点

需要真实浏览器（登录态 / JS 渲染）时，按实际页面操作和访问预算选择交互方式；随机动作本身不能证明反检测效果：

- **轨迹一致**：点击必须落在鼠标移动到达的同一个点——「移到 A、点击 B」是典型机器特征；进程内记住上次指针位置，连续操作不瞬移
- **交互契约**：项目要求原生点击时，坐标失败应修定位并验证事件，不能静默换成 JS 点击改变行为；其他自动化任务按页面契约选择方式，不设通用点击禁令
- **节奏拟人**：移动 / 滚动 / 输入带随机时长；滚动分段 + 段间停顿 + 中段偶发「阅读停顿」；单次操作完成后停留数秒再继续
- **UA 与会话绑定**：同一 Cookie / 账号会话内轮换 UA 本身是可疑特征；UA 池要和账号绑定，而不是每请求随机

## 监控与告警

| 指标 | 阈值 | 动作 |
|---|---|---|
| 连续 3 次零条目 | 告警 | 检查是否被封 |
| 成功率 < 80% | 告警 | 检查反爬升级 |
| 响应时间 P95 > 10s | 告警 | 降低并发或检查网络 |
| 429 频率 > 20% | 告警 | 立即降速 |
| 账号配额耗尽 | 已确认共享预算达上限 | 停止依赖操作，按窗口恢复；不通过换类型/账号绕过共享预算 |
| unsynced 积压持续增长 | 采集与落库脱节 | 检查同步程序；必要时暂停采集 |

告警本身要有纪律：分级（调试 / 运维 / 致命）、同类节流合并、发送失败不得阻塞采集主流程。零条目与积压的阈值按预期流量和新鲜度 SLA 定，不是通用计数。
