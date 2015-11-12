#!/usr/bin/env python3
# vim: set ts=4 sw=4 noet:

import asyncio
from collections import namedtuple
import logging
import re
from typing import List, Callable, Union

MessageHandler = namedtuple("MessageHandler", ("matcher", "handler"))


class LoggerMetaClass(type):

    def __new__(mcs, name, bases, namespace):
        inst = type.__new__(mcs, name, bases, namespace)
        inst._log = logging.getLogger("bot.{}".format(name))
        inst._log.debug("Attached logger to {}".format(name))
        return inst


RegEx = type(re.compile(""))


class User(metaclass=LoggerMetaClass):

    def __init__(self, prefix: str, client: 'Client'):
        self.nick, _, rest = prefix.partition("!")
        self.user, _, self.host = rest.partition("@")
        self.client = client

    async def message(self, text: str, notice: bool=False) -> None:
        await self.client.message(self.nick, text, notice=notice)


class Channel(metaclass=LoggerMetaClass):

    def __init__(self, name: str, client: 'Client'):
        self.name = name
        self.client = client
        self.users = []

    def __contains__(self, other: User) -> bool:
        return other in self.users

    async def message(self, text: str, notice: bool=False) -> None:
        await self.client.message(self.name, text, notice=notice)


class Message(metaclass=LoggerMetaClass):

    def __init__(self, sender: [User, Channel], recipient: [
                 User, Channel], text: str, notice: bool=False):
        self.sender = sender
        self.recipient = recipient
        self.text = text
        self.notice = notice

    async def reply(self, text: str, notice: bool=None) -> None:
        if notice is None:
            notice = self.notice
        recipient = self.recipient if isinstance(self.recipient, Channel) else self.sender
        await recipient.message(text, notice=notice)


