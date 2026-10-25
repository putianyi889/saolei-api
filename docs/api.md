# API 参考

实现依据：[扫雷网官方开放 API 文档](https://saolei.wang/page/api)，核对日期 2026-10-25。
5 个公开 GET 接口均使用 `X-Api-Key`，根地址为 `https://saolei.wang/api/public/v1/`。

## 客户端

```python
Client(api_key, *, timeout=30.0, min_interval=2.0, transport=None)
AsyncClient(api_key, *, timeout=30.0, min_interval=2.0, transport=None)
```

HTTP 连接由 [HTTPX](https://www.python-httpx.org/) 管理并复用；
模型校验与字段别名由 [Pydantic](https://docs.pydantic.dev/latest/) 提供。
不自行实现 HTTP 协议或 JSON 类型校验。

`timeout` 是 HTTPX 各网络操作的超时秒数，必须为正的有限数。
`min_interval` 是同一实例相邻请求开始时间的最小间隔秒数，必须为非负有限数。
默认 2 秒，即每实例至多约 30 次/分钟，符合官方对同步的建议。
测试可使用 `min_interval=0` 和 `httpx.MockTransport`。
节流是每实例的；共享 key 的多个实例、进程和服务必须自行协调。
同一个同步实例可在线程间使用；异步实例仅在一个事件循环内使用。

使用 `with Client(...)` / `async with AsyncClient(...)` 自动关闭连接，
或显式调用 `close()` / `await aclose()`。客户端关闭后不可复用。
不自动重试网络错误、429 或 5xx。异步取消会传播，不转换成网络异常。
不跟随 HTTP 重定向，避免将认证头传给其他地址。
自定义 transport 的生命周期由客户端管理。

## 方法与参数

异步版本的请求方法都需要 `await`；`iter_videos` 使用 `async for`。

| 方法 | 参数 | 响应 |
| --- | --- | --- |
| `stats()` | 无 | `StatsResponse` |
| `video_list(*, cursor=None, since=None, level=None, size=200)` | `cursor`、`since` 为非负整数；`level` 为 `beg` / `int` / `exp`；`size` 为 1–1000 | `VideoListResponse` |
| `video_info(ids)` | 正整数或 1–50 个正整数的序列 | `VideoInfoResponse` |
| `user_info(ids)` | 正整数或 1–50 个正整数的序列 | `UserInfoResponse` |
| `user_list(ids)` | 正整数或 1–100 个正整数的序列 | `UserListResponse` |
| `iter_videos(*, cursor=None, since=None, level=None, size=200, max_pages=None)` | 同 `video_list`，`max_pages` 为正整数或 `None` | `Iterator[Video]` / `AsyncIterator[Video]` |

无效参数在发送请求前抛出 `ValueError` / `TypeError`。布尔值不作为整数 ID 或游标接受。
批量参数不自动分组或试探缺失 ID，每次方法调用发送一个请求。

`video_list` 返回审核通过（status=20）的胜利录像，按 ID 升序排列。
首次可不传游标；`since` 过滤早于指定 Unix 秒上传的录像。
两者同时提供时，官方定义 `cursor` 优先。
`iter_videos` 在后续请求中使用服务端 `nextCursor`，去掉 `since`，保留 `level` 和 `size`。
服务端 `hasMore=false` 或达到 `max_pages` 时结束；停止消费即可停止请求。
`hasMore=true` 却未推进游标时抛出 `ResponseError`，防止无限循环。
分页不是数据库快照，数据可能在两次调用间改变。

`video_info` 可包含 status=10（待审）和 status=20（已通过）的公开录像；禁用录像不返回。
用户和录像批量响应不保证与输入 ID 的数量、顺序一致，请按返回对象的 `id` 建立映射。

## 模型

所有模型可从 `saolei_api` 导入，继承 `APIModel` / Pydantic `BaseModel`。
属性名为 snake_case；JSON 名称保留为别名。
额外字段使用 `extra="allow"` 保留；缺失必需字段或不兼容类型会触发 `ResponseError`。

| 官方字段 | Python 属性 | 说明 |
| --- | --- | --- |
| `generatedAt` | `generated_at` | 响应生成时间，Unix 秒 |
| `maxVideoId` / `maxUserId` | `max_video_id` / `max_user_id` | 增量同步 ID 上界 |
| `realTime` | `real_time` | 录像用时，毫秒 |
| `board3bv` | `board_3bv` | 盘面 3BV |
| `3bvs` | `three_bvs` | 官方整数形式的 3BVS，原样保留 |
| `3bvsVideoId` | `three_bvs_video_id` | 该成绩关联的录像 ID |
| `scoresNf` | `scores_nf` | NF 成绩体系 |
| `fileUrl` | `file_url` | 官方录像文件地址 |
| `beg3bvs` / `sum3bvs` 等 | `beg_3bvs` / `sum_3bvs` 等 | 玩家简表的 3BVS 成绩 |

- `StatsResponse`：`generated_at`、`stats: SiteStats`、`max_video_id`、`max_user_id`。
- `VideoListResponse`：`cursor`、`next_cursor`、`has_more`、`size`、`generated_at`、`items: list[Video]`。
- `VideoInfoResponse`：`generated_at`、`items: list[VideoInfo]`。
- `UserInfoResponse`：`generated_at`、`users: list[UserInfo]`。
- `UserListResponse`：`generated_at`、`users: list[UserSummary]`。

`VideoInfo` 在 `Video` 上增加 `status`、`signature`、`metrics`、`file_url`。
无回放指标时 `metrics=None`；指标中的 `cl`、`cl_left`、`cl_right`、`cl_double`、`ce`、
`path`、`ioe`、`stnb` 均可为空。`signature` / `file_url` 也接受 `None`。
其他未知指标仍会在模型和 JSON 导出中保留。

`UserInfo.scores` / `scores_nf` 包含 `beg`、`int`、`exp: LevelScore` 和 `sum: TotalScore`。
`LevelScore` 包含 `time`、`time_video_id`、`three_bvs`、`three_bvs_video_id`；
总成绩不包含录像 ID。`UserSummary.scores: SummaryScores` 是官方简表的 8 项平铺成绩。
录像 ID 为 0 时表示没有关联录像；`banned=True` 为官方公开的封禁标志。

### 单位

不转换时间、成绩、负值标志或缺失成绩的服务端占位值。
官方录像文档给出的 3BVS 公式为 `ROUND(board_3bv * 1e6 / real_time)`，
其中 `real_time` 单位为毫秒，因此整数 4900 对应 4.900 3BV/s。
负值表示小盘标志（初级 3BV<10、中高级 3BV<4），不能直接取绝对值后忽略其含义。
模型保留整数，便于和服务端数据精确对照。

`metrics` 使用站内 flop 的统计口径；`path` 按每格 16px 计算。
这些字段可能与其他网站或解析器的统计不同。

### 序列化

```python
result = api.user_info([1, 2])
python_data = result.model_dump()  # snake_case
upstream_data = result.model_dump(by_alias=True)  # 官方 JSON 字段名
json_text = result.model_dump_json(by_alias=True)
```

## 错误

| 异常 | 触发条件 | 可读取字段 |
| --- | --- | --- |
| `SaoleiError` | 包异常基类 | — |
| `AuthenticationError(APIError)` | HTTP 401 / 403 | `status_code`, `endpoint` |
| `RateLimitError(APIError)` | HTTP 429 | `status_code`, `endpoint`, `retry_after` |
| `APIError` | 其他非 2xx 状态，包括重定向 | `status_code`, `endpoint` |
| `TransportError` | HTTPX 连接、读取、超时等请求错误 | — |
| `ResponseError` | 无效 JSON、格式不兼容或不推进的游标 | — |

`retry_after` 可解析 HTTP `Retry-After` 的秒数或日期形式；缺失或不可解析时为 `None`。
异常消息不包含请求头、服务端响应正文或 key。HTTPX 的自定义日志仍由应用自行配置。

```python
from saolei_api import AuthenticationError, RateLimitError, SaoleiError

try:
    result = api.stats()
except AuthenticationError:
    print("请检查 API key")
except RateLimitError as exc:
    print("稍后重试，建议等待秒数：", exc.retry_after)
except SaoleiError as exc:
    print(exc)
```

## 使用边界

官方上限为每合作方 60 次/分钟，建议全量同步低于 30 次/分钟、增量同步每小时一次。
本包只访问上述 5 个 API，不使用网页、登录接口或未公开端点。
`file_url` 由 API 提供，应用如需下载，应遵守官方文件下载全站 3 次/秒限制。
引用数据请标注 **扫雷网 saolei.wang**；API key 应通过环境变量或应用秘密管理传入。

离线样本位于 `tests/fixtures/`，来自官方文档示例，数据来源为扫雷网。
真实验证工具为 `tools/verify_live.py`，只运行有限请求，不执行全量抓取。
