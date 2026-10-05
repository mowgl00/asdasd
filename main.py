import os
import asyncio
import discord
from discord.ext import commands, tasks

MY_ID = 1337973255977570345
APPLICATION_ID = 1521150234024214718

bot = commands.Bot(command_prefix='.', self_bot=True, help_command=None)


def is_me():
    def predicate(ctx):
        return ctx.author.id == MY_ID
    return commands.check(predicate)


async def reply_edit_or_send(message, content: str):
    if message.author.id == bot.user.id:
        try:
            await message.edit(content=content)
            return
        except Exception:
            pass
    try:
        await message.reply(content, mention_author=False)
    except Exception:
        try:
            await message.channel.send(content)
        except Exception as e:
            print(f"reply failed: {e}")


@tasks.loop(minutes=5)
async def keep_presence_alive():
    try:
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=".gg/36EAyW5Z4F",
            details="Read Bio",
            state="Germany",
            application_id=APPLICATION_ID,
            buttons=[
                discord.ActivityButton("dc", "https://discord.gg/36EAyW5Z4F"),
                discord.ActivityButton("guns", "https://guns.lol/tpa"),
            ],
        )
        await bot.change_presence(status=discord.Status.dnd, activity=activity)
        print("Presence updated.")
    except Exception as e:
        print(f"Presence failed: {e}")
        try:
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name=".gg/36EAyW5Z4F",
                details="Read Bio",
                state="Germany",
                application_id=APPLICATION_ID,
                buttons=[
                    {"label": "dc", "url": "https://discord.gg/36EAyW5Z4F"},
                    {"label": "guns", "url": "https://guns.lol/tpa"},
                ],
            )
            await bot.change_presence(status=discord.Status.dnd, activity=activity)
            print("Presence updated (fallback).")
        except Exception as e2:
            print(f"Presence fallback failed: {e2}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    if not keep_presence_alive.is_running():
        keep_presence_alive.start()
    await keep_presence_alive()
    print("Online + RPC running.")


@bot.command()
@is_me()
async def server(ctx, source_id: int):
    """Clone roles + channels from source guild into the current guild.
    Usage: .server <source_guild_id>
    Run this INSIDE the target (new) server.
    """
    target = ctx.guild
    if target is None:
        await reply_edit_or_send(ctx.message, "❌ Use this inside a server.")
        return

    source = bot.get_guild(source_id)
    if source is None:
        await reply_edit_or_send(ctx.message, "❌ Source server not found (you must be in both).")
        return

    await reply_edit_or_send(
        ctx.message,
        f"⏳ Cloning **{source.name}** → **{target.name}** ... this can take a while.",
    )

    role_map = {}
    created_roles = 0
    created_channels = 0

    try:
        roles = sorted(
            [r for r in source.roles if r.name != "@everyone"],
            key=lambda r: r.position,
        )
        for role in roles:
            try:
                new_role = await target.create_role(
                    name=role.name,
                    permissions=role.permissions,
                    colour=role.colour,
                    hoist=role.hoist,
                    mentionable=role.mentionable,
                    reason="Server clone",
                )
                role_map[role.id] = new_role
                created_roles += 1
                await asyncio.sleep(0.8)
            except Exception as e:
                print(f"Role fail {role.name}: {e}")

        cat_map = {}
        for cat in sorted(source.categories, key=lambda c: c.position):
            try:
                overwrites = {}
                for obj, ow in cat.overwrites.items():
                    if isinstance(obj, discord.Role) and obj.id in role_map:
                        overwrites[role_map[obj.id]] = ow
                    elif isinstance(obj, discord.Role) and obj.name == "@everyone":
                        overwrites[target.default_role] = ow
                new_cat = await target.create_category(
                    name=cat.name,
                    overwrites=overwrites or None,
                    reason="Server clone",
                )
                cat_map[cat.id] = new_cat
                created_channels += 1
                await asyncio.sleep(0.8)
            except Exception as e:
                print(f"Category fail {cat.name}: {e}")

        channels = sorted(
            [c for c in source.channels if not isinstance(c, discord.CategoryChannel)],
            key=lambda c: c.position,
        )
        for ch in channels:
            try:
                overwrites = {}
                for obj, ow in ch.overwrites.items():
                    if isinstance(obj, discord.Role) and obj.id in role_map:
                        overwrites[role_map[obj.id]] = ow
                    elif isinstance(obj, discord.Role) and obj.name == "@everyone":
                        overwrites[target.default_role] = ow
                parent = cat_map.get(ch.category_id) if ch.category_id else None

                if isinstance(ch, discord.TextChannel):
                    await target.create_text_channel(
                        name=ch.name,
                        topic=ch.topic,
                        slowmode_delay=ch.slowmode_delay,
                        nsfw=ch.nsfw,
                        category=parent,
                        overwrites=overwrites or None,
                        reason="Server clone",
                    )
                elif isinstance(ch, discord.VoiceChannel):
                    await target.create_voice_channel(
                        name=ch.name,
                        bitrate=min(ch.bitrate, target.bitrate_limit),
                        user_limit=ch.user_limit,
                        category=parent,
                        overwrites=overwrites or None,
                        reason="Server clone",
                    )
                created_channels += 1
                await asyncio.sleep(0.8)
            except Exception as e:
                print(f"Channel fail {ch.name}: {e}")

        await reply_edit_or_send(
            ctx.message,
            f"✅ Clone done!\nRoles: **{created_roles}**\nChannels/Cats: **{created_channels}**\n"
            f"`{source.name}` → `{target.name}`",
        )
    except Exception as e:
        await reply_edit_or_send(ctx.message, f"❌ Clone failed: `{e}`")


@bot.event
async def on_message(message):
    await bot.process_commands(message)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERROR: DISCORD_TOKEN is missing.")
        exit(1)
    bot.run(token)
