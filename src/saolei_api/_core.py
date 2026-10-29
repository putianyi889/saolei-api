"""Shared validation and response handling for the sync and async clients."""

import math
from collections.abc import Sequence
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TypeVar

import httpx
from pydantic import ValidationError

from .exceptions import APIError, AuthenticationError, RateLimitError, ResponseError
from .models import APIModel, Level, PostSearchResponse, VideoListResponse

BASE_URL = "https://saolei.wang/api/public/v1/"
ModelT = TypeVar("ModelT", bound=APIModel)


def integer(value: int, name: str, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{name} must be >= {minimum}" + (f" and <= {maximum}" if maximum else ""))
    return value


def number(value: float, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return float(value)


def headers(api_key: str) -> dict[str, str]:
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("api_key must be a nonempty string")
    if not api_key.isascii() or any(char.isspace() or ord(char) < 32 for char in api_key):
        raise ValueError(
            "api_key must contain only ASCII characters without whitespace or controls"
        )
    return {"X-Api-Key": api_key, "Accept": "application/json", "User-Agent": "saolei-api/0.4.0"}


def ids_params(ids: int | Sequence[int], limit: int) -> dict[str, str]:
    if isinstance(ids, int):
        values = [ids]
    elif isinstance(ids, Sequence) and not isinstance(ids, (str, bytes)):
        values = list(ids)
    else:
        raise TypeError("ids must be an integer or a sequence of integers")
    if not 1 <= len(values) <= limit:
        raise ValueError(f"ids must contain between 1 and {limit} IDs")
    return {"id": ",".join(str(integer(value, "id", 1)) for value in values)}


def video_params(
    cursor: int | None,
    since: int | None,
    level: Level | None,
    size: int,
    *,
    player_id: int | None = None,
) -> dict[str, str | int]:
    params: dict[str, str | int] = {"size": integer(size, "size", 1, 1000)}
    if cursor is not None:
        params["cursor"] = integer(cursor, "cursor")
    if since is not None:
        params["since"] = integer(since, "since")
    if player_id is not None:
        params["player_id"] = integer(player_id, "player_id", 1)
    if level is not None:
        if level not in ("beg", "int", "exp"):
            raise ValueError("level must be 'beg', 'int', or 'exp'")
        params["level"] = level
    return params


def retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
        return max(0.0, seconds) if math.isfinite(seconds) else None
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                date = date.replace(tzinfo=UTC)
            return max(0.0, (date - datetime.now(UTC)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return None


def post_search_params(keyword: str, cursor: int | None) -> dict[str, str | int]:
    if not isinstance(keyword, str):
        raise TypeError("keyword must be a string")
    if not keyword.strip() or len(keyword) > 30:
        raise ValueError("keyword must contain between 1 and 30 characters and not be blank")
    params: dict[str, str | int] = {"keyword": keyword}
    if cursor is not None:
        params["cursor"] = integer(cursor, "cursor")
    return params


def check_status(response: httpx.Response, endpoint: str) -> None:
    status = response.status_code
    if status in (401, 403):
        raise AuthenticationError(status, endpoint)
    if status == 429:
        raise RateLimitError(endpoint, retry_after(response.headers.get("Retry-After")))
    if not 200 <= status < 300:
        raise APIError(status, endpoint)


def parse_response(response: httpx.Response, endpoint: str, model: type[ModelT]) -> ModelT:
    check_status(response, endpoint)
    try:
        return model.model_validate_json(response.content)
    except ValidationError:
        raise ResponseError(f"Invalid JSON or response schema for {endpoint}") from None


def next_cursor(page: VideoListResponse, requested_cursor: int | None) -> int:
    previous = max(page.cursor, requested_cursor if requested_cursor is not None else 0)
    if page.next_cursor <= previous:
        raise ResponseError("video_list returned hasMore=true without an advancing cursor")
    return page.next_cursor


def next_post_cursor(page: PostSearchResponse, requested_cursor: int | None) -> int:
    # Zero denotes the first/newest page; subsequent cursors must decrease.
    cursors = [
        value for value in (page.cursor, requested_cursor) if value is not None and value > 0
    ]
    previous = min(cursors) if cursors else None
    following = page.next_cursor
    if following is None or following <= 0 or (previous is not None and following >= previous):
        raise ResponseError(
            "post_search returned hasMore=true without a decreasing positive cursor"
        )
    return following
