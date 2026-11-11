from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from saolei_api import ResponseError, VideoListResponse
from saolei_api._core import parse_response, retry_after


def test_retry_after_date():
    value = format_datetime(datetime.now(UTC) + timedelta(seconds=60), usegmt=True)
    assert 58 <= retry_after(value) <= 60


def test_retry_after_absent_or_past():
    assert retry_after(None) is None
    assert retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 0


def test_schema_error_reports_field_location():
    with pytest.raises(ResponseError) as caught:
        parse_response(httpx.Response(200, json={"cursor": 0}), "video_list", VideoListResponse)
    message = str(caught.value)
    assert message.startswith("Invalid JSON or response schema for video_list")
    assert "nextCursor" in message
    assert "[missing" in message
