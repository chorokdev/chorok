import contextlib
import enum
import logging
import os
import traceback
from typing import Any

import dico  # noqa
import dico.utils  # noqa
import dico_command
import dico_interaction as dico_inter
import discodo  # noqa
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
    def __init__(self, config: dict[str, Any], *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        dico_inter.InteractionClient(client=self, auto_register_commands=True)

        self.config: dict[str, Any] = config
        self.bot_logger = logging.getLogger("bot")
        self.audio = utils.discodo.DicoClient(self)
        self.koreanbots = utils.koreanbots.KoreanbotsClient(
            self, k_token := config["token"]["koreanbots"], bool(k_token))
        self.redis_cache = utils.cache.CacheClient(**config["cache"])

        for node_conf in self.config["node"]:
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
        self.on_("voice_state_update", self._voice_state_update_handler)
        self.on_("interaction_error", self._interaction_error_handler)

    def load_modules(self) -> None:
        for filename in os.listdir("addons"):
            if filename.endswith(".py"):
                try:
                    self.load_module(f"addons.{filename[:-3]}")
                    self.bot_logger.info(f"loaded module 'addons/{filename}'")
                except dico_command.ModuleAlreadyLoaded:
                    self.reload_module(f"addons.{filename[:-3]}")
                    self.bot_logger.info(
                        f"reloaded module 'addons/{filename}'")
                except dico_command.InvalidModule:
                    self.bot_logger.warning(
                        f"skipping invalid module 'addons/{filename}'")
                    continue

    async def _ready_handler(self, ready: dico.Ready) -> None:
        self.bot_logger.info(
            f"logged in as '{ready.user}' and can see {ready.guild_count} guilds and {len(self.shards)} shards"
        )
        self.load_modules()

        for index, shard in enumerate(self.shards):
            await shard.update_presence(activities=[
                dico.Activity(
                    name=f"/help, {index + 1}호기",
                    activity_type=dico.ActivityTypes.LISTENING).to_dict()
            ],
                status="online",
                afk=False,
                since=None)

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
            await ctx.send(embed=dico.Embed(
                description="알 수 없는 오류가 발생했습니다.\n"
                "오류가 계속 발생할 경우 [서포트 서버](https://discord.gg/P25nShtqFX)의 버그 채널에 문의하시기 바랍니다.\n"
                "```py\n" + tb + "\n```",
                color=Colors.error))
        self.bot_logger.error(
            f"an error occurred while handling '{ctx.data.name}'",
            exc_info=(type(error), error, error.__traceback__))

    async def _voice_state_update_handler(self, vs: dico.VoiceState) -> None:
        vc: discodo.VoiceClient = self.audio.get_vc(vs.guild_id, safe=True)

        if all((vs.user_id == self.application_id, vc, not vs.channel_id)):
            with contextlib.suppress(Exception):
                await vc.destroy()

        if not vc:
            return
