import contextlib
import enum
import itertools
import logging
import os
import traceback
from typing import Any

import dico  # noqa
import dico.utils  # noqa
import dico_command
import dico_interaction as dico_inter
from dico_command import Bot
from dico_interaction.exception import CheckFailed
from rich.logging import RichHandler

import utils

logging.basicConfig(
    level=logging.INFO,
    handlers=[RichHandler(rich_tracebacks=True)],
    format="%(name)s :\t%(message)s",
)


class Colors(enum.IntEnum):
    default = 0x1DD1A1
    information = 0xF9CA24
    error = 0xFF3838


class ChorokBot(Bot):  # type: ignore[call-arg, misc]
    def __init__(self, config: utils.config.Config, *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        dico_inter.InteractionClient(client=self)

        self.config: utils.config.Config = config
        self.bot_logger = logging.getLogger("bot")
        self.audio = utils.discodo.DicoClient(self)
        self.koreanbots = utils.koreanbots.KoreanbotsClient(
            self, k_token := config.token["koreanbots"], bool(k_token))
        self.redis_cache = utils.cache.CacheClient(**config.cache)

        for node_conf in self.config.node:
            if node_conf.get("local", False) or not any(
                (node_conf.get(key, None)
                 for key in ("host", "port", "password"))):
                self.audio.register_node()
                break
            self.audio.register_node(
                host=node_conf["host"],
                port=node_conf["port"],
                password=node_conf["password"],
            )

        self.on_("ready", self._ready_handler)
        self.on_("interaction_error", self._interaction_error_handler)

    def load_modules(self) -> None:
        for filename in os.listdir("addons"):
            if filename.endswith(".py"):
                try:
                    self.load_module(f"addons.{filename[:-3]}")
                    self.bot_logger.info(f"loaded module addons/{filename}")
                except dico_command.ModuleAlreadyLoaded:
                    self.reload_module(f"addons.{filename[:-3]}")
                    self.bot_logger.info(f"reloaded module addons/{filename}")
                except dico_command.InvalidModule:
                    self.bot_logger.warning(
                        f"skipping invalid module addons/{filename}")
                    continue

    async def _ready_handler(self, ready: dico.Ready) -> None:
        self.bot_logger.info(f"logged in as {ready.user}")
        self.load_modules()
        await self.register_slash_commands()

    async def _interaction_error_handler(  # noqa
            self, ctx: dico_inter.InteractionContext,
            error: Exception) -> None:
        if isinstance(error, CheckFailed):
            return

        tb: str = "".join(
            traceback.format_exception(type(error), error,
                                       error.__traceback__))
        tb = ("..." + tb[-1997:]) if len(tb) > 2000 else tb
        with contextlib.suppress(Exception):
            if not ctx.deferred:
                await ctx.defer()
            await ctx.send("```py\n" + tb + "\n```")
        raise error

    async def register_slash_commands(self) -> None:
        await self.bulk_overwrite_application_commands(
            *list(
                itertools.chain.from_iterable(
                    [[inter.command for inter in addon.interactions]
                     for addon in self.addons])),
            guild=self.config.slash_command_guild,
        )
