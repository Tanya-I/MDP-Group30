#!/usr/bin/env python3
# PC client that talks to Raspberry Pi server

import requests, base64
from pathlib import Path

RPI_IP = "192.168.30.1"      # <-- replace with your Pi's IP
BASE_URL = f"http://{RPI_IP}:5000"

def get_status():
    r = requests.get(f"{BASE_URL}/status", timeout=5)
    print("[STATUS]", r.json())

def capture_and_download():
    r = requests.post(f"{BASE_URL}/capture", timeout=10)
    data = r.json()
    if data.get("status") != "ok":
        print("[ERROR]", data)
        return
    img_data = base64.b64decode(data["image"])
    Path("downloaded_from_pi.jpg").write_bytes(img_data)
    print("[SUCCESS] Image saved as downloaded_from_pi.jpg")

if name == "__main__":
    get_status()
    capture_and_download()
    print(f"[INFO] You can also preview live video at  {BASE_URL}/preview")