import shlex
import subprocess
from datetime import datetime

from browser.common import BrowserCommand
from proxy.queues import BROWSER_CMD_QUEUE


class FlvDownloader:
    def __init__(self, url: str):
        if '?' in url:
            self._url = url + '&abr_pts=-1800'
        else:
            self._url = url + '?abr_pts=-1800'

    def download(self):
        now = datetime.now().strftime("%Y-%m-%d %H%M%S")
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
        print(cmd)
        args = shlex.split(cmd)
        result = subprocess.run(args)
        print(f"视频下载结果: {result}")
        cmd = BrowserCommand(BrowserCommand.CMD_OPENUSER, None, None)
        BROWSER_CMD_QUEUE.put(cmd)


class HlsDownloader:
    def __init__(self, url: str):
        self._url = url

    def download(self):
        now = datetime.now().strftime("%Y-%m-%d %H%M%S")
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
        print(cmd)
        args = shlex.split(cmd)
        result = subprocess.Popen(args)
        print(f"视频下载结果: {result}")
        cmd = BrowserCommand(BrowserCommand.CMD_OPENUSER, None, None)
        BROWSER_CMD_QUEUE.put(cmd)


if __name__ == '__main__':
    FlvDownloader("abc").download()
