# sensors/audio/config.py
# DEPRECATED: Use config_loader.py instead

from config_loader import get_config

config = get_config()

# Backward compatibility - keeping old variable names
REDIS_URL = config.get('redis.url', 'redis://localhost:6379/0')
STREAM_NAME = config.get('audio.redis.pcm_stream', 'audio:pcm:stream')
SAMPLE_RATE = config.get('audio.capture.sample_rate', 48000)
CHANNELS = config.get('audio.capture.channels', 1)
CHUNK_SIZE = config.get('audio.capture.chunk_size', 1024)
