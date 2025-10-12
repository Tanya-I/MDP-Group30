#!/usr/bin/env python3
#Basic code to just check the camera . If we want to just preview the camera feed on a web page
import cv2
from flask import Flask, Response

app = Flask(__name__)

# Initialize camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError("[ERROR] Could not open camera. Check connection or enable camera via raspi-config.")

def generate_frames():
    """Continuously capture frames and stream as MJPEG."""
    while True:
        success, frame = cap.read()
        if not success:
            continue
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    print("[INFO] Starting Flask camera preview server on port 5000...")
    print("[INFO] Visit: http://<your_rpi_ip>:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)