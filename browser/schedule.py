import random
import threading
from threading import Timer
from typing import Optional

from proxy.queues import BROWSER_CMD_QUEUE
from common import BrowserCommand


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

        if self._timer:
            cmd = BrowserCommand(BrowserCommand.CMD_REFRESH, None, None)
            BROWSER_CMD_QUEUE.put(cmd)
        # next
        self._timer = Timer(random.Random().randint(60, 120), self.startTimer)
        self._timer.start()

    def terminate(self):
        self._should_exit.set()
        if self._timer:
            self._timer.cancel()
