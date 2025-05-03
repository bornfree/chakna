import redis
import threading
import subprocess
import json
import signal
import sys
import alsaaudio

class SpeakerService:
    def __init__(self, redis_url="redis://localhost"):
        self.r = redis.from_url(redis_url)
        # Load or initialize audio configuration
        cfg = self.r.hgetall("audio:config")
        self.rate = int(cfg.get(b"rate", b"48000"))
        self.channels = int(cfg.get(b"channels", b"1"))
        self.chunk_size = int(cfg.get(b"chunk_size", b"1024"))

        self.stream_key = "audio:stream"
        self.cmd_channel = "audio:cmd"

        # ALSA setup
        self.playback = alsaaudio.PCM(type=alsaaudio.PCM_PLAYBACK)
        self.playback.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self.playback.setchannels(self.channels)
        self.playback.setrate(self.rate)
        self.playback.setperiodsize(self.chunk_size)

        self.stop_event = threading.Event()
        self.decode_proc = None

    def start(self):
        # Start command listener
        threading.Thread(target=self._cmd_loop, daemon=True).start()
        # Start playback loop (blocks)
        self._play_loop()

    def _cmd_loop(self):
        pubsub = self.r.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(self.cmd_channel)
        for msg in pubsub.listen():
            try:
                data = json.loads(msg['data'])
            except Exception:
                continue
            action = data.get('action')
            if action == 'play_file':
                path = data.get('path')
                self._start_decode(path)
            elif action == 'stop':
                self._stop_decode()

    def _start_decode(self, path):
        # Stop any existing decode
        self._stop_decode()
        # Spawn ffmpeg to decode file to raw PCM
        cmd = [
            'ffmpeg', '-hide_banner', '-loglevel', 'error',
            '-i', path,
            '-f', 's16le', '-ar', str(self.rate), '-ac', str(self.channels),
            'pipe:1'
        ]
        self.decode_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        # Push PCM chunks into Redis stream
        threading.Thread(target=self._decode_loop, daemon=True).start()
        # Update state
        self.r.hset("audio:state", mapping={"current_file": path, "status": "playing"})

    def _decode_loop(self):
        # Read and push decoded PCM data
        bytes_per_frame = 2 * self.channels  # 16-bit = 2 bytes
        while True:
            data = self.decode_proc.stdout.read(self.chunk_size * bytes_per_frame)
            if not data:
                break
            self.r.xadd(self.stream_key, {"data": data})
        # Mark stopped
        self.decode_proc = None
        self.r.hset("audio:state", "status", "stopped")

    def _stop_decode(self):
        if self.decode_proc:
            self.decode_proc.terminate()
            self.decode_proc.wait()
            self.decode_proc = None
        self.r.hset("audio:state", "status", "stopped")

    def _play_loop(self):
        last_id = '0-0'
        while not self.stop_event.is_set():
            # Block until a new chunk arrives
            entries = self.r.xread({self.stream_key: last_id}, block=0, count=1)
            if not entries:
                continue
            for _, msgs in entries:
                for msg_id, msg in msgs:
                    pcm = msg[b'data']
                    self.playback.write(pcm)
                    last_id = msg_id

    def stop(self):
        self.stop_event.set()
        self._stop_decode()

if __name__ == '__main__':
    svc = SpeakerService()
    def _shutdown(signum, frame):
        svc.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    svc.start()