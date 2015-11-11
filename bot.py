#!/usr/bin/env python3
# vim: set ts=4 sw=4 noet:

from bot import Client

import asyncio
import re
from youtube_scraper.scraper import scrape_html
import aiohttp

bot = Client(("localhost", 6697))
bot.user = "bot"
bot.realname = "The Bot"
bot.nick = "TheBot"

helpch = bot.join("#help")


@bot.on_connect
async def on_connect():
	await bot.send("NickServ", "IDENTIFY asdf")
	await bot.await_message("HostServ", "vhost.*activated", notice=True)


@helpch.on_message(re.compile("youtube\.com|youtu\.be"))
async def youtube_info(message):
	link_re = re.compile(r"""(?:https?://)(?:www\.)?(?:(?:youtube\.com(?:/embed/|/watch/?\?(?:.*)v=))|youtu\.be/)([A-Za-z0-9-_]+)""")
	match = link_re.search(message.text)
	if not match:
		return

	async with aiohttp.get(match.group(0)) as resp:
		info = scrape_html(await resp.text())

	reply = "YouTube: {i.title} by {i.poster} ({i.views} views)".format(i=info)
	await message.reply(reply)


@helpch.on_message
async def echo(message):
	await message.reply(message.text)


loop = asyncio.get_event_loop()
loop.run_until_complete(bot.run())
