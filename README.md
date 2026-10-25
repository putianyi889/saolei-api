# saolei-api

[![CI](https://github.com/putianyi889/saolei-api/actions/workflows/ci.yml/badge.svg)](https://github.com/putianyi889/saolei-api/actions/workflows/ci.yml)

扫雷网 [saolei.wang](https://saolei.wang/) 官方开放 API 的 Python 客户端。
完整支持 [官方文档](https://saolei.wang/page/api) 中的 5 个只读接口，
提供同步 / 异步调用、Pydantic 类型模型、录像分页迭代和请求节流。
Python 3.11+，包名 `saolei-api`，导入名 `saolei_api`。

## 安装

从 [GitHub Release](https://github.com/putianyi889/saolei-api/releases/latest) 安装：

```sh
python -m pip install "https://github.com/putianyi889/saolei-api/releases/download/v0.1.0/saolei_api-0.1.0-py3-none-any.whl"
```

也可以从源码安装：

```sh
python -m pip install "git+https://github.com/putianyi889/saolei-api.git@v0.1.0"
```

本项目发布到 GitHub Releases，尚未发布到 PyPI。

## 快速开始

API key 由扫雷网站长签发。将自己的 key 放入 `SAOLEI_API_KEY` 环境变量，
不要写入源码。客户端使用 `X-Api-Key` 请求头认证。

```python
import os
from saolei_api import Client

with Client(os.environ["SAOLEI_API_KEY"]) as api:
    stats = api.stats()
    print(stats.stats.user_total, stats.max_video_id)

    user = api.user_info(1).users[0]
    print(user.name, user.scores.exp.time)  # 毫秒

    videos = api.video_list(level="exp", size=10)
    for video in videos.items:
        print(video.id, video.real_time, video.three_bvs)

    detail = api.video_info(328090).items[0]
    print(detail.file_url, detail.metrics)
```

异步调用：

```python
import asyncio
import os
from saolei_api import AsyncClient


async def main():
    async with AsyncClient(os.environ["SAOLEI_API_KEY"]) as api:
        users = await api.user_list([1, 2])
        for user in users.users:
            print(user.name, user.scores.sum_time)


asyncio.run(main())
```

## 接口

| Python 方法（同步 / 异步同名） | 官方 GET 接口 | 返回模型 |
| --- | --- | --- |
| `stats()` | `/api/public/v1/stats` | `StatsResponse` |
| `video_list(cursor=None, since=None, level=None, size=200)` | `/api/public/v1/video_list` | `VideoListResponse` |
| `video_info(ids)` | `/api/public/v1/video_info` | `VideoInfoResponse` |
| `user_info(ids)` | `/api/public/v1/user_info` | `UserInfoResponse` |
| `user_list(ids)` | `/api/public/v1/user_list` | `UserListResponse` |

`ids` 接受单个正整数或整数序列。录像详情 / 玩家详情每次最多 50 个 ID，
玩家列表最多 100 个；不存在或不可公开的数据以服务端返回为准，不保证每个 ID 都有对应结果。

## 分页与增量

```python
with Client(os.environ["SAOLEI_API_KEY"]) as api:
    # 惰性获取，最多两页。省略 max_pages 会迭代到服务端 hasMore=false。
    for video in api.iter_videos(since=1790000000, size=200, max_pages=2):
        print(video.id)

    # 需要持久化断点时，直接获取分页响应。
    page = api.video_list(cursor=0, size=200)
    print(page.next_cursor, page.has_more)
```

异步分页使用 `async for video in api.iter_videos(...)`。
`since` 为 Unix 秒；同时传入 `cursor` 时，服务端以 `cursor` 为准。
迭代器首次请求使用给定筛选条件，后续仅保留游标、难度与页大小。
全量同步前可用 `stats().max_video_id` / `max_user_id` 确定范围，避免试探 ID。

## 数据与错误

- 属性使用 snake_case；`3bvs` 对应 `three_bvs`，`board3bv` 对应 `board_3bv`。
- 保留上游原值：时间戳为 Unix 秒，成绩时间为毫秒，3BVS 为官方整数表示，包含负值标记。
- `model_dump(by_alias=True)` / `model_dump_json(by_alias=True)` 可恢复官方字段名称；额外字段会保留。
- 无回放指标时 `metrics` 为 `None`。空结果返回空列表。
- 默认超时 30 秒，同一客户端请求开始时间至少间隔 2 秒；多个客户端 / 进程须自行协调共享额度。
- 401 / 403 抛出 `AuthenticationError`；429 抛出 `RateLimitError`，可读取 `retry_after` 秒数。
- 其他 HTTP 错误抛出 `APIError`，网络错误抛出 `TransportError`，格式或分页异常抛出 `ResponseError`。
- 不自动重试。应用可按 `Retry-After` 和自身任务调度恢复。请求不会自动跟随重定向。

详细参数、模型、错误处理和同步限制见 [API 参考](docs/api.md)。

## 开发与发布

```sh
python -m venv .venv
# 激活虚拟环境后执行：
python -m pip install -e ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest --cov=saolei_api --cov-report=term-missing
python -m build
python -m twine check dist/*
```

离线测试使用 HTTPX MockTransport，不需要真实 key，不访问网站。
设置 `SAOLEI_API_KEY` 后，可运行 `python tools/verify_live.py`：
最多 8 次只读 API 请求，验证全部接口、两页分页和异步访问。CI 不运行真实请求。
这是纯 Python 项目，无 ESLint 或 Cypress 测试。

推送与包版本一致的标签（如 `v0.1.0`）会运行完整 CI，
随后将 wheel、sdist、文档压缩包和 `SHA256SUMS` 发布到 GitHub Release。

## 数据来源与许可

数据来源：**扫雷网 saolei.wang**。引用数据时请注明来源并遵守
[官方 API 使用说明](https://saolei.wang/page/api)。
功能限于官方开放 API；录像详情提供官方 `fileUrl`，本包不抓取站内页面。
代码采用 [MIT](LICENSE) 许可，数据使用要求以扫雷网规定为准。本包为第三方客户端。

