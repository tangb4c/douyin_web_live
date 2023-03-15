import os

from config.helper import config
from output.IOutput import IOutput
from typing import IO
import time


class XMLWriter(IOutput):
    """
    可输出与B站弹幕姬兼容的xml弹幕格式，可用于转成ass字幕
    """

    def __init__(self):
        self._file_mappings: "dict[str, IO[str]]" = {}
        self.time_mappings: "dict[str, float]" = {}
        self._save_path: "str" = os.path.expanduser(config()['output']['xml']['save_path'])
        if not os.path.isdir(self._save_path):
            os.makedirs(self._save_path)
        file_pattern =  config()['output']['xml']['file_pattern']
        self._file_name_pattern: "str" = os.path.join(self._save_path, file_pattern)

    def _get_fd_by_room_id(self, room_id: str) -> IO[str]:
        if room_id in self._file_mappings:
            return self._file_mappings[room_id]
        cur_ts = time.time()
        fd = open(self._file_name_pattern.format_map({
            "room_id": room_id,
            "ts": cur_ts
        }), "w", encoding="UTF-8")
        self._file_mappings[room_id] = fd
        self.time_mappings[room_id] = cur_ts
        return fd

    def _close_fd_by_room_id(self, room_id: str):
        if room_id in self._file_mappings:
            fd = self._file_mappings[room_id]
            if not fd.closed:
                fd.close()
            del self._file_mappings[room_id]
        if room_id in self.time_mappings:
            del self.time_mappings[room_id]

    def control_output(self, message):
        # 下播了
        self._close_fd_by_room_id(message.room_id)

    def _get_bias_ts_by_room_id(self, room_id: str, cur_ts: float = 0):
        if cur_ts == 0:
            cur_ts = time.time()
        if room_id not in self.time_mappings:
            return 0
        return cur_ts - self.time_mappings[room_id]

    def chat_output(self, message):
        fd = self._get_fd_by_room_id(message.room_id)
        if fd is None:
            return
        cur_time = time.time()
        _c = """<d p="{:.2f},1,24,{},{:.0f},0,{},0" user="{}">{}</d>\r\n""".format(
            self._get_bias_ts_by_room_id(message.room_id, cur_time), message.room_id,
            cur_time * 1000, message.user().id, message.user().nickname, message.content
        )
        fd.write(_c)
        fd.flush()

    def gift_output(self, message):
        fd = self._get_fd_by_room_id(message.room_id)
        if fd is None:
            return
        cur_time = time.time()
        _c = """<gift ts="{:.2f}" user="{}" giftname="{}" giftcount="{}"></gift>\r\n""".format(
            self._get_bias_ts_by_room_id(message.room_id, cur_time),
            message.user().nickname, message.gift.name, message.instance.repeatCount
        )
        fd.write(_c)
        fd.flush()

    def terminate(self):
        print("保存所有弹幕文件中...")
        # copy
        _rooms = [i for i in self._file_mappings.keys()]
        for _room_id in _rooms:
            self._close_fd_by_room_id(_room_id)
        print("保存完毕")
