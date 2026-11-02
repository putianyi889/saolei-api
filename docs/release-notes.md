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
