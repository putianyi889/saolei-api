# saolei-api v0.2.0

Adds batch recording-file downloads to the synchronous and asynchronous clients.

- `VideoInfo.file_url` now returns only `YYYY/MM/DD/filename`; serialized `fileUrl` uses the same suffix.
  This changes the v0.1.0 full-URL behavior. `None` remains unchanged.
- `Client.download_videos(suffixes)` and `await AsyncClient.download_videos(suffixes)` return
  recording contents as `list[bytes]` in input order, including duplicates.
- File downloads have a separate 0.4-second default interval, shared across batches on one client.
  Data API requests retain their 2-second default interval.
- All suffixes are validated before the first request. Downloads stay on the official file origin,
  stop on the first HTTP/network error, and use the existing exception hierarchy without retries.
- The opt-in live verifier accepts `--download-videos` for at most four additional file requests.

Install the wheel attached to this release with `python -m pip install <wheel-url>`.
The source archive and documentation are included. `SHA256SUMS` covers all release artifacts.

Data source: 扫雷网 saolei.wang. Bring your own API key, issued by the site administrator.
Only the documented public API and its recording files are supported. This is a third-party client.
