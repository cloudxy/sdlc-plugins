# 数据源分析模板

## 基本信息
- 目标站点：{URL}
- 数据类型：{HTML / JSON API / RSS / 需 JS 渲染}
- 更新频率：{实时 / 每小时 / 每日 / 每周}

## 技术分析
- robots.txt：{允许 / 禁止 / 部分允许}
- 反爬措施：{无 / UA 检测 / IP 封禁 / JS 渲染 / CAPTCHA / 指纹检测}
- 数据提取方式：{CSS 选择器 / XPath / JSON 解析 / Playwright}
- 分页方式：{URL 参数 / POST / 无限滚动}

## 数据 Schema
| 字段 | 类型 | 必填 | 提取方式（选择器/API 字段名） |
|---|---|---|---|
| url | string | ✅ | response.url |
| title | string | ✅ | CSS: h2::text |
| price | float | | CSS: .price::text → re_first(r'[\d.]+') |

## 采集策略
- DOWNLOAD_DELAY：{N}秒
- 并发：{N} 请求/域名
- 代理：{不需要 / 需要住宅代理 / 需要数据中心代理}
- JS 渲染：{不需要 / 需要 Playwright}
- 预计耗时：{N}分钟/全量

## 风险评估
-被封风险：{低/中/高}
-数据变化频率：{低/中/高}
-建议：{...}
