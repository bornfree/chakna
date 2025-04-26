#!/usr/bin/env python3
"""
Simple application that uses the audio service to record 20 seconds of audio
and save it to a WAV file.
"""

import time
import wave
import os
import numpy as np
import threading
from sensors.audio.client import AudioClient

def main():
    # Create output directory if it doesn't exist
    os.makedirs("recordings", exist_ok=True)
    
    # Initialize the audio client
    client = AudioClient()
    
    # Get audio configuration
    config = client.config
    sample_rate = config['sample_rate']
    channels = config['channels']
    
    # Prepare WAV file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"recordings/audio_recording_{timestamp}.wav"
    
    # Create a buffer to store all audio data
    audio_buffer = []
    buffer_lock = threading.Lock()
    
    # Define callback to collect audio chunks
    def collect_audio(chunk, config):
        with buffer_lock:
            audio_buffer.append(chunk)
    
    print(f"Starting audio recording for 20 seconds...")
    print(f"Recording at {sample_rate}Hz, {channels} channel(s)")
    
    # Start streaming with our callback
    client.start_streaming(callback=collect_audio)
    
    # Record for 20 seconds
    try:
        for i in range(20):
            time.sleep(1)
            print(f"Recording: {i+1}/20 seconds", end="\r")
    except KeyboardInterrupt:
        print("\nRecording interrupted!")
    finally:
        # Stop streaming
        client.stop_streaming()
        print("\nStopped recording. Processing audio...")
        
        # Combine all chunks and save to WAV file
        with buffer_lock:
            if not audio_buffer:
                print("No audio data captured!")
                return
                
            # Combine all chunks
            audio_data = np.concatenate(audio_buffer)
            
            # Save as WAV file
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(channels)
                if config['format'] == 'int16':
                    wf.setsampwidth(2)  # 16-bit
                elif config['format'] == 'int32':
                    wf.setsampwidth(4)  # 32-bit
                else:
                    wf.setsampwidth(2)  # Default to 16-bit
                    
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            print(f"Audio saved to: {filename}")
            print(f"Recorded {len(audio_data)/sample_rate:.2f} seconds of audio")

if __name__ == "__main__":
    main()