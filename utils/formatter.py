def create_invite_link(bot_id: str, permissions: int) -> str:
    return f"https://discord.com/api/oauth2/authorize" \
           f"?client_id={bot_id}&permissions={permissions}&scope=bot%20applications.commands"
