"""Models for the documented public v1 endpoints. Values retain upstream units."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from ._files import normalize_file_url

Level = Literal["beg", "int", "exp"]


class APIModel(BaseModel):
    """Accept upstream aliases, expose snake_case, and preserve future fields."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="allow")


class SiteStats(APIModel):
    user_total: int
    ranked_total: int
    video_total: int
    video_comment_total: int
    bbs_topic_total: int
    bbs_reply_total: int
    practice_total: int


class StatsResponse(APIModel):
    generated_at: int
    stats: SiteStats
    max_video_id: int
    max_user_id: int


class Video(APIModel):
    id: int
    level: Level
    user_id: int
    user_name: str
    hash: str
    status: int
    upload_time: int
    review_time: int
    real_time: int
    board_3bv: int = Field(alias="board3bv")
    three_bvs: int = Field(alias="3bvs")
    nf: bool
    software: str
    version: str


class VideoMetrics(APIModel):
    cl: int | None = None
    cl_left: int | None = None
    cl_right: int | None = None
    cl_double: int | None = None
    ce: int | None = None
    path: float | None = None
    ioe: float | None = None
    stnb: float | None = None


class VideoInfo(Video):
    signature: str | None
    metrics: VideoMetrics | None
    file_url: str | None

    @field_validator("file_url")
    @classmethod
    def file_url_suffix(cls, value: str | None) -> str | None:
        """Expose only YYYY/MM/DD/filename, including in model serialization."""
        return normalize_file_url(value)


class VideoListResponse(APIModel):
    cursor: int
    next_cursor: int
    has_more: bool
    size: int
    generated_at: int
    items: list[Video]


class VideoInfoResponse(APIModel):
    generated_at: int
    items: list[VideoInfo]


class LevelScore(APIModel):
    time: int
    time_video_id: int
    three_bvs: int = Field(alias="3bvs")
    three_bvs_video_id: int = Field(alias="3bvsVideoId")


class TotalScore(APIModel):
    time: int
    three_bvs: int = Field(alias="3bvs")


class Scores(APIModel):
    beg: LevelScore
    int: LevelScore
    exp: LevelScore
    sum: TotalScore


class SummaryScores(APIModel):
    beg_time: int
    beg_3bvs: int = Field(alias="beg3bvs")
    int_time: int
    int_3bvs: int = Field(alias="int3bvs")
    exp_time: int
    exp_3bvs: int = Field(alias="exp3bvs")
    sum_time: int
    sum_3bvs: int = Field(alias="sum3bvs")


class UserSummary(APIModel):
    id: int
    name: str
    english_name: str
    sex: int
    area: str
    registered_at: int
    banned: bool
    scores: SummaryScores


class UserInfo(APIModel):
    id: int
    name: str
    english_name: str
    sex: int
    area: str
    registered_at: int
    banned: bool
    scores: Scores
    scores_nf: Scores
    signatures: list[str]


class UserInfoResponse(APIModel):
    generated_at: int
    users: list[UserInfo]


class UserListResponse(APIModel):
    generated_at: int
    users: list[UserSummary]


class Post(APIModel):
    """Public post metadata; the API does not provide post bodies or replies."""

    id: int
    title: str
    board: int
    user_id: int
    user_name: str
    post_time: int
    update_time: int
    last_reply_time: int
    replies: int
    clicks: int
    pinned: bool
    nice: bool
    locked: bool


class PostInfoResponse(APIModel):
    generated_at: int
    items: list[Post]


class PostSearchResponse(APIModel):
    cursor: int
    next_cursor: int | None
    has_more: bool
    keyword: str
    size: int
    generated_at: int
    items: list[Post]
