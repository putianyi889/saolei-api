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
    result = copy.deepcopy(payloads)
    result["video_info"]["items"][0]["fileUrl"] = "2025/07/31/6d58634fbe0987003dda90f4a68944a7.avf"
    return result


@pytest.fixture
def video_page(payloads):
    def make(cursor=0, next_cursor=25, has_more=False, video_id=24):
        result = copy.deepcopy(payloads["video_list"])
        result.update(cursor=cursor, nextCursor=next_cursor, hasMore=has_more)
        result["items"][0]["id"] = video_id
        return result

    return make
