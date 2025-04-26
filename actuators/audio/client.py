import socket
import json
from actuators.audio.config import SOCKET_PATH, STREAM_PORT

class SpeakerClient:
    def __init__(self, socket_path=SOCKET_PATH):
        self.socket_path = socket_path
        self.config = self._rpc_call('get_config')
        self.stream_socket = None

    def _rpc_call(self, method, params=None):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(self.socket_path)
            req = {'jsonrpc':'2.0','method':method,'params':params or {},'id':1}
            sock.send(json.dumps(req).encode('utf-8'))
            resp = json.loads(sock.recv(8192).decode('utf-8'))
        if 'error' in resp:
            raise RuntimeError(resp['error']['message'])
        return resp['result']

    def _ensure_stream(self):
        if self.stream_socket:
            return
        self.stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream_socket.connect(('localhost', STREAM_PORT))

    def play(self, chunk: bytes):
        """Send a raw audio chunk to the speaker service."""
        self._ensure_stream()
        self.stream_socket.sendall(chunk)

    def close(self):
        if self.stream_socket:
            self.stream_socket.close()
            self.stream_socket = None
