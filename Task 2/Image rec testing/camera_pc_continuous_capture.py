#!/usr/bin/env python3
"""
pc_image_recognition_client_pull_fixedip_offline.py
---------------------------------------------------
Offline YOLO client that pulls frames from a fixed Raspberry Pi IP address,
runs YOLO model (v1.pt) fully offline, and sends /direction ("L"/"R")
back when IDs 38 (Right) or 39 (Left) are detected.
"""

import base64
import time
import requests
import numpy as np
import cv2
from pathlib import Path
import os
from ultralytics import YOLO

# ──────────────────────────────────────────────────────────────
# FORCE OFFLINE MODE (no internet access required)
# ──────────────────────────────────────────────────────────────
os.environ["YOLO_OFFLINE"] = "True"
import ultralytics.utils
ultralytics.utils.is_online = lambda: False

# ──────────────────────────────────────────────────────────────
# FIXED CONFIGURATION
# ──────────────────────────────────────────────────────────────
RPI_IP = "192.168.30.1"           # ✅ Your fixed Raspberry Pi IP here
RPI_URL = f"http://{RPI_IP}:5000"
MODEL_PATH = "v1.pt"              # YOLO model weights
CONF_THRESHOLD = 0.6              # detection confidence
FRAME_INTERVAL = 1.0              # seconds between pulls
SAVE_DIR = Path("received_frames")
SAVE_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────────────────────
# LOAD YOLO MODEL IN MEMORY (OFFLINE)
# ──────────────────────────────────────────────────────────────
print(f"[INFO] Loading YOLO model '{MODEL_PATH}' in OFFLINE mode...")
model = YOLO(MODEL_PATH)
print("[INFO] Model loaded successfully.")

stop_flag = False


def send_direction(direction: str):
    """Send L/R command to Raspberry Pi"""
    print(f"[INFO] Sending direction '{direction}' to RPi...")
    try:
        resp = requests.post(f"{RPI_URL}/direction", json={"dir": direction}, timeout=5)
        print(f"[✓] RPi acknowledged: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Failed to send direction: {e}")


# ──────────────────────────────────────────────────────────────
# MAIN LOOP — PULL FRAMES AND RUN DETECTION
# ──────────────────────────────────────────────────────────────
print(f"[INFO] Pulling frames from {RPI_URL}/preview ...")

while not stop_flag:
    try:
        resp = requests.get(f"{RPI_URL}/preview", timeout=10)
        if resp.status_code != 200:
            print(f"[WARN] Capture failed (HTTP {resp.status_code})")
            time.sleep(FRAME_INTERVAL)
            continue

        data = resp.json()
        if data.get("status") != "ok":
            print(f"[WARN] Invalid response: {data}")
            time.sleep(FRAME_INTERVAL)
            continue

        # Decode image
        img_b64 = data["image"]
        img_bytes = base64.b64decode(img_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        ts = time.strftime("%Y%m%d_%H%M%S")
        img_path = SAVE_DIR / f"frame_{ts}.jpg"
        cv2.imwrite(str(img_path), frame)
        print(f"[INFO] Saved frame → {img_path}")

        # Run YOLO detection
        results = model.predict(source=frame, conf=CONF_THRESHOLD, verbose=False)
        detected_ids = []
        for r in results:
            if hasattr(r, "boxes") and r.boxes is not None:
                for c in r.boxes.cls:
                    detected_ids.append(int(c.item()))

        # Interpret detections
        if detected_ids:
            print(f"[INFO] Detected IDs: {detected_ids}")
            if 38 in detected_ids:  # Right
                send_direction("R")
                stop_flag = True
            elif 39 in detected_ids:  # Left
                send_direction("L")
                stop_flag = True
        else:
            print("[INFO] No detections above confidence threshold.")

    except requests.exceptions.ConnectionError:
        print("[WARN] Could not reach RPi. Retrying in 3s...")
        time.sleep(3)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")

    time.sleep(FRAME_INTERVAL)

print("[INFO] Stop flag triggered. Session ended.")
