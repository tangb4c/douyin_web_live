import threading
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from browser.chrome import ChromeDriver
from browser.common import BrowserCommand
from browser.edge import EdgeDriver
from browser.schedule import RandomPeriodSchedule
from config.helper import config
from proxy.queues import BROWSER_CMD_QUEUE

if TYPE_CHECKING:
    from typing import Type, Optional, List
    from browser.IDriver import IDriver

_manager: "Optional[BrowserManager]" = None
_random_period_timer: "Optional[RandomPeriodSchedule]" = None

class BrowserManager():
    _mapping: "dict[str, Type[IDriver]]" = {
        "chrome": ChromeDriver,
        "edge": EdgeDriver
    }

    def __init__(self):
        _config = config()["webdriver"]["use"]
        if _config not in self._mapping:
            raise Exception("不支持的浏览器")
        self._driver: IDriver = self._mapping[_config]()
        self._tabs: "List[TabInfo]" = []
        self._thread: "Optional[threading.Thread]" = None
        self._should_exit = threading.Event()

    def init_browser(self):
        _live_config = config().get("live", {})
        _users = _live_config.get("users", [])
        if type(_users) is not list:
            _users = [_users]
        _rooms = _live_config.get("rooms", [])
        if type(_rooms) is not list:
            _rooms = [_rooms]
        for _user in _users:
            self.open_user_page(str(_user))
        for _room in _rooms:
            self.open_live_page(str(_room))
        self._handle()

    @property
    def driver(self):
        return self._driver

    def open_user_page(self, sec_user_id: str):
        tab = TabInfo()
        tab.tab_type = TabInfo.TAB_TYPE_USER
        tab.user_id = sec_user_id
        tab.need_refresh = True
        if urlparse(sec_user_id).scheme:
            tab.url = sec_user_id
        else:
            # 单独的用户id
            tab.url = "https://www.douyin.com/user/" + sec_user_id
        self.open_tab(tab)

    def open_live_page(self, live_url: str):
        tab = TabInfo()
        tab.tab_type = TabInfo.TAB_TYPE_LIVE
        if not urlparse(live_url).scheme:
            # 单独的房间号
            live_url = "https://live.douyin.com/" + live_url
        tab.url = live_url
        self.open_tab(tab)

    def open_tab(self, tab_info: "TabInfo"):
        tab_handler = self._driver.new_tab()
        tab_info.tab_handler = tab_handler
        if not tab_info.tab_type:
            tab_info.tab_type = TabInfo.TAB_TYPE_OTHER
        self.driver.open_url(tab_info.url, tab_handler)
        if tab_info not in self._tabs:
            self._tabs.append(tab_info)

    def start_loop(self):
        self._should_exit.clear()
        self._thread = threading.Thread(target=self._handle)
        self._thread.start()

    def _handle(self):
        while True:
            message = BROWSER_CMD_QUEUE.get()
            if self._should_exit.is_set():
                if self._driver:
                    self._driver.terminate()
                break
            if message is None:
                continue
            if message.command == BrowserCommand.CMD_REDIRECT:
                self._handle_redirect(message)
            elif message.command == BrowserCommand.CMD_REFRESH:
                self._handle_refresh(message)
    def terminate(self):
        if not self._should_exit.is_set():
            self._should_exit.set()
            BROWSER_CMD_QUEUE.put(None)
        global _random_period_timer
        _random_period_timer.terminate()


    def _handle_redirect(self, message):
        tabinfo = next((x for x in self._tabs if x.user_id == message.user), None)
        if tabinfo:
            self.driver.close(tabinfo.tab_handler)
            self._tabs.remove(tabinfo)
            self.open_live_page(message.url)

    def _handle_refresh(self, message):
        # 刷新
        for x in self._tabs:
            if x.tab_type == TabInfo.TAB_TYPE_USER:
                self.driver.refresh(x.tab_handler)


class TabInfo(object):
    TAB_TYPE_OTHER = "other"
    TAB_TYPE_USER = "user"
    TAB_TYPE_LIVE = "live"

    def __init__(self):
        self.tab_handler: str = ""
        self.user_id: str = ""
        self.url: str = ""
        self.tab_type: str = self.TAB_TYPE_OTHER
        self.need_refresh = True


def init_manager():
    global _manager, _random_period_timer
    _manager = BrowserManager()
    _random_period_timer = RandomPeriodSchedule()

    threading.Thread(target=_manager.init_browser).start()
    _random_period_timer.startTimer()

    return _manager


def get_manager():
    if _manager is None:
        return init_manager()
    return _manager
