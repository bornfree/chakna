import socket, json, cv2, numpy as np, base64
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

            # === begin change ===
            # read until server closes
            buf = bytearray()
            while True:
                chunk = sock.recv(64 * 1024)
                if not chunk:
                    break
                buf.extend(chunk)
            data = buf.decode('utf-8')
            resp = json.loads(data)
            # === end change ===

        if 'error' in resp:
            raise RuntimeError(resp['error']['message'])
        return resp['result']


    def read(self):
        """
        Returns (frame_id:str, image:np.ndarray)
        """
        info = self._rpc_call('read')
        fid, b64 = info['frame_id'], info['jpeg_b64']
        jpg  = base64.b64decode(b64)
        arr  = np.frombuffer(jpg, dtype=np.uint8)
        img  = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return fid, img
