import datetime
import logging
import signal
import sys
import threading
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import util.bark
from browser.chrome import ChromeDriver
from browser.common import BrowserCommand
from browser.edge import EdgeDriver
from browser.schedule import RandomPeriodSchedule, ScheduleManager
from config.helper import config, getConfig
from proxy.queues import BROWSER_CMD_QUEUE

if TYPE_CHECKING:
    from typing import Type, Optional, List
    from browser.IDriver import IDriver, TabNotExistsException

_manager: "Optional[BrowserManager]" = None
_random_period_timer: ScheduleManager = ScheduleManager()

logger = logging.getLogger(__name__)
print(f"loggerName: {logger.name}")

class TabInfo(object):
    TAB_TYPE_OTHER = "other"
    TAB_TYPE_USER = "user"
    TAB_TYPE_LIVE = "live"

    def __init__(self):
        self.tab_handler: str = ""
        self.user: dict = {}  # 来自配置文件live.users
        self.user_id: str = ""
        self.url: str = ""
        self.tab_type: str = self.TAB_TYPE_OTHER
        self.need_refresh = True

    def __str__(self) -> str:
        return f"TabInfo: 刷新开关：{self.need_refresh} {self.tab_type} {self.user['name']} url:{self.url} handler:{self.tab_handler}"

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
        self._last_captcha_time = 0

    def fake_init_browser(self):
        print("fake_init_browser")
        tab = TabInfo()
        tab.tab_type = TabInfo.TAB_TYPE_OTHER
        tab.user_id = "follow"
        tab.url = "https://www.douyin.com/"
        self.open_tab(tab)

    def init_browser(self):
        print("init_browser")
        self.close_alltabs()

        _live_config = config().get("live", {})
        _users = _live_config.get("users", [])
        if type(_users) is not list:
            _users = [_users]
        _rooms = _live_config.get("rooms", [])
        if type(_rooms) is not list:
            _rooms = [_rooms]
        for _user in _users:
            self.open_user_page(_user)
        for _room in _rooms:
            # TODO: 这里的userid为空
            self.open_live_page(str(_room), None)
        self._handle()

    @property
    def driver(self):
        return self._driver

    def open_user_page(self, user: dict):
        if not user:
            return
        tab = TabInfo()
        tab.tab_type = TabInfo.TAB_TYPE_USER
        tab.user = user
        tab.user_id = user.get('sec_uid')
        tab.need_refresh = True
        if urlparse(tab.user_id).scheme:
            tab.url = tab.user_id
        else:
            # 单独的用户id
            tab.url = "https://www.douyin.com/user/" + tab.user_id
        self.open_tab(tab)
        logger.debug(f"打开了用户标签页:{tab}")
        # script_txt = '''
        # console.log("I am here!");
        # setTimeout(() => {
        #   document.location.reload();
        # }, 12*1000);
        # '''
        # self.driver.execute_script(script_txt, tab.tab_handler)
        # logger.error("Enter execute_script")

    def open_live_page(self, live_url: str, user):
        if not live_url:
            return
        tab = TabInfo()
        tab.user = user
        tab.user_id = user.get('sec_uid')
        tab.tab_type = TabInfo.TAB_TYPE_LIVE
        tab.need_refresh = True
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

    def close_alltabs(self):
        for x in self._tabs:
            self.driver.close(x.tab_handler)
        self._tabs.clear()

    def start_loop(self):
        self._should_exit.clear()
        self._thread = threading.Thread(target=self._handle)
        self._thread.start()

    def _handle(self):
        logger.debug('开始处理消息队列')
        try:
            while True:
                message = BROWSER_CMD_QUEUE.get()
                if self._should_exit.is_set():
                    break
                if message is None:
                    logger.debug("收到None消息")
                    continue
                # logger.debug(f"收到消息:{message}")
                if message.command == BrowserCommand.CMD_REDIRECT:
                    self._handle_redirect(message)
                elif message.command == BrowserCommand.CMD_REFRESH:
                    self._handle_refresh(message)
                elif message.command == BrowserCommand.CMD_OPENUSER:
                    self._handle_openuser(message)
                elif message.command == BrowserCommand.CMD_STOPLIVE:
                    self._handle_stoplive_refresh(message)
                elif message.command == BrowserCommand.CMD_QUICKMONITOR:
                    self._handle_quick_monitor(message)
        except TabNotExistsException as e:
            logger.exception(f"TAB未找到异常")
        except:
            logger.exception(f"发生异常, 发送退出信号, 直接退出")
            # signal.raise_signal(signal.SIGTERM)
            sys.exit()
        finally:
            if self._driver:
                self._driver.terminate()
                logger.info(f"已退出chrome")

    def terminate(self):
        _random_period_timer.terminate()
        if not self._should_exit.is_set():
            self._should_exit.set()
            BROWSER_CMD_QUEUE.put(None)

    def _handle_redirect(self, message):
        tabinfo = next((x for x in self._tabs if x.user_id == message.user.get('sec_uid')), None)
        if tabinfo:
            # self.driver.close(tabinfo.tab_handler)
            # self._tabs.remove(tabinfo)
            tabinfo.need_refresh = False
            self.open_live_page(message.url, message.user)

    def _handle_refresh(self, message):
        # 刷新
        for x in self._tabs[:]:
            # logger.debug(f"tab对象信息 {x}")
            if x.need_refresh and (x.user_id == None or x.user_id == message.user.get('sec_uid')):
                if x.tab_handler not in self.driver.handles():
                    logger.error(f"该handle{x}没有在chrome中找到:{self.driver.handles()} message:{message}")
                    self._tabs.remove(x)
                else:
                    self._check_captcha(x)
                    # self.driver.open_url(x.url, x.tab_handler)
                    logger.debug(f"准备刷新：{x}")
                    self.driver.refresh(x.tab_handler)
            # else:
            #    logger.debug(f"没有刷新. {x.need_refresh} {x}")

    def _handle_openuser(self, message):
        for x in self._tabs[:]:
            if x.tab_type == TabInfo.TAB_TYPE_USER and x.user_id == message.user.get('sec_uid'):
                x.need_refresh = True
            if x.tab_type == TabInfo.TAB_TYPE_LIVE and x.user_id == message.user.get('sec_uid'):
                # 顺便把live全给关了，这里逻辑写得比较烂，将就着用吧
                try:
                    self.driver.close(x.tab_handler)
                except:
                    logger.exception(f"异常发生。{message}")
                finally:
                    self._tabs.remove(x)

    def _handle_stoplive_refresh(self, message):
        for x in self._tabs:
            if x.tab_type == TabInfo.TAB_TYPE_LIVE and x.user_id == message.user.get('sec_uid'):
                x.need_refresh = False

    def _handle_quick_monitor(self, message):
        _random_period_timer.enable_quick_monitor(message.user)

    def _check_captcha(self, tab:TabInfo):
        # 判断是否要输入验证码
        with self.driver.op_tab(tab.tab_handler):
            title = self.driver.browser.title
            logger.debug(f"浏览器title:{title} {tab.user.get('name')}")
            if '验证码' in title and time.time() - self._last_captcha_time > 3600:
                util.bark.send_message("需要输入验证码", f"用户:{tab.user.get('name')} 窗口：{title}")
                self._last_captcha_time = time.time()
                logger.info(f"发现验证码窗口:{title} {tab} 并发送了通知")




def init_manager():
    global _manager
    _manager = BrowserManager()

    threading.Timer(5, _manager.init_browser).start()
    threading.Thread(target=_manager.fake_init_browser).start()

    # 添加定时刷新timer
    _users = getConfig("live.users")
    if not isinstance(_users, list):
        _users = [_users]
    for x in _users:
        _random_period_timer.add_timer(x)

    return _manager


def get_manager():
    if _manager is None:
        return init_manager()
    return _manager
