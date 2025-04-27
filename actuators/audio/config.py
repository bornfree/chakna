import os

# Audio playback settings
SAMPLE_RATE = 44100         # must match capture rate
CHANNELS    = 2             # stereo
FORMAT      = 'int16'       # 16-bit signed
CHUNK_SIZE  = 1024          # frames per buffer

# IPC & streaming
SOCKET_PATH = '/tmp/speaker.sock'
STREAM_PORT = 5001          # distinct from audio capture port

OUTPUT_DEVICE_INDEX=6