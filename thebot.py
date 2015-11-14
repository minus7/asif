#!/usr/bin/env python3
# vim: set ts=4 sw=4 noet:

import config
from bot import Client, Channel
import asyncio
import re
import aiohttp

bot = Client(**config.bot_config)


# helpch = bot.join("#help")


@bot.on_connected()
async def on_connect():
    # await bot.send("NickServ", "IDENTIFY asdf")
    # await bot.await_message("HostServ", "vhost.*activated", notice=True)
    await bot.join("#minus")


@bot.on_message(re.compile("youtube\.com|youtu\.be"))
async def youtube_info(message):
    link_re = re.compile(r"""(?:https?://)(?:www\.)?(?:(?:youtube\.com(?:/embed/|/watch/?\?(?:.*)v=))|youtu\.be/)(?P<id>[A-Za-z0-9-_]+)""")
    match = link_re.search(message.text)
    if not match:
        return

    params = {
        "id": match.group("id"),
        "part": "contentDetails,statistics,snippet",
        "key": config.youtube_api_key
    }
    async with aiohttp.get("https://www.googleapis.com/youtube/v3/videos", params=params) as resp:
        if resp.status != 200:
            return
        info = await resp.json()
    things = dict()
    things.update(info["items"][0]["snippet"])
    things.update(info["items"][0]["statistics"])
    reply = "YouTube: {title} by {channelTitle} ({viewCount} views)".format(**things)
    await message.reply(reply)


@bot.on_message("!quit")
async def quit(message):
    await bot.quit("Goodbye!")

@bot.on_message(matcher=lambda msg: msg.text.startswith("!join"))
async def join(message):
    await bot.join(message.text.partition(" ")[2])

@bot.on_message(matcher=lambda msg: isinstance(msg.recipient, Channel) and msg.text.startswith("!part"))
async def part(message):
    await message.recipient.part()
    await bot.get_user("minus").message("Left {}".format(message.recipient))

@bot.on_join()
async def hello(channel):
    await channel.message("Hello {}!".format(channel.name))

loop = asyncio.get_event_loop()
loop.run_until_complete(bot.run())
