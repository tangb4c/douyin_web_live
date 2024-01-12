import atexit
import logging
import logging.config
import random
import signal
import sys

from browser.manager import init_manager as init_browser_manager
from config.helper import config
from output.manager import OutputManager
from proxy.manager import init_manager as init_proxy_manager


def _init_log():
    logging.config.fileConfig('logging.conf')


if __name__ == '__main__':
    _init_log()
    random.seed()
    proxy_manager = init_proxy_manager()
    proxy_manager.start_loop()
    browser_manager = init_browser_manager()
    output_manager = OutputManager()


    def terminate(*_):
        print("terminate 收到终止信号", file=sys.stderr, flush=True)
        logging.error(f"terminate 收到终止信号")
        browser_manager.terminate()
        output_manager.terminate()
        proxy_manager.terminate()
        print("terminate 完成全部子模块的terminate的调用", file=sys.stderr, flush=True)
        logging.error(f"terminate 完成全部子模块的terminate的调用")


    atexit.register(terminate)
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    output_manager.start_loop()
    try:
        proxy_manager.join()
    except Exception as e:
        print("terminate 在proxy_manager.join()时，收到异常", file=sys.stderr, flush=True)
        logging.exception("terminate 在proxy_manager.join()时，收到异常")
    finally:
        logging.error("触发terminate")
        terminate()
