#!/bin/sh
echo "kill process in script"
pkill -f 'bin/python main.py douyin-live-service'
killall chromedriver chrome
killall -9 chromedriver chrome
sleep 1
echo "finished kill process in script, start it"
# 工作目录设置为/data/deploy/douyin_web_live
/bin/scl enable rh-python38 '/home/blaketang/.local/bin/pipenv run python main.py douyin-live-service'
