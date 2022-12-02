import json
import re
from typing import TYPE_CHECKING
from browser.common import BrowserCommand
from proxy.common import MessagePayload

if TYPE_CHECKING:
    from mitmproxy import http
    from queue import SimpleQueue


class UserInfoAddon:
    def __init__(self, queue: "SimpleQueue[MessagePayload]", cmd_queue: "SimpleQueue[BrowserCommand]"):
        self._queue = queue
        self._cmd_queue = cmd_queue

    def response(self, flow: http.HTTPFlow):
        if flow.response.status_code != 200:
            return
        # 主页URL
        re_c = re.search(r'^https://www\.douyin\.com/user/(\w{30,100})', flow.request.url)
        if re_c:
            # 直播链接
            re_live = re.search(r'https://live\.douyin\.com/\d{8,20}\?[^"]+', flow.response.text)
            if re_live:
                userid = re_c.group(1)
                url = re_live.group()
                browser_cmd = BrowserCommand(BrowserCommand.CMD_REDIRECT, userid, url)
                self._cmd_queue.put(browser_cmd)
                return
        re_c = re.match(r'https://live\.douyin\.com/webcast/web/enter/', flow.request.url)
        if re_c:
            # 直播流json
            payload = MessagePayload(None)
            payload.request_url = flow.request.url
            payload.request_query = flow.request.query
            payload.text = flow.request.text
            self._queue.put(payload)

    # def _parse_live_url_in_user_profile(self, flow: http.HTTPFlow):
