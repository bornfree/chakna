import face_recognition
import numpy as np
import redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
KEY_PREFIX = "face:"

def add_known_face(person_id: str, image_path: str):
    img = face_recognition.load_image_file(image_path)
    encs = face_recognition.face_encodings(img)
    if not encs:
        raise ValueError("No face found")
    vec = np.array(encs[0], dtype=np.float32).tobytes()
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    r.hset(f"{KEY_PREFIX}{person_id}", mapping={
        "embedding": vec,
        "person_id": person_id
    })
    print(f"Added {person_id}")
