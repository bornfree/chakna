"""
Simple application that plays a user-specified WAV file via the speaker actuator.
"""

import sys
import time
import wave

from actuators.audio.client import SpeakerClient

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path/to/file.wav")
        sys.exit(1)

    wav_path = sys.argv[1]
    try:
        wf = wave.open(wav_path, 'rb')
    except FileNotFoundError:
        print(f"File not found: {wav_path}")
        sys.exit(1)

    # Initialize speaker client (will fetch config and open stream)
    client = SpeakerClient()
    cfg = client.config
    chunk_size = cfg['chunk_size']
    sample_rate = cfg['sample_rate']

    print(f"Playing {wav_path} @ {sample_rate} Hz, chunks of {chunk_size} frames…")

    # Read and send frames
    try:
        while True:
            data = wf.readframes(chunk_size)
            if not data:
                break
            client.play(data)
            # pace the stream to real-time
            time.sleep(chunk_size / sample_rate)
    finally:
        client.close()
        wf.close()
        print("Playback finished.")

if __name__ == '__main__':
    main()
