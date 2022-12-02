import time


class MessagePayload(object):
    def __init__(self, body: bytes):
        self.body = body
        self.timestamp: float = time.time()
        self.request_url: str = ""
        self.request_query: dict[str, str] = {}
        self.text: str = ""
