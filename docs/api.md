# API 参考

实现依据：[扫雷网官方开放 API 文档](https://saolei.wang/page/api)，核对日期 2026-10-26。
5 个公开 GET 接口均使用 `X-Api-Key`，根地址为 `https://saolei.wang/api/public/v1/`。

## 客户端

```python
Client(api_key, *, timeout=30.0, min_interval=2.0, download_interval=0.4, transport=None)
AsyncClient(api_key, *, timeout=30.0, min_interval=2.0, download_interval=0.4, transport=None)
```

HTTP 连接由 [HTTPX](https://www.python-httpx.org/) 管理并复用；
模型校验与字段别名由 [Pydantic](https://docs.pydantic.dev/latest/) 提供。
不自行实现 HTTP 协议或 JSON 类型校验。

`timeout` 是 HTTPX 各网络操作的超时秒数，必须为正的有限数。
`min_interval` 是同一实例相邻请求开始时间的最小间隔秒数，必须为非负有限数。
默认 2 秒，即每实例至多约 30 次/分钟，符合官方对同步的建议。
测试可使用 `min_interval=0` 和 `httpx.MockTransport`。
`download_interval` 为相邻文件下载请求的最小间隔，默认 0.4 秒，独立于数据接口。
该参数必须为非负有限数；MockTransport 测试可设置为 0。
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
| `video_list(*, cursor=None, since=None, level=None, player_id=None, size=200)` | `cursor`、`since` 为非负整数；`level` 为 `beg` / `int` / `exp`；`player_id` 为正整数；`size` 为 1–1000 | `VideoListResponse` |
| `video_info(ids)` | 正整数或 1–50 个正整数的序列 | `VideoInfoResponse` |
| `user_info(ids)` | 正整数或 1–50 个正整数的序列 | `UserInfoResponse` |
| `user_list(ids)` | 正整数或 1–100 个正整数的序列 | `UserListResponse` |
| `iter_videos(*, cursor=None, since=None, level=None, player_id=None, size=200, max_pages=None)` | 同 `video_list`，`max_pages` 为正整数或 `None` | `Iterator[Video]` / `AsyncIterator[Video]` |
| `download_videos(suffixes)` | `YYYY/MM/DD/filename` 字符串序列 | `list[bytes]` |

无效参数在发送请求前抛出 `ValueError` / `TypeError`。布尔值不作为整数 ID 或游标接受。
批量参数不自动分组或试探缺失 ID，每次方法调用发送一个请求。
`download_videos` 每个文件发送一个 GET 请求；完整行为见下方批量下载说明。

`video_list` 按 ID 升序返回全部审核状态的录像：`status=0` 已屏蔽、`10` 待审、`20` 已通过。
客户端不按审核状态过滤，调用方如需已通过录像可筛选 `video.status == 20`。
`player_id` 限定玩家 ID，必须是大于 0 的整数；省略时不限制玩家，不能传入布尔值。
首次可不传游标；`since` 过滤早于指定 Unix 秒上传的录像。
两者同时提供时，官方定义 `cursor` 优先。
`iter_videos` 在后续请求中使用服务端 `nextCursor`，去掉 `since`，保留 `player_id`、`level` 和 `size`。
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
| `status` | `status` | 录像列表 / 详情共有的审核状态整数，0=已屏蔽、10=待审、20=已通过 |
| `fileUrl` | `file_url` | 录像文件的 `YYYY/MM/DD/filename` 后缀 |
| `beg3bvs` / `sum3bvs` 等 | `beg_3bvs` / `sum_3bvs` 等 | 玩家简表的 3BVS 成绩 |

- `StatsResponse`：`generated_at`、`stats: SiteStats`、`max_video_id`、`max_user_id`。
- `VideoListResponse`：`cursor`、`next_cursor`、`has_more`、`size`、`generated_at`、`items: list[Video]`。
- `VideoInfoResponse`：`generated_at`、`items: list[VideoInfo]`。
- `UserInfoResponse`：`generated_at`、`users: list[UserInfo]`。
- `UserListResponse`：`generated_at`、`users: list[UserSummary]`。

`Video` 和 `VideoInfo` 都包含必需的 `status: int`；未知状态整数也会保留。
`VideoInfo` 在 `Video` 上增加 `signature`、`metrics`、`file_url`。
无回放指标时 `metrics=None`；指标中的 `cl`、`cl_left`、`cl_right`、`cl_double`、`ce`、
`path`、`ioe`、`stnb` 均可为空。`signature` / `file_url` 也接受 `None`。
其他未知指标仍会在模型和 JSON 导出中保留。

自 v0.2.0 起，`file_url` 将官方完整 URL 转成 `YYYY/MM/DD/filename`，
例如 `2025/07/31/6d58634fbe0987003dda90f4a68944a7.avf`。
官方 `/videos/` 相对路径和已转换的后缀也可被模型接受，`None` 保持不变。
`model_dump()`、`model_dump(by_alias=True)` 和 JSON 导出都只返回后缀，不恢复完整 URL。
已有调用方如需下载，应将这些后缀传入 `download_videos`。

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

## 录像文件批量下载

```python
suffixes = [
    "2025/07/31/6d58634fbe0987003dda90f4a68944a7.avf",
    "2007/01/05/example.mvf",
]
files = api.download_videos(suffixes)  # 异步客户端使用 await
```

输入必须是后缀序列，不能传单个字符串、完整 URL 或带 `/videos/` 的路径。
每个后缀必须包含有效的四位年份、两位月份、两位日期和文件名；
文件名接受英文字母、数字、下划线、连字符和点，首字符必须为字母或数字。
路径跳转、反斜杠、查询参数、片段和编码路径均不接受。
整批输入在第一个请求前完成校验，避免下载半批后才发现参数错误。

客户端将后缀拼接到固定的 `https://saolei.wang/videos/` 并逐个 GET，
复用已有 HTTPX 连接，使用同站点的 API key；不跟随重定向。
同步返回 `list[bytes]`，异步 `await` 后也返回 `list[bytes]`。
结果按输入顺序排列，保留重复项；空序列不请求网络并返回 `[]`。
文件全部读入内存，不自动落盘；内存占用随本批文件总大小增长。

下载默认每 0.4 秒开始一个请求，使用独立于数据接口的计时器。
同一实例的不同批次共享下载计时器，数据查询仍维持原有 2 秒间隔。
该节流只覆盖当前实例，官方文件下载上限为全站 3 次/秒，多个实例 / 进程仍需协调。
首个失败请求会立即抛出与数据接口一致的异常，`endpoint` 为 `videos/<后缀>`；
后续文件不会请求，不自动重试，也不返回已下载部分。
异步取消会立即传播并释放等待锁，不影响客户端后续使用。

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
本包只访问上述 5 个 API 和官方文档提供的录像文件，不使用网页、登录接口或未公开端点。
`file_url` 后缀由 API 提供，`download_videos` 遵守单实例默认下载间隔；全局额度由调用方协调。
引用数据请标注 **扫雷网 saolei.wang**；API key 应通过环境变量或应用秘密管理传入。

离线样本位于 `tests/fixtures/`，来自官方文档示例，数据来源为扫雷网。
真实验证工具为 `tools/verify_live.py`，最多 10 次只读 API 请求，包含玩家筛选、分页和最近录像状态验证。
列表中的已屏蔽录像不会传给省略这些录像的详情接口，必要时使用官方示例 ID 验证详情，不执行 ID 扫描。
增加 `--download-videos` 可额外验证最多 4 次录像文件下载（同步 / 异步各最多 2 个）。
