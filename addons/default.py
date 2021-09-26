from typing import Any

import dico  # noqa
import dico_command
import dico_interaction as dico_inter
import psutil
from humanize import naturalsize

import utils
from models import ChorokBot, Colors


def load(bot: ChorokBot) -> None:
    bot.load_addons(Default)


def unload(bot: ChorokBot) -> None:
    bot.unload_addons(Default)


async def get_node_info(guild_id: dico.Guild.TYPING,
                        bot: ChorokBot) -> list[str]:
    if vc := bot.audio.get_vc(guild_id, safe=True):
        status: dict[str, Any] = vc.Node.getStatus()
        return [
            f"**{vc.Node.region}**"
            f"RAM: {naturalsize(status['UsedMemory'] * 1000000)}/{naturalsize(status['TotalMemory'] * 1000000)}\n"
            f"스레드 수: {status['Threads']}\n"
            f"인바운드: {naturalsize(status['NetworkInbound'] * 1000000)}\n"
            f"아웃바운드: {naturalsize(status['NetworkOutbound'] * 1000000)}\n"
        ]

    return [
        f"**{node.region}**\n"
        f"RAM: {naturalsize(status['UsedMemory'] * 1000000)}/{naturalsize(status['TotalMemory'] * 1000000)}\n"
        f"스레드 수: {status['Threads']}\n"
        f"인바운드: {naturalsize(status['NetworkInbound'] * 1000000)}\n"
        f"아웃바운드: {naturalsize(status['NetworkOutbound'] * 1000000)}\n"
        for status, node in [(await node.getStatus(), node)
                             for node in bot.audio.nodes]
    ]


class Default(dico_command.Addon):  # type: ignore[call-arg, misc]
    bot: ChorokBot
    name = "기본"

    @dico_inter.command(name="information", description="봇의 정보를 확인합니다.")
    async def _information(self, ctx: dico_inter.InteractionContext) -> None:
        embed = dico.Embed(title="정보", color=Colors.information)
        embed.add_field(
            name="봇",
            value=f"{len(self.bot.audio.voice_clients)}/{self.bot.guild_count} (노래를 재생중인 서버/총 서버)",
        )

        memory = psutil.virtual_memory()
        embed.add_field(
            name="서버",
            value=f"CPU: {psutil.cpu_percent()}%\n"
            f"RAM: {naturalsize(memory.used)}/{naturalsize(memory.total)}",
            inline=False,
        )

        embed.add_field(name="노드",
                        value="\n".join(await
                                        get_node_info(ctx.guild_id, self.bot)))
        await ctx.send(embed=embed)

    @dico_inter.command(name="ping", description="봇의 명령어 응답 속도를 확인합니다.")
    async def _ping(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.send(embed=dico.Embed(
            title="퐁!",
            description=f"**Discord 게이트웨이:** `{round(self.bot.ping * 1000)}ms`",
            color=Colors.information,
        ))

    @dico_inter.command(name="invite", description="봇의 초대 링크를 보냅니다.")
    async def _invite(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.send(embed=dico.Embed(
            title="초대하기",
            description=f"[여기를 눌러]({utils.formatter.create_invite_link(str(self.bot.application_id), 28624960)})"
            f" 초록을 초대하실 수 있습니다.",
            color=Colors.information,
        ))

    @dico_inter.command(name="support", description="공식 서포트 서버의 링크를 보냅니다.")
    async def _support(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.send(embed=dico.Embed(
            title="공식 서포트 서버",
            description=f"[여기를 눌러](https://discord.gg/P25nShtqFX) 공식 서포트 서버에 입장하실 수 있습니다.",
            color=Colors.information,
        ))
