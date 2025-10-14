#!/usr/bin/env python3
# rpi_camera_server_pull.py
# RPi waits for PC to pull frames. No need to know PC IP.
#Conitnuously captures frames and serves /preview and /capture API for PC to pull frames

import cv2, time, base64, threading
from flask import Flask, Response, jsonify, request
from pathlib import Path

app = Flask(__name__)
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("[ERROR] Cannot open camera. Enable via raspi-config > Interface Options > Camera.")
print("[INFO] Camera initialized successfully.")
print("[INFO] Access via: http://192.168.30.1:5000/capture")

capture_running = True

# ----------------------------------------------------------------
# Live preview (optional)
# ----------------------------------------------------------------
def generate_frames():
    while True:
        success, frame = cap.read()
        if not success:
            continue
        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

@app.route("/preview")
def preview():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

# ----------------------------------------------------------------
# Capture single frame (PC pulls)
# ----------------------------------------------------------------
@app.route("/capture", methods=["GET"])
def capture():
    """PC pulls this to get a new frame."""
    success, frame = cap.read()
    if not success:
        return jsonify({"status": "error", "message": "Camera read failed"}), 500

    # Save locally for logging/debug
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = SAVE_DIR / f"photo_{ts}.jpg"
    cv2.imwrite(str(filename), frame)

    ret, buffer = cv2.imencode(".jpg", frame)
    if not ret:
        return jsonify({"status": "error", "message": "JPEG encode failed"}), 500
    img_b64 = base64.b64encode(buffer).decode("utf-8")

    print(f"[INFO] Frame captured at {ts}")
    return jsonify({"status": "ok", "image": img_b64})

# ----------------------------------------------------------------
# Receive L/R command from PC
# ----------------------------------------------------------------
@app.route("/direction", methods=["POST"])
def direction():
    global capture_running
    data = request.get_json(force=True)
    direction = data.get("dir", "").upper()

    if direction in ["L", "R"]:
        print(f"[INFO] Received stop command: {direction}")
        capture_running = False
        cap.release()
        print("[INFO] Camera released. Exiting server.")
        return jsonify({"status": "stopped", "direction": direction})
    else:
        print(f"[WARN] Invalid direction received: {direction}")
        return jsonify({"status": "ignored"}), 400

# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------
if __name__ == "__main__":
    print("[INFO] Waiting for PC requests...")
    app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False)
