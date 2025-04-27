import os

# Audio playback settings
SAMPLE_RATE = 48000         # must match capture rate
CHANNELS    = 1             # mono
FORMAT      = 'int16'       # 16-bit signed
CHUNK_SIZE  = 1024          # frames per buffer

# IPC & streaming
SOCKET_PATH = '/tmp/speaker.sock'
STREAM_PORT = 5001          # distinct from audio capture port

OUTPUT_DEVICE_INDEX=0