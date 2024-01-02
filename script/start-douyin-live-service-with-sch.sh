#!/bin/sh

echo "pkill"
#pkill -f douyin-live-service
echo "killall"
killall chromedriver chrome
sleep 2
killall -9 chromedriver chrome
sleep 1
# ps aux|grep douyin-live-service
# 工作目录设置为/data/deploy/douyin_web_live
/bin/scl enable rh-python38 '/home/blaketang/.local/bin/pipenv run python main.py douyin-live-service'
