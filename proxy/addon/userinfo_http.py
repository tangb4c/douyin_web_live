import json
import logging
import re
from typing import TYPE_CHECKING
from browser.common import BrowserCommand
from proxy.common import MessagePayload

if TYPE_CHECKING:
    from mitmproxy import http
    from queue import SimpleQueue

logger = logging.getLogger(__name__)
print(f"loggerName: {logger.name}")
class UserInfoAddon:
    def __init__(self, queue: "SimpleQueue[MessagePayload]", cmd_queue: "SimpleQueue[BrowserCommand]"):
        self._queue = queue
        self._cmd_queue = cmd_queue

    def response(self, flow: "http.HTTPFlow"):
        if flow.response.status_code != 200:
            return
        self.record(flow)

        # for k, v in flow.request.headers.items(True):
        #     print(f"{k}: {v}")

        # 主页URL
        re_c = re.search(r'^https://www\.douyin\.com/user/([\w-]{30,100})', flow.request.url)
        if re_c:
            # 直播链接
            re_live = re.search(r'https://live\.douyin\.com/\d{8,20}\?[^"]+', flow.response.text)
            if re_live:
                userid = re_c.group(1)
                url = re_live.group()
                browser_cmd = BrowserCommand(BrowserCommand.CMD_REDIRECT, userid, url)
                self._cmd_queue.put(browser_cmd)
                logger.info(f"命令推入队列。{browser_cmd}")
                return
        re_c = re.match(r'https://live\.douyin\.com/webcast/[\w/]+/enter/', flow.request.url)
        if re_c:
            # 直播流json
            payload = MessagePayload(flow.response.content)
            payload.request_url = flow.request.url
            payload.request_query = flow.request.query
            payload.text = flow.response.text
            self._queue.put(payload)
            logger.info(f"json响应推入异步队列。url:{payload.request_url}")

    # def _parse_live_url_in_user_profile(self, flow: http.HTTPFlow):
    def record(self, flow: "http.HTTPFlow"):
        parts = flow.request.url.split('?', 1)
        only_url = parts[0]
        if 'douyin.com' not in flow.request.host:
            logger.debug(f"{only_url}")
            flow.request.pretty_url
        elif len(flow.response.content) == 0:
            logger.debug(f"{only_url} content-length:0")
        elif 'Content-Type' in flow.response.headers:
            content_type: str = flow.response.headers['Content-Type']
            allowed = ('text/', '/json')
            if any(x for x in allowed if x in content_type):

                logger.debug(f"{flow.request.url} body:\n{flow.response.text}")
            else:
                logger.debug(f"{flow.request.url} content-type:{content_type}")
        else:
            logger.debug(f"{only_url} No content-type")
