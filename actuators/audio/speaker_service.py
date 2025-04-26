import pyaudio
import socket
import threading
import json
import os
import logging
from actuators.audio.config import *  # reuse constants if you prefer

logger = logging.getLogger('SpeakerService')
logging.basicConfig(level=logging.INFO)

class SpeakerService:
    def __init__(self):
        # init PyAudio output stream
        self.p = pyaudio.PyAudio()
        pa_format = {
            'int16': pyaudio.paInt16,
            'int32': pyaudio.paInt32,
            'float32': pyaudio.paFloat32
        }.get(FORMAT, pyaudio.paInt16)

        self.stream = self.p.open(
            format=pa_format,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )
        self._stop = threading.Event()

        # start RPC & streaming threads
        threading.Thread(target=self._start_rpc, daemon=True).start()
        threading.Thread(target=self._start_stream_server, daemon=True).start()

        logger.info("Speaker service started (playback)")

    def _start_rpc(self):
        try: os.unlink(SOCKET_PATH)
        except OSError: pass

        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o660)
        srv.listen()

        while not self._stop.is_set():
            conn, _ = srv.accept()
            threading.Thread(target=self._handle_rpc, args=(conn,), daemon=True).start()

    def _handle_rpc(self, conn):
        data = conn.recv(4096).decode('utf-8')
        try:
            req = json.loads(data)
            method = req.get('method')
            rid    = req.get('id')
            if method == 'get_config':
                result = {
                    'sample_rate': SAMPLE_RATE,
                    'channels':    CHANNELS,
                    'format':      FORMAT,
                    'chunk_size':  CHUNK_SIZE,
                    'stream_port': STREAM_PORT
                }
                resp = {'jsonrpc':'2.0','result':result,'id':rid}
            else:
                resp = {
                  'jsonrpc':'2.0',
                  'error': {'code': -32601, 'message': 'Method not found'},
                  'id': rid
                }
        except Exception as e:
            resp = {'jsonrpc':'2.0','error':{'code':-32000,'message':str(e)},'id':None}

        conn.send(json.dumps(resp).encode('utf-8'))
        conn.close()

    def _start_stream_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', STREAM_PORT))
        server.listen(5)
        logger.info(f"Speaker streaming server on port {STREAM_PORT}")

        while not self._stop.is_set():
            client, _ = server.accept()
            threading.Thread(
                target=self._handle_stream_client,
                args=(client,),
                daemon=True
            ).start()

        server.close()

    def _handle_stream_client(self, client):
        """Read raw chunks and play them immediately."""
        try:
            while True:
                data = client.recv(CHUNK_SIZE * 2)  # *2 for int16
                if not data:
                    break
                self.stream.write(data)
        finally:
            client.close()

    def stop(self):
        self._stop.set()
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        try: os.unlink(SOCKET_PATH)
        except: pass
        logger.info("Speaker service stopped")


if __name__ == '__main__':
    svc = SpeakerService()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        svc.stop()
