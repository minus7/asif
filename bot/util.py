def no_highlight(nick: str) -> str:
    """
    Inserts a Unicode Zero Width Space into nick to prevent highlights
    """
    return nick[0:1] + "\u200b" + nick[1:]

def bold(text: str) -> str:
    return "\x02" + text + "\x02"

def yellow(text: str) -> str:
    return "\x03" + "08" + text + "\x0f"
