# record_mp3.py

import time
import wave
import tempfile
import subprocess
import os

from sensors.audio.client import AudioClient
from sensors.audio.config import SAMPLE_RATE, CHANNELS

# how long to record (seconds) and where to write
DURATION_SECONDS = 10
OUTPUT_MP3 = "output.mp3"

def record_raw(duration: float) -> bytes:
    """
    Pull raw PCM chunks from the Redis stream for `duration` seconds.
    """
    client = AudioClient()
    end_ts = time.time() + duration
    buf = bytearray()

    for chunk in client.stream_chunks():
        buf.extend(chunk["pcm_bytes"])
        if time.time() >= end_ts:
            break

    return bytes(buf)

def write_wav(raw_pcm: bytes, path: str):
    """
    Write raw PCM bytes to a WAV file.
    Assumes 16-bit little-endian samples.
    """
    sample_width = 2  # bytes (int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(sample_width)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(raw_pcm)

def convert_wav_to_mp3(wav_path: str, mp3_path: str):
    """
    Convert WAV → MP3 using ffmpeg.
    Make sure ffmpeg is installed on your system.
    """
    subprocess.run(
        ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", mp3_path],
        check=True
    )

def main():
    print(f"▶ Recording {DURATION_SECONDS}s of audio…")
    raw = record_raw(DURATION_SECONDS)

    # write to temp WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    write_wav(raw, wav_path)
    print(f"✔ WAV written to {wav_path}")

    # convert to mp3
    convert_wav_to_mp3(wav_path, OUTPUT_MP3)
    print(f"✔ MP3 written to {OUTPUT_MP3}")

    # cleanup
    os.remove(wav_path)

if __name__ == "__main__":
    main()
