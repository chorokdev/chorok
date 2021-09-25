import aioredis
import dico  # noqa


class CacheClient:
    def __init__(self, host: str, port: int = 6379) -> None:
        self.host = host
        self.port = port

        self.redis: aioredis.Redis = aioredis.from_url(
            f"redis://{self.host}:{self.port}")  # type: ignore

    async def get_users(self, channel: dico.Channel) -> list[str]:
        users: list[str] = []

        for i in range(0, await self.redis.llen(str(channel.id))):
            users.append(str(await self.redis.lindex(str(channel.id), i)))

        return users

    async def add_user(self, channel: dico.Channel,
                       user: dico.Snowflake) -> None:
        if str(user) in (await self.get_users(channel)):
            return

        await self.redis.lpush(str(channel.id), str(user.id))