class Client(metaclass=LoggerMetaClass):

    def __init__(self, host: str, port: int, nick: str="TheBot", user: str="bot",
                 realname: str="The Bot", secure: bool=False, encoding: str="utf-8"):
        self.host = host
        self.port = port
        self.secure = secure
        self.nick = nick
        self.user = user
        self.realname = realname
        self.encoding = encoding

        self._on_connected_handlers = []
        self._on_message_handlers = []
        self._users = {}
        self._channels = {}
        self._on_command_handlers = {}
        self._channel_types = ""
        self._connected = False

    def on_connected(self) -> Callable[[Callable], Callable]:
        def decorator(fn: Callable[[], None]):
            self._on_connected_handlers.append(fn)
            return fn

        return decorator

    def on_message(self, message: Union[str, RegEx]=None, channel: Union[str, RegEx]=None,
                   sender: Union[str, RegEx]=None, matcher: Callable[[Message], None]=None
                   ) -> Callable[[Callable], Callable]:
        if not matcher:
            matchers = []

            # message
            if message is None:
                pass
            elif isinstance(message, str):
                def matcher(msg: Message) -> bool:
                    return msg.text == message

                matchers.append(matcher)
            elif hasattr(message, "search"):
                # regex or so
                def matcher(msg: Message) -> bool:
                    return message.search(msg.text) is not None

                matchers.append(matcher)
            else:
                raise ValueError("Don't know what to do with message={}".format(message))

            # sender
            if sender is None:
                pass
            elif isinstance(sender, str):
                def matcher(msg: Message) -> bool:
                    return msg.sender == sender

                matchers.append(matcher)
            elif hasattr(sender, "search"):
                # regex or so
                def matcher(msg: Message) -> bool:
                    return message.search(msg.sender) is not None

                matchers.append(matcher)
            else:
                raise ValueError("Don't know what to do with sender={}".format(sender))

            # channel
            if channel is None:
                pass
            elif isinstance(channel, str):
                def matcher(msg: Message) -> bool:
                    return msg.recipient == channel

                matchers.append(matcher)
            elif hasattr(channel, "search"):
                # regex or so
                def matcher(msg: Message) -> bool:
                    return message.search(msg.recipient) is not None

                matchers.append(matcher)
            else:
                raise ValueError("Don't know what to do with channel={}".format(channel))

            def matcher(msg: Message) -> bool:
                return all(m(msg) for m in matchers)

        def decorator(fn: Callable[[Message], None]) -> Callable[[Message], None]:
            handler = MessageHandler(matcher, fn)
            self._on_message_handlers.append(handler)
            return fn

        return decorator

    IrcMessage = namedtuple("IrcMessage", ("prefix", "command", "args", "rest"))

    def on_command(self, command: str) -> Callable[[Callable], Callable]:
        def decorator(fn: Callable[[self.IrcMessage], None]):
            self._on_command_handlers.setdefault(command, []).append(fn)
            return fn

        return decorator

    def remove_command_handler(self, command: str, handler: Callable[[IrcMessage], None]) -> None:
        handler_list = self._on_command_handlers[command]
        handler_list.remove(handler)
        if not handler_list:
            del self._on_command_handlers[command]

    async def await_command(self, command: str) -> IrcMessage:
        fut = asyncio.Future()
        @self.on_command(command)
        async def handler(msg):
            self.remove_command_handler(command, handler)
            fut.set_result(msg)
        return await fut

    def parsemsg(self, msg: str) -> IrcMessage:
        # adopted from twisted/words/protocols/irc.py
        prefix = None
        rest = None
        if msg[0] == ":":
            prefix, msg = msg[1:].split(" ", 1)
        if " :" in msg:
            msg, rest = msg.split(" :", 1)
            args = msg.split()
        else:
            args = msg.split()
        command = args.pop(0)
        return self.IrcMessage(prefix, command, args, rest)

    def buildmsg(self, *args: List[str], prefix: str=None, rest: str=None) -> str:
        msg = ""
        if prefix:
            msg += ":{} ".format(prefix)
        msg += " ".join(args)
        if rest:
            msg += " :{}".format(rest)
        return msg

    async def send(self, *args: List[str], prefix: str=None, rest: str=None) -> None:
        msg = self.buildmsg(*args, prefix=prefix, rest=rest)
        self._log.debug("<- {}".format(msg))
        self._writer.write(msg.encode(self.encoding) + b"\r\n")

    async def message(self, recipient: str, text: str, notice: bool=False) -> None:
        await self.send("PRIVMSG" if not notice else "NOTICE", recipient, rest=text)

    async def _get_message(self) -> IrcMessage:
        line = await self._reader.readline()
        line = line.decode(self.encoding).strip("\r\n")

        if not line and self._reader.at_eof():
            return

        self._log.debug("-> {}".format(line))

        msg = self.parsemsg(line)

        if await self._handle_special(msg):
            return

        return msg

    async def run(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

        asyncio.ensure_future(self._connect())

        while not self._reader.at_eof():

            try:
                msg = await self._get_message()
            except:
                self._log.exception("Error during receiving")
                raise


            if not msg:
                continue

            if msg.command in self._on_command_handlers:
                for handler in self._on_command_handlers[msg.command]:
                    asyncio.ensure_future(handler(msg))

            if not self._connected:
                continue

            if msg.command in ("PRIVMSG", "NOTICE"):
                sender = self._resolve_sender(msg.prefix)
                recipient = self._resolve_recipient(msg.args[0])
                message = Message(sender, recipient, msg.rest, (msg.command == "NOTICE"))
                await self._handle_on_message(message)
                continue

            # self._log.info("Unhandled command: {} {}".format(command, kwargs))

        self._log.info("Connection closed, exiting")

    async def _handle_special(self, msg: IrcMessage) -> bool:
        if msg.command == "PING":
            await self.send("PONG", rest=msg.rest)
            return True
        return False

    async def _handle_on_message(self, message: Message) -> None:
        for mh in self._on_message_handlers:
            if mh.matcher(message):
                await mh.handler(message)

    async def _connect(self) -> None:
        await self.send("NICK", self.nick)
        await self.send("USER", self.user, "0", "*", rest=self.realname)

        @self.on_command("005")  # Feature list
        async def feature_list(msg):
            for feature in filter(lambda arg: arg.startswith("CHANTYPES="), msg.args):
                self._channel_types = feature.partition("=")[2]
                self.remove_command_handler("005", feature_list)

        self._log.debug("Waiting for the end of the MOTD")
        await self.await_command("376")  # End of MOTD
        self._log.debug("End of the MOTD found, running handlers")

        for handler in self._on_connected_handlers:
            try:
                await handler()
            except:
                self._log.exception("Connect handler {} raised exception".format(handler))

        self._connected = True

    def _resolve_sender(self, prefix: str) -> User:
        if "!" in prefix and "@" in prefix:
            return self.get_user(prefix)
        # message probably sent by the server
        return None

    def get_user(self, prefix: str) -> User:
        nick = prefix
        if "!" in prefix:
            nick = prefix.partition("!")[0]
        return self._users.setdefault(nick, User(prefix, self))

    def get_channel(self, channel: str) -> Channel:
        return self._users.setdefault(channel, Channel(channel, self))

    def _resolve_recipient(self, recipient: str) -> Union[User, Channel]:
        if recipient[0] in self._channel_types:
            return self.get_channel(recipient)
        return self.get_user(recipient)

    async def join(self, channel: str) -> Channel:
        await self.send("JOIN", channel)
        #await self.await_command("JOIN", channel)

    async def quit(self, reason: str=None) -> Channel:
        await self.send("QUIT", rest=reason)
