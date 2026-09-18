# 分层与契约映射

## 为什么分层依赖必须单向

`Router → Service → Repository → ORM`

单向的收益不是「代码好看」，是三件具体的事：

1. **可测**：Service 能脱离 HTTP 测（不用起服务器），Repository 能脱离业务测
2. **可换**：换 Web 框架只动 Router 层；换 ORM 只动 Repository 层
3. **变更影响可预测**：改表结构影响止于 Repository，不会传到 API 响应

违规的具体代价：

| 违规 | 代价 |
|---|---|
| Router import ORM | 改表字段名 → API 响应字段跟着变 → 前端崩。且序列化行为不可控（懒加载触发意外查询） |
| Service 返回 ORM 对象 | 同上，且 ORM 对象脱离 session 后访问关联字段会报错 |
| Repository 调 Service | 循环依赖，无法单独测试 Repository |
| Service 里写 SQL | 数据访问逻辑散落，换存储时找不全 |

## 契约到代码的完整映射

以 `POST /api/v1/exports` 为例，逐项落位。

### 契约片段

```
POST /api/v1/exports
Header: Idempotency-Key (required, UUID, 24h)
Body: { filter: {status[], created_from, created_to, assignee_ids[]},
        format: "csv", columns[] }
校验: created_to ≥ created_from 且区间 ≤ 90 天
      columns 白名单，1–20 个
      assignee_ids 最多 50 个；客服只能填自己的 ID
响应: 200（同步完成）/ 202（转异步）
错误: 400 INVALID_PARAM / 403 FORBIDDEN_SCOPE
      409 EXPORT_IN_PROGRESS / 422 ROW_LIMIT_EXCEEDED
```

### 落位表

| 契约元素 | 落在哪 | 具体做法 |
|---|---|---|
| 路径、方法、202/200 区分 | Router | 根据 Service 返回的 status 决定状态码 |
| 字段类型、必填、枚举、长度 | Schema | 声明式校验器 |
| `created_to ≥ created_from`、区间 ≤ 90 天 | Schema | 跨字段校验器（同一层，因为是纯参数约束） |
| `columns` 白名单 | Schema | 枚举校验 |
| **客服只能填自己的 ID** | **Service** | 需要知道当前用户角色 = 业务规则，不是参数约束 |
| 「已有进行中任务」→ 409 | Service | 查询 + 抛业务异常 |
| 行数预估 → 走同步还是异步 | Service | 业务决策 |
| 幂等（同 key 返回首次结果） | Service + 唯一约束 | 见下文 |
| 数据查询与写入 | Repository | |
| 业务异常 → HTTP 状态码 + code | 统一异常处理器 | 不在 Router 里逐个 try/except |

**「客服只能填自己的 ID」这条的归属值得注意**：它看起来像参数校验，但需要当前用户的角色信息，所以属于业务规则，归 Service。Schema 层不该知道「谁在调用」。

### 代码骨架

```python
# schemas/export.py —— 只管协议形状，不含业务
class ExportFilter(BaseModel):
    status: list[TicketStatus] | None = None
    created_from: date | None = None
    created_to: date | None = None
    assignee_ids: list[int] | None = Field(None, max_length=50)

    @model_validator(mode="after")
    def check_date_range(self):
        if self.created_from and self.created_to:
            if self.created_to < self.created_from:
                raise ValueError("created_to must be >= created_from")
            if (self.created_to - self.created_from).days > 90:
                raise ValueError("date range must be <= 90 days")
        return self

class ExportCreateRequest(BaseModel):
    filter: ExportFilter
    format: Literal["csv"]
    columns: list[ExportColumn] = Field(min_length=1, max_length=20)

class ExportResponse(BaseModel):        # 与 ORM 无 import 关系
    export_id: str
    status: ExportStatus
    row_count: int | None = None        # 契约里标了可空的，这里也可空
    file_url: str | None = None
    expires_at: datetime | None = None
    created_at: datetime


# routers/export.py —— 只做协议转换
@router.post("/exports", responses={200: {...}, 202: {...}})
async def create_export(
    body: ExportCreateRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    current_user: Annotated[User, Depends(get_current_user)],
    svc: Annotated[ExportService, Depends()],
    response: Response,
) -> ExportResponse:
    result = await svc.create(
        actor=current_user, req=body, idempotency_key=idempotency_key
    )
    response.status_code = 200 if result.status == ExportStatus.COMPLETED else 202
    return ExportResponse.model_validate(result, from_attributes=True)
    # 注意：这里是从 Service 返回的 DTO 转换，不是从 ORM 对象转换


# services/export.py —— 业务规则唯一归属地
class ExportService:
    async def create(self, actor, req, idempotency_key) -> ExportResult:
        logger.info("export.create.start",
                    actor_id=actor.id, format=req.format,
                    column_count=len(req.columns))   # 入口日志，脱敏

        # 幂等：先试唯一约束，重复则返回首次结果
        existing = await self.repo.find_by_idempotency_key(idempotency_key)
        if existing:
            return self._to_result(existing)

        # 业务规则：数据范围权限（需要角色信息，所以在这一层）
        scope = self._resolve_scope(actor, req.filter)

        # 业务规则：并发任务限制 → 409
        if await self.repo.exists_in_progress(actor.id):
            raise ExportInProgressError()

        estimated = await self.repo.estimate_rows(scope)
        if estimated > SYNC_THRESHOLD and not ASYNC_ENABLED:
            raise RowLimitExceededError(limit=SYNC_THRESHOLD, actual=estimated)

        try:
            task = await self.repo.create_task(
                actor_id=actor.id, scope=scope,
                columns=req.columns, idempotency_key=idempotency_key,
            )
        except UniqueViolation:                    # 并发下另一个请求先插入了
            existing = await self.repo.find_by_idempotency_key(idempotency_key)
            return self._to_result(existing)      # 幂等：返回首次结果

        if estimated <= SYNC_THRESHOLD:
            return await self._run_sync(task)
        await self._enqueue(task)                 # 事务已提交后才入队
        return self._to_result(task)

    def _resolve_scope(self, actor, filter_):
        """客服只能查自己负责的（FR-04）"""
        if actor.role == Role.SUPERVISOR:
            return Scope(group_id=actor.group_id, **filter_.model_dump())
        requested = set(filter_.assignee_ids or [])
        if requested - {actor.id}:
            raise ForbiddenScopeError("只能导出自己负责的工单")
        return Scope(assignee_ids=[actor.id], **filter_.model_dump(exclude={"assignee_ids"}))
```

