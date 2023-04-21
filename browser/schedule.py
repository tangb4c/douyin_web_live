import datetime
import logging
import random
import threading
from threading import Timer
from typing import Optional, List

from config.share import g_download_lock
from proxy.queues import BROWSER_CMD_QUEUE
from browser.common import BrowserCommand

logger = logging.getLogger(__name__)
print(f"loggerName: {logger.name}")


class RandomPeriodSchedule:
    def __init__(self, userid):
        self._userid = userid
        self._timer: Optional[Timer] = None
        self._should_exit = threading.Event()
        self._quick_monitor_count = 0  # 快速监测次数

    def reset(self):
        self._should_exit.clear()
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def enable_quick_watch_mode(self):
        self._quick_monitor_count = 10
        logger.info(f"已开启快速检测模式, {self._userid}")

    @property
    def userid(self):
        return self._userid

    def startTimer(self):
        if self._should_exit.is_set():
            return

        # 仅在工作时间内刷新
        if self._timer:
            if self._is_worktime():
                if not g_download_lock.is_locked(self._userid):
                    cmd = BrowserCommand(BrowserCommand.CMD_REFRESH, self._userid, None)
                    BROWSER_CMD_QUEUE.put(cmd)
                else:
                    logger.info(f"{self.userid} 已被锁住，跳过")
            else:
                logger.info(f"不在工作时间，跳过消息推送")
        else:
            logger.info(f"timer为null")
        # next
        if self._quick_monitor_count > 0:
            self._quick_monitor_count -= 1
            next_refresh_interval = random.randint(10, 25)
        else:
            next_refresh_interval = random.randint(130, 360)

        logger.info(f"下次刷新间隔:{next_refresh_interval}秒")
        self._timer = Timer(next_refresh_interval, self.startTimer)
        self._timer.start()

    def _is_worktime(self):
        begin = datetime.time.fromisoformat("07:00:00")
        end = datetime.time.fromisoformat("21:00:00")
        now = datetime.datetime.now().time()
        return begin <= now and now <= end

    def terminate(self):
        self._should_exit.set()
        if self._timer:
            self._timer.cancel()


class ScheduleManager:
    def __init__(self):
        self.timers: "List[RandomPeriodSchedule]" = list()

    def add_timer(self, userid):
        t = RandomPeriodSchedule(userid)
        t.startTimer()
        self.timers.append(t)
        logger.info(f"添加定时刷新timer, useid: {userid}")

    def enable_quick_monitor(self, userid):
        for x in self.timers:
            if x.userid == userid:
                x.enable_quick_watch_mode()

    def terminate(self):
        for x in self.timers:
            x.terminate()
        self.timers.clear()
