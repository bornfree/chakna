#!/usr/bin/env python3
"""
Simple application that uses the vision service to read a frame.
Converts it to gray scale. If a frame is completely white, saves it as a persistent memory.
"""

import time
import cv2
import numpy as np

from sensors.vision.client import VisionClient
from sensors.vision.config import INTERVAL_SEC

def main():
    client = VisionClient()
    last_id = None

    try:
        while True:
            frame_id, frame = client.read()
            # skip if we’ve already processed this one
            if frame_id == last_id:
                time.sleep(0.01)
                continue
            last_id = frame_id

            # convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # detect full-white “white-out”
            if np.all(gray == 255):
                print(f"[!] white-out detected in {frame_id!r}, marking persistent")
                client.mark_persistent(frame_id, {'memory': 'white-out'})
            else:
                print("Writing regular frame")
                cv2.imwrite("Grayscale Feed.jpg", gray)

            time.sleep(INTERVAL_SEC)

    except KeyboardInterrupt:
        print("Interrupted, exiting…")
    finally:
        cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
