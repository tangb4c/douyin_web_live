import logging
import os.path
import platform
import re
import shlex
import subprocess
import threading
from datetime import datetime

from browser.common import BrowserCommand
from config.helper import getPath, getConfig
from proxy.queues import BROWSER_CMD_QUEUE

logger = logging.getLogger(__name__)
print(f"loggerName: {logger.name}")


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


_encoding_event = threading.Lock()
_download_lock = DownloadLock()


class VideoInfo:
    live_resolution: str = ""
    url: str = ""
    sec_uid: str = ""
    nickname: str = ""

    def __str__(self) -> str:
        return f"主播昵称:{self.nickname} 解析度:{self.live_resolution} url:{self.url} sec_uid:{self.sec_uid}"


class FlvDownloader:
    def __init__(self, video: VideoInfo):
        self._encoding = False
        self.video = video
        if '?' in self.video.url:
            self.video.url += '&abr_pts=-1800'
        else:
            self.video.url += '?abr_pts=-1800'
        self.output_prefix = getConfig('output.video.file_prefix')
        self.output_path = getPath('output.video.save_path', True)
        if not self.output_path:
            raise Exception(f"视频保存路径未设置")

    def download(self):
        if not _download_lock.acquire(self.video.sec_uid):
            logger.warning(f"当前主播正在下载，同时只允许1个下载")
            return

        # TODO 暂时停止编码
        # self._encoding = _encoding_event.acquire(blocking=False)
        logger.info(f"启动下载：{self.video.sec_uid} 编码锁锁定状态：{self._encoding}")

        result = "下载未完成"
        try:
            cmd = self._get_ffmpeg_cmd()
            logger.info(cmd)
            args = shlex.split(cmd)
            result = subprocess.run(args)
        except:
            logger.exception("编码发生异常")

        _download_lock.release(self.video.sec_uid)

        if self._encoding:
            self._encoding = False
            _encoding_event.release()
            logger.info(f"清除编码锁定标记")

        logger.info(f"释放下载锁，以及清除编码锁定标记。视频下载结果: {result}")

        # 开启刷新（并关闭live窗口)
        cmd = BrowserCommand(BrowserCommand.CMD_OPENUSER, self.video.sec_uid, None)
        BROWSER_CMD_QUEUE.put(cmd)
        # 强制刷新
        cmd = BrowserCommand(BrowserCommand.CMD_REFRESH, self.video.sec_uid, None)
        BROWSER_CMD_QUEUE.put(cmd)
        # 开启快速刷新
        cmd = BrowserCommand(BrowserCommand.CMD_QUICKMONITOR, self.video.sec_uid, None)
        BROWSER_CMD_QUEUE.put(cmd)

    def getOutputFileName(self):
        nickname = re.sub(r'[/<>:\"\\?*]+', '-', self.video.nickname)
        dst_path = os.path.join(self.output_path, nickname)
        os.makedirs(dst_path, exist_ok=True)

        encoding_state = 'h264' if self._encoding else 'origin'
        filename = datetime.now().strftime(f"{nickname}_%Y-%m-%dT%H%M%S.{encoding_state}.mp4")
        return os.path.join(self.output_path, nickname, filename)

    def _get_ffmpeg_cmd(self):
        user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.5563.64 Safari/537.36'
        if platform.system() == 'Darwin':
            logger.info("MacOS模式")
            user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'

        header = """accept: */*
accept-encoding: gzip, deflate, br
accept-language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6

"""
        return f"""ffmpeg -y -icy 0 \
                    -referer "https://live.douyin.com/" \
                    -user_agent "{user_agent}" \
                    -headers "{header}" \
                    -i '{self.video.url}' \
                    {self._get_encoding_param()} \
                    '{self.getOutputFileName()}'"""

    def _get_encoding_param(self):
        if self._encoding:
            if 'tlinux' in platform.release():
                return """-c:v libx264 -crf 28 -preset veryslow -ar 32000 -ac 1 -c:a libfdk_aac -profile:a aac_he -b:a 28k"""
            elif 'Linux' == platform.system():
                return '-c copy'
            else:
                return '-c:v libx264 -crf 28 -preset veryslow -af aresample=resampler=soxr -ar 32000 -ac 1 -c:a libfdk_aac -profile:a aac_he -b:a 28k'
        else:
            logger.info("已有其它编码正在进行")
            return '-c copy'


class HlsDownloader:
    def __init__(self, url: str):
        self._url = url

    def download(self):
        now = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        header = """accept: */*
        accept-encoding: gzip, deflate, br
        accept-language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6
        """
        cmd = f"""ffmpeg -y -icy 0 \
            -referer "https://live.douyin.com/" \
            -user_agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36" \
            -headers "{header}" \
            -i '{self._url}' \
              -c:v libx264 -crf 28 -preset veryslow\
              -af aresample=resampler=soxr -ar 32000 -ac 1 -c:a libfdk_aac -profile:a aac_he -b:a 28k \
              '/Users/blaketang/Movies/刘平直播11月/刘平直播-{now}.mp4'"""
        logger.info(cmd)
        args = shlex.split(cmd)
        result = subprocess.Popen(args)
        logger.info(f"视频下载结果: {result}")
        cmd = BrowserCommand(BrowserCommand.CMD_OPENUSER, None, None)
        BROWSER_CMD_QUEUE.put(cmd)


if __name__ == '__main__':
    # FlvDownloader("abc").download()
    pass
