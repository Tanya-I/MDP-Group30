#Used for checklist task A5. Takes picture and gets image recognition from PC via the model.
#Hosted on RPI
import cv2
import os
import serial
import time
import threading
import subprocess
from flask import Flask, Response, send_file, request
import serial.serialutil

# ----------------------------
# Kill conflicting processes
# ----------------------------
def cleanup():
    print("[SYS] Cleaning up old processes...")
    try:
        subprocess.run(["sudo", "fuser", "-k", "/dev/ttyACM0"], check=False)
        subprocess.run(["sudo", "fuser", "-k", "5000/tcp"], check=False)
        subprocess.run(["sudo", "fuser", "-k", "/dev/video0"], check=False)
    except Exception as e:
        print(f"[WARN] Cleanup failed: {e}")

cleanup()

# ----------------------------
# Flask Setup
# ----------------------------
app = Flask(__name__)
last_photo = "photo.jpg"

# Initialize camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[ERROR] Could not open camera. Exiting.")
    exit(1)

# Serial port for STM
try:
    ser = serial.Serial("/dev/ttyACM0", baudrate=115200, timeout=1)
    time.sleep(2)  # STM resets on port open
except Exception as e:
    print(f"[ERROR] Could not open serial port: {e}")
    exit(1)

# ----------------------------
# Camera Functions
# ----------------------------
def generate_frames():
    """Stream live camera frames as MJPEG."""
    while True:
        success, frame = cap.read()
        if not success:
            continue
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/preview')
def camera_preview():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_photo')
def get_photo():
    """Download the last captured photo."""
    if os.path.exists(last_photo):
        return send_file(last_photo, mimetype='image/jpeg')
    else:
        return "No photo captured yet", 404

@app.route('/capture')
def capture_photo():
    """Capture photo on demand."""
    success, frame = cap.read()
    if success:
        cv2.imwrite(last_photo, frame)
        return f"Photo saved as {last_photo}"
    else:
        return "Failed to capture photo", 500

@app.route('/send_command', methods=['POST'])
def send_command():
    """PC sends command (n or y), Pi forwards to STM."""
    cmd = request.data.decode().strip().lower()
    if cmd in ["n", "y", "w"]:
        try:
            ser.write((cmd + "\n").encode())
            print(f"[STM] Forwarded command: {cmd}")
            return f"Sent {cmd} to STM", 200
        except Exception as e:
            return f"Serial error: {e}", 500
    return "Invalid command", 400

# ----------------------------
# STM Communication Loop
# ----------------------------
def stm_loop():
    """Continuously listen to STM and act when it says 'ready'."""
    print("[STM] Sending initial 'w'")
    ser.write(b"w\n")  # start movement

    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                print(f"[RAW STM] {repr(line)}")
                norm_line = line.lower()
                if norm_line == "ready":
                    print("[STM] Ready signal received. Capturing photo...")
                    success, frame = cap.read()
                    if success:
                        cv2.imwrite(last_photo, frame)
                        print(f"[CAM] Photo captured as {last_photo}")
                    else:
                        print("[CAM] Failed to capture photo")
        except serial.serialutil.SerialException as e:
            print(f"[ERROR] Serial read failed: {e}")
            time.sleep(1)
            continue

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    # Start Flask in background thread
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, debug=False),
        daemon=True
    )
    flask_thread.start()

    # Run STM listener in main thread
    stm_loop()
