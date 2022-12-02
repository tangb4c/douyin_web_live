
class BrowserCommand(object):
    def __init__(self, body: bytes):
        self.body = body
        self.request_url: str = ""
        self.request_query: dict[str, str] = {}
