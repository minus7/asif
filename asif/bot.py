#!/usr/bin/env python3

from . import command_codes as cc

import asyncio
from collections import namedtuple
import logging
import re
from typing import List, Callable, Union, Sequence, Any
from types import coroutine


class LoggerMetaClass(type):

    def __new__(mcs, name, bases, namespace):
        inst = type.__new__(mcs, name, bases, namespace)
        inst._log = logging.getLogger("bot.{}".format(name))
        inst._log.debug("Attached logger to {}".format(name))
        return inst


RegEx = type(re.compile(""))


class User(metaclass=LoggerMetaClass):

    def __init__(self, nick: str, client: 'Client', hostmask: str=None):
        self.name = nick
        self.hostmask = hostmask
        self.client = client

        self._log.debug("Created {}".format(self))

    async def message(self, text: str, notice: bool=False) -> None:
        await self.client.message(self.name, text, notice=notice)

    def __eq__(self, other: 'User') -> bool:
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "<User {self.name}!{self.hostmask}>".format(self=self)


class Channel(metaclass=LoggerMetaClass):

    def __init__(self, name: str, client: 'Client'):
        self.name = name
        self.client = client
        self.users = set()

        self._log.debug("Created {}".format(self))

    def on_message(self, *args, accept_query=False, matcher=None, **kwargs):
        """
        Convenience wrapper of `Client.on_message` pre-bound with `channel=self.name`.
        """

        if accept_query:
            def new_matcher(msg: Message):
                ret = True
                if matcher:
                    ret = matcher(msg)
                    if ret is None or ret is False:
                        return ret
                if msg.recipient is not self and not isinstance(msg.sender, User):
                    return False
                return ret
        else:
            kwargs.setdefault("channel", self.name)
            new_matcher = matcher
        return self.client.on_message(*args, matcher=new_matcher, **kwargs)

    async def message(self, text: str, notice: bool=False) -> None:
        await self.client.message(self.name, text, notice=notice)

    async def part(self, reason: str=None, block: bool=False) -> None:
        await self.client.part(self.name, reason=reason, block=block)

    def __contains__(self, other: User) -> bool:
        return other in self.users

    def __eq__(self, other: 'Channel') -> bool:
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return "<Channel {self.name} users={num_users}>" \
            .format(self=self, num_users=len(self.users))


class Message(metaclass=LoggerMetaClass):

    def __init__(self, sender: Union[User, Channel],
                 recipient: Union[User, Channel],
                 text: str, notice: bool=False):
        self.sender = sender
        self.recipient = recipient
        self.text = text
        self.notice = notice

    async def reply(self, text: str, notice: bool=None) -> None:
        if notice is None:
            notice = self.notice
        recipient = self.recipient if isinstance(self.recipient, Channel) else self.sender
        await recipient.message(text, notice=notice)

    def __repr__(self):
        return "<Message sender={self.sender} recipient={self.recipient}>".format(self=self)


