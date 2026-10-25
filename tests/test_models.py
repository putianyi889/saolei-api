import copy

import pytest

from saolei_api import (
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
    ],
)
def test_official_examples_round_trip(payloads, endpoint, model):
    payload = payloads[endpoint]
    assert model.model_validate(payload).model_dump(by_alias=True) == payload


def test_aliases_and_units(payloads):
    video = VideoListResponse.model_validate(payloads["video_list"]).items[0]
    assert video.board_3bv == 4
    assert video.real_time == 1110
    assert video.three_bvs == -3604
    user = UserInfoResponse.model_validate(payloads["user_info"]).users[0]
    assert user.scores.beg.time_video_id == 154
    assert user.scores.beg.three_bvs == 7289
    assert user.scores_nf.sum.three_bvs == 13835


def test_future_fields_are_preserved(payloads):
    payload = copy.deepcopy(payloads["video_info"])
    payload["newTopField"] = "future"
    payload["items"][0]["newVideoField"] = 12
    parsed = VideoInfoResponse.model_validate(payload)
    assert parsed.model_dump(by_alias=True) == payload


def test_unavailable_metrics_and_file(payloads):
    payload = copy.deepcopy(payloads["video_info"])
    payload["items"][0].update(metrics=None, fileUrl=None, signature=None)
    parsed = VideoInfoResponse.model_validate(payload).items[0]
    assert parsed.metrics is None and parsed.file_url is None and parsed.signature is None


@pytest.mark.parametrize(
    "endpoint,model,field",
    [
        ("video_list", VideoListResponse, "items"),
        ("video_info", VideoInfoResponse, "items"),
        ("user_info", UserInfoResponse, "users"),
        ("user_list", UserListResponse, "users"),
    ],
)
def test_empty_results_are_valid(payloads, endpoint, model, field):
    payload = copy.deepcopy(payloads[endpoint])
    payload[field] = []
    assert getattr(model.model_validate(payload), field) == []
