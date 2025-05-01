#!/usr/bin/env python3
"""
redis_picamera_service.py

Captures from the Raspberry Pi camera using Picamera2 and publishes each
frame (JPEG, base64-encoded) to a Redis channel—no OpenCV required.

NOTE:
This file needs to be run using system python.
Does not work inside uv venv because of picamera2 not being supported.

"""

import time
import uuid
import base64
import json
import io

import redis
from picamera2 import Picamera2
from PIL import Image

# ------ Config ------
REDIS_HOST     = 'localhost'
REDIS_PORT     = 6379
VISION_CHANNEL = 'sensors:vision:frames'

INTERVAL_SEC   = 1.0               # seconds between captures
RESOLUTION     = (640, 480)        # (width, height)

# ------------

def main():
    # 1) Connect to Redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    # 2) Initialize and start the Picamera2
    picam2 = Picamera2()
    preview_conf = picam2.create_preview_configuration(
        main={"size": RESOLUTION}
    )
    picam2.configure(preview_conf)
    picam2.start()

    try:
        while True:
            # 3) Grab an RGB array from the camera
            rgb_array = picam2.capture_array()

            # 4) Convert to a PIL Image
            img = Image.fromarray(rgb_array).convert("RGB")

            # 5) JPEG-encode into a bytes buffer
            with io.BytesIO() as buf:
                img.save(buf, format='JPEG')
                jpeg_bytes = buf.getvalue()

            # 6) Base64 + JSON + publish
            payload = {
                "frame_id":  str(uuid.uuid4()),
                "timestamp": time.time(),
                "jpeg_b64":  base64.b64encode(jpeg_bytes).decode('ascii')
            }
            r.publish(VISION_CHANNEL, json.dumps(payload))

            # 7) Pause until next capture
            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        print("Interrupted—shutting down.")
    finally:
        picam2.stop()

if __name__ == '__main__':
    main()
