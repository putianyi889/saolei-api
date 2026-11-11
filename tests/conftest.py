import copy
import json
from pathlib import Path

import pytest


@pytest.fixture
def payloads():
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in Path(__file__).with_name("fixtures").glob("*.json")
    }


@pytest.fixture
def normalized_payloads(payloads):
    # Legacy /videos/ URLs are normalized separately in test_models.py.
    return copy.deepcopy(payloads)


@pytest.fixture
def video_page(payloads):
    def make(cursor=0, next_cursor=25, has_more=False, video_id=24):
        result = copy.deepcopy(payloads["video_list"])
        result.update(cursor=cursor, nextCursor=next_cursor, hasMore=has_more)
        result["items"][0]["id"] = video_id
        return result

    return make


@pytest.fixture
def post_page(payloads):
    def make(cursor=0, next_cursor=None, has_more=False, post_id=24361):
        result = copy.deepcopy(payloads["post_search"])
        result.update(cursor=cursor, nextCursor=next_cursor, hasMore=has_more)
        result["items"][0]["id"] = post_id
        return result

    return make
