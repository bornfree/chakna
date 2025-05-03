# sensors/audio/config.py

import os

# Redis
REDIS_URL    = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_NAME  = os.getenv("AUDIO_STREAM", "audio:pcm:stream")

# Audio capture
SAMPLE_RATE  = int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))   # Hz
CHANNELS     = int(os.getenv("AUDIO_CHANNELS", "1"))
CHUNK_SIZE   = int(os.getenv("AUDIO_CHUNK_SIZE", "1024"))    # frames per buffer
