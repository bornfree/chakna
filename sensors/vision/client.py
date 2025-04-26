import socket
import json
import cv2
from sensors.vision.config import SOCKET_PATH

class VisionClient:
    def __init__(self, socket_path=SOCKET_PATH):
        self.socket_path = socket_path

    def _rpc_call(self, method, params=None):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(self.socket_path)
            req = {
                'jsonrpc': '2.0',
                'method':  method,
                'params':  params or {},
                'id':      1
            }
            sock.send(json.dumps(req).encode('utf-8'))
            resp = json.loads(sock.recv(8192).decode('utf-8'))
        if 'error' in resp:
            raise RuntimeError(resp['error']['message'])
        return resp['result']

    def read(self):
        """
        Returns (frame_id:str, image:np.ndarray)
        """
        info = self._rpc_call('read')
        frame_id, path = info['frame_id'], info['path']
        img = cv2.imread(path)
        return frame_id, img

    def mark_persistent(self, frame_id, meta=None):
        """
        Marks the given frame UUID as persistent, attaching optional meta dict.
        """
        self._rpc_call('mark_persistent', {
            'frame_id': frame_id,
            'meta':      meta or {}
        })
