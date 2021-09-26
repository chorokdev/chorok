import aioredis
import dico  # noqa


class CacheClient:
    def __init__(self, host: str, port: int = 6379) -> None:
        self.host = host
        self.port = port

        self.redis: aioredis.Redis = aioredis.from_url(
            f"redis://{self.host}:{self.port}")  # type: ignore

    async def get_users(self, channel: dico.Channel.TYPING) -> list[str]:
        users: list[str] = []

        for i in range(0, await self.redis.llen(str(channel.id))):
            users.append((await self.redis.lindex(str(channel.id),
                                                  i)).decode())

        return users

    async def add_user(self, channel: dico.Channel.TYPING,
                       user: dico.User.TYPING) -> None:
        if str(user.id) in (await self.get_users(channel)):
            return

        await self.redis.lpush(str(channel.id), str(user.id))

    async def delete_user(self, channel: dico.Channel.TYPING,
                          user: dico.User.TYPING) -> None:
        if str(user.id) not in (await self.get_users(channel)):
            return

        await self.redis.lrem(str(channel.id), 1, str(user.id))
