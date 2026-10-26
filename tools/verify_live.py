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
    player_id = 1
    with Client(key) as api:
        stats = api.stats()
        page = api.video_list(player_id=player_id, size=2)
        if not page.items:
            raise RuntimeError("Expected at least one public video")
        assert all(item.user_id == player_id for item in page.items)
        video = page.items[0]
        # The list includes blocked recordings, which video_info omits. The fallback
        # is a public example ID from the official documentation, not an ID scan.
        detail_ids = [item.id for item in page.items if item.status in (10, 20)] or [328090]
        details = api.video_info(detail_ids)
        users = api.user_info([video.user_id])
        summaries = api.user_list([video.user_id])
        assert details.items and all(item.id in detail_ids for item in details.items)
        assert users.users and users.users[0].id == video.user_id
        assert summaries.users and summaries.users[0].id == video.user_id
        # At most two pages; never start a full synchronization for a smoke test.
        videos = list(api.iter_videos(player_id=player_id, size=1, max_pages=2))
        assert len(videos) == 2 and videos[0].id < videos[1].id
        assert all(item.user_id == player_id for item in videos)
        # Check recent records as well as old approved records: the updated list
        # can include pending/blocked items with different score values.
        recent = api.video_list(cursor=max(0, stats.max_video_id - 5), size=5)
        if download_videos:
            suffixes = [item.file_url for item in details.items if item.file_url is not None][:2]
            assert suffixes and all(not value.startswith("/") for value in suffixes)
            downloaded = api.download_videos(suffixes)
            assert len(downloaded) == len(suffixes) and all(downloaded)
    async with AsyncClient(key) as api:
        async_stats = await api.stats()
        assert async_stats.max_user_id >= stats.max_user_id
        async_page = await api.video_list(player_id=player_id, size=2)
        assert async_page.items and all(item.user_id == player_id for item in async_page.items)
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
                "player_filter_verified": player_id,
                "list_statuses_observed": sorted(
                    {item.status for item in [*page.items, *recent.items]}
                ),
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
