"""Canonical recording file suffixes shared by models and downloads."""

import re
from collections.abc import Sequence
from datetime import date

VIDEO_FILE_BASE_URL = "https://saolei.wang/videos/"


def file_suffix(value: str) -> str:
    """Validate YYYY/MM/DD/filename without accepting arbitrary URLs or paths."""
    if not isinstance(value, str):
        raise TypeError("file suffix must be a string")
    match = re.fullmatch(r"([0-9]{4})/([0-9]{2})/([0-9]{2})/([A-Za-z0-9][A-Za-z0-9_.-]*)", value)
    if match is None:
        raise ValueError("file suffix must have the form YYYY/MM/DD/filename")
    date(*(int(part) for part in match.groups()[:3]))
    return value


def normalize_file_url(value: str | None) -> str | None:
    """Convert an official absolute/root-relative file URL into its suffix."""
    if value is None:
        return None
    for prefix in (VIDEO_FILE_BASE_URL, "/videos/"):
        if value.startswith(prefix):
            return file_suffix(value.removeprefix(prefix))
    return file_suffix(value)


def file_suffixes(values: Sequence[str]) -> list[str]:
    """Validate the whole batch before any download starts, preserving order."""
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise TypeError("suffixes must be a sequence of file suffix strings")
    return [file_suffix(value) for value in values]
