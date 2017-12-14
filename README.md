# Asyncio-powered IRC Bot Framework
asif allows you to write an IRC bot that listens to commands in a **Flask**-like manner. Commands are functions, registered to the framework via decorators. Writing long-running background processes is possible because the whole framework is based on asyncio, just use `asyncio.ensure_future` on your function as usual.

Requires Python 3.6 for the **async/await** syntax.

## Example Code
```python
#!/usr/bin/env python3

from bot import Client, Channel

import asyncio
import re

bot = Client(
    host="localhost",
    port=6667,
    user="bot",
    realname="The Bot",
    nick="TheBot",
)

@bot.on_connected()
async def connected():
    await bot.join("#mychan")

@bot.on_message(re.compile("^!ping"))
async def pong(message):
    """
    A simple ping/pong command. Replies to your !ping messages
    """
    await message.reply("pong" + message.text[5:])

loop = asyncio.get_event_loop()
loop.run_until_complete(bot.run())
```

## License
This software is published under the MIT license, see [LICENSE](LICENSE)
