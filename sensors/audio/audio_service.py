#!/usr/bin/env python3
"""
redis_audio_service.py

Captures from the microphone via PyAudio and publishes each chunk
(as raw PCM, base64-encoded JSON) to a Redis channel—no RPC socket needed.
"""

import os
import time
import json
import base64

import redis
import pyaudio

from sensors.audio.config import SAMPLE_RATE, CHUNK_SIZE, CHANNELS, FORMAT

# ------ CONFIG ------
REDIS_HOST     = os.getenv("AUDIO_REDIS_HOST", "localhost")
REDIS_PORT     = int(os.getenv("AUDIO_REDIS_PORT", 6379))
AUDIO_CHANNEL  = os.getenv("AUDIO_CHANNEL", "sensors:audio:chunks")
# ------

def main():
    # 1) Connect to Redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)

    # 2) Initialize PyAudio input stream
    p = pyaudio.PyAudio()
    pa_format = {
        'int16': pyaudio.paInt16,
        'int32': pyaudio.paInt32,
        'float32': pyaudio.paFloat32
    }.get(FORMAT, pyaudio.paInt16)

    stream = p.open(
        format=pa_format,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    print(f"Publishing audio chunks → {AUDIO_CHANNEL} (chunk size={CHUNK_SIZE} frames)")
    chunk_id = 0
    try:
        while True:
            # 3) Read one chunk
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)

            # 4) Base64 + JSON + publish
            payload = {
                "chunk_id":    chunk_id,
                "timestamp":   time.time(),
                "audio_b64":   base64.b64encode(data).decode("ascii")
            }
            r.publish(AUDIO_CHANNEL, json.dumps(payload))
            chunk_id += 1

    except KeyboardInterrupt:
        print("Interrupted, shutting down.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    main()
