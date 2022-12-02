from queue import SimpleQueue
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Optional
    from proxy.common import MessagePayload

MESSAGE_QUEUE: "SimpleQueue[Optional[MessagePayload]]" = SimpleQueue()
BROWSER_CMD_QUEUE: "SimpleQueue[Optional[MessagePayload]]" = SimpleQueue()