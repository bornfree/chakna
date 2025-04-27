import os

# Audio capture settings
SAMPLE_RATE = 48000         # 44kHz, good for speech recognition
CHUNK_SIZE = 1024           # Number of frames per buffer
CHANNELS = 1                # Mono audio
FORMAT = 'int16'            # 16-bit signed integer

# Socket settings
SOCKET_PATH = '/tmp/audio.sock'
STREAM_PORT = 5000          # For TCP streaming

# Buffer settings
MAX_BUFFER_SIZE = 10        # Max number of chunks to keep in buffer
INPUT_DEVICE_INDEX=1