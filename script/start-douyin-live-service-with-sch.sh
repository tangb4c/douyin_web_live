#!/usr/bin/env bash

killall chromedriver chrome
sleep 2
killall -9 chromedriver chrome
sleep 1
/bin/scl enable rh-python38 '/home/blaketang/.local/bin/pipenv run python main.py douyin-live-service'
