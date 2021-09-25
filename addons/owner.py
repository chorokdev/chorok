import dico  # noqa
import dico_command
import dico_interaction as dico_inter

try:
    import meval  # noqa
except ImportError:
    meval = None

from models import ChorokBot


def load(bot: ChorokBot) -> None:
    bot.load_addons(Owner)


def unload(bot: ChorokBot) -> None:
    bot.unload_addons(Owner)


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
        if not meval:
            await ctx.send("eval을 사용하기 위해선 meval 모듈을 설치해야 합니다.",
                           ephemeral=True)
            return

        result = await meval.meval(code, globals(), ctx=ctx, bot=self.bot)
        await ctx.send(str(result), ephemeral=True)
