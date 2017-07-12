#!/usr/bin/env python3

import config
from asif import Client, Channel, CommandSet
from misc import async_input

import asyncio
import re
import aiohttp

bot = Client(**config.bot_config)
cs = CommandSet(bot, ident="Example bot checking in")
chan = bot.get_channel("#asif-test")

@bot.on_connected()
async def on_connect():
    if hasattr(config, "nickserv_password"):
        # register waiter before sending the message to be sure to catch it
        nickserv_ok = bot.await_message(sender="NickServ", message=re.compile("Password accepted"))
        await bot.message("NickServ", "IDENTIFY {}".format(config.nickserv_password))
        await nickserv_ok
    await bot.join("#asif-test")


@bot.on_message(re.compile("youtube\.com|youtu\.be"))
async def youtube_info(message):
    if not hasattr(config, "youtube_api_key"):
        return
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

@bot.on_message(re.compile("^!join"))
async def join(message):
    await bot.join(message.text.partition(" ")[2])

@bot.on_message(matcher=lambda msg: isinstance(msg.recipient, Channel) and msg.text.startswith("!part"))
async def part(message):
    await message.recipient.part()
    await bot.get_user("minus").message("Left {}".format(message.recipient))

@bot.on_join()
async def greet(channel):
    await channel.message("Hello {}!".format(channel.name))

@cs.command()
async def ping():
    """
    .ping: respond with pong
    """
    return "pong"

async def cli_input():
    while True:
        inp = await async_input("> ")
        msg = bot._parsemsg(inp)
        await bot._send(*msg.args, prefix=msg.prefix, rest=msg.rest)

bot._bg(cli_input())
loop = asyncio.get_event_loop()
loop.run_until_complete(bot.run())
