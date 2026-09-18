# 反爬升级策略

## 判定：被哪种方式拦截

| 症状 | 拦截方式 | 应对 |
|---|---|---|
| HTTP 403 / 429 | IP 封禁或频率限制 | 降速 → 代理 → 换 IP 池 |
| HTTP 200 但内容是验证码 | 软拦截（JS 挑战） | Splash/Playwright 渲染 → 验证码服务 |
| HTTP 200 但内容与预期不同 | 内容混淆/动态加载 | 检查 API 端点 → Playwright 渲染 |
| 返回空数据但无错误 | 蜜罐或内容指纹检测 | 检查 UA/Cookie/请求头完整性 |
| 连接被重置 | TCP 层封禁 | 换 IP → 降低并发 → 检查 TLS 指纹 |

## 升级顺序（成本递增）

1. **速率控制**: DOWNLOAD_DELAY ≥ 1s, AUTOTHROTTLE_ENABLED = True
2. **UA 轮换**: 中间件 + 真实 UA 池（10+ 个，含移动端）
3. **Cookie 管理**: 登录获取会话，维持有效 Cookie
4. **代理池**: 住宅代理 > 数据中心代理；按目标站点封禁策略选择
5. **JS 渲染**: Splash 或 Playwright（成本高，仅 JS 渲染页面使用）
6. **验证码服务**: 2captcha / anti-captcha（最后手段，按次计费）

## 每级的关键配置

### Scrapy settings.py
```python
# 基础（第 1-2 级）
DOWNLOAD_DELAY = 2
AUTOTHROTTLE_ENABLED = True
USER_AGENT = '<从 UA 池随机>'

# 代理（第 4 级）
HTTPPROXY_TUNNELING = True
HTTP_PROXY = 'http://user:pass@proxy:port'
```

### 中间件顺序
```python
DOWNLOADER_MIDDLEWARE = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': 400,
    'myproject.middlewares.UARotationMiddleware': 400,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 550,
    'myproject.middlewares.ProxyMiddleware': 750,
}
```

## 监控

- 连续 3 次零条目 → 告警（可能被封）
- 成功率 < 80% → 告警
- 响应时间 > 10s → 告警（可能被限速）

## 数据源适配

| 源类型 | 提取方式 | 注意 |
|---|---|---|
| 静态 HTML | CSS/XPath 选择器 | 检查 robots.txt |
| JSON API | 直接解析 JSON | 检查认证要求 |
| JS 渲染页面 | Splash/Playwright | 成本高，确认必要 |
| RSS/Atom | feedparser | 最友好的方式 |
| 分页 | URL 模式 or AJAX 端点 | 检查是否有 API 可直接调用 |
