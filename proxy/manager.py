import asyncio
import threading
from typing import TYPE_CHECKING

from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from config.helper import config
from proxy.addon.danmaku_ws import DanmakuWebsocketAddon
from proxy.addon.userinfo_http import UserInfoAddon
from proxy.queues import MESSAGE_QUEUE, BROWSER_CMD_QUEUE

if TYPE_CHECKING:
    from typing import Optional

_manager: "Optional[ProxyManager]" = None


class ProxyManager:
    def __init__(self):
        self._mitm_instance = None
        self._loop: "asyncio.AbstractEventLoop" = asyncio.new_event_loop()
        opts = Options(
            listen_host=config()['mitm']['host'],
            listen_port=config()['mitm']['port'],
        )
        async def _init_mitm_instance():
            self._mitm_instance = DumpMaster(options=opts)
            self._load_addon()
            opts.update_defer(
                flow_detail=0,
                termlog_verbosity="error",
            )
        self._loop.run_until_complete(_init_mitm_instance())
        self._thread = None

    def __del__(self):
        self.terminate()

    def terminate(self):
        if self._mitm_instance:
            self._mitm_instance.shutdown()
        # if self._loop:
        #     if self._loop.is_running():
        #         self._loop.stop()

    def _load_addon(self):
        self._mitm_instance.addons.add(DanmakuWebsocketAddon(MESSAGE_QUEUE))
        self._mitm_instance.addons.add(UserInfoAddon(MESSAGE_QUEUE, BROWSER_CMD_QUEUE))

    def _start(self):
        asyncio.set_event_loop(self._loop)
        if self._mitm_instance:
            self._loop.run_until_complete(self._mitm_instance.run())

    def start_loop(self):
        self._thread = threading.Thread(target=self._start, args=())
        self._thread.start()

    def join(self):
        if self._thread:
            self._thread.join()


def init_manager():
    global _manager
    _manager = ProxyManager()
    return _manager


def get_manager():
    if _manager is None:
        return init_manager()
    return _manager
