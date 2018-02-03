import textwrap
import shlex
import inspect
from typing import Sequence
from asif.bot import Channel, User

class _Command:
    def __init__(self, name: str, hint: str, fn):
        self.name = name
        self.hint = hint
        self._fn = fn
        self._spec = inspect.getfullargspec(fn)
        if fn.__doc__:
            self.doc = fn.__doc__.lstrip("\n").rstrip("\n ")
            self.doc = textwrap.dedent(self.doc)
        else:
            self.doc = None

    def __call__(self, *args, **kwargs):
        return self._fn(*args, **{
            key: kwargs[key] for key in kwargs if (key in self._spec.args
                    or key in self._spec.kwonlyargs)
        })

class CommandSet:
    def __init__(self, client, prefix=".", ident=None):
        """
        Initializes a new command set for this client.

        :param client: The asif.bot.Client to use.
        :param prefix: The command prefix to use.
        :param ident: The identification; if provided it will be used in
            response to the .bots command
        """
        self.client = client
        self.prefix = prefix
        self.ident = None
        self._commands = dict()
        self._aliases = dict()

        client.on_message()(self._dispatch)

        self.command("help")(self._help)

        if ident:
            @self.command("bots")
            async def _bots(message):
                await message.reply(ident)

    async def _help(self, *args, message):
        if len(args) == 0:
            docs = list(self.prefix + key + (f" ({cmd.hint})" if cmd.hint else "")
                for key, cmd in self._commands.items() if key not in ("bots", "help"))
            lines = textwrap.wrap("; ".join(docs), width=400)
            for line in lines:
                if isinstance(message.recipient, Channel):
                    await message.sender.message(line, notice=True)
                else:
                    await message.sender.message(line)
        elif len(args) == 1:
            cmd = self._commands.get(args[0])
            if not cmd:
                return
            if not cmd.doc:
                await message.sender.message(
                        "No help available for that command",
                        notice=True)
            else:
                for line in cmd.doc.split("\n"):
                    await message.sender.message(line, notice=True)

    async def _dispatch(self, message):
        try:
            args = shlex.split(message.text)
        except ValueError:
            return
        if len(args) == 0:
            return
        if args[0] in [f"{self.client.nick}:", f"{self.client.nick},"] and len(args) >= 2:
            _cmd = args[1]
            args = args[2:]
        elif args[0][0] == self.prefix:
            _cmd = args[0][1:]
            args = args[1:]
        elif isinstance(message.recipient, User):
            _cmd = args[0]
            args = args[1:]
        else:
            return
        cmd = self._commands.get(_cmd)
        if not cmd:
            return
        reply = await cmd(*args,
            message=message,
            client=self.client,
            cmdset=self)
        if isinstance(reply, str):
            if isinstance(message.recipient, Channel):
                reply = f"{message.sender.name}: {reply}"
            await message.reply(reply)

    def command(self, name: str=None, hint: str=None, aliases: Sequence[str]=list()):
        """
        Register a command handler that will be invoked when a command is
        detected. If your handler has a docstring, it will be shown for
        .help [command]. The function will be invoked with *args set to the
        list of parameters given (as parsed by shlex.split). You may also
        include any of these keyword arguments in your signature:

        message:    the original message this was invoked in response to
        client:     the value of CommandSet.client
        cmdset:     this command set

        If your function returns a string, it will be given back to the user
        who issued the command.

        :param name: name of the command. Defaults to __name__ if None.
        :param hint: hint for the command (shown for .help).
        :param aliases: aliases for this command.
        """
        def decorator(fn):
            _name = name or fn.__name__
            cmd = _Command(_name, hint, fn)
            self._commands[_name] = cmd
            for alias in aliases:
                self._aliases[alias] = cmd
            return fn
        return decorator
