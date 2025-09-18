#!/usr/bin/env python3
import redis
import json
from config_loader import get_config

config = get_config()

r = redis.Redis.from_url(config.get('redis.url', 'redis://localhost:6379/0'))
last_id = "0-0"
transcript_stream = config.get('audio.redis.transcript_stream', 'audio:transcriptions')

print("Waiting for new transcripts…")
while True:
    resp = r.xread({transcript_stream: last_id}, block=0, count=1)
    if not resp:
        continue
    _, entries = resp[0]
    for entry_id, fields in entries:
        last_id = entry_id
        result = { k.decode(): v.decode() for k,v in fields.items() }
        print(f"[{entry_id.decode()} @ {result['timestamp']}] {result['text']}")
