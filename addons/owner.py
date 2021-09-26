import asyncio
from typing import Optional

import dico  # noqa
import dico_command
import dico_interaction as dico_inter
from dp.pager import Pager
from dp.pyeval import PYEval

from models import ChorokBot


def load(bot: ChorokBot) -> None:
    bot.load_addons(Owner)


def unload(bot: ChorokBot) -> None:
    bot.unload_addons(Owner)


async def delete_wait(bot: ChorokBot,
                      ctx: dico_inter.InteractionContext,
                      content: Optional[str] = None,
                      embed: Optional[dico.Embed] = None) -> None:
    delete_button = dico.Button(style=dico.ButtonStyles.DANGER,
                                emoji="🗑️",
                                custom_id="trash")
    delete_button.custom_id += str(ctx.id)
    await ctx.send(content,
                   embed=embed,
                   components=[dico.ActionRow(delete_button)])
    try:
        inter: dico.Interaction = await bot.wait(
            "interaction_create",
            check=lambda i: int(i.author) == int(ctx.author.user.id) and i.data
            .custom_id == delete_button.custom_id,
            timeout=60)
        await inter.message.delete()
    except asyncio.TimeoutError:
        return


class Owner(dico_command.Addon):  # type: ignore[call-arg, misc]
    bot: ChorokBot
    name = "오너"

    @dico_inter.command(
        name="eval",
        description="코드를 실행합니다. (오너 ONLY)",
        options=[
            dico.ApplicationCommandOption(
                dico.ApplicationCommandOptionType.STRING, "code", "실행할 코드",
                True)
        ],
    )
    async def _eval(self, ctx: dico_inter.InteractionContext,
                    code: str) -> None:
        if (ctx.author.user.id
                not in (await
                        self.bot.request_current_bot_application_information()
                        ).owner_ids):
            await ctx.send("이 명령어는 애플리케이션의 오너만 사용할 수 있습니다.", ephemeral=True)
            return
        await ctx.defer()
        ev = PYEval(ctx, self.bot, code)
        delete_button = dico.Button(style=dico.ButtonStyles.DANGER,
                                    emoji="🗑️",
                                    custom_id="trash")
        resp = await ev.evaluate()
        str_resp = [f"Result {i}:\n{x}" for i, x in enumerate(resp, start=1)
                    ] if len(resp) > 1 else [*map(str, resp)]
        pages = []
        for x in str_resp:
            if len(x) > 2000:
                while len(x) > 2000:
                    pages.append(x[:2000])
                    x = x[2000:]
                pages.append(x)
            else:
                pages.append(x)
        if len(pages) == 1:
            return await delete_wait(self.bot, ctx, content=str(pages[0]))
        # TODO: fix message
        pager = Pager(self.bot,
                      self.bot.get(ctx.channel_id, storage_type="channel"),
                      ctx.author,
                      pages,
                      reply=ctx.message,
                      extra_button=delete_button,
                      timeout=60)
        async for _ in pager.start():
            await pager.message.delete()
            break
