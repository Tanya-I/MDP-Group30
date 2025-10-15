#!/usr/bin/env python3
"""
PC Client for Week 9 Task - POLLING MODE
-----------------------------------------
Continuously polls RPI for new photos, performs image recognition immediately,
and sends L/R commands back for maximum speed.
The latest one we have been using to test , is an optimised version of task2_pc.py
"""
import os
import sys

# Set offline mode BEFORE importing ultralytics
os.environ["YOLO_OFFLINE"] = "1"
os.environ["ULTRALYTICS_HUB"] = "0"
os.environ["YOLO_VERBOSE"] = "False"
os.environ["TORCH_HOME"] = os.getcwd()  # Keep models local

import time
import cv2
import numpy as np
import hashlib
from datetime import datetime

# Patch requests to work offline
import requests
from requests.adapters import HTTPAdapter

class OfflineAdapter(HTTPAdapter):
    """Adapter that blocks external requests but allows local"""
    def send(self, request, **kwargs):
        # Allow localhost and local network
        if any(host in request.url for host in ['192.168.', '127.0.0.1', 'localhost']):
            return super().send(request, **kwargs)
        # Block everything else (GitHub, etc)
        raise requests.exceptions.ConnectionError(f"Offline mode: blocked {request.url}")

# Monkey patch requests.get for ultralytics
_original_get = requests.get
def patched_get(url, *args, **kwargs):
    if 'github.com' in url or 'ultralytics.com' in url:
        raise requests.exceptions.ConnectionError("Offline mode")
    return _original_get(url, *args, **kwargs)
requests.get = patched_get

# Import YOLO after patching
try:
    from ultralytics import YOLO
    try:
        from ultralytics.utils import SETTINGS
        SETTINGS['sync'] = False  # Disable telemetry
    except:
        pass  # Ignore if settings don't exist
except ImportError as e:
    print(f"[ERROR] Failed to import ultralytics: {e}")
    print(f"[ERROR] Install with: pip install ultralytics")
    sys.exit(1)

# Restore requests.get for actual use
requests.get = _original_get

# ---- CONFIG ----
RPI_IP = "192.168.30.1"  # Set your RPI's fixed IP here
RPI_URL = f"http://{RPI_IP}:5000"

# Get script directory for relative paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, "v1.pt")  # Path to your YOLOv8 model
CONF_THRESHOLD = 0.6
IMGSZ = 640
DEVICE = None  # None (auto), "cpu", or "cuda:0"

POLL_INTERVAL = 0.15  # Poll every 150ms for maximum responsiveness
MAX_CYCLES = 2  # Stop after processing 2 photos (Task 2 has 2 obstacles)
POLL_TIMEOUT = 90  # Maximum time to wait for new photo (seconds)
REQUEST_TIMEOUT = 3  # HTTP request timeout

# Output directories
OUTPUT_DIR = "./week9_outputs"
ANNOTATED_DIR = os.path.join(OUTPUT_DIR, "annotated")
GALLERY_DIR = os.path.join(OUTPUT_DIR, "raw_clips")
GALLERY_OUT = os.path.join(OUTPUT_DIR, "gallery.jpg")

# Create directories
os.makedirs(ANNOTATED_DIR, exist_ok=True)
os.makedirs(GALLERY_DIR, exist_ok=True)

# ---- ID MAPPING ----
BASE_ID_MAP = {
    "1": 11, "2": 12, "3": 13, "4": 14, "5": 15, "6": 16, "7": 17, "8": 18, "9": 19,
    "A": 20, "B": 21, "C": 22, "D": 23, "E": 24, "F": 25, "G": 26, "H": 27,
    "S": 28, "T": 29, "U": 30, "V": 31, "W": 32, "X": 33, "Y": 34, "Z": 35,
    "up": 36, "down": 37, "right": 38, "left": 39, "stop": 40,
}
ID_TO_PRETTY = {v: k for k, v in BASE_ID_MAP.items()}

# ---- HELPER FUNCTIONS ----
def get_image_hash(image_data):
    """Calculate hash of image data to detect changes."""
    return hashlib.md5(image_data).hexdigest()

