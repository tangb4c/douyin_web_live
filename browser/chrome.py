from selenium import webdriver
from selenium.webdriver import Proxy, DesiredCapabilities
from selenium.webdriver.common.proxy import ProxyType

from config.helper import config
from browser.IDriver import IDriver
from selenium.webdriver.chrome.options import Options


class ChromeDriver(IDriver):
    def __init__(self):
        super(ChromeDriver, self).__init__()
        options = Options()
        if config()['webdriver']['headless']:
            options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
        options.add_argument('--proxy-server=%s:%s' % (config()['mitm']['host'], config()['mitm']['port']))
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--incognito')
        options.add_experimental_option('excludeSwitches', ['ignore-certificate-errors'])
        if config()['webdriver']['chrome']['no_sandbox']:
            options.add_argument('--no-sandbox')
        proxy = Proxy()
        proxy.proxy_type = ProxyType.MANUAL
        proxy.http_proxy = "%s:%s" % (config()['mitm']['host'], config()['mitm']['port'])
        proxy.ssl_proxy = "%s:%s" % (config()['mitm']['host'], config()['mitm']['port'])
        capabilities = DesiredCapabilities.CHROME
        proxy.add_to_capabilities(capabilities)

        self.browser = webdriver.Chrome(options=options,
                                        desired_capabilities=capabilities,
                                        executable_path=config()['webdriver']['chrome']['bin']
                                        )

    def new_tab(self) -> str:
        current_window_handles = self.browser.window_handles
        self.browser.execute_script("window.open('')")
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
        with self.op_tab(tab_handler):
            self.browser.close()