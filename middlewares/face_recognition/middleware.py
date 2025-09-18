import os, time, json, logging
import face_recognition
import numpy as np
import redis

from sensors.vision.client import VisionClient
from .search import find_similar_faces
from config_loader import get_config

config = get_config()

REDIS_HOST = config.get('redis.host', 'localhost')
REDIS_PORT = config.get('redis.port', 6379)
VISION_CHAN = config.get('vision.redis.frames_channel', 'sensors:vision:frames')

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    vision = VisionClient(host=REDIS_HOST, port=REDIS_PORT, channel=VISION_CHAN)
    logging.info("Face middleware started…")

    while True:
        try:
            fid, img = vision.read(timeout=1.0)
            rgb = img[:, :, ::-1]
            encs = face_recognition.face_encodings(rgb)
            if not encs:
                continue
            matches = find_similar_faces(np.array(encs[0]))
            output = {"frame_id": fid, "timestamp": time.time(), "matches": matches}
            print(json.dumps(output), flush=True)
        except TimeoutError:
            continue
        except Exception:
            logging.exception("Error, retrying in 1s")
            time.sleep(1)

if __name__ == "__main__":
    main()
