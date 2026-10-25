import asyncio
import inspect

import httpx
import pytest

from saolei_api import (
    APIError,
    AsyncClient,
    AuthenticationError,
    Client,
    RateLimitError,
    ResponseError,
    TransportError,
)


class Harness:
    def __init__(self, asynchronous):
        self.requests = []
        self.responses = []
        self.asynchronous = asynchronous
        client_class = AsyncClient if asynchronous else Client
        self.client = client_class(
            "sk-test-only",
            min_interval=0,
            download_interval=0,
            transport=httpx.MockTransport(self.handle),
        )

    def handle(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def call(self, method, *args, **kwargs):
        result = getattr(self.client, method)(*args, **kwargs)
        return await result if inspect.isawaitable(result) else result

    async def videos(self, **kwargs):
        result = self.client.iter_videos(**kwargs)
        return [video async for video in result] if self.asynchronous else list(result)


@pytest.fixture(params=[False, True], ids=["sync", "async"])
async def api(request):
    harness = Harness(request.param)
    if harness.asynchronous:
        async with harness.client:
            yield harness
    else:
        with harness.client:
            yield harness


@pytest.mark.parametrize(
    "endpoint,kwargs",
    [
        ("stats", {}),
        ("video_list", {"cursor": 0, "since": 123, "level": "exp", "size": 1000}),
        ("video_info", {"ids": [1, 2]}),
        ("user_info", {"ids": 1}),
        ("user_list", {"ids": [1, 2]}),
    ],
)
async def test_endpoint_contract(api, payloads, endpoint, kwargs):
    api.responses.append(httpx.Response(200, json=payloads[endpoint]))
    result = await api.call(endpoint, **kwargs)
    assert result.generated_at == payloads[endpoint]["generatedAt"]
    if endpoint == "video_info":
        assert result.items[0].file_url == "2025/07/31/6d58634fbe0987003dda90f4a68944a7.avf"
    request = api.requests[0]
    assert str(request.url).split("?")[0] == f"https://saolei.wang/api/public/v1/{endpoint}"
    assert request.method == "GET"
    assert request.headers["X-Api-Key"] == "sk-test-only"
    assert request.headers["Accept"] == "application/json"
    assert request.headers["User-Agent"] == "saolei-api/0.2.0"
    if endpoint == "video_list":
        assert dict(request.url.params) == {
            "cursor": "0",
            "since": "123",
            "level": "exp",
            "size": "1000",
        }
    elif endpoint != "stats":
        assert request.url.params["id"] == ("1" if kwargs["ids"] == 1 else "1,2")


async def test_video_defaults_omit_absent_filters(api, payloads):
    api.responses.append(httpx.Response(200, json=payloads["video_list"]))
    await api.call("video_list")
    assert dict(api.requests[0].url.params) == {"size": "200"}


@pytest.mark.parametrize(
    "method,limit", [("video_info", 50), ("user_info", 50), ("user_list", 100)]
)
async def test_batch_limits(api, payloads, method, limit):
    api.responses.append(httpx.Response(200, json=payloads[method]))
    await api.call(method, list(range(1, limit + 1)))
    assert len(api.requests[0].url.params["id"].split(",")) == limit
    with pytest.raises(ValueError):
        await api.call(method, list(range(1, limit + 2)))
    assert len(api.requests) == 1


@pytest.mark.parametrize(
    "ids,error",
    [
        ([], ValueError),
        (0, ValueError),
        (-1, ValueError),
        (True, TypeError),
        ("1,2", TypeError),
        ([1, "2"], TypeError),
        ([False], TypeError),
        (1.0, TypeError),
    ],
)
@pytest.mark.parametrize("method", ["video_info", "user_info", "user_list"])
async def test_invalid_ids_never_send_a_request(api, method, ids, error):
    with pytest.raises(error):
        await api.call(method, ids)
    assert not api.requests


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"cursor": -1}, ValueError),
        ({"since": -1}, ValueError),
        ({"cursor": True}, TypeError),
        ({"since": "123"}, TypeError),
        ({"level": "expert"}, ValueError),
        ({"size": 0}, ValueError),
        ({"size": 1001}, ValueError),
        ({"size": 2.5}, TypeError),
    ],
)
async def test_invalid_video_filters_never_send_a_request(api, kwargs, error):
    with pytest.raises(error):
        await api.call("video_list", **kwargs)
    assert not api.requests


