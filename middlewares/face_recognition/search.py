import redis
from redis.commands.search.query import Query
import numpy as np

REDIS_HOST = "localhost"
REDIS_PORT = 6379
INDEX_NAME = "faces"
TOP_K = 5
MATCH_THRESHOLD = 0.6

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
