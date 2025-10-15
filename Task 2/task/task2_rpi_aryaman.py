#!/usr/bin/env python3
# Modified RPI server for Week 9 task
# Handles Android (Bluetooth) -> STM coordination and PC image recognition responses
import cv2
import os
import io
import serial
import time
import threading
import subprocess
import logging
import hashlib
from flask import Flask, Response, send_file, request
import serial.serialutil
from bluetooth import *

# ----------------------------
# Configuration
# ----------------------------
STM_PORT = "/dev/ttyACM0"
STM_BAUDRATE = 115200

# ----------------------------
# Setup Logging
# ----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RPiServer")

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
last_photo_bytes = None  # store latest photo in memory (as bytes)

# Initialize camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[ERROR] Could not open camera. Exiting.")
    exit(1)

# Serial port for STM
try:
    ser = serial.Serial(STM_PORT, baudrate=STM_BAUDRATE, timeout=1)
    time.sleep(2)  # STM resets on port open
    print("[STM] Serial connection established")
except Exception as e:
    print(f"[ERROR] Could not open serial port: {e}")
    exit(1)

# Global state
android_command_received = False
ready_count = 0  # Track how many "ready" signals we've received
max_ready_count = 2  # We expect 2 ready signals
bt_client_sock = None
last_photo_hash = None  # Track hash to prevent duplicates
photo_lock = threading.Lock()  # Thread-safe photo access

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
    """Send latest captured photo directly from memory."""
    global last_photo_bytes

    with photo_lock:
        if last_photo_bytes is None:
            return "No photo captured yet", 404

        # Stream image bytes directly (no file I/O)
        return send_file(
            io.BytesIO(last_photo_bytes),
            mimetype='image/jpeg',
            as_attachment=False
        )

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
    """PC sends command (l or r), Pi forwards to STM."""
    cmd = request.data.decode().strip()  # <--- remove .upper()
    if cmd in ["l", "r"]:
        try:
            ser.write((cmd + "\n").encode())
            print(f"[STM] Forwarded command from PC: {cmd}")
            return f"Sent {cmd} to STM", 200
        except Exception as e:
            return f"Serial error: {e}", 500
    return "Invalid command", 400

# ----------------------------
# Bluetooth Android Communication
# ----------------------------
def bluetooth_listener():
    """Listen for WEEK9_COMMAND from Android via Bluetooth."""
    global android_command_received, bt_client_sock
    
    server_sock = BluetoothSocket(RFCOMM)
    server_sock.bind(("", 1))  # RFCOMM channel 1
    server_sock.listen(1)
    
    port = server_sock.getsockname()[1]
    print(f"[BT] Bluetooth server running on RFCOMM channel {port}")
    print("[BT] Waiting for Android connection...")
    
    try:
        while True:
            client_sock, client_info = server_sock.accept()
            bt_client_sock = client_sock
            print(f"[BT] Connected to Android: {client_info}")
            
            try:
                while True:
                    data = client_sock.recv(1024).decode("utf-8")
                    if not data:
                        print("[BT] Android disconnected")
                        bt_client_sock = None
                        break
                    
                    message = data.strip()
                    print(f"[BT] Received from Android: {message}")
                    
                    if message == "WEEK9_COMMAND":
                        print("[BT] ✓ WEEK9_COMMAND received!")
                        android_command_received = True
                        
                        # Send 'S' to STM
                        try:
                            ser.write(b"s\n")
                            print("[STM] Sent 's' command")
                        except Exception as e:
                            print(f"[ERROR] Failed to send 's' to STM: {e}")
                        
                        # Acknowledge to Android
                        try:
                            client_sock.send(b"ACK\n")
                            print("[BT] Sent ACK to Android")
                        except Exception as e:
                            print(f"[BT] Failed to send ACK: {e}")
                    
            except OSError as e:
                print(f"[BT] Connection error: {e}")
                bt_client_sock = None
            except Exception as e:
                print(f"[BT] Error: {e}")
                bt_client_sock = None
            finally:
                try:
                    client_sock.close()
                except:
                    pass
                bt_client_sock = None
                print("[BT] Session closed, waiting for new connection...")
                
    except Exception as e:
        print(f"[BT] Server error: {e}")
    finally:
        server_sock.close()
        print("[BT] Bluetooth server shut down")