class Client(metaclass=LoggerMetaClass):

    def __init__(self, host: str, port: int, nick: str="TheBot", user: str="bot",
                 realname: str="The Bot", secure: bool=False, encoding: str="utf-8",
                 password: str=None):
        self.host = host
        self.port = port
        self.secure = secure
        self.nick = nick
        self.user = user
        self.realname = realname
        self.encoding = encoding
        self.password = password

        self._on_connected_handlers = []
        self._on_disconnected_handlers = []
        self._on_message_handlers = []
        self._users = {}
        self._channels = {}
        self._on_command_handlers = []
        self._on_join_handlers = []
        # default chan types, can be overridden by `cc.RPL_ISUPPORT` CHANTYPES
        self._channel_types = "#&"
        # default user mode prefixes, can be overridden by `cc.RPL_ISUPPORT` PREFIX
        self._prefix_map = {"@": "o", "+": "v"}
        self._connected = False
        self._modules = []

        # Register JOIN, QUIT, PART, NICK handlers
        self.on_command(cc.JOIN)(self._on_join)
        self.on_command(cc.QUIT)(self._on_quit)
        self.on_command(cc.PART)(self._on_part)
        self.on_command(cc.NICK)(self._on_nick)

    def on_connected(self) -> Callable[[Callable], Callable]:
        def decorator(fn: Callable[[], None]):
            self._on_connected_handlers.append(fn)
            return fn

        return decorator

    def on_disconnected(self) -> Callable[[Callable], Callable]:
        def decorator(fn: Callable[[str], None]):
            self._on_disconnected_handlers.append(fn)
            return fn

        return decorator

    MessageHandler = namedtuple("MessageHandler", ("matcher", "handler"))

    def on_message(self, message: Union[str, RegEx]=None, channel: Union[str, RegEx]=None,
                   sender: Union[str, RegEx]=None, matcher: Callable[[Message], None]=None,
                   notice: bool=None) -> Callable[[Callable], Callable]:
        """

        Register a handler that's called after a message is received (PRIVMSG, NOTICE).
        The handler is called with the `Message` as argument, must be a coroutine
        and is run non-blocking. All filters must match for a message to be accepted.
        :param message: message filter, string (exact match) or compiled regex object
        :param channel: channel filter, string (exact match) or compiled regex object
        :param sender: sender filter, string (exact match) or compiled regex object
        :param matcher: test function, return true to accept the message.
                        Gets the `Message` as parameter
        """
        matchers = []

        if notice is not None:
            def notice_matcher(msg: Message) -> bool:
                return msg.notice == notice
            matchers.append(notice_matcher)

        if matcher:
            matchers.append(matcher)

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
                m = message.search(msg.text)
                if m is not None:
                    return m.groupdict()

            matchers.append(matcher)
        else:
            raise ValueError("Don't know what to do with message={}".format(message))

        # sender
        if sender is None:
            pass
        elif isinstance(sender, User):
            def matcher(msg: Message) -> bool:
                return msg.sender == sender

            matchers.append(matcher)
        elif isinstance(sender, str):
            def matcher(msg: Message) -> bool:
                return msg.sender.name == sender

            matchers.append(matcher)
        elif hasattr(sender, "search"):
            # regex or so
            def matcher(msg: Message) -> bool:
                m = sender.search(msg.sender.name)
                if m is not None:
                    return m.groupdict()

            matchers.append(matcher)
        else:
            raise ValueError("Don't know what to do with sender={}".format(sender))

        # channel
        if channel is None:
            pass
        elif isinstance(channel, Channel):
            def matcher(msg: Message) -> bool:
                return isinstance(msg.recipient, Channel) \
                       and msg.recipient == channel

            matchers.append(matcher)
        elif isinstance(channel, str):
            def matcher(msg: Message) -> bool:
                return isinstance(msg.recipient, Channel) \
                       and msg.recipient.name == channel

            matchers.append(matcher)
        elif hasattr(channel, "search"):
            # regex or so
            def matcher(msg: Message) -> bool:
                if not isinstance(msg.recipient, Channel):
                    return
                m = channel.search(msg.recipient.name)
                if m is not None:
                    return m.groupdict()

            matchers.append(matcher)
        else:
            raise ValueError("Don't know what to do with channel={}".format(channel))

        def message_matcher(msg: Message) -> bool:
            fn_kwargs = {}
            for m in matchers:
                ret = m(msg)
                # Internal matchers may return False or None to fail
                if ret is None or ret is False:
                    return
                # If one returns a dict the values in it will be passed to the handler
                if isinstance(ret, dict):
                    fn_kwargs.update(ret)
            return fn_kwargs

        def decorator(fn: Callable[[Message], None]) -> Callable[[Message], None]:
            mh = self.MessageHandler(message_matcher, fn)
            self._on_message_handlers.append(mh)
            self._log.debug("Added message handler {} with matchers {}".format(mh, matchers))
            return fn

        return decorator

    def remove_message_handler(self, handler: Callable[[Message], None]) -> None:
        for mh in self._on_message_handlers:
            if mh.handler == handler:
                self._log.debug("Removing message handler {}".format(mh))
                self._on_message_handlers.remove(mh)

    def await_message(self, *args, **kwargs) -> 'asyncio.Future[Message]':
        """
        Block until a message matches. See `on_message`
        """
        fut = asyncio.Future()
        @self.on_message(*args, **kwargs)
        async def handler(message):
            fut.set_result(message)
        # remove handler when done or cancelled
        fut.add_done_callback(lambda _: self.remove_message_handler(handler))
        return fut

    IrcMessage = namedtuple("IrcMessage", ("prefix", "args", "rest"))

    JoinHandler = namedtuple("JoinHandler", ("channel", "handler"))

    def on_join(self, channel: str=None) -> Callable[[Callable], Callable]:
        """
        Register a handler that's called after a channel is joined.
        The handler is called with the `Channel` as argument, must be a coroutine
        and is run non-blocking.
        :param channel: channel to look out for or `None` for all channels
        """
        def decorator(fn: Callable[[self.IrcMessage], None]):
            jh = self.JoinHandler(channel, fn)
            self._on_join_handlers.append(jh)
            self._log.debug("Added join handler {}".format(jh))
            return fn

        return decorator

    def remove_join_handler(self, handler: Callable[[Channel], None]) -> None:
        for jh in self._on_join_handlers:
            if jh.handler == handler:
                self._log.debug("Removing join handler {}".format(jh))
                self._on_join_handlers.remove(jh)

    CommandHandler = namedtuple("CommandHandler", ("args", "rest", "handler"))

    def on_command(self, *args: Sequence[str], rest: str=None) -> Callable[[Callable], Callable]:
        """
        Register a handler that's called when (the beginning of) a `IrcMessage` matches.
        The handler is called with the `IrcMessage` as argument, must be a coroutine
        and is run blocking, i.e. you cannot use `await_command` in it!
        :param args: commands args that must match (the actual command is the first arg)
        :param rest: match the rest (after the " :") of the `IrcMessage`
        """
        def decorator(fn: Callable[[self.IrcMessage], None]):
            ch = self.CommandHandler(args, rest, fn)
            self._on_command_handlers.append(ch)
            self._log.debug("Added command handler {}".format(ch))
            return fn

        return decorator

    def remove_command_handler(self, handler: Callable[[IrcMessage], None]) -> None:
        for ch in self._on_command_handlers:
            if ch.handler == handler:
                self._log.debug("Removing command handler {}".format(ch))
                self._on_command_handlers.remove(ch)

    def await_command(self, *args, **kwargs) -> 'asyncio.Future[IrcMessage]':
        """
        Block until a command matches. See `on_command`
        """
        fut = asyncio.Future()
        @self.on_command(*args, **kwargs)
        async def handler(msg):
            fut.set_result(msg)
        # remove handler when done or cancelled
        fut.add_done_callback(lambda _: self.remove_command_handler(handler))
        return fut

    def _parsemsg(self, msg: str) -> IrcMessage:
        # adopted from twisted/words/protocols/irc.py
        if not msg:
            return
        prefix = None
        rest = None
        if msg[0] == ":":
            prefix, msg = msg[1:].split(" ", 1)
        if " :" in msg:
            msg, rest = msg.split(" :", 1)
            args = msg.split()
        else:
            args = msg.split()
        return self.IrcMessage(prefix, tuple(args), rest)

    def _buildmsg(self, *args: List[str], prefix: str=None, rest: str=None) -> str:
        msg = ""
        if prefix:
            msg += ":{} ".format(prefix)
        msg += " ".join((str(arg) for arg in args))
        if rest:
            msg += " :{}".format(rest)
        return msg

    async def _send(self, *args: List[Any], prefix: str=None, rest: str=None) -> None:
        msg = self._buildmsg(*args, prefix=prefix, rest=rest)
        self._log.debug("<- {}".format(msg))
        self._writer.write(msg.encode(self.encoding) + b"\r\n")

    async def message(self, recipient: str, text: str, notice: bool=False) -> None:
        """
        Lower level messaging function used by User and Channel
        """
        await self._send(cc.PRIVMSG if not notice else cc.NOTICE, recipient, rest=text)

    async def _get_message(self) -> IrcMessage:
        line = await self._reader.readline()
        line = line.decode(self.encoding).strip("\r\n")

        if not line and self._reader.at_eof():
            return

        self._log.debug("-> {}".format(line))

        msg = self._parsemsg(line)

        if msg and await self._handle_special(msg):
            return

        return msg

    async def run(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)

        self._bg(self._connect())

        while not self._reader.at_eof():

            try:
                msg = await self._get_message()
            except:
                self._log.exception("Error during receiving")
                raise


            if not msg:
                continue

            for ch in self._on_command_handlers:
                args = msg.args[:len(ch.args)]
                if ch.args == args and (not ch.rest or ch.rest == msg.rest):
                    self._log.debug("Calling command handler {} with input {}".format(ch, msg))
                    await ch.handler(msg)

            if not self._connected:
                continue

            if msg.args[0] in (cc.PRIVMSG, cc.NOTICE):
                sender = self._resolve_sender(msg.prefix)
                recipient = self._resolve_recipient(msg.args[1])
                message = Message(sender, recipient, msg.rest, (msg.args[0] == cc.NOTICE))
                await self._handle_on_message(message)
                continue

            # self._log.info("Unhandled command: {} {}".format(command, kwargs))

        self._writer.close()

        self._log.info("Connection closed, exiting")

    def _bg(self, coro: coroutine) -> asyncio.Task:
        """Run coro in background, log errors"""
        async def runner():
            try:
                await coro
            except:
                self._log.exception("async: Coroutine raised exception")
        return asyncio.ensure_future(runner())

    async def _handle_special(self, msg: IrcMessage) -> bool:
        if msg.args[0] == cc.PING:
            await self._send(cc.PONG, rest=msg.rest)
            return True
        return False

    async def _handle_on_message(self, message: Message) -> None:
        for mh in self._on_message_handlers:
            match = mh.matcher(message)
            if match is not None:
                self._bg(mh.handler(message, **match))

    async def _connect(self) -> None:
        if self.password:
            await self._send(cc.PASS, self.password)
        nick = self._send(cc.NICK, self.nick)
        user = self._send(cc.USER, self.user, 0, "*", rest=self.realname)

        @self.on_command(cc.ERR_NICKNAMEINUSE)
        async def nick_in_use(msg):
            self.nick += "_"
            await self._send(cc.NICK, self.nick)

        @self.on_command(cc.RPL_ISUPPORT)
        async def feature_list(msg):
            for feature, _, value in map(lambda arg: arg.partition("="), msg.args):
                if feature == "CHANTYPES":  # CHANTYPES=#&
                    self._channel_types = value
                if feature == "PREFIX":  # PREFIX=(ov)@+
                    modes, _, prefixes = value[1:].partition(")")
                    self._prefix_map = dict(zip(prefixes, modes))

        end_motd = self.await_command(cc.RPL_ENDOFMOTD)

        await nick
        await user
        self._log.debug("Waiting for the end of the MOTD")
        await end_motd
        self._log.debug("End of the MOTD found, running handlers")

        # `cc.RPL_ISUPPORT` is either done or not available
        self.remove_command_handler(feature_list)
        # Nick chosen by now
        self.remove_command_handler(nick_in_use)

        self._connected = True

        for handler in self._on_connected_handlers:
            try:
                await handler()
            except:
                self._log.exception("Connect handler {} raised exception".format(handler))

    def _resolve_sender(self, prefix: str) -> User:
        if "!" in prefix and "@" in prefix:
            return self.get_user(prefix)
        # message probably sent by the server
        return None

    def get_user(self, nick: str) -> User:
        """
        :param nick: nick or prefix
        """
        hostmask = None
        if "!" in nick:
            nick, _, hostmask = nick.partition("!")
        user = self._users.get(nick)
        if not user:
            self._users[nick] = user = User(nick, self, hostmask=hostmask)
        elif not user.hostmask:
            user.hostmask = hostmask
        return user

    def get_channel(self, name: str) -> Channel:
        ch = self._channels.get(name)
        if not ch:
            self._channels[name] = ch = Channel(name, self)
        return ch

    def _resolve_recipient(self, recipient: str) -> Union[User, Channel]:
        if recipient[0] in self._channel_types:
            return self.get_channel(recipient)
        return self.get_user(recipient)

    async def join(self, channel: str, block: bool=False) -> Channel:
        if block:
            fut = asyncio.Future()
            @self.on_join(channel)
            async def waiter(channel_obj):
                self.remove_join_handler(waiter)
                fut.set_result(channel_obj)

        self._log.debug("Joining channel {}".format(channel))
        await self._send(cc.JOIN, channel)

        if block:
            return await fut

    async def _on_join(self, msg: IrcMessage) -> None:
        channel = self.get_channel(msg.rest)
        user = self.get_user(msg.prefix)
        if user.name != self.nick:
            channel.users.add(user)
            self._log.info("{} joined channel {}".format(user, channel))
            return
        # TODO: make less ugly
        @self.on_command(cc.RPL_NAMREPLY, self.nick, "=", channel.name)
        @self.on_command(cc.RPL_NAMREPLY, self.nick, "*", channel.name)
        @self.on_command(cc.RPL_NAMREPLY, self.nick, "@", channel.name)
        async def gather_nicks(msg):
            for nick in msg.rest.strip().split(" "):
                mode = self._prefix_map.get(nick[0], None)
                if mode:
                    nick = nick[1:]
                user = self.get_user(nick)
                # TODO: channel_user = ChannelUser(user, mode, channel)
                channel.users.add(user)

        # register a handler for waiting because we can't block in a command handler
        @self.on_command(cc.RPL_ENDOFNAMES, self.nick, channel.name)
        async def join_finished(msg):
            self.remove_command_handler(gather_nicks)
            self.remove_command_handler(join_finished)
            self._log.info("Joined channel {}".format(channel))

            for jh in self._on_join_handlers:
                if not jh.channel or jh.channel == channel.name:
                    self._bg(jh.handler(channel))

    async def part(self, channel: str, reason: str=None, block: bool=None) -> None:
        if block:
            part_done = self.await_command(cc.PART, channel)
        await self._send(cc.PART, channel, rest=reason)
        if block:
            await part_done

    async def quit(self, reason: str=None) -> Channel:
        for handler in self._on_disconnected_handlers:
            try:
                await handler(reason)
            except:
                self._log.exception("Connect handler {} raised exception".format(handler))
        await self._send(cc.QUIT, rest=reason)

    def add_module(self, module: 'Module'):
        self._modules.append(module)
        module._populate(self)

    async def _on_quit(self, msg: IrcMessage) -> None:
        user = self.get_user(msg.prefix)
        for channel in self._channels.values():
            channel.users.discard(user)
        del self._users[user.name]
        self._log.info("{} has quit: {}".format(user, msg.rest))

    async def _on_part(self, msg: IrcMessage) -> None:
        user = self.get_user(msg.prefix)
        channel = self.get_channel(msg.args[1])
        channel.users.remove(user)
        self._log.info("{} has left {}: {}".format(user, channel, msg.rest))

    async def _on_nick(self, msg: IrcMessage) -> None:
        """
        Nick change
        """
        user = self.get_user(msg.prefix)
        old_nick = user.name
        del self._users[old_nick]
        user.name = msg.rest
        if old_nick == self.nick:
            # (Forced?) Nick change for ourself
            self.nick = user.name
        self._users[user.name] = user
        self._log.info("{} changed their nick from {} to {}".format(user, old_nick, user.name))


