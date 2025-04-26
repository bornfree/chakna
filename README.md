
# Chakna

> Building a silly robot that passes around chakna around the house to guests.

> It may be useful. It may be not. But it will be fun.

### Raspberry Pi 4
Install Raspbian 64 bit lite version

### Install uv
```bash
$ uv add opencv-python requests
```

### Install libGL stuff
```bash
sudo apt install -y libgl1-mesa-glx
sudo apt install libglib2.0-0 libsm6 libxrender1 libxext6
```

### Install CMake
```bash
sudo apt install -y cmake build-essential libboost-all-dev
sudo apt install -y libopenblas-dev liblapack-dev
sudo apt install -y libx11-dev libgtk-3-dev  # For OpenCV support
```

### Install face recognition stuff
```bash
uv add face_recognition
```