@pytest.mark.parametrize(
    "status,error",
    [
        (301, APIError),
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, APIError),
        (429, RateLimitError),
        (500, APIError),
        (503, APIError),
    ],
)
async def test_http_errors_do_not_retry_or_leak_bodies(api, status, error):
    api.responses.append(httpx.Response(status, text="sk-sensitive-reflected-key"))
    with pytest.raises(error) as caught:
        await api.call("stats")
    assert caught.value.status_code == status
    assert "sk-sensitive" not in str(caught.value)
    assert len(api.requests) == 1


async def test_redirects_never_forward_key(api):
    api.responses.append(httpx.Response(302, headers={"Location": "https://other.invalid/"}))
    with pytest.raises(APIError):
        await api.call("stats")
    assert len(api.requests) == 1


@pytest.mark.parametrize("value,expected", [("12", 12), ("-2", 0), ("bad", None), ("nan", None)])
async def test_retry_after(api, value, expected):
    api.responses.append(httpx.Response(429, headers={"Retry-After": value}))
    with pytest.raises(RateLimitError) as caught:
        await api.call("stats")
    assert caught.value.retry_after == expected


@pytest.mark.parametrize("body", [b"<html>upstream unavailable</html>", b"{}", b"null", b"[]"])
async def test_bad_response(api, body):
    api.responses.append(httpx.Response(200, content=body))
    with pytest.raises(ResponseError):
        await api.call("stats")


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ReadTimeout])
async def test_transport_errors(api, error):
    api.responses.append(error("sk-sensitive-reflected-key"))
    with pytest.raises(TransportError) as caught:
        await api.call("stats")
    assert "sk-sensitive" not in str(caught.value)
    assert len(api.requests) == 1


async def test_lazy_pagination_and_since_transition(api, video_page):
    api.responses.extend(
        [
            httpx.Response(200, json=video_page(next_cursor=25, has_more=True)),
            httpx.Response(200, json=video_page(cursor=25, next_cursor=30, video_id=30)),
        ]
    )
    generator = api.client.iter_videos(since=123, size=1, level="beg")
    assert not api.requests
    videos = [v async for v in generator] if api.asynchronous else list(generator)
    assert [v.id for v in videos] == [24, 30]
    assert dict(api.requests[0].url.params) == {"since": "123", "size": "1", "level": "beg"}
    assert dict(api.requests[1].url.params) == {"cursor": "25", "size": "1", "level": "beg"}


async def test_max_pages(api, video_page):
    api.responses.append(httpx.Response(200, json=video_page(has_more=True)))
    assert len(await api.videos(max_pages=1)) == 1
    assert len(api.requests) == 1


@pytest.mark.parametrize("next_value", [0, 1, 24])
async def test_broken_cursor_cannot_loop(api, video_page, next_value):
    api.responses.append(
        httpx.Response(200, json=video_page(next_cursor=next_value, has_more=True))
    )
    with pytest.raises(ResponseError):
        await api.videos(cursor=24)
    assert len(api.requests) == 1


async def test_empty_last_page(api, video_page):
    page = video_page()
    page["items"] = []
    api.responses.append(httpx.Response(200, json=page))
    assert await api.videos() == []


@pytest.mark.parametrize("value,error", [(0, ValueError), (-1, ValueError), (True, TypeError)])
async def test_invalid_max_pages(api, value, error):
    with pytest.raises(error):
        await api.videos(max_pages=value)
    assert not api.requests


