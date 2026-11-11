# saolei-api v0.4.2

Fixes `video_info` batches against the official API's new recording download address
(checked 2026-11-11). Since the site switched `fileUrl` from
`https://saolei.wang/videos/YYYY/MM/DD/filename` to
`https://saolei.wang/video/download/{id}`, the old strict suffix validator rejected
every item and a single detail request could fail a whole 50-video batch.

- `VideoInfo.file_url` now preserves the official download address instead of raising
  a validation error. Legacy `/videos/` URLs are still normalized to
  `YYYY/MM/DD/filename`, root-relative download addresses are made absolute, and
  missing, blank or `None` values all mean "no file".
- `signature`, `metrics` and `file_url` may be omitted by the upstream response and
  default to `None`.
- Unrecognized `fileUrl` strings are kept for download-time validation rather than
  breaking the whole response; `download_videos` stays restricted to official
  `https://saolei.wang/videos/` and `/video/download/` paths.
- `download_videos` accepts both legacy suffixes and the new official addresses.
  Each result is a `bytes` subclass `VideoFile` whose `name` carries the safe
  `Content-Disposition` filename when the server supplies one, so callers can still
  choose the correct replay parser.
- `ResponseError` schema messages now also list the Pydantic error categories
  (for example `missing` or `value_error`) without exposing response values.
- Documentation, fixtures, release tooling and the packaged `User-Agent` follow v0.4.2.

Data source: 扫雷网 saolei.wang. Bring your own API key, issued by the site administrator.
Only the documented public API and its recording files are supported. This is a third-party client.

# saolei-api v0.4.1

Fixes catalogue sync against the current official API (checked 2026-11-02).

- `VideoListResponse.next_cursor` is now `int | None`: the last page of `video_list`
  returns `nextCursor: null`, which 0.4.0 rejected as a schema error. Every paged
  catalogue stopped one page early and lost that page.
- Added `Video.no_record` / `VideoInfo.no_record` (`noRecord`) for luck boards
  (3BV below the level minimum: beg < 2, int < 30, exp < 100). Responses that omit
  the field still parse and default to `False`.
- `ResponseError` for schema mismatches now ends with the offending field locations,
  so callers can see which field broke without reading the response body.
- Documentation, fixtures, examples and the packaged `User-Agent` follow the current
  official contract, including `player_id`, all review statuses and `noRecord`.

Data source: 扫雷网 saolei.wang. Bring your own API key, issued by the site administrator.
Only the documented public API and its recording files are supported. This is a third-party client.

# saolei-api v0.4.0

Adds the two post endpoints documented by the official API on 2026-10-29.

- `post_info(ids)` retrieves public metadata for up to 50 post IDs.
- `post_search(keyword, cursor=...)` searches titles with a 1–30 character keyword,
  returning 20 results per page in descending ID order.
- `iter_posts(keyword, max_pages=...)` lazily follows decreasing cursors and stops at the null end cursor.
  Malformed/non-decreasing cursors raise `ResponseError` instead of looping.
- All three methods support synchronous and asynchronous clients and reuse existing throttling,
  HTTPX connections, argument validation, and errors.
- Exported `Post`, `PostInfoResponse`, and `PostSearchResponse` models preserve timestamp aliases,
  board numbers, reply/view counts, and pinned/featured/locked flags.
- Added official examples, offline regression coverage, documentation, and bounded live post checks.
  Post bodies and reply contents are outside the public API scope and are not fetched.

Install the wheel attached to this release with `python -m pip install <wheel-url>`.
The source archive and documentation are included. `SHA256SUMS` covers all release artifacts.

Data source: 扫雷网 saolei.wang. Bring your own API key, issued by the site administrator.
Only the documented public API and its recording files are supported. This is a third-party client.
