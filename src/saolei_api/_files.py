"""Canonical recording file references shared by models and downloads."""

import re
from collections.abc import Sequence
from datetime import date
from email.message import Message
from pathlib import PurePosixPath
from urllib.parse import urlsplit

import httpx

OFFICIAL_ORIGIN = "https://saolei.wang"
VIDEO_FILE_BASE_URL = f"{OFFICIAL_ORIGIN}/videos/"
VIDEO_DOWNLOAD_BASE_URL = f"{OFFICIAL_ORIGIN}/video/download/"

_SUFFIX_RE = re.compile(r"([0-9]{4})/([0-9]{2})/([0-9]{2})/([A-Za-z0-9][A-Za-z0-9_.-]*)")
_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
_DOWNLOAD_PATH_RE = re.compile(rf"/video/download/{_SEGMENT}(?:/{_SEGMENT})*")
_QUERY_RE = re.compile(r"[A-Za-z0-9_&=%.-]*")


class VideoFile(bytes):
    """Recording content with the filename supplied by the download response."""

    name: str | None

    def __new__(cls, content: bytes, name: str | None = None) -> "VideoFile":
        value = super().__new__(cls, content)
        value.name = name
        return value


def file_suffix(value: str) -> str:
    """Validate YYYY/MM/DD/filename without accepting arbitrary URLs or paths."""
    if not isinstance(value, str):
        raise TypeError("file suffix must be a string")
    match = _SUFFIX_RE.fullmatch(value)
    if match is None:
        raise ValueError("file suffix must have the form YYYY/MM/DD/filename")
    date(*(int(part) for part in match.groups()[:3]))
    return value


def normalize_file_url(value: str | None) -> str | None:
    """Keep a usable file reference; never reject an unfamiliar official value."""
    if value is None or value == "":
        return None
    for prefix in (VIDEO_FILE_BASE_URL, "/videos/"):
        if value.startswith(prefix):
            candidate = value.removeprefix(prefix).split("?", 1)[0]
            try:
                return file_suffix(candidate)
            except (TypeError, ValueError):
                return value
    if value.startswith("/video/download/"):
        return f"{OFFICIAL_ORIGIN}{value}"
    return value


def download_url(value: str) -> str:
    """Resolve a stored reference to an official URL before any request is sent."""
    if not isinstance(value, str):
        raise TypeError("file reference must be a string")
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        if (
            parts.scheme != "https"
            or parts.netloc != "saolei.wang"
            or parts.username
            or parts.password
            or parts.fragment
        ):
            raise ValueError("file reference must be an official saolei.wang URL")
        if _DOWNLOAD_PATH_RE.fullmatch(parts.path):
            if parts.query and not _QUERY_RE.fullmatch(parts.query):
                raise ValueError("invalid query in file reference")
            return f"{OFFICIAL_ORIGIN}{parts.path}" + (f"?{parts.query}" if parts.query else "")
        if parts.path.startswith("/videos/") and not parts.query:
            return VIDEO_FILE_BASE_URL + file_suffix(parts.path.removeprefix("/videos/"))
        raise ValueError("unsupported official file URL path")
    return VIDEO_FILE_BASE_URL + file_suffix(value)


def download_urls(values: Sequence[str]) -> list[str]:
    """Validate the whole batch before any download starts, preserving order."""
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise TypeError("file references must be a sequence of strings")
    return [download_url(value) for value in values]


def endpoint_name(url: str) -> str:
    """Identify a download in errors without exposing its query string."""
    return urlsplit(url).path.lstrip("/")


def response_file_name(headers: httpx.Headers) -> str | None:
    """Extract a safe basename from Content-Disposition, if the server supplies one."""
    header = headers.get("Content-Disposition")
    if not header:
        return None
    message = Message()
    message["Content-Disposition"] = header
    name = message.get_filename()
    if not name:
        return None
    name = PurePosixPath(name.replace("\\", "/")).name
    if "." not in name or any(ord(char) < 32 for char in name):
        return None
    return name
