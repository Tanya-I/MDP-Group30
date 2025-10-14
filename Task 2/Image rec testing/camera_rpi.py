#!/usr/bin/env python3
# rpi_camera_server_keypress_headless.py
#takes single photos on keypress, and serves /preview and /capture API for PC to pull frames

import cv2, time, base64, threading
from flask import Flask, Response, jsonify
from pathlib import Path

app = Flask(__name__)
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("[ERROR] Cannot open camera. Enable via raspi-config > Interface Options > Camera.")
print("[INFO] Camera initialized successfully.")
print("[INFO] Visit http://<RPI_IP>:5000/preview to view live feed")

SAVE_DIR = Path("captured_photos")
SAVE_DIR.mkdir(exist_ok=True)

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

@app.route("/status")
def status():
    return jsonify({"status": "online", "camera_ok": cap.isOpened()})

@app.route("/preview")
def preview():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/capture", methods=["POST"])
def capture_api():
    success, frame = cap.read()
    if not success:
        return jsonify({"status": "error", "message": "Camera read failed"}), 500
    ret, buffer = cv2.imencode(".jpg", frame)
    if not ret:
        return jsonify({"status": "error", "message": "JPEG encode failed"}), 500
    img_b64 = base64.b64encode(buffer).decode("utf-8")
    print("[INFO] /capture API request served.")
    return jsonify({"status": "ok", "image": img_b64})

def keypress_loop():
    print("[INFO] Headless mode — press 'a' then Enter to capture, 'q' then Enter to quit.")
    while True:
        user_input = input("Command (a/q): ").strip().lower()
        if user_input == "a":
            success, frame = cap.read()
            if success:
                ts = time.strftime("%Y%m%d_%H%M%S")
                filename = SAVE_DIR / f"photo_{ts}.jpg"
                cv2.imwrite(str(filename), frame)
                print(f"[INFO] Saved {filename}")
            else:
                print("[WARN] Capture failed.")
        elif user_input == "q":
            print("[INFO] Exiting...")
            break

    cap.release()
    print("[INFO] Camera released.")

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False), daemon=True).start()
    keypress_loop()