@pytest.mark.parametrize("client_class", [Client, AsyncClient])
@pytest.mark.parametrize("key", ["", " ", "sk-a\nb", "sk-a b", "sk-\u4e2d", "sk-\x00"])
def test_bad_key(client_class, key):
    with pytest.raises(ValueError):
        client_class(key)


@pytest.mark.parametrize("client_class", [Client, AsyncClient])
@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"timeout": 0}, ValueError),
        ({"timeout": float("inf")}, ValueError),
        ({"min_interval": -1}, ValueError),
        ({"min_interval": float("nan")}, ValueError),
        ({"min_interval": True}, TypeError),
        ({"download_interval": -1}, ValueError),
        ({"download_interval": float("inf")}, ValueError),
        ({"download_interval": True}, TypeError),
    ],
)
def test_bad_options(client_class, kwargs, error):
    with pytest.raises(error):
        client_class("sk-test-only", **kwargs)


async def test_closed_client(api):
    await api.call("aclose" if api.asynchronous else "close")
    with pytest.raises(RuntimeError):
        await api.call("stats")
    assert not api.requests


def test_sync_pacing(monkeypatch, payloads):
    now = [100.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    monkeypatch.setattr("saolei_api.client.time.monotonic", lambda: now[0])
    monkeypatch.setattr("saolei_api.client.time.sleep", sleep)
    with Client(
        "sk-test-only",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payloads["stats"])),
    ) as client:
        client.stats()
        client.stats()
        client.stats()
    assert sleeps == [2.0, 2.0]


async def test_async_pacing_and_cancellation(monkeypatch, payloads):
    entered = asyncio.Event()
    release = asyncio.Event()
    starts = []

    async def sleep(seconds):
        entered.set()
        await release.wait()

    def handle(request):
        starts.append(request)
        return httpx.Response(200, json=payloads["stats"])

    monkeypatch.setattr("saolei_api.client.asyncio.sleep", sleep)
    async with AsyncClient("sk-test-only", transport=httpx.MockTransport(handle)) as client:
        await client.stats()
        pending = asyncio.create_task(client.stats())
        await entered.wait()
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        release.set()
        await client.stats()
    assert len(starts) == 2


async def test_download_videos_preserves_binary_order_and_duplicates(api):
    suffixes = ["2025/07/31/first.avf", "2007/01/05/second.mvf", "2025/07/31/first.avf"]
    contents = [b"\x00\xfffirst", b"\x01\x80second", b"\x00\xfffirst"]
    api.responses.extend(httpx.Response(200, content=content) for content in contents)
    assert await api.call("download_videos", suffixes) == contents
    for request, suffix in zip(api.requests, suffixes, strict=True):
        assert str(request.url) == f"https://saolei.wang/videos/{suffix}"
        assert request.method == "GET"
        assert request.headers["Accept"] == "application/octet-stream"
        assert request.headers["X-Api-Key"] == "sk-test-only"


async def test_download_videos_from_metadata(api, payloads):
    api.responses.extend(
        [
            httpx.Response(200, json=payloads["video_info"]),
            httpx.Response(200, content=b"recording"),
        ]
    )
    result = await api.call("video_info", 328090)
    assert await api.call("download_videos", [result.items[0].file_url]) == [b"recording"]
    assert str(api.requests[-1].url) == payloads["video_info"]["items"][0]["fileUrl"]


async def test_empty_download_batch(api):
    assert await api.call("download_videos", []) == []
    assert not api.requests


@pytest.mark.parametrize(
    "bad_value",
    [
        "https://other.invalid/file.avf",
        "//other.invalid/file.avf",
        "/2025/07/31/file.avf",
        "/videos/2025/07/31/file.avf",
        "../file.avf",
        "2025/07/31/../../file.avf",
        "2025/07/31/%2e%2e.avf",
        "2025/07/31/file.avf?x=y",
        "2025/07/31/file.avf#x",
        "2025/07/31/file\\other.avf",
        "2025/07/31/file.avf\n",
        "2025/02/30/file.avf",
        "2025/7/31/file.avf",
        "2025/07/31/",
        "",
        None,
        1,
    ],
)
async def test_whole_download_batch_validated_before_network(api, bad_value):
    with pytest.raises((ValueError, TypeError)):
        await api.call("download_videos", ["2025/07/31/valid.avf", bad_value])
    assert not api.requests


