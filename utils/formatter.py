def create_invite_link(bot_id: str, permissions: int) -> str:
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={bot_id}&permissions={permissions}&scope=bot%20applications.commands"
    )


def make_progress_bar(value: float, total: float) -> str:
    position_front = round(value / total * 16)
    position_back = 16 - position_front

    return "▬" * position_front + "🔘" + "▬" * position_back


def duration_format(seconds: float) -> str:
    minute, second = divmod(int(seconds), 60)
    hour, minute = divmod(minute, 60)

    return (f"{hour:02}:" if hour else "") + f"{minute:02}:{second:02}"


def create_page(lines: list[str], limit: int) -> list[list[str]]:
    total: list[list[str]] = []
    temp: list[str] = []

    for line in lines:
        if len("\n".join(temp) + f"\n{line}") > limit:
            total.append(temp)
            temp = []
        temp.append(line)
    total.append(temp)

    return total
