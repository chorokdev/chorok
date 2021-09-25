import asyncio
import contextlib

import aiohttp
import dico  # noqa


class KoreanbotsClient:
    BASE = "https://koreanbots.dev/api/v2"

    def __init__(self,
                 client: dico.Client,
                 token: str,
                 auto_post: bool = False) -> None:
        self.client = client
        self.token = token
        self._session: aiohttp.ClientSession = aiohttp.ClientSession()

        if auto_post:
            self.post_guilds_automatically()

    async def post_guilds(self) -> None:
        async with self._session.post(
                f"{self.BASE}/bots/{self.client.application_id}/stats",
                headers={"Authorization": self.token},
                json={
                    "servers": self.client.guild_count,
                    "shards": self.client.shard_count,
                },
        ) as resp:
            resp.raise_for_status()

    def post_guilds_automatically(self) -> None:
        async def async_callback() -> None:
            while True:
                with contextlib.suppress(Exception):
                    await self.post_guilds()
                    await asyncio.sleep(60 * 30)

        self.client.loop.create_task(async_callback())
