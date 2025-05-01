#!/usr/bin/env python3
"""
sensors/vision/client.py

VisionClient for redis_picamera_service.py:
- Subscribes to a Redis channel of base64-JPEG frames
- Decodes and caches the latest frame
- Provides blocking read() and non-blocking latest() methods
"""

import threading
import time
import json
import base64

import redis
import numpy as np
import cv2

class VisionClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        channel: str = "sensors:vision:frames"
    ):
        """
        Connect to Redis and start a background listener.
        Args:
            host: Redis server hostname
            port: Redis server port
            channel: Redis Pub/Sub channel delivering frames
        """
        self._redis = redis.Redis(host=host, port=port)
        self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        self._pubsub.subscribe(channel)

        self._lock = threading.Lock()
        self._latest = None  # will hold (frame_id: str, image: np.ndarray)

        # launch listener thread
        t = threading.Thread(target=self._listener, daemon=True)
        t.start()

    def _listener(self):
        for msg in self._pubsub.listen():
            try:
                payload = json.loads(msg["data"])
                fid = payload["frame_id"]
                b64 = payload["jpeg_b64"]
                jpg = base64.b64decode(b64)
                arr = np.frombuffer(jpg, dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                with self._lock:
                    self._latest = (fid, img)
            except Exception:
                # silently skip invalid messages
                continue

    def read(self, timeout: float = None):
        """
        Blocking: wait until the first frame arrives (or timeout).
        Returns:
            (frame_id: str, image: np.ndarray)
        Raises:
            TimeoutError if no frame in `timeout` seconds.
        """
        start = time.time()
        while True:
            with self._lock:
                if self._latest is not None:
                    return self._latest
            if timeout is not None and (time.time() - start) >= timeout:
                raise TimeoutError(f"No frame received in {timeout} s")
            time.sleep(0.01)

    def latest(self):
        """
        Non-blocking: returns the most recent frame or None if none yet.
        Returns:
            (frame_id: str, image: np.ndarray) or None
        """
        with self._lock:
            return self._latest
