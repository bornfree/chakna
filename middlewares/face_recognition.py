"""
Face Recognition Middleware using Supabase (with pgvector) and dotenv for configuration.

This version continuously processes every frame from VisionClient and auto-publishes detections.
Clients can subscribe on Unix socket with:
 - RPC method: `get_latest` to fetch the most recent detection results.
 - RPC method: `process` remains available for on-demand processing.
 
 """

import os
import socket
import threading
import json
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
import numpy as np

load_dotenv()

import face_recognition
from supabase import create_client, Client
from sensors.vision.client import VisionClient
from sensors.vision.config import INTERVAL_SEC

# configure logging
default_format = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(format=default_format, level=logging.INFO)
logger = logging.getLogger('FaceMiddleware')

DEFAULT_SOCKET = os.getenv('SOCKET_PATH', '/tmp/face_middleware.sock')
MATCH_THRESHOLD = float(os.getenv('MATCH_THRESHOLD', 0.6))

class FaceRecognitionMiddleware:
    def __init__(
        self,
        supabase_url: str = None,
        supabase_key: str = None,
        socket_path: str = None,
        match_threshold: float = None
    ):
        # Initialize Supabase
        url = supabase_url or os.getenv('SUPABASE_URL')
        key = supabase_key or os.getenv('SUPABASE_KEY')
        self.match_threshold = match_threshold or MATCH_THRESHOLD

        self.supabase: Client = create_client(url, key)
        logger.info('Supabase client initialized')

        # Vision client for reading frames
        self.vision = VisionClient()
        logger.info('VisionClient connected')

        # Setup RPC socket
        self.socket_path = socket_path or DEFAULT_SOCKET
        try:
            os.unlink(self.socket_path)
        except OSError:
            pass
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.socket_path)
        os.chmod(self.socket_path, 0o660)
        self.server.listen()

        # Lock and storage for latest result
        self._lock = threading.Lock()
        self._latest = None

        # Start RPC server
        threading.Thread(target=self._serve, daemon=True).start()
        logger.info(f'RPC server listening on {self.socket_path}')

        # Start continuous detection loop
        threading.Thread(target=self._detection_loop, daemon=True).start()
        logger.info('Continuous detection loop started')

    def _serve(self):
        while True:
            conn, _ = self.server.accept()
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        data = conn.recv(4096).decode('utf-8')
        try:
            req = json.loads(data)
            method = req.get('method')
            rid = req.get('id')

            if method == 'process':
                result = self.process_frame()
                resp = {'jsonrpc':'2.0','result':result,'id':rid}

            elif method == 'get_latest':
                with self._lock:
                    resp = {'jsonrpc':'2.0','result':self._latest,'id':rid}

            else:
                resp = {'jsonrpc':'2.0','error':{'code':-32601,'message':'Method not found'},'id':rid}

        except Exception as e:
            logger.exception('Error handling request')
            resp = {'jsonrpc':'2.0','error':{'code':-32000,'message':str(e)},'id':None}

        try:
            conn.send(json.dumps(resp).encode('utf-8'))
        except BrokenPipeError:
            logger.warning('Client disconnected before send')
        finally:
            conn.close()

    def _detection_loop(self):
        while True:
            try:
                result = self.process_frame()
                with self._lock:
                    self._latest = result
            except Exception:
                logger.exception('Error in detection loop')
            time.sleep(INTERVAL_SEC)

    def process_frame(self) -> dict:
        frame_id, frame = self.vision.read()
        rgb = np.ascontiguousarray(frame[:, :, ::-1])
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)
        logger.info(f'Detected {len(locations)} faces in frame {frame_id}')

        profiles = []
        now = datetime.utcnow().isoformat()
        for bbox, enc in zip(locations, encodings):
            rpc_res = self.supabase.rpc(
                'match_face',
                {'emb': enc.tolist(), 'thresh': self.match_threshold}
            ).execute()

            match = rpc_res.data[0] if rpc_res.data else None

            if match:
                self.supabase.table('profiles') \
                    .update({'last_seen': now}) \
                    .eq('id', match['id']) \
                    .execute()
                profiles.append({
                    'profile_id': match['id'],
                    'name': match['name'],
                    'distance': match.get('distance'),
                    'bbox': bbox,
                    'last_seen': now
                })
            else:
                ins = {'name': 'unknown', 'embedding': enc.tolist(), 'first_seen': now, 'last_seen': now}
                insert_res = self.supabase.table('profiles').insert(ins).execute()
                new_id = insert_res.data[0]['id']
                profiles.append({
                    'profile_id': new_id,
                    'name': 'unknown',
                    'distance': None,
                    'bbox': bbox,
                    'last_seen': now
                })

        return {'frame_id': frame_id, 'timestamp': now, 'profiles': profiles}

if __name__ == '__main__':
    svc = FaceRecognitionMiddleware()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info('Shutting down FaceRecognitionMiddleware...')