## 统一异常处理

**不要在每个 Router 里 try/except。** 业务异常定义一次，处理器映射一次。

```python
# exceptions.py
class BizError(Exception):
    http_status: int
    code: str
    def __init__(self, message: str = "", **detail):
        self.message = message or self.__doc__
        self.detail = detail

class ForbiddenScopeError(BizError):
    """权限不足"""
    http_status, code = 403, "FORBIDDEN_SCOPE"

class ExportInProgressError(BizError):
    """已有导出任务进行中"""
    http_status, code = 409, "EXPORT_IN_PROGRESS"

class RowLimitExceededError(BizError):
    """超出行数上限"""
    http_status, code = 422, "ROW_LIMIT_EXCEEDED"


# main.py
@app.exception_handler(BizError)
async def biz_error_handler(request, exc: BizError):
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message,
                 "detail": exc.detail or None,
                 "trace_id": get_trace_id()},
    )

@app.exception_handler(Exception)                 # 兜底：5xx 必带 trace_id
async def unhandled_handler(request, exc):
    trace_id = get_trace_id()
    logger.exception("unhandled", trace_id=trace_id, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR",
                 "message": "服务暂时不可用，请稍后重试",
                 "trace_id": trace_id},
    )
```

**5xx 的 message 不要暴露内部细节**（堆栈、SQL、内部服务名）——那是给攻击者的信息。细节进日志，客户端只拿 `trace_id`。

## 契约对齐自检

实现完成后，逐项对照契约核对。**这一步能挡掉绝大多数联调冲突：**

- [ ] 所有响应字段名与契约一致（大小写、下划线/驼峰）
- [ ] 契约标可空的字段，实现里真的可能为 null
- [ ] 契约标不可空的字段，实现里保证不为 null
- [ ] 集合类字段空时返回 `[]` 不是 `null`
- [ ] 每个契约错误码都有代码路径能触发
- [ ] 没有契约之外的错误码（多出来的前端不认识）
- [ ] 时间字段格式为 ISO 8601 UTC
- [ ] 分页默认值与上限与契约一致
- [ ] 幂等行为与契约一致（重复请求返回首次结果还是 409）
- [ ] 状态枚举值拼写与契约、`db-spec`、`/qa` 用例三处一致

**「多出来的错误码」是隐蔽问题**：前端只处理了契约里列的，多出来的会走到 default 分支显示「未知错误」。新增错误码要回 `/architect` 更契约。

## 配置分层

```
config/
  base.py        # 默认值与结构定义
  local.py       # 本地开发
  test.py        # 测试
  prod.py        # 生产（值来自环境变量，不写在代码里）
```

三条纪律：

- **代码里零硬编码**：连接串、密钥、端口、外部地址、超时值、阈值
- **密钥只从环境变量或密钥管理服务读**，不进版本库（`.env` 要在 `.gitignore` 里）
- **启动时校验配置完整性**：缺关键配置就快速失败，不要等第一个请求进来才报错

阈值类配置（如 `SYNC_THRESHOLD = 10000`）也走配置——它会被调，调的时候不该改代码发版。
