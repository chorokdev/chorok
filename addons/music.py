import asyncio
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


async def on_voice_channel(ctx: dico_inter.InteractionContext) -> bool:
    if isinstance(ctx.author, dico.User):
        ctx.client.loop.create_task(  # noqa
            ctx.send("이 명령어는 초록이 있는 서버에서만 사용할 수 있습니다.", ephemeral=True))
        return False
    if not bool(ctx.author.user.voice_state) or not bool(
            ctx.author.user.voice_state.channel_id):
        ctx.client.loop.create_task(  # noqa
            ctx.send(
                "이 명령어는 음성 채널에서만 사용할 수 있습니다.\n"
                "만약 이미 음성 채널에 있다면 나갔다 들어와 다시 시도해 보시기 바랍니다.",
                ephemeral=True,
            ))
        return False
    return True


async def on_playing(ctx: dico_inter.InteractionContext) -> bool:
    vc: discodo.VoiceClient = ctx.client.audio.get_vc(ctx.guild_id,
                                                      safe=True)  # noqa
    await vc.getCurrent()

    if not vc or not vc.current:
        await ctx.send("이 명령어는 노래가 재생 중일 때만 사용하실 수 있습니다.", ephemeral=True)
        return False
    return True


async def on_same_voice_channel(ctx: dico_inter.InteractionContext) -> bool:
    vc: discodo.VoiceClient = ctx.client.audio.get_vc(ctx.guild_id,
                                                      safe=True)  # noqa
    if not vc or not ctx.author.user.voice_state:
        return True

    if vc.channel_id == ctx.author.user.voice_state.channel_id:
        return True

    await ctx.send(f"이 명령어는 <#{vc.channel_id}>에서만 사용하실 수 있습니다.",
                   ephemeral=True)
    return False


