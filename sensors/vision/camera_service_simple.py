import cv2, os, time, threading, json, shutil, uuid
from datetime import datetime
from pathlib import Path
from sensors.vision.config import *

class CameraService:
    def __init__(self):
        # prepare dirs
        for d in (TRANSIENT_DIR, PERSISTENT_DIR):
            os.makedirs(d, exist_ok=True)

        # open camera
        self.cap = cv2.VideoCapture(0)
        w, h = RESOLUTION
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)

        # start capture loop
        self._stop = threading.Event()
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def _rotate_transient(self):
        files = sorted(Path(TRANSIENT_DIR).glob("*.jpg"))
        if len(files) > MAX_TRANSIENT_FILES:
            for old in files[:-MAX_TRANSIENT_FILES]:
                old.unlink()

    def _capture_loop(self):
        while not self._stop.is_set():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            frame_id = str(uuid.uuid4())
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            fname = f"{frame_id}_{ts}.jpg"
            fpath = os.path.join(TRANSIENT_DIR, fname)
            cv2.imwrite(fpath, frame)

            # update symlink ‘latest.jpg’
            try:
                if os.path.islink(LATEST_SYMLINK):
                    os.unlink(LATEST_SYMLINK)
                os.symlink(fpath, LATEST_SYMLINK)
            except OSError:
                pass

            self._rotate_transient()
            time.sleep(INTERVAL_SEC)

    def read(self):
        """
        Return (frame_id:str, frame_matrix)
        """
        link = Path(LATEST_SYMLINK).resolve()
        # filename is "<uuid>_<timestamp>.jpg"
        frame_id = link.stem.split('_', 1)[0]
        img = cv2.imread(str(link))
        return frame_id, img

    def mark_persistent(self, frame_id: str, meta: dict):
        """
        Moves specified frame to persistent store and writes meta JSON.
        """
        pattern = f"{frame_id}_*.jpg"
        matches = list(Path(TRANSIENT_DIR).glob(pattern))
        if not matches:
            raise FileNotFoundError(f"No frame {frame_id} in transient")
        src = matches[0]
        dst = Path(PERSISTENT_DIR) / src.name
        shutil.move(str(src), str(dst))

        # write metadata sidecar
        meta_path = Path(PERSISTENT_DIR) / f"meta_{frame_id}.json"
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

    def stop(self):
        self._stop.set()
        self.cap.release()

if __name__ == "__main__":
    svc = CameraService()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        svc.stop()
