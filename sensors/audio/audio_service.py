# sensors/audio/service.py

import time
import base64
import threading
import sounddevice as sd
import redis
from datetime import datetime

from .config import REDIS_URL, STREAM_NAME, SAMPLE_RATE, CHANNELS, CHUNK_SIZE

class AudioCaptureService:
    def __init__(self):
        self.redis = redis.Redis.from_url(REDIS_URL)
        self.stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        """
        sounddevice callback: gets called with each chunk
        """
        if status:
            print(f"[AudioCapture] Status: {status}", flush=True)

        # timestamp as ISO
        ts = datetime.utcnow().isoformat()
        # raw PCM bytes
        pcm = indata.tobytes()
        # base64-encode so Redis can store clean strings
        pcm_b64 = base64.b64encode(pcm).decode('ascii')

        # push into Redis stream
        self.redis.xadd(
            STREAM_NAME,
            {
                "timestamp": ts,
                "pcm_b64": pcm_b64
            },
            maxlen=10_000,  # trim old entries
            approximate=True
        )

    def start(self):
        """
        Begin capturing audio
        """
        print(f"[AudioCapture] Starting @ {SAMPLE_RATE}Hz, {CHANNELS}ch, chunk={CHUNK_SIZE}")
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            blocksize=CHUNK_SIZE,
            callback=self._audio_callback,
            dtype='int16'
        )
        with self.stream:
            print("[AudioCapture] Running... press Ctrl+C to stop")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("[AudioCapture] Stopping...")

if __name__ == "__main__":
    svc = AudioCaptureService()
    svc.start()
