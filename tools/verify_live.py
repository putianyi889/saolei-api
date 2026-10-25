"""Opt-in bounded live smoke test. Never used by CI; key is read from the environment."""

import argparse
import asyncio
import json
import os

from saolei_api import AsyncClient, Client


async def main(*, download_videos: bool = False) -> None:
    key = os.environ["SAOLEI_API_KEY"]
    downloaded: list[bytes] = []
    suffixes: list[str] = []
    with Client(key) as api:
        stats = api.stats()
        page = api.video_list(size=2)
        if not page.items:
            raise RuntimeError("Expected at least one public video")
        video = page.items[0]
        details = api.video_info([item.id for item in page.items])
        users = api.user_info([video.user_id])
        summaries = api.user_list([video.user_id])
        assert details.items and details.items[0].id == video.id
        assert users.users and users.users[0].id == video.user_id
        assert summaries.users and summaries.users[0].id == video.user_id
        # At most two pages; never start a full synchronization for a smoke test.
        videos = list(api.iter_videos(size=1, max_pages=2))
        assert len(videos) == 2 and videos[0].id < videos[1].id
        if download_videos:
            suffixes = [item.file_url for item in details.items if item.file_url is not None][:2]
            assert suffixes and all(not value.startswith("/") for value in suffixes)
            downloaded = api.download_videos(suffixes)
            assert len(downloaded) == len(suffixes) and all(downloaded)
    async with AsyncClient(key) as api:
        async_stats = await api.stats()
        assert async_stats.max_user_id >= stats.max_user_id
        if download_videos:
            assert await api.download_videos(suffixes) == downloaded
    print(
        json.dumps(
            {
                "endpoints_verified": [
                    "stats",
                    "video_list",
                    "video_info",
                    "user_info",
                    "user_list",
                ],
                "sync_and_async": True,
                "pagination_pages": 2,
                "downloaded_files_per_client": len(downloaded),
                "downloaded_bytes_per_client": sum(map(len, downloaded)),
                "generated_at": stats.generated_at,
                "max_video_id": stats.max_video_id,
                "max_user_id": stats.max_user_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--download-videos",
        action="store_true",
        help="Also fetch up to two public recording files with each client (up to four downloads)",
    )
    asyncio.run(main(download_videos=parser.parse_args().download_videos))
