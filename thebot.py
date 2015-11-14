#!/usr/bin/env python3
# vim: set ts=4 sw=4 noet:

import config
from bot import Client, Channel
from misc import async_input

import asyncio
import re
import aiohttp

bot = Client(**config.bot_config)


# helpch = bot.join("#help")


@bot.on_connected()
async def on_connect():
    if hasattr(config, "nickserv_password"):
        await bot.message("NickServ", "IDENTIFY {}".format(config.nickserv_password))
        await bot.await_message(sender="HostServ", message=re.compile("vhost.*activated"))
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


async def cli_input():
    while True:
        inp = await async_input("> ")
        print("Got input:", inp)
        msg = bot._parsemsg(inp)
        print("Decoded message: {}".format(msg))
        await bot._send(*msg.args, prefix=msg.prefix, rest=msg.rest)
        print("Message sent!")

bot._bg(cli_input())
loop = asyncio.get_event_loop()
loop.run_until_complete(bot.run())
