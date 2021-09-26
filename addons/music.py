import contextlib
from typing import Any, Optional, Union

import dico  # noqa
import dico_command
import dico_interaction as dico_inter
import discodo  # noqa
from discodo.client.models import AudioData, AudioSource  # noqa

from models import ChorokBot, Colors
from utils.formatter import create_page, duration_format, make_progress_bar


def load(bot: ChorokBot) -> None:
    bot.load_addons(Music)


def unload(bot: ChorokBot) -> None:
    bot.unload_addons(Music)


def on_voice_channel(ctx: dico_inter.InteractionContext) -> bool:
    if isinstance(ctx.author, dico.User):
        ctx.client.loop.create_task(  # noqa
            ctx.send("이 명령어는 초록이 있는 서버에서만 사용할 수 있습니다.", ephemeral=True))
        return False
    if not bool(ctx.author.user.voice_state):
        ctx.client.loop.create_task(  # noqa
            ctx.send(
                "이 명령어는 음성 채널에서만 사용할 수 있습니다.\n"
                "만약 이미 음성 채널에 있다면 나갔다 들어와 다시 시도해 보시기 바랍니다.",
                ephemeral=True,
            ))
        return False
    return True


def on_playing(ctx: dico_inter.InteractionContext) -> bool:
    vc: discodo.VoiceClient = ctx.client.audio.get_vc(  # noqa
        ctx.guild_id,
        safe=True)
    ctx.client.loop.create_task(vc.getCurrent())  # noqa

    if not vc or not vc.current:
        ctx.client.loop.create_task(  # noqa
            ctx.send("이 명령어는 노래가 재생 중일 때만 사용하실 수 있습니다.", ephemeral=True))
        return False
    return True


def on_same_voice_channel(ctx: dico_inter.InteractionContext) -> bool:
    vc: discodo.VoiceClient = ctx.client.audio.get_vc(ctx.guild_id, safe=True)  # noqa
    if not vc or not ctx.author.user.voice_state:
        return True

    if vc.channel_id == ctx.author.user.voice_state.channel_id:
        return True

    ctx.client.loop.create_task( # noqa
        ctx.send(f"이 명령어는 <#{vc.channel_id}> 채널에서만 사용하실 수 있습니다.", ephemeral=True)
    )
    return False


