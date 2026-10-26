"""Python interface to the official saolei.wang public API."""

from .client import AsyncClient, Client
from .exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    ResponseError,
    SaoleiError,
    TransportError,
)
from .models import (
    APIModel,
    Level,
    LevelScore,
    Scores,
    SiteStats,
    StatsResponse,
    SummaryScores,
    TotalScore,
    UserInfo,
    UserInfoResponse,
    UserListResponse,
    UserSummary,
    Video,
    VideoInfo,
    VideoInfoResponse,
    VideoListResponse,
    VideoMetrics,
)

__version__ = "0.3.0"

__all__ = [
    "APIError",
    "APIModel",
    "AsyncClient",
    "AuthenticationError",
    "Client",
    "Level",
    "LevelScore",
    "RateLimitError",
    "ResponseError",
    "SaoleiError",
    "Scores",
    "SiteStats",
    "StatsResponse",
    "SummaryScores",
    "TotalScore",
    "TransportError",
    "UserInfo",
    "UserInfoResponse",
    "UserListResponse",
    "UserSummary",
    "Video",
    "VideoInfo",
    "VideoInfoResponse",
    "VideoListResponse",
    "VideoMetrics",
    "__version__",
]
