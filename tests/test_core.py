from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

from saolei_api._core import retry_after


def test_retry_after_date():
    value = format_datetime(datetime.now(UTC) + timedelta(seconds=60), usegmt=True)
    assert 58 <= retry_after(value) <= 60


def test_retry_after_absent_or_past():
    assert retry_after(None) is None
    assert retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 0