class Module(metaclass=LoggerMetaClass):
    class ChannelProxy(metaclass=LoggerMetaClass):
        def __init__(self, name: str, module: 'Module'):
            self.name = name
            self._module = module
            self._channel = None
            self._buffered_calls = []

        def _populate(self, channel):
            """
            Populate proxy with the real channel when available
            """
            self._channel = channel
            for fn in self._buffered_calls:
                self._log.debug("Executing buffered call {}".format(fn))
                fn()

        def _buffer_call(self, callable):
            self._buffered_calls.append(callable)

        def __getattr__(self, method):
            if self._channel:
                return getattr(self._channel, method)
            else:
                if not method.startswith("on_"):
                    raise AttributeError(method)

                def on_anything(*args, **kwargs):
                    def decorator(fn):
                        self._log.debug("Cannot execute method {}(*{}, **{}) now, buffering".format(method, args, kwargs))
                        self._buffer_call(lambda: getattr(self._channel, method)(*args, **kwargs)(fn))
                        return fn
                    return decorator

                return on_anything

    def __init__(self, name: str):
        self.module_name = name

        # set by the Client
        self.client = None
        """:type: Client"""

        self._buffered_calls = []

    def _populate(self, client):
        """
        Populate module with the client when available
        """
        self.client = client
        for fn in self._buffered_calls:
            self._log.debug("Executing buffered call {}".format(fn))
            fn()

    def _buffer_call(self, callable):
        self._buffered_calls.append(callable)

    def get_channel(self, name: str) -> Union[Channel, ChannelProxy]:
        if self.client:
            return self.client.get_channel(name)

        self._log.debug("Cannot get channel {} now, returning proxy".format(name))
        proxy = self.ChannelProxy(name, self)
        self._buffer_call(lambda: proxy._populate(self.client.get_channel(name)))
        return proxy

    def __getattr__(self, method):
        if method not in ("on_connected", "on_message", "on_command", "on_join"):
            raise AttributeError(method)

        if self.client:
            return getattr(self.client, method)(*args, **kwargs)

        def on_anything(*args, **kwargs):
            def decorator(fn):
                self._log.debug("Cannot execute method {}(*{}, **{}) now, buffering".format(method, args, kwargs))
                self._buffer_call(lambda: getattr(self.client, method)(*args, **kwargs)(fn))
                return fn
            return decorator

        return on_anything
