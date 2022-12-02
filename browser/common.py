from typing import Optional


class BrowserCommand(object):
    CMD_REDIRECT = "redirect-url"
    CMD_REFRESH = "refresh"

    def __init__(self, command: str, userid: Optional[str], url: Optional[str]):
        self.command: str = command
        self.user: str = userid
        self.url: str = url
