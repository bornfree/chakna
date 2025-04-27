import cv2, os, time, threading, json, socket, base64, uuid
from sensors.vision.config import *
from datetime import datetime

class CameraService:
    def __init__(self):
        # open camera
        self.cap = cv2.VideoCapture(0)
        w, h = RESOLUTION
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

        # holders for the latest frame
        self._lock = threading.Lock()
        self._latest_id = None
        self._latest_jpeg = None

        # start capture + RPC threads
        self._stop = threading.Event()
        threading.Thread(target=self._capture_loop, daemon=True).start()
        threading.Thread(target=self._start_rpc, daemon=True).start()

    def _start_rpc(self):
        try: os.unlink(SOCKET_PATH)
        except OSError: pass

        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o660)
        srv.listen()
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn):
        try:
            data   = conn.recv(4096).decode('utf-8')
            req    = json.loads(data)
            method = req.get('method')
            rid    = req.get('id')
            if method == 'read':
                with self._lock:
                    result = {
                        'frame_id': self._latest_id,
                        'jpeg_b64': self._latest_jpeg
                    }
                resp = {'jsonrpc':'2.0','result':result,'id':rid}
            else:
                resp = {
                  'jsonrpc':'2.0',
                  'error':{'code':-32601,'message':'Method not found'},
                  'id':rid
                }
        except Exception as e:
            resp = {'jsonrpc':'2.0',
                    'error':{'code':-32000,'message':str(e)},
                    'id':None}
        conn.send(json.dumps(resp).encode('utf-8'))
        conn.close()

    def _capture_loop(self):
        while not self._stop.is_set():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # encode to JPEG in memory
            fid = str(uuid.uuid4())
            _, buf = cv2.imencode('.jpg', frame)
            b64 = base64.b64encode(buf).decode('ascii')

            with self._lock:
                self._latest_id   = fid
                self._latest_jpeg = b64

            time.sleep(INTERVAL_SEC)

    def stop(self):
        self._stop.set()
        self.cap.release()

if __name__ == "__main__":
    svc = CameraService()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        svc.stop()
