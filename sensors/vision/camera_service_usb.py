#!/usr/bin/env python3
"""
redis_usb_camera_service.py

Captures from a USB webcam via OpenCV and publishes each frame
(as JPEG, base64-encoded JSON) to a Redis channel—no RPC socket needed.
"""

import os
import time
import uuid
import json
import base64

import cv2
import redis

# ------ CONFIG -------
from config_loader import get_config

config = get_config()

REDIS_HOST = config.get('redis.host', 'localhost')
REDIS_PORT = config.get('redis.port', 6379)
VISION_CHANNEL = config.get('vision.redis.frames_channel', 'sensors:vision:frames')
INTERVAL_SEC = config.get('vision.camera.interval_sec', 1.0)
RESOLUTION = (config.get('vision.camera.resolution.width', 640), config.get('vision.camera.resolution.height', 480))
CAMERA_INDEX = config.get('vision.camera.index', 0)
# ------

def main():
    # 1) Connect to Redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    # 2) Open USB camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    w, h = RESOLUTION
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera index {CAMERA_INDEX}")

    print(f"Publishing frames from camera {CAMERA_INDEX} → {VISION_CHANNEL} every {INTERVAL_SEC}s")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # 3) Encode to JPEG
            fid = str(uuid.uuid4())
            success, buf = cv2.imencode(".jpg", frame)
            if not success:
                continue

            # 4) Base64 + JSON + publish
            payload = {
                "frame_id":  fid,
                "timestamp": time.time(),
                "jpeg_b64":  base64.b64encode(buf.tobytes()).decode("ascii")
            }
            r.publish(VISION_CHANNEL, json.dumps(payload))

            # 5) Wait
            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        print("Interrupted—shutting down.")
    finally:
        cap.release()

if __name__ == "__main__":
    main()
