# Asyncio-powered IRC Bot Framework
asif allows you to write an IRC bot that listens to commands in a **Flask**-like manner. Commands are functions, registered to the framework via decorators. Writing long-running background processes is possible because the whole framework is based on asyncio, just use `asyncio.ensure_future` on your function as usual.

Requires Python 3.5 for the **async/await** syntax.

## Example Code
```python
#!/usr/bin/env python3

import config
from bot import Client, Channel

import asyncio
import re
import aiohttp

bot = Client(**config.bot_config)

@bot.on_message(re.compile("^!ping"))
async def pong(message):
    """
    A simple ping/pong command
    """
    await message.reply("pong" + message.text[5:])

@bot.on_message(re.compile("youtube\.com|youtu\.be"))
async def youtube_info(message):
    """
    A more involved example, posting information about YouTube links to channels and queries
    """
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

loop = asyncio.get_event_loop()
loop.run_until_complete(bot.run())
```

## License
This software is published under the MIT license, see [LICENSE](LICENSE)
