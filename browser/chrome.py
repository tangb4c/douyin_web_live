import os.path
import platform

from selenium import webdriver
from selenium.webdriver import Proxy, DesiredCapabilities
from selenium.webdriver.common.proxy import ProxyType

from config.helper import config, getPath
from browser.IDriver import IDriver
from selenium.webdriver.chrome.options import Options


class ChromeDriver(IDriver):
    def __init__(self):
        super(ChromeDriver, self).__init__()
        options = Options()
        # chrome开关帮助
        # https://peter.sh/experiments/chromium-command-line-switches/
        if platform.system() == 'Linux':
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            # ssh -N -L 59314:localhost:59314 cdev
            # chrome://inspect, 配置中加入 localhost:59314
            options.add_argument("--remote-debugging-port=59314")
            # 去掉全局监听
            # options.add_argument("--remote-debugging-address=0.0.0.0")
            # 禁止图片和css加载
            # prefs = {"profile.managed_default_content_settings.images": 2, 'permissions.default.stylesheet': 2}
            # options.add_experimental_option("prefs", prefs)
            # options.add_argument('blink-settings=imagesEnabled=false')

            # https://iwiki.woa.com/pages/viewpage.action?pageId=1674340994
            # 公司网络安全要求开启沙箱。该选项开启，要求chrome在linux中运行在普通用户下，否则会报错（不过我关闭该选项后，似乎不会报错）
            # Chrome Headless doesn't launch on Debian · Issue #290 · puppeteer/puppeteer
            # https://github.com/puppeteer/puppeteer/issues/290
            # options.add_argument("--no-sandbox")

            # 这个选项一般是shm内存较少，发生crash时，可以开启这个
            # options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-browser-side-navigation")
            options.add_argument("disable-infobars")
            # 不用等待，因为我们没用到dom
            options.page_load_strategy = 'none'
            #
            options.add_argument("--window-size=800,600")
            options.binary_location = "/opt/google/chrome/chrome"
        elif config()['webdriver']['headless']:
            options.add_argument("--headless")
            options.add_argument("--window-size=1280,720")
        # 可以保存cookie
        options.add_argument(f"user-data-dir={getPath('webdriver.chrome.user_data_dir', create_if_not_exist=True)}")
        # user-agent
        # 默认：
        # Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/111.0.5563.64 Safari/537.36
        # options.add_argument('user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"')
        options.add_argument('user-agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.5563.64 Safari/537.36"')

        options.add_argument('--proxy-server=%s:%s' % (config()['mitm']['host'], config()['mitm']['port']))
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        # options.add_argument('--incognito')
        # 容易被反爬，加上这个选项
        options.add_argument('--disable-features=UserAgentClientHint')
        # options.add_experimental_option('excludeSwitches', ['ignore-certificate-errors'])
        # 关闭 'enable-automation', 避免在js中被 window.navigator.webdriver 检测到
        options.add_experimental_option('excludeSwitches', ['ignore-certificate-errors', 'enable-automation'])
        # 规避检测 selenium修改window.navigator.webdriver
        # https://blog.csdn.net/qq_35866846/article/details/113185737
        options.add_argument("--disable-blink-features=AutomationControlled")

        # 【自动化】Selenium如何隐藏“Chrome is being controlled...” - 知乎
        # https://zhuanlan.zhihu.com/p/89451454
        # 有时浏览器会弹窗：disable developer mode extensions，使用下面的选项，可以禁止该弹窗
        options.add_experimental_option('useAutomationExtension', False)
        # 隐藏“Save password”弹窗
        options.add_experimental_option("prefs", {"profile.password_manager_enabled": False, "credentials_enable_service": False})

        # 禁止加载图片，提升爬取速度
        # prefs = {"profile.managed_default_content_settings.images": 2}
        # options.add_experimental_option("prefs", prefs)

        if config()['webdriver']['chrome']['no_sandbox']:
            options.add_argument('--no-sandbox')
        proxy = Proxy()
        proxy.proxy_type = ProxyType.MANUAL
        proxy.http_proxy = "%s:%s" % (config()['mitm']['host'], config()['mitm']['port'])
        proxy.ssl_proxy = "%s:%s" % (config()['mitm']['host'], config()['mitm']['port'])
        capabilities = DesiredCapabilities.CHROME
        proxy.add_to_capabilities(capabilities)

        chrome_binary_path = os.path.expanduser(config()['webdriver']['chrome']['bin'])
        self.browser = webdriver.Chrome(options=options,
                                        desired_capabilities=capabilities,
                                        executable_path=chrome_binary_path,
                                        )
        # Remove navigator.webdriver Flag using JavaScript
        # self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def new_tab(self) -> str:
        current_window_handles = self.browser.window_handles
        self.browser.execute_script("window.open('', '_blank')")
        new_window_handles = self.browser.window_handles
        for _handle in new_window_handles:
            if _handle not in current_window_handles:
                return _handle
        return ""

    def change_tab(self, tab_handler: str):
        if tab_handler not in self.browser.window_handles:
            return
        if tab_handler == self.browser.current_window_handle:
            return
        self.browser.switch_to.window(tab_handler)

    def open_url(self, url: str, tab_handler: str = ""):
        with self.op_tab(tab_handler):
            self.browser.get(url)

    def refresh(self, tab_handler: str = ""):
        with self.op_tab(tab_handler):
            self.browser.refresh()

    def screenshot(self, tab_handler: str = "") -> str:
        with self.op_tab(tab_handler):
            return self.browser.get_screenshot_as_base64()

    def close(self, tab_handler: str = "") -> None:
        if tab_handler in self.browser.window_handles:
            self.change_tab(tab_handler)
            self.browser.close()
            if len(self.browser.window_handles) > 0:
                self.browser.switch_to.window(self.browser.window_handles[0])

    def execute_script(self, script: str, tab_handler: str = "") -> None:
        with self.op_tab(tab_handler):
            self.browser.execute_script(script)

    def handles(self):
        return self.browser.window_handles
