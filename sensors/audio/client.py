# sensors/audio/client.py

import base64
import redis
from typing import Iterator, Dict

from .config import REDIS_URL, STREAM_NAME

class AudioClient:
    def __init__(self, group: str = None, consumer: str = None):
        self.redis = redis.Redis.from_url(REDIS_URL)
        self.stream = STREAM_NAME
        # For simple reads we won't use consumer groups

    def stream_chunks(self, block_ms: int = 5000) -> Iterator[Dict]:
        """
        Yield new audio chunks as they arrive.
        """
        last_id = "$"
        while True:
            resp = self.redis.xread({self.stream: last_id}, block=block_ms, count=1)
            if not resp:
                continue
            _, entries = resp[0]
            for entry_id, fields in entries:
                last_id = entry_id
                pcm_b64 = fields[b"pcm_b64"].decode("ascii")
                audio = base64.b64decode(pcm_b64)
                yield {
                    "id": entry_id.decode(),
                    "timestamp": fields[b"timestamp"].decode(),
                    "pcm_bytes": audio
                }

    def get_history(self, start_id: str = "-", end_id: str = "+") -> Iterator[Dict]:
        """
        Replay already-captured audio between two entry IDs.
        Defaults to entire history.
        """
        entries = self.redis.xrange(self.stream, min=start_id, max=end_id)
        for entry_id, fields in entries:
            pcm_b64 = fields[b"pcm_b64"].decode("ascii")
            audio = base64.b64decode(pcm_b64)
            yield {
                "id": entry_id.decode(),
                "timestamp": fields[b"timestamp"].decode(),
                "pcm_bytes": audio
            }
