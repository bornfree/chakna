import os
import threading
import time
import tempfile
import wave
import uuid
import json
from datetime import datetime

import numpy as np
import openai
import redis

from sensors.audio.client import AudioClient
from sensors.audio.config import REDIS_URL, SAMPLE_RATE, CHANNELS
from dotenv import load_dotenv

load_dotenv()

# ——— Configuration ———
TRANSCRIPT_STREAM      = os.getenv("TRANSCRIPT_STREAM", "audio:transcriptions")
LATEST_KEY             = os.getenv("LATEST_TRANSCRIPT_KEY", "audio:latest_transcript")
MODEL_NAME             = os.getenv("TRANSCRIPTION_MODEL", "gpt-4o-transcribe")
CHUNK_DURATION_SEC     = float(os.getenv("CHUNK_DURATION_SEC", "5.0"))
OVERLAP_SEC            = float(os.getenv("OVERLAP_SEC", "1.0"))
SILENCE_THRESHOLD      = int(os.getenv("SILENCE_THRESHOLD", "500"))

# Ensure OpenAI key is set
oai_key = os.getenv("OPENAI_API_KEY")
if not oai_key:
    raise RuntimeError("Please set OPENAI_API_KEY in your environment")
openai.api_key = oai_key

class SpeechTranscriptionService:
    def __init__(self):
        # Redis client
        self.redis = redis.Redis.from_url(REDIS_URL)
        # Audio stream client
        self.client = AudioClient()

        # Audio format
        self.sample_rate  = SAMPLE_RATE
        self.channels     = CHANNELS
        self.sample_width = 2  # bytes per sample (int16)

        # Segment sizing
        self.segment_bytes = int(CHUNK_DURATION_SEC * self.sample_rate * self.sample_width * self.channels)
        self.overlap_bytes = int(OVERLAP_SEC * self.sample_rate * self.sample_width * self.channels)

        # Internal buffers
        self.buffer      = bytearray()
        self.buffer_lock = threading.Lock()
        self.segment_q   = []

        # Start background loops
        threading.Thread(target=self._read_audio, daemon=True).start()
        threading.Thread(target=self._chunker,    daemon=True).start()
        threading.Thread(target=self._transcribe, daemon=True).start()

    def _read_audio(self):
        for msg in self.client.stream_chunks():
            pcm = msg["pcm_bytes"]
            with self.buffer_lock:
                self.buffer.extend(pcm)

    def _chunker(self):
        while True:
            with self.buffer_lock:
                if len(self.buffer) >= self.segment_bytes:
                    seg = bytes(self.buffer[:self.segment_bytes])
                    # retain overlap
                    self.buffer = self.buffer[self.segment_bytes - self.overlap_bytes:]
                    self.segment_q.append(seg)
            time.sleep(0.05)

    def _transcribe(self):
        while True:
            if not self.segment_q:
                time.sleep(0.1)
                continue
            segment = self.segment_q.pop(0)
            arr = np.frombuffer(segment, dtype=np.int16)
            if np.max(np.abs(arr)) < SILENCE_THRESHOLD:
                print("Silent...")
                continue

            # Write segment to temp WAV
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wav_path = tmp.name
            tmp.close()
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.sample_width)
                wf.setframerate(self.sample_rate)
                wf.writeframes(segment)

            # Transcribe
            try:
                with open(wav_path, "rb") as f:
                    resp = openai.audio.transcriptions.create(
                        model=MODEL_NAME,
                        file=f,
                        response_format="text"
                    )
                text = resp.strip() if isinstance(resp, str) else resp.get("text", "")
            except Exception as e:
                text = f"<error: {e}>"
            finally:
                try:
                    os.remove(wav_path)
                except OSError:
                    pass

            # Build result
            result = {
                "segment_id": uuid.uuid4().hex,
                "timestamp":   datetime.utcnow().isoformat(),
                "text":        text
            }
            # Publish and update latest
            self.redis.xadd(TRANSCRIPT_STREAM, result)
            self.redis.set(LATEST_KEY, json.dumps(result))

    def run(self):
        print("SpeechTranscriptionService running with Redis streams…")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping SpeechTranscriptionService.")

if __name__ == "__main__":
    svc = SpeechTranscriptionService()
    svc.run()
