import datetime
import logging
import random
import threading
from threading import Timer
from typing import Optional

from proxy.queues import BROWSER_CMD_QUEUE
from browser.common import BrowserCommand
logger = logging.getLogger(__name__)
print(f"loggerName: {logger.name}")

class RandomPeriodSchedule:
    def __init__(self):
        self._timer: Optional[Timer] = None
        self._should_exit = threading.Event()

    def reset(self):
        self._should_exit.clear()
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def startTimer(self):
        if self._should_exit.is_set():
            return

        # 仅在工作时间内刷新
        if self._timer and self._is_worktime():
            cmd = BrowserCommand(BrowserCommand.CMD_REFRESH, None, None)
            BROWSER_CMD_QUEUE.put(cmd)
        # next
        next_refresh_interval = random.randint(60, 200)
        logger.info(f"下次刷新间隔:{next_refresh_interval}秒")
        self._timer = Timer(next_refresh_interval, self.startTimer)
        self._timer.start()

    def _is_worktime(self):
        begin = datetime.time.fromisoformat("08:00:00")
        end = datetime.time.fromisoformat("16:30:00")
        now = datetime.datetime.now().time()
        return begin <= now and now <= end

    def terminate(self):
        self._should_exit.set()
        if self._timer:
            self._timer.cancel()
