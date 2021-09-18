import sys

import dico  # noqa

import utils
from models import ChorokBot

config = utils.config.load("config.json", sys.argv[1])
if not config:
    raise SystemError("invalid config")

bot = ChorokBot(config.token["discord"],
                "",
                intents=dico.Intents.no_privileged(),
                default_allowed_mentions=dico.AllowedMentions())

bot.run()
