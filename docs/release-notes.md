# saolei-api v0.3.0

Updates the client to match the official API documentation checked on 2026-10-26.

- `video_list(player_id=...)` and `iter_videos(player_id=...)` support the new positive-integer
  player filter in both synchronous and asynchronous clients, preserving it across all pages.
- `Video.status` is now a required typed field inherited by `VideoInfo`.
  The upstream list includes all review states: 0 (blocked), 10 (pending), and 20 (approved).
  Applications requiring only approved recordings should filter `video.status == 20`.
- Updated official fixtures, parameter/status regression tests, documentation, and live verification.
  The bounded verifier checks player filtering, cursor pagination, and recent recording schemas.
- Recording URL suffixes and ordered batch file downloads remain available.

Install the wheel attached to this release with `python -m pip install <wheel-url>`.
The source archive and documentation are included. `SHA256SUMS` covers all release artifacts.

Data source: 扫雷网 saolei.wang. Bring your own API key, issued by the site administrator.
Only the documented public API and its recording files are supported. This is a third-party client.
