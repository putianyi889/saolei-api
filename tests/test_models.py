import copy

import pytest
from pydantic import ValidationError

from saolei_api import (
    PostInfoResponse,
    PostSearchResponse,
    StatsResponse,
    UserInfoResponse,
    UserListResponse,
    VideoInfoResponse,
    VideoListResponse,
)


@pytest.mark.parametrize(
    "endpoint,model",
    [
        ("stats", StatsResponse),
        ("video_list", VideoListResponse),
        ("video_info", VideoInfoResponse),
        ("user_info", UserInfoResponse),
        ("user_list", UserListResponse),
        ("post_info", PostInfoResponse),
        ("post_search", PostSearchResponse),
    ],
)
def test_official_examples_normalize_and_round_trip(payloads, normalized_payloads, endpoint, model):
    payload = payloads[endpoint]
    parsed = model.model_validate(payload)
    assert parsed.model_dump(by_alias=True) == normalized_payloads[endpoint]
    assert model.model_validate_json(parsed.model_dump_json(by_alias=True)) == parsed


def test_aliases_and_units(payloads):
    video = VideoListResponse.model_validate(payloads["video_list"]).items[0]
    assert video.board_3bv == 4
    assert video.real_time == 1110
    assert video.three_bvs == -3604
    assert video.status == 20
    user = UserInfoResponse.model_validate(payloads["user_info"]).users[0]
    assert user.scores.beg.time_video_id == 154
    assert user.scores.beg.three_bvs == 7289
    assert user.scores_nf.sum.three_bvs == 13835


def test_future_fields_are_preserved(payloads):
    payload = copy.deepcopy(payloads["video_info"])
    payload["newTopField"] = "future"
    payload["items"][0]["newVideoField"] = 12
    parsed = VideoInfoResponse.model_validate(payload)
    payload["items"][0]["fileUrl"] = "2025/07/31/6d58634fbe0987003dda90f4a68944a7.avf"
    assert parsed.model_dump(by_alias=True) == payload


def test_unavailable_metrics_and_file(payloads):
    payload = copy.deepcopy(payloads["video_info"])
    payload["items"][0].update(metrics=None, fileUrl=None, signature=None)
    parsed = VideoInfoResponse.model_validate(payload).items[0]
    assert parsed.metrics is None and parsed.file_url is None and parsed.signature is None


@pytest.mark.parametrize(
    "value",
    [
        "https://saolei.wang/videos/2025/07/31/example.avf",
        "/videos/2025/07/31/example.avf",
        "2025/07/31/example.avf",
    ],
)
def test_file_urls_expose_suffix_only(payloads, value):
    payload = copy.deepcopy(payloads["video_info"])
    payload["items"][0]["fileUrl"] = value
    parsed = VideoInfoResponse.model_validate(payload)
    assert parsed.items[0].file_url == "2025/07/31/example.avf"
    assert parsed.model_dump(by_alias=True)["items"][0]["fileUrl"] == "2025/07/31/example.avf"
    assert "https://" not in parsed.model_dump_json()


@pytest.mark.parametrize(
    "value",
    [
        "https://other.invalid/videos/2025/07/31/example.avf",
        "https://saolei.wang/videos/2025/07/31/../example.avf",
        "2025/02/30/example.avf",
        "2025/07/31/example.avf?token=value",
    ],
)
def test_invalid_upstream_file_url(payloads, value):
    payload = copy.deepcopy(payloads["video_info"])
    payload["items"][0]["fileUrl"] = value
    with pytest.raises(ValidationError):
        VideoInfoResponse.model_validate(payload)


@pytest.mark.parametrize(
    "endpoint,model,field",
    [
        ("video_list", VideoListResponse, "items"),
        ("video_info", VideoInfoResponse, "items"),
        ("user_info", UserInfoResponse, "users"),
        ("user_list", UserListResponse, "users"),
        ("post_info", PostInfoResponse, "items"),
        ("post_search", PostSearchResponse, "items"),
    ],
)
def test_empty_results_are_valid(payloads, endpoint, model, field):
    payload = copy.deepcopy(payloads[endpoint])
    payload[field] = []
    assert getattr(model.model_validate(payload), field) == []


def test_post_timestamps_and_flags(payloads):
    post = PostInfoResponse.model_validate(payloads["post_info"]).items[0]
    assert post.id == 362 and post.board == 1
    assert post.post_time == 1181620008
    assert post.update_time == 1201508595
    assert post.last_reply_time == 1637886023
    assert post.replies == 35 and post.clicks == 187923
    assert post.nice and not post.pinned and not post.locked


def test_post_last_page_null_cursor_and_future_fields(post_page):
    payload = post_page()
    payload["items"][0]["futureField"] = "preserved"
    page = PostSearchResponse.model_validate(payload)
    assert page.next_cursor is None and not page.has_more
    assert page.model_dump(by_alias=True) == payload
