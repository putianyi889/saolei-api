# saolei-api v0.1.0

Python 3.11+ client for all five documented saolei.wang public API endpoints:
stats, video_list, video_info, user_info, and user_list.

- Reusable synchronous and asynchronous HTTPX clients with API key authentication.
- Typed Pydantic models with snake_case attributes, upstream JSON aliases, and preserved extra fields.
- Lazy video pagination, incremental cursors, batch-size validation, and a default 2-second interval.
- Explicit authentication, rate limit, HTTP, transport, and response exceptions.
- Chinese documentation, offline tests, and an opt-in bounded live verification script.

Install the wheel attached to this release with `python -m pip install <wheel-url>`.
The source archive and documentation are included. `SHA256SUMS` covers all release artifacts.

Data source: 扫雷网 saolei.wang. Bring your own API key, issued by the site administrator.
Only the documented public API is supported. This package is a third-party client.