class Music(dico_command.Addon):  # type: ignore[call-arg, misc]
    bot: ChorokBot
    name = "뮤직"

    def on_load(self) -> None:
        self.bot.audio.dispatcher.on("SOURCE_START", self.send_next_source)

    def on_unload(self) -> None:
        self.bot.audio.dispatcher.off("SOURCE_START", self.send_next_source)

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
        with contextlib.suppress(Exception):
            await self.bot.delete_message(channel,
                                          voice.context["lastMessage"])
        message: dico.Message = await channel.send(embed=dico.Embed(
            title="현재 재생 중" if not data["source"]["related"] else "추천 영상 재생 중",
            description=f"[{data['source']['title']}]({data['source']['webpage_url']})",
            color=Colors.default,
        ))
        voice.context["lastMessage"] = int(message.id)
        await voice.setContext(voice.context)

    def set_requester(self, vc: discodo.VoiceClient,
                      requester: dico.Snowflake) -> None:
        async def async_callback() -> None:
            await self.bot.audio.dispatcher.wait_for(
                "SOURCE_START", lambda v, d: v.guild_id == vc.guild_id)
            await (await
                   vc.getCurrent()).setContext({"requester": int(requester)})

        self.bot.loop.create_task(async_callback())

    @dico_inter.command(name="join", description="음성 채널에 입장합니다.")
    @dico_inter.deco.checks(on_voice_channel)
    async def _join(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.defer()

        await self.connect_voice(ctx.author.user.voice_state.channel,
                                 ctx.channel_id)
        await ctx.send(embed=dico.Embed(
            description=f"{ctx.author.user.voice_state.channel.mention}에 입장했습니다.",
            color=Colors.information,
        ))

    @dico_inter.command(
        name="play",
        description="노래를 재생합니다.",
        options=[
            dico.ApplicationCommandOption(
                dico.ApplicationCommandOptionType.STRING, "query",
                "검색할 내용이나 링크", True)
        ],
    )
    @dico_inter.deco.checks(on_voice_channel, on_same_voice_channel)
    async def _play(self, ctx: dico_inter.InteractionContext,
                    query: str) -> None:
        await ctx.defer()

        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id,
                                                        safe=True)
        if not vc:
            vc = await self.connect_voice(ctx.author.user.voice_state.channel,
                                          ctx.channel_id)

        data: Union[AudioData, list[AudioData]] = await vc.loadSource(query)

        if isinstance(data, list):
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data[0].title}]({data[0].webpage_url}) 외 {len(data) - 1}개",
                color=Colors.default,
            )
        else:
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data.title}]({data.webpage_url})",
                color=Colors.default,
            )
        self.set_requester(vc, ctx.author.user.id)

        await ctx.send(embed=embed)

    @dico_inter.command(name="재생하기",
                        command_type=dico.ApplicationCommandTypes.MESSAGE)
    @dico_inter.deco.checks(on_voice_channel, on_same_voice_channel)
    async def _play_context_menu(self,
                                 ctx: dico_inter.InteractionContext) -> None:
        await ctx.defer()

        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id,
                                                        safe=True)

        if not vc:
            vc = await self.connect_voice(
                ctx.target.author.voice_state.channel, ctx.channel_id)

        data: Union[AudioData,
                    list[AudioData]] = await vc.loadSource(ctx.target.content)

        if isinstance(data, list):
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data[0].title}]({data[0].webpage_url}) 외 {len(data) - 1}개",
                color=Colors.default,
            )
            for _ in data:
                self.set_requester(vc, ctx.author.user.id)
        else:
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data.title}]({data.webpage_url})",
                color=Colors.default,
            )
            self.set_requester(vc, ctx.author.user.id)

        await ctx.send(embed=embed)

    @dico_inter.command(
        name="skip",
        description="현재 재생중인 노래를 건너뜁니다.",
        options=[
            dico.ApplicationCommandOption(
                dico.ApplicationCommandOptionType.INTEGER,
                "offset",
                "스킵할 곡의 개수",
                required=False,
            )
        ],
    )
    @dico_inter.deco.checks(on_voice_channel, on_playing, on_same_voice_channel)
    async def _skip(self,
                    ctx: dico_inter.InteractionContext,
                    offset: int = 1) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        await vc.skip(offset)
        await ctx.send(embed=dico.Embed(
            description=f"성공적으로{f' {offset}개의' if offset > 1 else ''} 곡을 스킵했습니다.",
            color=Colors.information,
        ))

    @dico_inter.command(name="stop", description="대기열을 초기화하고 음성 채널에서 나갑니다.")
    @dico_inter.deco.checks(on_voice_channel)
    async def _stop(self, ctx: dico_inter.InteractionContext) -> None:
        await self.bot.audio.destroy(ctx.guild_id)
        await ctx.send(embed=dico.Embed(
            description="대기열을 초기화하고 음성 채널에서 나갔습니다.", color=Colors.information))

    @dico_inter.command(
        name="volume",
        description="볼륨을 조절하거나 확인합니다.",
        options=[
            dico.ApplicationCommandOption(
                dico.ApplicationCommandOptionType.INTEGER,
                "percent",
                "조절할 볼륨의 퍼센트(숫자만)",
                required=False,
            )
        ],
    )
    @dico_inter.deco.checks(on_voice_channel, on_playing, on_same_voice_channel)
    async def _volume(self,
                      ctx: dico_inter.InteractionContext,
                      percent: Optional[int] = None) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        if not percent:
            await ctx.send(embed=dico.Embed(
                title="현재 볼륨",
                description=f"**{round(vc.volume * 100, 1)}**%",
                color=Colors.information,
            ))
            return

        await vc.setVolume(percent / 100)
        await ctx.send(embed=dico.Embed(
            description=f"볼륨을 **{round(vc.volume * 100, 1)}**%로 설정했습니다.",
            colors=Colors.information,
        ))

    @dico_inter.command(name="nowplaying", description="현재 재생중인 노래를 확인합니다")
    @dico_inter.deco.checks(on_playing)
    async def _nowplaying(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        if not vc.current:
            embed = dico.Embed(title="현재 재생중인 노래",
                               description="현재 재생중인 노래가 없습니다.",
                               color=Colors.error)
        else:
            chapters = list(
                filter(
                    lambda x: x["start_time"] <= vc.current.position < x[
                        "end_time"],
                    vc.current.get("chapters", []),
                ))
            chapter = chapters[0] if chapters else None
            chapter_str = (
                f"\n\n`[{duration_format(chapter['start_time'])} ~ {duration_format(chapter['end_time'])}]`"
                f" **{chapter['title']}**" if chapter else "")
            progress_bar = (
                f"{make_progress_bar(vc.position, vc.duration)} "
                f"`[{duration_format(vc.position)}/{duration_format(vc.duration)}]`"
                if not vc.current.is_live else "`[🔴LIVE]`")
            embed = dico.Embed(
                title=f"{vc.current.title}",
                url=f"{vc.current.webpage_url}&t={int(vc.current.position)}",
                description=f"**요청**: <@{vc.current.context['requester']}>{chapter_str}\n{progress_bar}",
                color=Colors.information,
            )
            embed.set_author(name="현재 재생 중인 노래")
            if vc.current.thumbnail:
                embed.set_thumbnail(url=vc.current.thumbnail)

        await ctx.send(embed=embed)

    @dico_inter.command(name="queue", description="서버의 대기열을 확인합니다.")
    @dico_inter.deco.checks(on_playing)
    async def _queue(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        if not vc.Queue:
            await self._nowplaying.coro(ctx)
            return

        formatted_queue = create_page(
            [
                f"**{idx + 1}.** [{item.title}]({item.webpage_url})"
                for idx, item in enumerate(vc.Queue)
            ],
            1024,
        )
        embeds: list[dico.Embed] = [
            dico.Embed(
                title=f"{self.bot.get(ctx.guild_id).name}의 대기열",
                description="\n".join(page),
                color=Colors.information,
            ) for page in formatted_queue
        ]

        await ctx.send(embeds=embeds)

    @dico_inter.command(name="autoplay", description="자동 재생을 켜거나 끕니다.")
    @dico_inter.deco.checks(on_voice_channel, on_playing, on_same_voice_channel)
    async def _autoplay(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        await vc.setAutoplay(not vc.autoplay)

        await ctx.send(embed=dico.Embed(
            description=f"자동 재생을 {'켰' if vc.autoplay else '껐'}습니다.",
            color=Colors.information,
        ))

    @dico_inter.command(name="pause", description="노래를 일시정지합니다.")
    @dico_inter.deco.checks(on_voice_channel, on_playing, on_same_voice_channel)
    async def _pause(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        await vc.pause()

        await ctx.send(embed=dico.Embed(description="노래를 일시정지했습니다.",
                                        color=Colors.information))

    @dico_inter.command(name="resume", description="노래를 다시 재생합니다.")
    @dico_inter.deco.checks(on_voice_channel, on_same_voice_channel)
    async def _resume(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        await vc.resume()

        await ctx.send(embed=dico.Embed(description="노래를 다시 재생합니다.",
                                        color=Colors.information))
