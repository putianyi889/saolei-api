"""Opt-in bounded live smoke test. Never used by CI; key is read from the environment."""

import asyncio
import json
import os

from saolei_api import AsyncClient, Client


async def main() -> None:
    key = os.environ["SAOLEI_API_KEY"]
    with Client(key) as api:
        stats = api.stats()
        page = api.video_list(size=2)
        if not page.items:
            raise RuntimeError("Expected at least one public video")
        video = page.items[0]
        details = api.video_info([video.id])
        users = api.user_info([video.user_id])
        summaries = api.user_list([video.user_id])
        assert details.items and details.items[0].id == video.id
        assert users.users and users.users[0].id == video.user_id
        assert summaries.users and summaries.users[0].id == video.user_id
        # At most two pages; never start a full synchronization for a smoke test.
        videos = list(api.iter_videos(size=1, max_pages=2))
        assert len(videos) == 2 and videos[0].id < videos[1].id
    async with AsyncClient(key) as api:
        async_stats = await api.stats()
        assert async_stats.max_user_id >= stats.max_user_id
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
                "generated_at": stats.generated_at,
                "max_video_id": stats.max_video_id,
                "max_user_id": stats.max_user_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
