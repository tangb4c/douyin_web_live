import logging
from typing import Optional

logger = logging.getLogger(__name__)
print(f"loggerName: {logger.name}")
class BrowserCommand(object):
    def __str__(self) -> str:
        return f"BrowserCommand{{cmd:{self.command} user:{self.user} url:{self.url}}}"

    # 重定向到live直播间，并关闭对应的user窗口
    CMD_REDIRECT = "redirect-url"
    CMD_REFRESH = "refresh"
    CMD_STOPLIVE = "stop-live-refresh"
    # 打开user窗口
    CMD_OPENUSER = "open-user"
    # 快速心跳检测
    CMD_QUICKMONITOR = "quick-monitor"

    def __init__(self, command: str, userid: Optional[str], url: Optional[str]):
        self.command: str = command
        self.user: str = userid
        self.url: str = url
