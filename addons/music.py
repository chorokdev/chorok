from typing import Optional, Union, Any

import dico  # noqa
import dico_command
import dico_interaction as dico_inter
import discodo  # noqa

import utils
from models import ChorokBot, Colors


def load(bot: ChorokBot) -> None:
    bot.load_addons(Music)


def unload(bot: ChorokBot) -> None:
    bot.unload_addons(Music)


class Music(dico_command.Addon):  # type: ignore[call-arg, misc]
    bot: ChorokBot

    def __init__(self, bot: ChorokBot) -> None:
        super(Music, self).__init__(bot)
        self.bot.audio.dispatcher.on("SOURCE_START", self.send_next_source)

    async def connect_voice(
            self, voice_channel: dico.Channel,
            text_channel_id: dico.Snowflake) -> discodo.VoiceClient:
        vc = await self.bot.audio.connect(voice_channel)
        await vc.setContext({
            "textChannel": int(text_channel_id),
        })

        return vc

    async def send_next_source(self, voice: discodo.VoiceClient,
                               data: dict[str, Any]) -> None:
        channel: dico.Channel = self.bot.get(voice.context["textChannel"],
                                             storage_type="channel")
        await channel.send(embed=dico.Embed(
            title="현재 재생중",
            description=f"[{data['source']['title']}]({data['source']['webpage_url']})",
            color=Colors.default))

    @dico_inter.command(name="join", description="음성 채널에 입장합니다.")
    async def _join(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.defer()

        await self.connect_voice(ctx.author.user.voice_state.channel,
                                 ctx.channel_id)
        await ctx.send(embed=dico.Embed(
            description=f"{ctx.author.user.voice_state.channel.mention}에 입장했습니다.",
            color=Colors.information))

    @dico_inter.command(name="play",
                        description="노래를 재생합니다.",
                        options=[
                            dico.ApplicationCommandOption(
                                dico.ApplicationCommandOptionType.STRING,
                                "query", "검색할 내용이나 링크", True)
                        ])
    async def _play(self, ctx: dico_inter.InteractionContext,
                    query: str) -> None:
        await ctx.defer()

        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id,
                                                        safe=True)
        if not vc:
            vc = await self.connect_voice(ctx.author.user.voice_state.channel,
                                          ctx.channel_id)

        data: Union[discodo.AudioData,
                    list[discodo.AudioData]] = await vc.loadSource(query)

        if isinstance(data, list):
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data[0].title}]({data[0].webpage_url}) 외 {len(data) - 1}개",
                color=Colors.default)
        else:
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data.title}]({data.webpage_url})",
                color=Colors.default)

        await ctx.send(embed=embed)

    @dico_inter.command(name="skip",
                        description="현재 재생중인 노래를 건너뜁니다.",
                        options=[
                            dico.ApplicationCommandOption(
                                dico.ApplicationCommandOptionType.INTEGER,
                                "offset",
                                "스킵할 곡의 개수",
                                required=False)
                        ])
    async def _skip(self,
                    ctx: dico_inter.InteractionContext,
                    offset: Optional[int] = 1) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        await vc.skip(offset)
        await ctx.send(embed=dico.Embed(
            description=f"성공적으로{f' {offset}개의' if offset > 1 else ''} 곡을 스킵했습니다.",
            color=Colors.information))

    @dico_inter.command(name="stop", description="대기열을 초기화하고 음성 채널에서 나갑니다.")
    async def _stop(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        await vc.destroy()
        await ctx.send(embed=dico.Embed(
            description="대기열을 초기화하고 음성 채널에서 나갔습니다.", color=Colors.information))

    @dico_inter.command(name="volume",
                        description="볼륨을 조절하거나 확인합니다.",
                        options=[
                            dico.ApplicationCommandOption(
                                dico.ApplicationCommandOptionType.INTEGER,
                                "percent",
                                "조절할 볼륨의 퍼센트(숫자만)",
                                required=False)
                        ])
    async def _volume(self,
                      ctx: dico_inter.InteractionContext,
                      percent: Optional[int] = None) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        if not percent:
            await ctx.send(embed=dico.Embed(
                title="현재 볼륨",
                description=f"**{round(vc.volume * 100, 1)}**%",
                color=Colors.information))
            return

        await vc.setVolume(percent / 100)
        await ctx.send(embed=dico.Embed(
            description=f"볼륨을 **{round(vc.volume * 100, 1)}**%로 설정했습니다.",
            colors=Colors.information))

    @dico_inter.command(name="nowplaying", description="현재 재생중인 노래를 확인합니다")
    async def _nowplaying(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        chapters = list(
            filter(
                lambda x: x["start_time"] <= vc.current.position < x["end_time"],
                vc.current.get("chapters") or [],
            ))
        chapter = chapters[0] if chapters else None
        if not vc.current:
            embed = dico.Embed(title="현재 재생중인 노래",
                               description="현재 재생중인 노래가 없습니다.",
                               color=Colors.error)
        else:
            chapter_str = (
                f"`[{utils.formatter.duration_format(chapter['start_time'])} ~"
                f" {utils.formatter.duration_format(chapter['end_time'])}]`"
                f" **{chapter['title']}**\n" if chapter else "")
            progress_bar = (
                f"{utils.formatter.make_progress_bar(vc.position, vc.duration)}\n"
                + f"`{utils.formatter.duration_format(vc.position)}/"
                f"{utils.formatter.duration_format(vc.duration)}`"
                if not vc.current.is_live else "`🔴LIVE`")
            embed = dico.Embed(
                title="현재 재생중인 노래",
                description=f"{chapter_str}\n"
                f"[{vc.current.title}]"
                f"({vc.current.webpage_url})\n"
                f"{progress_bar}\n\n",
                color=Colors.information,
            )
            if vc.current.thumbnail:
                embed.set_thumbnail(url=vc.current.thumbnail)

        await ctx.send(embed=embed)
