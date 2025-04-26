import os

# capture settings
INTERVAL_SEC   = 1.0             # capture every second
RESOLUTION     = (640, 480)     # (width, height)

# filesystem paths
BASE_DIR       = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'memory/vision'))
TRANSIENT_DIR  = os.path.join(BASE_DIR, 'transient')
PERSISTENT_DIR = os.path.join(BASE_DIR, 'persistent')
LATEST_SYMLINK = os.path.join(TRANSIENT_DIR, 'latest.jpg')

# rotation
MAX_TRANSIENT_FILES = 60

# Unix socket for control/API
SOCKET_PATH = '/tmp/vision.sock'
