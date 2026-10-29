"""HTTPX clients for the documented public APIs and their recording files."""

import asyncio
import threading
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Self

import httpx

from ._core import (
    BASE_URL,
    ModelT,
    check_status,
    headers,
    ids_params,
    integer,
    next_cursor,
    next_post_cursor,
    number,
    parse_response,
    post_search_params,
    video_params,
)
from ._files import VIDEO_FILE_BASE_URL, file_suffixes
from .exceptions import TransportError
from .models import (
    Level,
    Post,
    PostInfoResponse,
    PostSearchResponse,
    StatsResponse,
    UserInfoResponse,
    UserListResponse,
    Video,
    VideoInfoResponse,
    VideoListResponse,
)


class Client:
    """Reusable sync client. Use as a context manager or call close()."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30.0,
        min_interval: float = 2.0,
        download_interval: float = 0.4,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        request_headers = headers(api_key)
        request_timeout = number(timeout, "timeout", positive=True)
        self._interval = number(min_interval, "min_interval")
        self._download_interval = number(download_interval, "download_interval")
        self._last_request: float | None = None
        self._last_download: float | None = None
        self._lock = threading.Lock()
        self._download_lock = threading.Lock()
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers=request_headers,
            timeout=request_timeout,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> Self:
        self._http.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def _wait(self, *, download: bool = False) -> None:
        lock = self._download_lock if download else self._lock
        with lock:
            last = self._last_download if download else self._last_request
            interval = self._download_interval if download else self._interval
            if last is not None:
                wait = interval - (time.monotonic() - last)
                if wait > 0:
                    time.sleep(wait)
            if download:
                self._last_download = time.monotonic()
            else:
                self._last_request = time.monotonic()

    def _get(
        self, endpoint: str, model: type[ModelT], params: dict[str, str | int] | None = None
    ) -> ModelT:
        self._wait()
        try:
            response = self._http.get(endpoint, params=params)
        except httpx.RequestError:
            raise TransportError(f"Request failed for {endpoint}") from None
        return parse_response(response, endpoint, model)

    def stats(self) -> StatsResponse:
        return self._get("stats", StatsResponse)

    def video_list(
        self,
        *,
        cursor: int | None = None,
        since: int | None = None,
        level: Level | None = None,
        player_id: int | None = None,
        size: int = 200,
    ) -> VideoListResponse:
        return self._get(
            "video_list",
            VideoListResponse,
            video_params(cursor, since, level, size, player_id=player_id),
        )

    def video_info(self, ids: int | Sequence[int]) -> VideoInfoResponse:
        return self._get("video_info", VideoInfoResponse, dict(ids_params(ids, 50)))

    def user_info(self, ids: int | Sequence[int]) -> UserInfoResponse:
        return self._get("user_info", UserInfoResponse, dict(ids_params(ids, 50)))

    def user_list(self, ids: int | Sequence[int]) -> UserListResponse:
        return self._get("user_list", UserListResponse, dict(ids_params(ids, 100)))

    def post_info(self, ids: int | Sequence[int]) -> PostInfoResponse:
        return self._get("post_info", PostInfoResponse, dict(ids_params(ids, 50)))

    def post_search(self, keyword: str, *, cursor: int | None = None) -> PostSearchResponse:
        return self._get("post_search", PostSearchResponse, post_search_params(keyword, cursor))

    def iter_posts(
        self, keyword: str, *, cursor: int | None = None, max_pages: int | None = None
    ) -> Iterator[Post]:
        """Search titles lazily from newer to older IDs, at most 20 posts per page."""
        if max_pages is not None:
            integer(max_pages, "max_pages", 1)
        pages = 0
        while True:
            page = self.post_search(keyword, cursor=cursor)
            following = next_post_cursor(page, cursor) if page.has_more else None
            yield from page.items
            pages += 1
            if following is None or (max_pages is not None and pages >= max_pages):
                return
            cursor = following

    def download_videos(self, suffixes: Sequence[str]) -> list[bytes]:
        """Return recording file contents in input order; stop on the first error."""
        paths = file_suffixes(suffixes)
        files: list[bytes] = []
        for suffix in paths:
            self._wait(download=True)
            endpoint = f"videos/{suffix}"
            try:
                response = self._http.get(
                    f"{VIDEO_FILE_BASE_URL}{suffix}", headers={"Accept": "application/octet-stream"}
                )
            except httpx.RequestError:
                raise TransportError(f"Request failed for {endpoint}") from None
            check_status(response, endpoint)
            files.append(response.content)
        return files

    def iter_videos(
        self,
        *,
        cursor: int | None = None,
        since: int | None = None,
        level: Level | None = None,
        player_id: int | None = None,
        size: int = 200,
        max_pages: int | None = None,
    ) -> Iterator[Video]:
        """Fetch lazily until hasMore=false, max_pages is reached, or iteration stops."""
        if max_pages is not None:
            integer(max_pages, "max_pages", 1)
        pages = 0
        while True:
            page = self.video_list(
                cursor=cursor, since=since, level=level, player_id=player_id, size=size
            )
            # Check before yielding so a broken page cannot silently loop or duplicate data.
            following = next_cursor(page, cursor) if page.has_more else None
            yield from page.items
            pages += 1
            if following is None or (max_pages is not None and pages >= max_pages):
                return
            cursor, since = following, None


class AsyncClient:
    """Reusable async client for one event loop. Use async with or await aclose()."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30.0,
        min_interval: float = 2.0,
        download_interval: float = 0.4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        request_headers = headers(api_key)
        request_timeout = number(timeout, "timeout", positive=True)
        self._interval = number(min_interval, "min_interval")
        self._download_interval = number(download_interval, "download_interval")
        self._last_request: float | None = None
        self._last_download: float | None = None
        self._lock = asyncio.Lock()
        self._download_lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=request_headers,
            timeout=request_timeout,
            transport=transport,
            follow_redirects=False,
        )

    async def __aenter__(self) -> Self:
        await self._http.__aenter__()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _wait(self, *, download: bool = False) -> None:
        lock = self._download_lock if download else self._lock
        async with lock:
            last = self._last_download if download else self._last_request
            interval = self._download_interval if download else self._interval
            if last is not None:
                wait = interval - (time.monotonic() - last)
                if wait > 0:
                    await asyncio.sleep(wait)
            if download:
                self._last_download = time.monotonic()
            else:
                self._last_request = time.monotonic()

    async def _get(
        self, endpoint: str, model: type[ModelT], params: dict[str, str | int] | None = None
    ) -> ModelT:
        await self._wait()
        try:
            response = await self._http.get(endpoint, params=params)
        except httpx.RequestError:
            raise TransportError(f"Request failed for {endpoint}") from None
        return parse_response(response, endpoint, model)

    async def stats(self) -> StatsResponse:
        return await self._get("stats", StatsResponse)

    async def video_list(
        self,
        *,
        cursor: int | None = None,
        since: int | None = None,
        level: Level | None = None,
        player_id: int | None = None,
        size: int = 200,
    ) -> VideoListResponse:
        return await self._get(
            "video_list",
            VideoListResponse,
            video_params(cursor, since, level, size, player_id=player_id),
        )

    async def video_info(self, ids: int | Sequence[int]) -> VideoInfoResponse:
        return await self._get("video_info", VideoInfoResponse, dict(ids_params(ids, 50)))

    async def user_info(self, ids: int | Sequence[int]) -> UserInfoResponse:
        return await self._get("user_info", UserInfoResponse, dict(ids_params(ids, 50)))

    async def user_list(self, ids: int | Sequence[int]) -> UserListResponse:
        return await self._get("user_list", UserListResponse, dict(ids_params(ids, 100)))

    async def post_info(self, ids: int | Sequence[int]) -> PostInfoResponse:
        return await self._get("post_info", PostInfoResponse, dict(ids_params(ids, 50)))

    async def post_search(self, keyword: str, *, cursor: int | None = None) -> PostSearchResponse:
        return await self._get(
            "post_search", PostSearchResponse, post_search_params(keyword, cursor)
        )

    async def iter_posts(
        self, keyword: str, *, cursor: int | None = None, max_pages: int | None = None
    ) -> AsyncIterator[Post]:
        """Iterate title-search results in descending ID order without blocking."""
        if max_pages is not None:
            integer(max_pages, "max_pages", 1)
        pages = 0
        while True:
            page = await self.post_search(keyword, cursor=cursor)
            following = next_post_cursor(page, cursor) if page.has_more else None
            for post in page.items:
                yield post
            pages += 1
            if following is None or (max_pages is not None and pages >= max_pages):
                return
            cursor = following

    async def download_videos(self, suffixes: Sequence[str]) -> list[bytes]:
        """Download sequentially without blocking the event loop; preserve input order."""
        paths = file_suffixes(suffixes)
        files: list[bytes] = []
        for suffix in paths:
            await self._wait(download=True)
            endpoint = f"videos/{suffix}"
            try:
                response = await self._http.get(
                    f"{VIDEO_FILE_BASE_URL}{suffix}", headers={"Accept": "application/octet-stream"}
                )
            except httpx.RequestError:
                raise TransportError(f"Request failed for {endpoint}") from None
            check_status(response, endpoint)
            files.append(response.content)
        return files

    async def iter_videos(
        self,
        *,
        cursor: int | None = None,
        since: int | None = None,
        level: Level | None = None,
        player_id: int | None = None,
        size: int = 200,
        max_pages: int | None = None,
    ) -> AsyncIterator[Video]:
        if max_pages is not None:
            integer(max_pages, "max_pages", 1)
        pages = 0
        while True:
            page = await self.video_list(
                cursor=cursor, since=since, level=level, player_id=player_id, size=size
            )
            following = next_cursor(page, cursor) if page.has_more else None
            for video in page.items:
                yield video
            pages += 1
            if following is None or (max_pages is not None and pages >= max_pages):
                return
            cursor, since = following, None
