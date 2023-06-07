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
    def __init__(self, user):
        self._user = user
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
        logger.info(f"已开启快速检测模式, {self._user}")

    @property
    def user(self):
        return self._user

    @property
    def userinfo(self):
        return f"{self.user.get('name')}"

    def _getNextRefreshInterval(self):
        if 'monitor_plan' in self.user:
            now_weekday = datetime.datetime.now().isoweekday()
            time_now = datetime.datetime.now().time()
            for plan in self.user.get('monitor_plan'):
                if ('weekday' in plan) and not any(x for x in plan.get('weekday') if x == now_weekday):
                    logger.info(f"【获取下次刷新间隔】跳过当前计划。当前星期{now_weekday},{self.userinfo} 不在监视计划内:{plan}")
                    continue
                time_begin = datetime.datetime.strptime(plan.get('time_begin'), "%H:%M:%S").time()
                time_end = datetime.datetime.strptime(plan.get('time_end'), "%H:%M:%S").time()
                if time_begin <= time_now <= time_end:
                    interval_min = plan.get('interval_min')
                    interval_max = plan.get('interval_max')
                    interval = random.randint(interval_min, interval_max)
                    logger.info(f"【获取下次刷新间隔】命中监视计划:{plan}, {self.userinfo} 采用间隔：{interval}")
                    return interval
                # else:
                #     logger.info(f"未命中此监控计划:{plan}, {self.userinfo}")
        logger.info(f"【获取下次刷新间隔】未找到自定义计划，采用系统默认间隔设置, {self.userinfo}")
        return random.randint(130, 360)

    def _isWork(self):
        if 'monitor_plan' in self.user:
            now_weekday = datetime.datetime.now().isoweekday()
            time_now = datetime.datetime.now().time()
            for plan in self.user.get('monitor_plan'):
                if ('weekday' in plan) and not any(x for x in plan.get('weekday') if x == now_weekday):
                    logger.info(f"跳过当前计划。当前星期{now_weekday},{self.userinfo} 不在计划内:{plan}")
                    continue
                time_begin = datetime.datetime.strptime(plan.get('time_begin'), "%H:%M:%S").time()
                time_end = datetime.datetime.strptime(plan.get('time_end'), "%H:%M:%S").time()
                if time_begin <= time_now <= time_end:
                    logger.info(f"命中监视计划，{self.userinfo} 允许工作:{plan}")
                    return True
        # 非工作时间
        if not self._is_worktime():
            logger.info(f"当前为非工作时间. {self.userinfo}")
            return False

        if 'monitor_mode' in self.user:
            monitor_mode = self.user.get('monitor_mode')
            if monitor_mode == 'watch':
                logger.info(f"当前监视模式为watch，允许监视 {self.userinfo}")
                return True

        logger.info(f"暂停刷新，跳过: {self.userinfo}")
        return False

    def startTimer(self):
        if self._should_exit.is_set():
            return

        # 仅在工作时间内刷新
        if self._timer:
            if self._isWork():
                if not g_download_lock.is_locked(self._user.get('sec_uid')):
                    cmd = BrowserCommand(BrowserCommand.CMD_REFRESH, self._user, None)
                    BROWSER_CMD_QUEUE.put(cmd)
                else:
                    logger.info(f"{self.userinfo} 已被锁住，跳过自动刷新")
        else:
            logger.info(f"timer为null")

        # 快速刷新模式
        if self._quick_monitor_count > 0:
            self._quick_monitor_count -= 1
            next_refresh_interval = random.randint(10, 25)
            logger.info(
                f"快速刷模式. {self.userinfo} 剩余次数：{self._quick_monitor_count} 下次间隔:{next_refresh_interval}")
        else:
            next_refresh_interval = self._getNextRefreshInterval()

        logger.info(f"下次刷新间隔:{next_refresh_interval}秒 {self.userinfo}")
        if not self._should_exit.is_set():
            self._timer = Timer(next_refresh_interval, self.startTimer)
            self._timer.start()

    def _is_worktime(self):
        begin = datetime.time.fromisoformat("07:00:00")
        end = datetime.time.fromisoformat("21:00:00")
        now = datetime.datetime.now().time()
        return begin <= now <= end

    def terminate(self):
        self._should_exit.set()
        if self._timer:
            self._timer.cancel()


class ScheduleManager:
    def __init__(self):
        self.timers: "List[RandomPeriodSchedule]" = list()

    def add_timer(self, user):
        t = RandomPeriodSchedule(user)
        t.startTimer()
        self.timers.append(t)
        logger.info(f"添加定时刷新timer, user: {user}")

    def enable_quick_monitor(self, userid):
        for x in self.timers:
            if x.user.get('sec_uid') == userid:
                x.enable_quick_watch_mode()

    def terminate(self):
        for x in self.timers:
            x.terminate()
        self.timers.clear()
