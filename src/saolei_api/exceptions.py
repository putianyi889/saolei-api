"""Public exceptions. Messages do not include request headers or response bodies."""


class SaoleiError(Exception):
    """Base class for errors from this package."""


class TransportError(SaoleiError):
    """The request failed before a usable HTTP response arrived."""


class APIError(SaoleiError):
    """An HTTP error; status_code is available for application-specific handling."""

    def __init__(self, status_code: int, endpoint: str) -> None:
        self.status_code = status_code
        self.endpoint = endpoint
        super().__init__(f"saolei.wang API returned HTTP {status_code} for {endpoint}")


class AuthenticationError(APIError):
    """The API key was missing, invalid, or forbidden (401/403)."""


class RateLimitError(APIError):
    """HTTP 429. retry_after is seconds, or None if absent/unparseable."""

    def __init__(self, endpoint: str, retry_after: float | None) -> None:
        self.retry_after = retry_after
        super().__init__(429, endpoint)


class ResponseError(SaoleiError):
    """A response is invalid JSON, violates the schema, or has a broken cursor."""
