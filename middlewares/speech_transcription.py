import os
import socket
import threading
import json
import time
import wave
import tempfile
import uuid
import queue
from datetime import datetime
from dotenv import load_dotenv
import numpy as np

load_dotenv()

import openai
from sensors.audio.client import AudioClient

# Configuration
CHUNK_DURATION_SEC = 5.0       # audio segment length (seconds)
OVERLAP_SEC = 1.0              # overlap between segments (seconds)
SOCKET_PATH = '/tmp/speech_transcription.sock'
MODEL_NAME = 'gpt-4o-transcribe'  # audio-capable ChatGPT model
SILENCE_THRESHOLD = 500  # tweak this: lower → more sensitive to quiet speech

# Ensure OpenAI API key is set in environment
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("Please set the OPENAI_API_KEY environment variable")

class SpeechTranscriptionMiddleware:
    """
    Continuously pull audio from AudioClient, chunk it,
    transcribe via OpenAI, and expose latest text via JSON-RPC.
    """
    def __init__(self):
        # Initialize AudioClient
        self.audio_client = AudioClient()
        cfg = self.audio_client.config
        self.sample_rate = cfg['sample_rate']
        self.channels = cfg.get('channels', 1)
        self.sample_width = 2  # 16-bit PCM

        # Byte calculations
        self.segment_bytes = int(CHUNK_DURATION_SEC * self.sample_rate * self.sample_width * self.channels)
        self.overlap_bytes = int(OVERLAP_SEC * self.sample_rate * self.sample_width * self.channels)

        # Buffers
        self.buffer = bytearray()
        self.buffer_lock = threading.Lock()
        self.segment_queue = queue.Queue()
        self._latest = None
        self.latest_lock = threading.Lock()

        # RPC socket
        try: os.unlink(SOCKET_PATH)
        except OSError: pass
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o660)
        self.server.listen()
        threading.Thread(target=self._serve, daemon=True).start()

        # Start chunker and transcription
        threading.Thread(target=self._chunker_loop, daemon=True).start()
        threading.Thread(target=self._transcription_loop, daemon=True).start()

        # Start streaming
        self.audio_client.start_streaming(callback=self._audio_callback)
        print("Speech transcription middleware started")

    def _audio_callback(self, chunk, config):
        """Accumulate PCM bytes"""
        data = chunk.tobytes()
        with self.buffer_lock:
            self.buffer.extend(data)

    def _chunker_loop(self):
        """Slice buffer into overlapping segments"""
        while True:
            with self.buffer_lock:
                if len(self.buffer) >= self.segment_bytes:
                    seg = bytes(self.buffer[:self.segment_bytes])
                    # keep overlap
                    self.buffer = self.buffer[self.segment_bytes - self.overlap_bytes:]
                    self.segment_queue.put(seg)
            time.sleep(0.1)

    def _transcription_loop(self):
        """Write WAV and call OpenAI transcription"""
        while True:
            segment = self.segment_queue.get()
            
            arr = np.frombuffer(segment, dtype=np.int16)
            peak = np.max(np.abs(arr))
            if peak < SILENCE_THRESHOLD:
                # skip this chunk entirely
                print("Silent...")
                continue

            print("Audio activity detected...")
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            try:
                # write PCM to WAV
                with wave.open(tmp.name, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(self.sample_width)
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(segment)
                # transcribe
                with open(tmp.name, 'rb') as audio_file:
                    resp = openai.audio.transcriptions.create(
                        model=MODEL_NAME,
                        file=audio_file,
                        response_format='text'
                    )
                # resp is a raw string when response_format='text'
                text = resp.strip() if isinstance(resp, str) else resp.get('text', '')
            except Exception as e:
                text = f"<error: {e}>"
            finally:
                tmp.close()
                try: os.unlink(tmp.name)
                except OSError: pass

            result = {
                "segment_id": uuid.uuid4().hex,
                "timestamp": datetime.utcnow().isoformat(),
                "text": text
            }
            with self.latest_lock:
                self._latest = result

    def _serve(self):
        """Accept JSON-RPC"""
        while True:
            conn, _ = self.server.accept()
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn):
        """Serve methods"""
        data = conn.recv(4096).decode('utf-8')
        try:
            req = json.loads(data)
            mid = req.get('method')
            rid = req.get('id')
            if mid in ('transcribe','get_latest'):
                with self.latest_lock:
                    res = self._latest
                resp = {'jsonrpc':'2.0','result':res,'id':rid}
            else:
                resp = {'jsonrpc':'2.0','error':{'code':-32601,'message':'Method not found'},'id':rid}
        except Exception as e:
            resp = {'jsonrpc':'2.0','error':{'code':-32000,'message':str(e)},'id':None}
        conn.send(json.dumps(resp).encode())
        conn.close()

    def stop(self):
        """Cleanup"""
        self.audio_client.stop_streaming()
        try:
            self.server.close()
            os.unlink(SOCKET_PATH)
        except: pass

if __name__ == '__main__':
    svc = SpeechTranscriptionMiddleware()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        svc.stop()
