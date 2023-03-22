import collections
import gzip
import json
import logging
import threading
from typing import TYPE_CHECKING

from browser.common import BrowserCommand
from config.helper import config
from messages.chat import ChatMessage
from messages.control import ControlMessage
from messages.fansclub import FansclubMessage
from messages.gift import GiftMessage
from messages.like import LikeMessage
from messages.member import MemberMessage
from messages.roomuserseq import RoomUserSeqMessage
from messages.social import SocialMessage
from output.debug import DebugWriter
from output.videodownloader import FlvDownloader, HlsDownloader, VideoInfo
from output.print import Print
from output.xml import XMLWriter
from protobuf import message_pb2, wss_pb2
from proxy.queues import MESSAGE_QUEUE, BROWSER_CMD_QUEUE

logger = logging.getLogger(__name__)
print(f"loggerName: {logger.name}")

if TYPE_CHECKING:
    from typing import Type, Optional, List
    from output.IOutput import IOutput
    from proxy.common import MessagePayload


class OutputManager():
    _mapping: "dict[str, Type[IOutput]]" = {
        "print": Print,
        "xml": XMLWriter,
        "debug": DebugWriter,
    }
    _writer: "List[IOutput]" = []
    _thread: "Optional[threading.Thread]" = None
    _should_exit = threading.Event()

    def __init__(self):
        _config = config()['output']['use']
        if type(_config) != list:
            _config = [_config]
        for _c in _config:
            if _c not in self._mapping:
                raise Exception("不支持的输出方式")
            self._writer.append(self._mapping[_c]())

    def __del__(self):
        self.terminate()

    def decode_payload(self, message: "MessagePayload"):
        try:
            if message.text:
                self._decode_liveurl(message)
            else:
                response = message_pb2.Response()
                wss = wss_pb2.WssResponse()
                wss.ParseFromString(message.body)
                decompressed = gzip.decompress(wss.data)
                response.ParseFromString(decompressed)
                self.decode_message(response.messages)
        except Exception as e:
            for writer in self._writer:
                writer.error_output("ParseError", message.body, e)

    def decode_message(self, message_list: "List[message_pb2.Message]"):
        for message in message_list:
            try:
                if message.method == 'WebcastMemberMessage':
                    member_message = MemberMessage()
                    member_message.set_payload(message.payload)
                    for writer in self._writer:
                        writer.member_output(member_message)
                elif message.method == 'WebcastSocialMessage':
                    social_message = SocialMessage()
                    social_message.set_payload(message.payload)
                    for writer in self._writer:
                        writer.social_output(social_message)
                elif message.method == 'WebcastChatMessage':
                    chat_message = ChatMessage()
                    chat_message.set_payload(message.payload)
                    for writer in self._writer:
                        writer.chat_output(chat_message)
                elif message.method == 'WebcastLikeMessage':
                    like_message = LikeMessage()
                    like_message.set_payload(message.payload)
                    for writer in self._writer:
                        writer.like_output(like_message)
                elif message.method == 'WebcastGiftMessage':
                    gift_message = GiftMessage()
                    gift_message.set_payload(message.payload)
                    for writer in self._writer:
                        writer.gift_output(gift_message)
                elif message.method == 'WebcastRoomUserSeqMessage':
                    room_user_seq_message = RoomUserSeqMessage()
                    room_user_seq_message.set_payload(message.payload)
                    for writer in self._writer:
                        writer.userseq_output(room_user_seq_message)
                elif message.method == 'WebcastControlMessage':
                    control_message = ControlMessage()
                    control_message.set_payload(message.payload)
                    for writer in self._writer:
                        writer.control_output(control_message)
                elif message.method == 'WebcastFansclubMessage':
                    fansclub_message = FansclubMessage()
                    fansclub_message.set_payload(message.payload)
                    for writer in self._writer:
                        writer.fansclub_output(fansclub_message)
                else:
                    for writer in self._writer:
                        writer.other_output(message.method, message.payload)
            except Exception as e:
                for writer in self._writer:
                    writer.error_output(message.method, message.payload, e)

    def start_loop(self):
        self._should_exit.clear()
        self._thread = threading.Thread(target=self._handle)
        self._thread.start()

    def _handle(self):
        while True:
            message = MESSAGE_QUEUE.get()
            if self._should_exit.is_set():
                break
            if message is None:
                continue
            self.decode_payload(message)

    def terminate(self):
        if not self._should_exit.is_set():
            self._should_exit.set()
        MESSAGE_QUEUE.put(None)

        for writer in self._writer:
            writer.terminate()

    def _decode_liveurl(self, message: "MessagePayload"):
        cc = json.loads(message.text, object_pairs_hook=collections.OrderedDict)
        if True:
            video = self._parse(cc)
            if video == None:
                logger.warning(f"没有解析出video链接，注意检查. {message.text}")
                return
            print(f"开始下载：{video}")
            cmd = BrowserCommand(BrowserCommand.CMD_STOPLIVE, video.sec_uid, None)
            BROWSER_CMD_QUEUE.put(cmd)

            flv = FlvDownloader(video)
            threading.Thread(target=flv.download).start()

        else:
            hls_pull_url = cc['data']['data'][0]['stream_url']['hls_pull_url']
            # http://pull-hls-f26.douyincdn.com/stage/stream-688563396677206698_or4.m3u8?expire=639a89b7&sign=945cee6e9626cad639ebc9d9acababb6
            print(f"hls_pull_url: {hls_pull_url}")
            if hls_pull_url:
                hls = HlsDownloader(hls_pull_url)
                threading.Thread(target=hls.download).start()

    def _parse(self, cc: dict):
        flv_pull_urls = cc['data']['data'][0]['stream_url']['flv_pull_url']
        print(flv_pull_urls)
        if len(flv_pull_urls) > 0:
            first_item = next(x for x in flv_pull_urls.items())
            video = VideoInfo()
            # FULL_HD1
            video.live_resolution = first_item[0]
            # http://pull-flv-l26.douyincdn.com/stage/stream-688531551841943691_or4.flv?expire=639330de&sign=74135965ff2e50585d7f085fd9ff1762
            video.url = first_item[1]
            video.sec_uid = cc['data']['user']['sec_uid']
            video.nickname = cc['data']['user']['nickname']
            return video
        return None
