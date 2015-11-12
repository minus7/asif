#!/usr/bin/env python3
# vim: set ts=4 sw=4 noet:

import config
from bot import Client
import asyncio
import re
from youtube_scraper.scraper import scrape_html
import aiohttp

bot = Client(**config.bot_config)


# helpch = bot.join("#help")


@bot.on_connect()
async def on_connect():
    # await bot.send("NickServ", "IDENTIFY asdf")
    # await bot.await_message("HostServ", "vhost.*activated", notice=True)
    await bot.join("#minus")


@bot.on_message(re.compile("youtube\.com|youtu\.be"))
async def youtube_info(message):
    return
    link_re = re.compile(
        r"""(?:https?://)(?:www\.)?(?:(?:youtube\.com(?:/embed/|/watch/?\?(?:.*)v=))|youtu\.be/)([A-Za-z0-9-_]+)""")
    match = link_re.search(message.text)
    if not match:
        return

    async with aiohttp.get(match.group(0)) as resp:
        info = scrape_html(await resp.text())

    reply = "YouTube: {i.title} by {i.poster} ({i.views} views)".format(i=info)
    await message.reply(reply)


@bot.on_message()
async def echo(message):
    pass  # await message.reply(message.text)


loop = asyncio.get_event_loop()
loop.run_until_complete(bot.run())
