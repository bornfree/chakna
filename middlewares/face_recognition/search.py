import redis
from redis.commands.search.query import Query
import numpy as np
from config_loader import get_config

config = get_config()

REDIS_HOST = config.get('redis.host', 'localhost')
REDIS_PORT = config.get('redis.port', 6379)
INDEX_NAME = config.get('face_recognition.redis.index_name', 'faces')
TOP_K = config.get('face_recognition.search.top_k', 5)
MATCH_THRESHOLD = config.get('face_recognition.search.match_threshold', 0.6)

def find_similar_faces(embedding: np.ndarray):
    vec = embedding.astype(np.float32).tobytes()
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    q = (
        Query(f"*=>[KNN {TOP_K} @embedding $vec AS score]")
        .sort_by("score")
        .return_fields("person_id", "score")
        .paging(0, TOP_K)
        .dialect(2)
    )
    res = r.ft(INDEX_NAME).search(q, {"vec": vec})
    return [
        {"person_id": doc.person_id, "score": float(doc.score)}
        for doc in res.docs
        if float(doc.score) <= MATCH_THRESHOLD
    ]