class Music(dico_command.Addon):  # type: ignore[call-arg, misc]
    bot: ChorokBot
    name = "뮤직"

    def on_load(self) -> None:
        self.bot.audio.dispatcher.on("SOURCE_START", self.send_next_source)
        self.bot.audio.dispatcher.on("SOURCE_STOP", self.set_loop)

    def on_unload(self) -> None:
        self.bot.audio.dispatcher.off("SOURCE_START", self.send_next_source)
        self.bot.audio.dispatcher.off("SOURCE_STOP", self.set_loop)

    async def connect_voice(
            self, guild_id: dico.Snowflake, voice_channel: dico.Snowflake,
            text_channel_id: dico.Snowflake) -> discodo.VoiceClient:
        vc = await self.bot.audio.connect(guild_id, voice_channel)

        with contextlib.suppress(Exception):
            await self.bot.modify_guild_member(guild_id,
                                               self.bot.application_id,
                                               mute=False,
                                               deaf=True)

        await vc.setContext({
            "textChannel": int(text_channel_id),
        })

        return vc

    async def send_next_source(self, voice: discodo.VoiceClient,
                               data: dict[str, Any]) -> None:
        with contextlib.suppress(Exception):
            await self.bot.delete_message(voice.context["textChannel"],
                                          voice.context["lastMessage"])
        message: dico.Message = await self.bot.create_message(
            channel=voice.context["textChannel"],
            embed=dico.Embed(
                title="현재 재생 중"
                if not data["source"]["related"] else "추천 영상 재생 중",
                description=f"[{data['source']['title']}]({data['source']['webpage_url']})",
                color=Colors.default,
            ))
        voice.context["lastMessage"] = str(message.id)
        await voice.setContext(voice.context)

    async def set_loop(self, voice: discodo.VoiceClient,
                       data: dict[str, Any]) -> None:
        if voice.context.get("loop", False):
            await voice.loadSource(data["source"]["webpage_url"])

    @dico_inter.command(name="join", description="음성 채널에 입장합니다.")
    @dico_inter.deco.checks(on_voice_channel)
    async def _join(self, ctx: dico_inter.InteractionContext) -> None:
        await ctx.defer()

        await self.connect_voice(ctx.guild_id,
                                 ctx.author.user.voice_state.channel_id,
                                 ctx.channel_id)
        await ctx.send(embed=dico.Embed(
            description=f"<#{ctx.author.user.voice_state.channel_id}>에 입장했습니다.",
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
            vc = await self.connect_voice(
                ctx.guild_id, ctx.author.user.voice_state.channel_id,
                ctx.channel_id)

        data: Union[AudioData, list[AudioData]] = await vc.loadSource(query)

        if isinstance(data, list):
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data[0].title}]({data[0].webpage_url}) 외 {len(data) - 1}개 - {ctx.author.user.mention}",
                color=Colors.default,
            )
        else:
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data.title}]({data.webpage_url}) - {ctx.author.user.mention}",
                color=Colors.default,
            )

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
                ctx.guild_id, ctx.target.author.voice_state.channel_id,
                ctx.channel_id)

        data: Union[AudioData,
                    list[AudioData]] = await vc.loadSource(ctx.target.content)

        if isinstance(data, list):
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data[0].title}]({data[0].webpage_url}) 외 {len(data) - 1}개 - {ctx.author.user.mention}",
                color=Colors.default,
            )
        else:
            embed = dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data.title}]({data.webpage_url}) - {ctx.author.user.mention}",
                color=Colors.default,
            )

        await ctx.send(embed=embed)

    @dico_inter.command(
        name="search",
        description="노래를 검색 및 재생합니다.",
        options=[
            dico.ApplicationCommandOption(
                dico.ApplicationCommandOptionType.STRING, "query", "검색할 내용",
                True)
        ],
    )
    @dico_inter.deco.checks(on_voice_channel, on_same_voice_channel)
    async def _search(self, ctx: dico_inter.InteractionContext,
                      query: str) -> None:
        await ctx.defer(ephemeral=True)

        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id,
                                                        safe=True)
        if not vc:
            vc = await self.connect_voice(
                ctx.guild_id, ctx.author.user.voice_state.channel_id,
                ctx.channel_id)

        data: list[AudioData] = await vc.searchSources(query)
        data_select = dico.SelectMenu(
            custom_id=f"{ctx.guild_id}_{ctx.channel_id}_{ctx.author.user.id}",
            options=[
                dico.SelectOption(label=source.title,
                                  value=str(index),
                                  description=source.uploader)
                for index, source in enumerate(data)
            ],
        )

        await ctx.send(
            "30초 안에 선택하지 않을 경우 취소됩니다.",
            ephemeral=True,
            components=[dico.ActionRow(data_select)],
        )
        try:
            inter: dico.Interaction = await self.bot.wait(
                "interaction_create",
                check=lambda i: int(i.author) == int(ctx.author.user.id) and i.
                data.custom_id == data_select.custom_id,
                timeout=30,
            )
            await vc.putSource(data[int(inter.data.values[0])])
            await inter.message.channel.send(embed=dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data[int(inter.data.values[0])].title}]({data[int(inter.data.values[0])].webpage_url})"
                f" - {ctx.author.user.mention}",
                color=Colors.default,
            ))
            data_select.disabled = True

            await inter.create_response(
                dico.InteractionResponse(
                    dico.InteractionCallbackType.UPDATE_MESSAGE,
                    dico.InteractionApplicationCommandCallbackData(
                        content="선택되었습니다.",
                        components=[dico.ActionRow(data_select)]),
                ))
        except asyncio.TimeoutError:
            await (await
                   ctx.request_original_response()).edit(content="취소되었습니다.",
                                                         components=None)

    @dico_inter.command(name="검색하기",
                        command_type=dico.ApplicationCommandTypes.MESSAGE)
    @dico_inter.deco.checks(on_voice_channel, on_same_voice_channel)
    async def _search_context_menu(self,
                                   ctx: dico_inter.InteractionContext) -> None:
        await ctx.defer(ephemeral=True)

        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id,
                                                        safe=True)
        if not vc:
            vc = await self.connect_voice(
                ctx.guild_id, ctx.author.user.voice_state.channel_id,
                ctx.channel_id)

        data: list[AudioData] = await vc.searchSources(ctx.target.content)
        data_select = dico.SelectMenu(
            custom_id=f"{ctx.guild_id}_{ctx.channel_id}_{ctx.author.user.id}",
            options=[
                dico.SelectOption(label=source.title,
                                  value=str(index),
                                  description=source.uploader)
                for index, source in enumerate(data)
            ],
        )

        await ctx.send(
            "30초 안에 선택하지 않을 경우 취소됩니다.",
            ephemeral=True,
            components=[dico.ActionRow(data_select)],
        )
        try:
            inter: dico.Interaction = await self.bot.wait(
                "interaction_create",
                check=lambda i: int(i.author) == int(ctx.author.user.id) and i.
                data.custom_id == data_select.custom_id,
                timeout=30,
            )
            await vc.putSource(data[int(inter.data.values[0])])
            await inter.message.channel.send(embed=dico.Embed(
                title="대기열에 추가되었습니다.",
                description=f"[{data[int(inter.data.values[0])].title}]({data[int(inter.data.values[0])].webpage_url})"
                f" - {ctx.author.user.mention}",
                color=Colors.default,
            ))
            data_select.disabled = True

            await inter.create_response(
                dico.InteractionResponse(
                    dico.InteractionCallbackType.UPDATE_MESSAGE,
                    dico.InteractionApplicationCommandCallbackData(
                        content="선택되었습니다.",
                        components=[dico.ActionRow(data_select)]),
                ))
        except asyncio.TimeoutError:
            await (await
                   ctx.request_original_response()).edit(content="취소되었습니다.",
                                                         components=None)

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
    @dico_inter.deco.checks(on_voice_channel, on_playing,
                            on_same_voice_channel)
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
    @dico_inter.deco.checks(on_voice_channel, on_same_voice_channel)
    async def _stop(self, ctx: dico_inter.InteractionContext) -> None:
        await self.bot.audio.get_vc(ctx.guild_id).destroy()
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
    @dico_inter.deco.checks(on_voice_channel, on_playing,
                            on_same_voice_channel)
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

    @dico_inter.command(
        name="seek",
        description="현재 곡에서 해당 위치로 이동합니다.",
        options=[
            dico.ApplicationCommandOption(
                dico.ApplicationCommandOptionType.STRING,
                "offset",
                "이동할 위치(00:00)",
                required=True,
            )
        ],
    )
    @dico_inter.deco.checks(on_voice_channel, on_playing,
                            on_same_voice_channel)
    async def _seek(self, ctx: dico_inter.InteractionContext,
                    offset: str) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        await vc.seek(
            sum([
                int(value) * (60**index)
                for index, value in enumerate(reversed(offset))
            ]))
        await ctx.send(embed=dico.Embed(description=f"`{offset}` 부분으로 이동했습니다.",
                                        color=Colors.information))

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
                f"**{chapter['title']}** " if chapter else ""
                f"`[{duration_format(chapter['start_time'])} ~ {duration_format(chapter['end_time'])}]`\n\n"
            )
            progress_bar = (
                f"{make_progress_bar(vc.position, vc.duration)} "
                f"`[{duration_format(vc.position)}/{duration_format(vc.duration)}]`"
                if not vc.current.is_live else "`[🔴LIVE]`")
            embed = dico.Embed(
                title=f"{vc.current.title}",
                url=f"{vc.current.webpage_url}&t={int(vc.current.position)}",
                description=f"{chapter_str}\n{progress_bar}",
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
            await self._nowplaying.coro(self, ctx)
            return

        formatted_queue = create_page(
            [
                f"**{idx + 1}.** [{item.title}]({item.webpage_url})"
                for idx, item in enumerate(vc.Queue)
            ],
            4096,
        )
        embeds: list[dico.Embed] = [
            dico.Embed(
                title=f"서버 대기열",
                description="\n".join(page),
                color=Colors.information,
            ) for page in formatted_queue
        ]

        await ctx.send(embeds=embeds)

    @dico_inter.command(name="remove",
                        description="대기열에서 해당 인덱스의 곡을 삭제합니다.",
                        options=[
                            dico.ApplicationCommandOption(
                                dico.ApplicationCommandOptionType.NUMBER,
                                "index", "삭제할 곡의 인덱스", True)
                        ])
    async def _remove(self, ctx: dico_inter.InteractionContext,
                      index: int) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        with contextlib.suppress(Exception):
            data: discodo.AudioData = vc.Queue[index - 1]
            await vc.Queue[index - 1].remove()
            await ctx.send(embed=dico.Embed(
                description=f"[{data.title}]({data.webpage_url})을(를) 삭제했습니다.",
                color=Colors.information))

    @dico_inter.command(name="autoplay", description="자동 재생을 켜거나 끕니다.")
    @dico_inter.deco.checks(on_voice_channel, on_playing,
                            on_same_voice_channel)
    async def _autoplay(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        await vc.setAutoplay(not vc.autoplay)

        await ctx.send(embed=dico.Embed(
            description=f"자동 재생을 {'켰' if vc.autoplay else '껐'}습니다.",
            color=Colors.information,
        ))

    @dico_inter.command(name="loop", description="대기열 전체 반복을 켜거나 끕니다.")
    @dico_inter.checks(on_voice_channel, on_playing, on_same_voice_channel)
    async def _loop(self, ctx: dico_inter.InteractionContext) -> None:
        vc: discodo.VoiceClient = self.bot.audio.get_vc(ctx.guild_id)

        if vc.context.get("loop", False):
            vc.context["loop"] = False
        else:
            vc.context["loop"] = True
        await vc.setContext(vc.context)

        await ctx.send(embed=dico.Embed(
            description=f"대기열 반복을 {'켰' if vc.context['loop'] else '껐'}습니다.",
            color=Colors.information,
        ))

    @dico_inter.command(name="pause", description="노래를 일시정지합니다.")
    @dico_inter.deco.checks(on_voice_channel, on_playing,
                            on_same_voice_channel)
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
