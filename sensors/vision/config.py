# sensors/vision/config.py

# capture settings
INTERVAL_SEC   = 1.0             # capture every second
RESOLUTION     = (640, 480)      # (width, height)

# Unix socket for control/API
SOCKET_PATH = '/tmp/vision.sock'