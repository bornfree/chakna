#!/usr/bin/env python3
import redis
import json

r = redis.Redis.from_url("redis://localhost:6379/0")
last_id = "0-0"

print("Waiting for new transcripts…")
while True:
    resp = r.xread({"audio:transcriptions": last_id}, block=0, count=1)
    if not resp:
        continue
    _, entries = resp[0]
    for entry_id, fields in entries:
        last_id = entry_id
        result = { k.decode(): v.decode() for k,v in fields.items() }
        print(f"[{entry_id.decode()} @ {result['timestamp']}] {result['text']}")
