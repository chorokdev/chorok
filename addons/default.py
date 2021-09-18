import dico  # noqa
import dico_command
import dico_interaction as dico_inter

import utils.formatter
from models import ChorokBot, Colors


def load(bot: ChorokBot) -> None:
    bot.load_addons(Default)


def unload(bot: ChorokBot) -> None:
    bot.unload_addons(Default)


class Default(dico_command.Addon):  # type: ignore[call-arg, misc]
    name = "기본"

    @dico_inter.command(name="ping", description="봇의 명령어 응답 속도를 확인합니다.")
    async def _ping(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.send(embed=dico.Embed(
            title="퐁!",
            description=f"**Discord 게이트웨이:** `{round(self.bot.ws.ping * 1000)}ms`",
            color=Colors.information))

    @dico_inter.command(name="invite", description="봇의 초대 링크를 보냅니다.")
    async def _invite(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.send(embed=dico.Embed(
            title="초록 초대하기",
            description=f"[여기를 눌러]({utils.formatter.create_invite_link(self.bot.application_id, 28624960)})"
            f" 초록을 초대하실 수 있습니다.",
            color=Colors.information))

    @dico_inter.command(name="support", description="공식 서포트 서버의 링크를 보냅니다.")
    async def _support(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.send(embed=dico.Embed(
            title="공식 서포트 서버",
            description=f"[여기를 눌러](https://discord.gg/P25nShtqFX) 공식 서포트 서버에 입장하실 수 있습니다.",
            color=Colors.information))
