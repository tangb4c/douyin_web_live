import shlex
import subprocess
from datetime import datetime

class FlvDownloader:
    def __init__(self, url: str):
        if '?' in url:
            self._url = url + '&abr_pts=-1800'
        else:
            self._url = url + '?abr_pts=-1800'

    def download(self):
        now = datetime.now().strftime("%Y-%m-%d %H%M%S")
        cmd = f"""ffmpeg -y -icy 0 \
            -referer "https://live.douyin.com/" \
            -user_agent "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36" \
            -headers "" \
            -t 20s -i '{self._url}' \
              -c:v libx264 -crf 28  \
              -af aresample=resampler=soxr -ar 32000 -ac 1 -c:a libfdk_aac -profile:a aac_he -b:a 28k \
              '刘平直播-{now}.mp4'"""
        print(cmd)
        args = shlex.split(cmd)
        subprocess.Popen(args)

if __name__ == '__main__':
    FlvDownloader("abc").download()