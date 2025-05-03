import threading
import time
import json
import base64
import queue

import redis
import numpy as np

class AudioClient:
    """
    Subscribes to Redis channel of base64-encoded audio chunks.
    Provides blocking read() and non-blocking latest() methods.
    """

    def __init__(
        self,
        host: str    = "localhost",
        port: int    = 6379,
        channel: str = "sensors:audio:chunks"
    ):
        self._redis   = redis.Redis(host=host, port=port)
        self._pubsub  = self._redis.pubsub(ignore_subscribe_messages=True)
        self._pubsub.subscribe(channel)

        self._lock    = threading.Lock()
        self._latest  = None  # will hold (chunk_id: int, data: bytes)

        # launch listener thread
        t = threading.Thread(target=self._listener, daemon=True)
        t.start()

    def _listener(self):
        for msg in self._pubsub.listen():
            try:
                payload = json.loads(msg["data"])
                cid     = payload["chunk_id"]
                b64     = payload["audio_b64"]
                data    = base64.b64decode(b64)
                with self._lock:
                    self._latest = (cid, data)
            except Exception:
                continue

    def read(self, timeout: float = None):
        """
        Blocking: wait until the first chunk arrives (or timeout).
        Returns:
            (chunk_id: int, data: bytes)
        Raises:
            TimeoutError if no chunk in `timeout` seconds.
        """
        start = time.time()
        while True:
            with self._lock:
                if self._latest is not None:
                    return self._latest
            if timeout is not None and (time.time() - start) >= timeout:
                raise TimeoutError(f"No audio chunk in {timeout}s")
            time.sleep(0.01)

    def latest(self):
        """
        Non-blocking: returns the most recent chunk or None if none yet.
        Returns:
            (chunk_id: int, data: bytes) or None
        """
        with self._lock:
            return self._latest

    def read_as_array(self):
        """
        Convenience: returns numpy int16 array (if FORMAT=='int16').
        """
        item = self.read()
        if not item:
            return None
        cid, data = item
        # assume int16 PCM
        arr = np.frombuffer(data, dtype=np.int16)
        return cid, arr
