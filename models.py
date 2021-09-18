import enum
import logging
import os
from typing import Any

import dico  # noqa
import dico_command
import dico_interaction
from dico_command import Bot
from rich.logging import RichHandler

logging.basicConfig(level=logging.INFO,
                    handlers=[RichHandler()],
                    format="%(name)s :\t%(message)s")


class Colors(enum.IntEnum):
    default = 0x1DD1A1
    information = 0xF9CA24
    error = 0xFF3838


class ChorokBot(Bot):  # type: ignore[call-arg, misc]
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        dico_interaction.InteractionClient(client=self)

        self.bot_logger = logging.getLogger("bot")

        self.on_ready = self._ready_handler

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

    def _ready_handler(self, ready: dico.Ready) -> None:
        self.bot_logger.info(f"logged in as {ready.user}")
        self.load_modules()
        self.loop.create_task(self.register_slash_commands())

    async def register_slash_commands(self) -> None:
        for addon in self.addons:
            await self.bulk_overwrite_application_commands(
                *[interaction.command for interaction in addon.interactions])