@pytest.mark.parametrize("batch", ["2025/07/31/file.avf", b"2025/07/31/file.avf", None, 1])
async def test_invalid_download_container(api, batch):
    with pytest.raises(TypeError):
        await api.call("download_videos", batch)
    assert not api.requests


@pytest.mark.parametrize(
    "status,error",
    [
        (302, APIError),
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, APIError),
        (429, RateLimitError),
        (500, APIError),
    ],
)
async def test_download_error_stops_batch_without_retry(api, status, error):
    api.responses.extend(
        [
            httpx.Response(200, content=b"first"),
            httpx.Response(
                status,
                text="private reflected contents",
                headers={"Retry-After": "3", "Location": "https://other.invalid/"},
            ),
            httpx.Response(200, content=b"third"),
        ]
    )
    with pytest.raises(error) as caught:
        await api.call("download_videos", [f"2025/07/31/{i}.avf" for i in range(3)])
    assert caught.value.endpoint == "videos/2025/07/31/1.avf"
    assert caught.value.status_code == status
    if status == 429:
        assert caught.value.retry_after == 3
    assert "private reflected" not in str(caught.value)
    assert len(api.requests) == 2


async def test_download_transport_error(api):
    api.responses.append(httpx.ReadError("private reflected contents"))
    with pytest.raises(TransportError) as caught:
        await api.call("download_videos", ["2025/07/31/file.avf"])
    assert "private reflected" not in str(caught.value)


@pytest.mark.parametrize("asynchronous", [False, True], ids=["sync", "async"])
async def test_download_throttle_is_shared_across_batches_and_independent_of_api(
    monkeypatch, payloads, asynchronous
):
    now = [100.0]
    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    async def async_sleep(seconds):
        sleep(seconds)

    def handle(request):
        if request.url.path.startswith("/videos/"):
            return httpx.Response(200, content=b"video")
        return httpx.Response(200, json=payloads["stats"])

    monkeypatch.setattr("saolei_api.client.time.monotonic", lambda: now[0])
    monkeypatch.setattr("saolei_api.client.time.sleep", sleep)
    monkeypatch.setattr("saolei_api.client.asyncio.sleep", async_sleep)
    if asynchronous:
        async with AsyncClient("sk-test-only", transport=httpx.MockTransport(handle)) as client:
            await client.stats()
            assert await client.download_videos(["2025/07/31/a.avf"]) == [b"video"]
            assert await client.download_videos(["2025/07/31/b.avf"]) == [b"video"]
            await client.stats()
    else:
        with Client("sk-test-only", transport=httpx.MockTransport(handle)) as client:
            client.stats()
            assert client.download_videos(["2025/07/31/a.avf"]) == [b"video"]
            assert client.download_videos(["2025/07/31/b.avf"]) == [b"video"]
            client.stats()
    assert sleeps == pytest.approx([0.4, 1.6])


async def test_download_cancellation_releases_limiter(monkeypatch):
    entered = asyncio.Event()
    release = asyncio.Event()
    starts = []

    async def sleep(seconds):
        entered.set()
        await release.wait()

    def handle(request):
        starts.append(request)
        return httpx.Response(200, content=b"recording")

    monkeypatch.setattr("saolei_api.client.asyncio.sleep", sleep)
    async with AsyncClient("sk-test-only", transport=httpx.MockTransport(handle)) as client:
        assert await client.download_videos(["2025/07/31/first.avf"]) == [b"recording"]
        pending = asyncio.create_task(client.download_videos(["2025/07/31/cancelled.avf"]))
        await entered.wait()
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        release.set()
        assert await client.download_videos(["2025/07/31/last.avf"]) == [b"recording"]
    assert len(starts) == 2