def poll_for_new_photo(last_hash, timeout):
    """
    Poll RPI until a new photo is available (different from last_hash).
    Returns: (image_data, new_hash) or (None, None) on timeout
    """
    print(f"[PC] Polling for new photo (checking every {POLL_INTERVAL}s)...")
    start_time = time.time()
    poll_count = 0
    connection_errors = 0

    while time.time() - start_time < timeout:
        poll_count += 1
        try:
            resp = requests.get(f"{RPI_URL}/get_photo", timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                image_data = resp.content
                current_hash = get_image_hash(image_data)

                if current_hash != last_hash:
                    elapsed = time.time() - start_time
                    print(f"[PC] ✓ New photo detected! (after {elapsed:.2f}s, {poll_count} polls)")
                    return image_data, current_hash

                # Same photo, keep polling
                if poll_count % 10 == 0:  # Print status every 10 polls
                    print(f"[PC]   ... still waiting ({poll_count} polls, {time.time()-start_time:.1f}s)")
            else:
                print(f"[PC] ⚠ HTTP {resp.status_code}: {resp.text[:50]}")

        except requests.exceptions.Timeout:
            connection_errors += 1
            if connection_errors % 5 == 0:
                print(f"[PC] ⚠ Request timeout ({connection_errors} timeouts)")
        except requests.exceptions.ConnectionError:
            connection_errors += 1
            if connection_errors % 5 == 0:
                print(f"[PC] ⚠ Connection error ({connection_errors} errors)")
        except requests.exceptions.RequestException as e:
            print(f"[PC] ⚠ Request error: {e}")

        time.sleep(POLL_INTERVAL)

    print(f"[PC] ✗ Timeout waiting for new photo after {timeout}s")
    return None, None

def normalize_label(raw):
    """Normalize model class names to canonical keys."""
    if raw is None:
        return ""
    if isinstance(raw, (int, float)):
        raw = str(int(raw))
    s = str(raw).strip().lower()
    
    # Handle arrow directions
    if "left" in s:
        return "left"
    if "right" in s:
        return "right"
    if "up" in s:
        return "up"
    if "down" in s:
        return "down"
    if "stop" in s:
        return "stop"
    
    # Handle single letter
    if len(s) == 1 and s.isalpha():
        return s.upper()
    
    return s

def class_to_id(cls):
    """Convert class name to ID."""
    key = normalize_label(cls)
    if not key:
        return "NA"
    if key.isdigit():
        return int(key)
    return BASE_ID_MAP.get(key, "NA")

def save_annotated_frame(img_bgr, boxes, names, save_path, conf_threshold):
    """Save annotated image with bounding boxes and labels. Only arrows are considered valid."""
    out_img = img_bgr.copy()
    detected_symbols = []

    if boxes is None or len(boxes) == 0:
        cv2.imwrite(save_path, out_img)
        return detected_symbols

    for i in range(len(boxes)):
        xyxy = boxes.xyxy[i].cpu().numpy().tolist()
        x1, y1, x2, y2 = map(int, xyxy)
        cls_id = int(boxes.cls[i].item())
        conf_i = float(boxes.conf[i].item())

        if conf_i < conf_threshold:
            continue

        cls_name = names.get(cls_id, str(cls_id))
        obj_id = class_to_id(cls_name)
        pretty = ID_TO_PRETTY.get(obj_id, str(cls_name)) if isinstance(obj_id, int) else str(cls_name)

        # Check if it's an arrow (left=39, right=38)
        is_arrow = obj_id in [38, 39]

        if obj_id != "NA":
            detected_symbols.append((obj_id, pretty, conf_i))

        # Draw bounding box - GREEN for arrows, RED for non-arrows
        box_color = (0, 255, 0) if is_arrow else (0, 0, 255)  # Green for arrows, Red for others
        cv2.rectangle(out_img, (x1, y1), (x2, y2), box_color, 2)

        # Draw label with arrow indicator
        arrow_marker = "→ ARROW" if is_arrow else "✗ IGNORED"
        label = f"{obj_id}_{pretty}_{conf_i:.2f} {arrow_marker}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        y_top = max(0, y1 - th - 8)
        cv2.rectangle(out_img, (x1, y_top), (x1 + tw + 6, y1), box_color, -1)
        cv2.putText(out_img, label, (x1 + 3, max(0, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    cv2.imwrite(save_path, out_img)
    return detected_symbols

def save_individual_clips(img_bgr, boxes, names, gallery_dir, conf_threshold, cycle_num=0):
    """Save individual cropped images for ARROW detections only."""
    # Removed saved_symbols set to allow duplicates
    
    if boxes is None or len(boxes) == 0:
        return

    arrow_count = 0  # Counter for multiple arrows in same cycle
    
    for i in range(len(boxes)):
        xyxy = boxes.xyxy[i].cpu().numpy().tolist()
        x1, y1, x2, y2 = map(int, xyxy)
        cls_id = int(boxes.cls[i].item())
        conf_i = float(boxes.conf[i].item())

        if conf_i < conf_threshold:
            continue

        cls_name = names.get(cls_id, str(cls_id))
        obj_id = class_to_id(cls_name)
        pretty = ID_TO_PRETTY.get(obj_id, str(cls_name)) if isinstance(obj_id, int) else str(cls_name)

        # ONLY save arrows (left=39, right=38)
        is_arrow = obj_id in [38, 39]
        if not is_arrow:
            continue  # Skip non-arrows

        # Make filename unique by including cycle number and arrow count
        arrow_count += 1
        symbol_key = f"cycle{cycle_num}_{obj_id}_{pretty}_arrow{arrow_count}"
        
        # Save the frame with bounding box (green for arrows)
        single = img_bgr.copy()
        cv2.rectangle(single, (x1, y1), (x2, y2), (0, 255, 0), 3)

        label = f"ARROW: {pretty.upper()} (conf: {conf_i:.2f})"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        y_top = max(0, y1 - th - 10)
        cv2.rectangle(single, (x1, y_top), (x1 + tw + 8, y1), (0, 255, 0), -1)
        cv2.putText(single, label, (x1 + 4, max(0, y1 - 7)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

        save_path = os.path.join(gallery_dir, f"{symbol_key}.jpg")
        cv2.imwrite(save_path, single)
        print(f"[PC]      Saved gallery clip: {symbol_key}.jpg")
        
def make_tiled_gallery(gallery_dir, out_path, tile_w=360, cols=3, pad=8):
    """Create a tiled gallery from individual images."""
    import math
    
    files = [os.path.join(gallery_dir, f) for f in os.listdir(gallery_dir)
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    
    if not files:
        return False
    
    imgs = []
    for fp in files:
        im = cv2.imread(fp)
        if im is None:
            continue
        h, w = im.shape[:2]
        imr = cv2.resize(im, (tile_w, int(h * tile_w / float(w))))
        imgs.append((fp, imr))
    
    if not imgs:
        return False
    
    rows = math.ceil(len(imgs) / cols)
    max_h_per_row = [max(im.shape[0] for _, im in imgs[r*cols:(r+1)*cols]) for r in range(rows)]
    canvas_w = cols * tile_w + (cols + 1) * pad
    canvas_h = sum(max_h_per_row) + (rows + 1) * pad
    canvas = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)

    y = pad
    idx = 0
    for r in range(rows):
        x = pad
        for _ in range(cols):
            if idx >= len(imgs):
                break
            _, im = imgs[idx]
            h, w = im.shape[:2]
            canvas[y:y+h, x:x+w] = im
            x += tile_w + pad
            idx += 1
        y += max_h_per_row[r] + pad
    
    cv2.imwrite(out_path, canvas)
    return True

def perform_inference(image_path, model):
    """Run YOLOv8 inference on the image with optimized settings."""
    # Use aggressive settings for speed
    results = model.predict(
        source=image_path,
        imgsz=IMGSZ,
        conf=CONF_THRESHOLD,
        verbose=False,
        device=DEVICE,
        half=False,  # Set to True if using GPU for faster inference
        max_det=10,  # Limit max detections (we only need 1-2 arrows)
        agnostic_nms=True,  # Speed up NMS
    )
    return results

def decide_command(detected_symbols):
    """
    Decide L or R based on detected symbols.
    ONLY looks for arrow directions (left/right) - ignores all other symbols.
    """
    if not detected_symbols:
        print("[PC] ⚠ No symbols detected, defaulting to R")
        return "r"

    # Filter to ONLY arrow detections
    arrow_detections = []
    other_detections = []

    for obj_id, pretty, conf in detected_symbols:
        pretty_lower = pretty.lower()

        # Check if it's an arrow
        if pretty_lower == "left" or obj_id == 39:
            arrow_detections.append(("LEFT", conf))
            print(f"[PC]    ✓ Detected LEFT arrow (ID: {obj_id}, conf: {conf:.2f})")
        elif pretty_lower == "right" or obj_id == 38:
            arrow_detections.append(("RIGHT", conf))
            print(f"[PC]    ✓ Detected RIGHT arrow (ID: {obj_id}, conf: {conf:.2f})")
        else:
            # Ignore bullseye and other symbols
            other_detections.append((pretty, obj_id, conf))
            print(f"[PC]    ✗ Ignored: {pretty} (ID: {obj_id}, conf: {conf:.2f}) - not an arrow")

    # Decision based on arrows only
    if arrow_detections:
        # Use the highest confidence arrow
        best_arrow = max(arrow_detections, key=lambda x: x[1])
        direction = best_arrow[0]
        confidence = best_arrow[1]

        if direction == "LEFT":
            print(f"[PC]  → Decision: LEFT arrow (conf: {confidence:.2f}) → sending L")
            return "l"
        else:
            print(f"[PC]  → Decision: RIGHT arrow (conf: {confidence:.2f}) → sending R")
            return "r"
    else:
        print(f"[PC] ⚠ No arrows detected (found {len(other_detections)} non-arrow symbols), defaulting to R")
        return "r"

def send_command_to_rpi(command):
    """Send l or r command back to RPI with retry logic."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(f"{RPI_URL}/send_command", data=command, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                print(f"[PC] ✓ Sent command '{command.upper()}' to RPI")
                return True
            else:
                print(f"[PC] ⚠ Failed to send command: {resp.status_code}, {resp.text}")
        except requests.exceptions.Timeout:
            print(f"[PC] ⚠ Timeout sending command (attempt {attempt+1}/{max_retries})")
        except requests.exceptions.ConnectionError:
            print(f"[PC] ⚠ Connection error (attempt {attempt+1}/{max_retries})")
        except Exception as e:
            print(f"[PC] ⚠ Error sending command: {e}")

        if attempt < max_retries - 1:
            time.sleep(0.5)  # Wait before retry

    print(f"[PC] ✗ Failed to send command after {max_retries} attempts")
    return False

def process_one_cycle(cycle_num, model, last_hash):
    """
    Process one photo cycle: poll → fetch → infer → decide → send.
    Returns: (success, new_hash)
    """
    print(f"\n{'='*60}")
    print(f"[PC] CYCLE {cycle_num}")
    print(f"{'='*60}")
    
    cycle_start = time.time()
    
    # Step 1: Poll for new photo
    image_data, new_hash = poll_for_new_photo(last_hash, POLL_TIMEOUT)
    if image_data is None:
        print(f"[PC] Failed to get new photo for cycle {cycle_num}")
        return False, last_hash
    
    # Step 2: Save the photo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    input_image = os.path.join(OUTPUT_DIR, f"cycle{cycle_num}_{timestamp}.jpg")
    with open(input_image, "wb") as f:
        f.write(image_data)
    print(f"[PC] Saved photo: {input_image}")
    
    # Step 3: Run inference
    infer_start = time.time()
    print(f"[PC]  Running image recognition...")
    img_bgr = cv2.imread(input_image)
    if img_bgr is None:
        print(f"[PC] Failed to read image: {input_image}")
        return False, new_hash
    
    results = perform_inference(input_image, model)
    infer_time = time.time() - infer_start
    print(f"[PC] Inference complete ({infer_time:.3f}s)")
    
    # Step 4: Process results and save outputs
    detected_symbols = []
    for r in results:
        boxes = r.boxes
        names = r.names
        
        # Save annotated image
        annotated_path = os.path.join(ANNOTATED_DIR, f"cycle{cycle_num}_{timestamp}_annotated.jpg")
        detected_symbols = save_annotated_frame(img_bgr, boxes, names, annotated_path, CONF_THRESHOLD)
        print(f"[PC] Saved annotated image: {annotated_path}")
        
        # Save individual clips for gallery
        save_individual_clips(img_bgr, boxes, names, GALLERY_DIR, CONF_THRESHOLD)
    
    # Step 5: Decide command
    command = decide_command(detected_symbols)
    
    # Step 6: Send command to RPI IMMEDIATELY
    send_start = time.time()
    success = send_command_to_rpi(command)
    send_time = time.time() - send_start
    
    # Timing summary
    cycle_time = time.time() - cycle_start
    poll_time = cycle_time - infer_time - send_time

    print(f"\n[PC] {'─'*50}")
    print(f"[PC] Cycle {cycle_num} Performance Summary:")
    print(f"[PC] {'─'*50}")
    print(f"[PC]   📷 Photo polling:    {poll_time:.3f}s")
    print(f"[PC]   🔍 Inference:        {infer_time:.3f}s")
    print(f"[PC]   📡 Command send:     {send_time:.3f}s")
    print(f"[PC]   ⏱️  Total cycle time: {cycle_time:.3f}s")
    print(f"[PC] {'─'*50}\n")

    return success, new_hash

def main():
    print("="*60)
    print("[PC] Week 9 PC Client - POLLING MODE")
    print("="*60)
    print(f"[PC] RPI URL: {RPI_URL}")
    print(f"[PC] Model: {MODEL_PATH}")
    print(f"[PC] Confidence threshold: {CONF_THRESHOLD}")
    print(f"[PC] Poll interval: {POLL_INTERVAL}s")
    print(f"[PC] Max cycles: {MAX_CYCLES}")
    print(f"[PC] Request timeout: {REQUEST_TIMEOUT}s")
    print(f"[PC] Output directory: {OUTPUT_DIR}")
    print("="*60)
    
    # Load YOLO model
    print(f"[PC] Loading YOLO model from {MODEL_PATH}...")

    # Check if model file exists
    if not os.path.exists(MODEL_PATH):
        print(f"[PC] ✗ Error: Model file '{MODEL_PATH}' not found!")
        print(f"[PC] Please ensure v1.pt is in the current directory")
        print(f"[PC] Current directory: {os.getcwd()}")
        return

    try:
        # Suppress urllib3 and requests warnings
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning)
        import urllib3
        urllib3.disable_warnings()

        # Load model with offline settings (ignore connectivity errors)
        try:
            model = YOLO(MODEL_PATH, task='detect')
        except Exception as load_error:
            # If it's a network error during model check, ignore it and load anyway
            error_msg = str(load_error).lower()
            if 'connection' in error_msg or 'resolve' in error_msg or 'github' in error_msg:
                print(f"[PC] ⚠ Network check failed (expected in offline mode), loading model anyway...")
                # Force load the local model file
                model = YOLO(MODEL_PATH)
            else:
                raise

        print(f"[PC] ✓ Model loaded successfully")

        # Warm up the model with a dummy inference
        print(f"[PC] Warming up model...")
        dummy_img = np.zeros((640, 640, 3), dtype=np.uint8)
        dummy_path = os.path.join(OUTPUT_DIR, "dummy.jpg")
        cv2.imwrite(dummy_path, dummy_img)
        try:
            _ = model.predict(dummy_path, verbose=False)
        except:
            # Ignore any errors during warmup
            pass
        if os.path.exists(dummy_path):
            os.remove(dummy_path)
        print(f"[PC] ✓ Model ready")

    except Exception as e:
        print(f"[PC] ✗ Failed to load model: {e}")
        print(f"[PC] Error type: {type(e).__name__}")
        print(f"[PC] Please check that v1.pt is a valid YOLO model file")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n[PC] Ready to process photos!")
    print(f"[PC] Waiting for RPI to capture first photo...")
    
    # Start with no previous hash (will accept any photo)
    last_hash = None
    
    # Process cycles with polling
    cycle = 0
    successful_cycles = 0

    while successful_cycles < MAX_CYCLES:
        cycle += 1
        success, last_hash = process_one_cycle(cycle, model, last_hash)
        if success:
            successful_cycles += 1
            print(f"[PC] ✓ Completed {successful_cycles}/{MAX_CYCLES} obstacles")
        else:
            print(f"[PC] ⚠ Cycle {cycle} failed, retrying...")
            time.sleep(1)

            # Safety check: if too many failed attempts, abort
            if cycle > MAX_CYCLES + 5:
                print(f"[PC] ✗ Too many failed attempts, aborting")
                break

    # Create tiled gallery at the end
    print(f"\n{'='*60}")
    print("[PC] Creating tiled gallery for supervisor verification...")
    print(f"{'='*60}")

    if make_tiled_gallery(GALLERY_DIR, GALLERY_OUT):
        print(f"[PC] ✓ Tiled gallery saved: {GALLERY_OUT}")
        print(f"[PC] → Show this file to supervisor for verification")
    else:
        print(f"[PC] ⚠ No images to create gallery")

    # Print summary
    print("\n" + "="*60)
    print(f"[PC] ✓✓ Week 9 Task Complete! ✓✓")
    print(f"[PC] Processed {successful_cycles}/{MAX_CYCLES} obstacles")
    print(f"[PC] Raw images: {OUTPUT_DIR}")
    print(f"[PC] Annotated images: {ANNOTATED_DIR}")
    print(f"[PC] Gallery for supervisor: {GALLERY_OUT}")
    print("="*60)

if __name__ == "__main__":
    main()