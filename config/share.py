import threading


# 下载锁，一个主播同时只能下载一次
class DownloadLock:
    def __init__(self):
        self._userlist = set()
        self._lock = threading.Lock()

    def acquire(self, user):
        with self._lock:
            if user in self._userlist:
                return False
            else:
                self._userlist.add(user)
                return True

    def release(self, user):
        with self._lock:
            self._userlist.remove(user)

    def is_locked(self, user):
        with self._lock:
            return user in self._userlist


g_download_lock = DownloadLock()
