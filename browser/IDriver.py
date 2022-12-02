import contextlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver


class IDriver():
    browser: "WebDriver"

    def __del__(self):
        self.terminate()

    def terminate(self):
        self.browser.quit()

    def new_tab(self) -> str:
        ...

    def change_tab(self, tab_handler: str):
        ...

    def open_url(self, url: str, tab_handler: str = ""):
        ...

    @contextlib.contextmanager
    def op_tab(self, tab_handler: str):
        cur_handle = self.browser.current_window_handle
        if tab_handler == "":
            tab_handler = cur_handle
        try:
            self.change_tab(tab_handler)
            yield self
        finally:
            self.change_tab(cur_handle)

    def refresh(self, tab_handler: str = ""):
        ...

    def screenshot(self, tab_handler: str = "") -> str:
        ...

    def close(self, tab_handler: str = "") -> None:
        ...
