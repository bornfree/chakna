
# Chakna

> Building a silly robot that passes around chakna around the house to guests.

> It may be useful. It may be not. But it will be fun.

### Raspberry Pi 4
Install Raspbian 64 bit lite version

### Install uv
```bash
$ uv add opencv-python requests
```

### Install libraries
```bash
$ sudo apt install -y libgl1-mesa-glx
$ sudo apt install libglib2.0-0 libsm6 libxrender1 libxext6
$ sudo apt-get install portaudio19-dev
```

### Install CMake
```bash
$ sudo apt install -y cmake build-essential libboost-all-dev
$ sudo apt install -y libopenblas-dev liblapack-dev
$ sudo apt install -y libx11-dev libgtk-3-dev  # For OpenCV support
```

## Sensors


### VisionClient aka Eyes 👀

You can write applications that want to play with camera feed. The camera is assumed to be regular USB webcam.

Run the service
```bash
$ uv run -m sensors.vision.camera_service
```

Then the applications will be able to read the last frame the camera has seen. 

```python
from sensors.vision.client import VisionClient

# Initialize client
client = VisionClient()

# 1. Read the latest frame
frame_id, image = client.read()

# 2. Process the image and do something fun

# 3. If you want to “remember” this frame, mark it persistent
client.mark_persistent(frame_id, meta={'memory': 'Saw something amazing!'})
```

### AudioClient aka Ears 👂👂

Run the service
```bash
$ uv run -m sensors.audio.audio_service
```

Then write an application to listen to audio.
```python
from sensors.audio.client import AudioClient

def process_audio(chunk, config):
    # Process audio chunk in real-time
    pass

# Initialize client
client = AudioClient()

# Start streaming with callback
client.start_streaming(callback=process_audio)

# ... application logic ...

# When done
client.stop_streaming()
```

## Sample applications
See some sample applications in the [applications](./applications) directory.

## Development related stuff
To keep code synced between your machine and the Pi, place the following in file called `sync.sh`
```bash
rsync -avz --delete --exclude ".venv/" --exclude "__pycache__/" ./  pi@raspberrypi.local:/home/pi/chakna/
```

and then do
```bash
$ chmod +x sync.sh
$ ./sync.sh
```
