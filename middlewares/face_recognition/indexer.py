import redis
from redis.commands.search.field import VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType

REDIS_HOST = "localhost"
REDIS_PORT = 6379
INDEX_NAME = "faces"
KEY_PREFIX = "face:"

def create_face_index(dimensions: int = 128):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    try:
        r.ft(INDEX_NAME).info()
        print("Index already exists.")
    except:
        schema = VectorField(
            "embedding", "HNSW", {
                "TYPE": "FLOAT32",
                "DIM": dimensions,
                "DISTANCE_METRIC": "COSINE",
                "M": 40,
                "EF_CONSTRUCTION": 200
            }
        )
        definition = IndexDefinition(prefix=[KEY_PREFIX], index_type=IndexType.HASH)
        r.ft(INDEX_NAME).create_index(fields=[schema], definition=definition)
        print("Created face vector index.")
