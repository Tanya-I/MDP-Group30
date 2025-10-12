#Hosted on PC with Image rec model , used for checklist task A5
#Gets the image using API from RPI , and sends y or n back depending on if its a bullseye or not
import requests
import time
import subprocess
from datetime import datetime
import json

# ---- CONFIG ----
PI_URL = "http://192.168.30.30:5000"   # Pi API
SERVER_URL = "http://127.0.0.1:8000/infer"  # Local inference server (uvicorn)

# Step 1: Fetch latest photo from Pi
resp = requests.get(f"{PI_URL}/get_photo")
if resp.status_code == 200:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_image = f"fetched_{timestamp}.jpg"

    with open(input_image, "wb") as f:
        f.write(resp.content)
    print(f"[PC] Downloaded photo as {input_image}")
else:
    print("[PC] No photo available yet")
    exit(1)

# Step 2: Run inference on local server
try:
    with open(input_image, "rb") as f:
        files = {"file": (input_image, f, "image/jpeg")}
        r = requests.post(SERVER_URL, files=files, timeout=30)
    r.raise_for_status()
    result = r.json()
    print(f"[PC] Raw inference result: {json.dumps(result, indent=2)}")
except Exception as e:
    print(f"[ERROR] Inference failed: {e}")
    result = {"detections": []}

# Step 3: Decide y or n
detections = result.get("detections", [])
cmd = "n"  # default = invalid

if detections:
    # Pick the first detection
    label = detections[0].get("label", "").lower()
    if label == "bullseye" or label == "null":
        cmd = "n"
    else:
        cmd = "y"

print(f"[PC] Final decision → {cmd.upper()} (based on label)")

# Step 4: Send command back to Pi → STM
resp = requests.post(f"{PI_URL}/send_command", data=cmd)
if resp.status_code == 200:
    print(f"[PC] Sent '{cmd}' successfully")
else:
    print(f"[PC] Failed to send '{cmd}' → {resp.status_code}, {resp.text}")

time.sleep(1)