# ----------------------------
# STM Communication Loop
# ----------------------------
def stm_loop():
    """Listen to STM for 'ready' signals and capture photos."""
    global ready_count
    
    print("[STM] Waiting for Android command before processing STM signals...")
    
    # Wait for Android command
    while not android_command_received:
        time.sleep(0.1)
    
    print("[STM] Android command received, now listening to STM...")
    
    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                print(f"[RAW STM] {repr(line)}")
                norm_line = line.lower()
                
                if norm_line == "ready":
                    ready_count += 1
                    print(f"[STM] Ready signal #{ready_count} received")

                    # Capture fresh photo with hash tracking to prevent duplicates
                    with photo_lock:
                        # Flush old frames to ensure a fresh capture
                        for _ in range(5):
                            cap.grab()

                        # Small delay to stabilize
                        time.sleep(0.05)

                        success, frame = cap.read()
                        if success:
                            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                            photo_bytes = buffer.tobytes()

                            # Calculate hash to prevent duplicates
                            global last_photo_bytes, last_photo_hash
                            new_hash = hashlib.md5(photo_bytes).hexdigest()

                            if new_hash != last_photo_hash:
                                last_photo_bytes = photo_bytes
                                last_photo_hash = new_hash
                                print(f"[CAM] ✓ Fresh photo captured ({len(last_photo_bytes)} bytes, hash: {new_hash[:8]})")
                            else:
                                print(f"[CAM] ⚠ Warning: Duplicate photo detected, re-capturing...")
                                # Try one more time
                                time.sleep(0.1)
                                cap.grab()
                                success, frame = cap.read()
                                if success:
                                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                                    last_photo_bytes = buffer.tobytes()
                                    last_photo_hash = hashlib.md5(last_photo_bytes).hexdigest()
                                    print(f"[CAM] ✓ Re-captured photo ({len(last_photo_bytes)} bytes, hash: {last_photo_hash[:8]})")
                        else:
                            print("[CAM] ✗ Failed to capture photo")


                    # After max_ready_count, send completion signal
                    if ready_count >= max_ready_count:
                        print(f"[STM] Completed {max_ready_count} ready cycles")
                        print(f"[TASK] Week 9 task complete!")

                        # Send WEEK9_TASK_DONE to Android
                        if bt_client_sock:
                            try:
                                bt_client_sock.send(b"WEEK9_TASK_DONE\n")
                                print("[BT] Sent WEEK9_TASK_DONE to Android")
                            except Exception as e:
                                print(f"[BT] Failed to send completion: {e}")

                        # Optionally reset for another run
                        # ready_count = 0
                        # android_command_received = False
                        
        except serial.serialutil.SerialException as e:
            print(f"[ERROR] Serial read failed: {e}")
            time.sleep(1)
            continue
        except Exception as e:
            print(f"[ERROR] Unexpected error in STM loop: {e}")
            time.sleep(1)

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("[INIT] Starting RPI Week 9 Server")
    print("=" * 60)
    
    # Start Flask in background thread
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    print("[FLASK] ✓ Server started on port 5000")
    
    # Start Bluetooth listener in background thread
    bt_thread = threading.Thread(target=bluetooth_listener, daemon=True)
    bt_thread.start()
    print("[BT] ✓ Bluetooth listener thread started")
    
    # Give threads time to initialize
    time.sleep(1)
    
    print("=" * 60)
    print("[INIT] All systems ready")
    print("[INIT] Workflow:")
    print("  1. Waiting for Android to send 'WEEK9_COMMAND' via Bluetooth")
    print("  2. Upon receipt, will send 'S' to STM")
    print("  3. Will capture 2 photos when STM sends 'ready'")
    print("  4. PC will fetch photos and send 'L' or 'R' responses")
    print("=" * 60)
    
    # Run STM listener in main thread
    try:
        stm_loop()
    except KeyboardInterrupt:
        print("\n[INIT] Shutting down...")
        cap.release()
        ser.close()
