#!/usr/bin/env python3
"""
Modified pc_client_full.py - Sends only half the number of w10 commands
"""

import requests
import json
import time
import base64
import os
import sys
import math
import datetime

# ──────────────────────────────────────────────────────────────
# Imports with better error handling
# ──────────────────────────────────────────────────────────────
try:
    from vision import call_local_yolo, class_to_id, draw_predictions
    VISION_AVAILABLE = True
except ImportError:
    print("[WARN] vision_3.py not available, using mock recognition.")
    VISION_AVAILABLE = False

try:
    from planner_integration_og import plan_full_task, DEFAULT_STANDOFF, DEFAULT_R_MIN
    PLANNER_AVAILABLE = True
except ImportError:
    print("[WARN] planner_integration.py not available, using simple navigation.")
    PLANNER_AVAILABLE = False

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────
DEFAULT_RPI_HOST = '192.168.30.1'
DEFAULT_RPI_PORT = 5000
YOLO_MODEL_PATH = 'v1.pt'
YOLO_CONFIDENCE = 0.6
YOLO_IMAGE_SIZE = 640
YOLO_DEVICE = None
MAX_RETRIES = 1
RETRY_ADJUST_CM = 5
TASK_TIMEOUT = 120  # seconds

# ──────────────────────────────────────────────────────────────
# Command Filtering Helper
# ──────────────────────────────────────────────────────────────
def filter_w10_commands(commands):
    """
    Count w10 commands and return filtered list with only half of them.
    
    Args:
        commands: List of command strings
    
    Returns:
        Filtered list with only half the w10 commands
    """
    w10_count = sum(1 for cmd in commands if cmd == 'w10')
    
    if w10_count == 0:
        return commands
    
    target_w10_count = w10_count // 2  # Integer division for half
    print(f"[FILTER] Found {w10_count} w10 commands, keeping {target_w10_count}")
    
    filtered = []
    w10_kept = 0
    
    for cmd in commands:
        if cmd == 'w10':
            if w10_kept < target_w10_count:
                filtered.append(cmd)
                w10_kept += 1
            else:
                print(f"[FILTER] Skipping w10 command ({w10_kept}/{target_w10_count} kept)")
        else:
            filtered.append(cmd)
    
    return filtered


# ──────────────────────────────────────────────────────────────
# RPi Client
# ──────────────────────────────────────────────────────────────
class RPIClient:
    def __init__(self, host, port=DEFAULT_RPI_PORT):
        self.base_url = f"http://{host}:{port}"
        self.timeout = 30

    def get_obstacles(self):
        try:
            r = requests.get(f"{self.base_url}/obstacles", timeout=5)
            r.raise_for_status()
            return r.json()['obstacles']
        except Exception as e:
            print(f"[ERROR] Failed to get obstacles: {e}")
            return None

    def get_status(self):
        try:
            r = requests.get(f"{self.base_url}/status", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[ERROR] Failed to get status: {e}")
            return None

    def start_task(self):
        try:
            r = requests.post(f"{self.base_url}/start_task", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[ERROR] Failed to start task: {e}")
            return None

    def send_stm_command(self, command):
        try:
            data = {'command': command}
            r = requests.post(f"{self.base_url}/stm_command", json=data, timeout=self.timeout)
            r.raise_for_status()
            result = r.json()
            if result.get('status') == 'ok':
                return result.get('response')
            else:
                print(f"[WARN] STM command failed: {result}")
                return None
        except Exception as e:
            print(f"[ERROR] STM command error: {e}")
            return None

    def capture_image(self, obstacle_id):
        try:
            data = {'obstacle_id': obstacle_id}
            r = requests.post(f"{self.base_url}/capture", json=data, timeout=10)
            r.raise_for_status()
            result = r.json()
            if result.get('status') == 'ok':
                return result.get('image')
            return None
        except Exception as e:
            print(f"[ERROR] Image capture failed: {e}")
            return None

    def update_image_id(self, obstacle_id, image_id):
        try:
            data = {'obstacle_id': obstacle_id, 'image_id': image_id}
            r = requests.post(f"{self.base_url}/update_image", json=data, timeout=5)
            r.raise_for_status()
            return r.json().get('status') == 'ok'
        except Exception as e:
            print(f"[ERROR] Failed to update image: {e}")
            return False

    def stop_task(self):
        try:
            r = requests.post(f"{self.base_url}/stop_task", timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[ERROR] Failed to stop task: {e}")
            return None


# ──────────────────────────────────────────────────────────────
# Recognition using local saved JPGs
# ──────────────────────────────────────────────────────────────
def recognize_image(img_b64, obstacle_id):
    """
    Run YOLO recognition on the saved .jpg in ./rpi_downloads for this obstacle.
    Saves annotated results to ./rpi_downloads/annotated.
    """
    if not VISION_AVAILABLE:
        print("[WARN] Vision not available, returning mock ID.")
        return 11

    if not os.path.exists(YOLO_MODEL_PATH):
        print(f"[ERROR] Model not found: {YOLO_MODEL_PATH}")
        return None

    save_dir = os.path.join(os.getcwd(), "rpi_downloads")
    if not os.path.exists(save_dir):
        print("[ERROR] Folder rpi_downloads not found.")
        return None

    # Find latest downloaded image for this obstacle
    files = sorted(
        [os.path.join(save_dir, f) for f in os.listdir(save_dir) if f.startswith(f"obstacle_{obstacle_id}_")],
        key=os.path.getmtime,
        reverse=True
    )
    if not files:
        print(f"[ERROR] No saved image found for obstacle {obstacle_id}.")
        return None

    image_path = files[0]
    print(f"[VISION] Running YOLO on saved image → {image_path}")

    try:
        results = call_local_yolo(
            model_path=YOLO_MODEL_PATH,
            image_path=image_path,
            conf=YOLO_CONFIDENCE,
            imgsz=YOLO_IMAGE_SIZE,
            device=YOLO_DEVICE
        )

        # Draw & save annotated version
        annotated_dir = os.path.join(save_dir, "annotated")
        os.makedirs(annotated_dir, exist_ok=True)
        draw_predictions(
            image_path, results, conf_thresh=YOLO_CONFIDENCE,
            gallery_dir=os.path.join(annotated_dir, "raw_clips"),
            gallery_out=os.path.join(annotated_dir, "gallery.jpg")
        )

        # Pick best prediction
        best_pred, best_conf = None, 0.0
        for r in results:
            boxes = r.boxes
            names = r.names
            if boxes is None or len(boxes) == 0:
                continue
            for i in range(len(boxes)):
                conf = float(boxes.conf[i].item())
                if conf > best_conf:
                    best_conf = conf
                    cls_id = int(boxes.cls[i].item())
                    cls_name = names.get(cls_id, str(cls_id))
                    best_pred = cls_name

        if best_pred and best_conf >= 0.3:
            img_id = class_to_id(best_pred)
            print(f"[VISION] Obstacle {obstacle_id}: {best_pred} (conf={best_conf:.2f}) → ID {img_id}")
            return img_id

        print(f"[VISION] No valid recognition for obstacle {obstacle_id}.")
        return None

    except Exception as e:
        print(f"[ERROR] Recognition failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# ──────────────────────────────────────────────────────────────
# Navigation + Task Execution
# ──────────────────────────────────────────────────────────────
def navigate_to_obstacle_direct(rpi_client, obstacle):
    standoff = DEFAULT_STANDOFF if PLANNER_AVAILABLE else 0.30
    if obstacle['face'] == 'N':
        target_x = obstacle['x'] + 0.05
        target_y = obstacle['y'] + 0.10 + standoff
        target_heading = 270
    elif obstacle['face'] == 'S':
        target_x = obstacle['x'] + 0.05
        target_y = obstacle['y'] - standoff
        target_heading = 90
    elif obstacle['face'] == 'E':
        target_x = obstacle['x'] + 0.10 + standoff
        target_y = obstacle['y'] + 0.05
        target_heading = 180
    else:
        target_x = obstacle['x'] - standoff
        target_y = obstacle['y'] + 0.05
        target_heading = 0

    status = rpi_client.get_status()
    if not status:
        return False

    robot_pos = status['robot_pos']
    dx = target_x - robot_pos['x']
    dy = target_y - robot_pos['y']
    dist = math.hypot(dx, dy)
    move_heading = math.degrees(math.atan2(dy, dx))

    angle_diff = (move_heading - robot_pos['heading'] + 180) % 360 - 180
    if abs(angle_diff) > 5:
        turn_cmd = f"d{int(abs(angle_diff))}" if angle_diff > 0 else f"a{int(abs(angle_diff))}"
        print(f"  Turn: {turn_cmd}")
        if not rpi_client.send_stm_command(turn_cmd):
            return False
        time.sleep(0.3)

    dist_cm = int(dist * 100)
    if dist_cm > 2:
        move_cmd = f"w{dist_cm}"
        print(f"  Move: {move_cmd}")
        if not rpi_client.send_stm_command(move_cmd):
            return False
        time.sleep(0.3)

    return True


# ──────────────────────────────────────────────────────────────
# Task Execution Logic
# ──────────────────────────────────────────────────────────────
def execute_task_with_planning(rpi_client, obstacles):
    print("="*70)
    print("TASK EXECUTION - WITH INTEGRATED PATH PLANNING")
    print("="*70)

    rpi_client.start_task()
    start_time = time.time()
    status = rpi_client.get_status()
    if not status:
        print("[ERROR] Cannot get robot status.")
        return 0, len(obstacles)

    robot_pos = status['robot_pos']
    start_pose = (robot_pos['x'], robot_pos['y'], math.radians(robot_pos['heading']))

    print(f"Robot start: ({start_pose[0]:.3f}, {start_pose[1]:.3f}, {math.degrees(start_pose[2]):.1f}°)")

    if PLANNER_AVAILABLE:
        visit_order, command_sequences = plan_full_task(start_pose, obstacles)
        # Filter w10 commands from each sequence
        command_sequences = [filter_w10_commands(seq) for seq in command_sequences]
    else:
        visit_order = [obs['id'] for obs in obstacles]
        command_sequences = None

    identified_count = 0
    total_obstacles = len(obstacles)

    for leg_idx, obs_id in enumerate(visit_order):
        elapsed = time.time() - start_time
        if elapsed > TASK_TIMEOUT:
            print(f"[TIMEOUT] Exceeded {TASK_TIMEOUT}s")
            break

        obstacle = next((o for o in obstacles if o['id'] == obs_id), None)
        if not obstacle:
            continue

        print(f"\n→ Obstacle {obs_id}")
        if command_sequences and leg_idx < len(command_sequences):
            for cmd in command_sequences[leg_idx]:
                rpi_client.send_stm_command(cmd)
                time.sleep(0.2)
        else:
            navigate_to_obstacle_direct(rpi_client, obstacle)

        print(f"\n📷 Capturing image for obstacle {obs_id}...")
        img_b64 = rpi_client.capture_image(obs_id)
        if img_b64:
            SAVE_DIR = os.path.join(os.getcwd(), "rpi_downloads")
            os.makedirs(SAVE_DIR, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = os.path.join(SAVE_DIR, f"obstacle_{obs_id}_{timestamp}.jpg")
            with open(save_path, "wb") as f:
                f.write(base64.b64decode(img_b64))
            print(f"[CLIENT] Saved raw image → {save_path}")

        image_id = recognize_image(img_b64, obs_id)
        if image_id and rpi_client.update_image_id(obs_id, image_id):
            identified_count += 1
            print(f"✓ Obstacle {obs_id} identified as ID {image_id}")

        print(f"Progress: {identified_count}/{total_obstacles}")

    rpi_client.stop_task()
    print(f"Total identified: {identified_count}/{total_obstacles}")
    return identified_count, total_obstacles


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
def main():
    print("="*70)
    print("PC CLIENT - MDP ROBOT NAVIGATION SYSTEM")
    print("="*70)
    print(f"RPI: {DEFAULT_RPI_HOST}:{DEFAULT_RPI_PORT}")
    print(f"Model: {YOLO_MODEL_PATH}")
    print(f"Confidence: {YOLO_CONFIDENCE}")
    print(f"Planning: {'Enabled' if PLANNER_AVAILABLE else 'Simple navigation'}")
    print(f"Vision: {'Enabled' if VISION_AVAILABLE else 'Disabled (mock mode)'}")
    print("="*70)

    if VISION_AVAILABLE and not os.path.exists(YOLO_MODEL_PATH):
        print(f"❌ Model not found: {YOLO_MODEL_PATH}")
        return 1

    rpi = RPIClient(DEFAULT_RPI_HOST, DEFAULT_RPI_PORT)
    print("\n⏳ Waiting for obstacles from Android...")
    obstacles = None
    for _ in range(60):
        obstacles = rpi.get_obstacles()
        if obstacles:
            break
        time.sleep(1)

    if not obstacles:
        print("❌ No obstacles received.")
        return 1

    print(f"✓ Received {len(obstacles)} obstacles.")
    input("Press ENTER to start task...")

    identified, total = execute_task_with_planning(rpi, obstacles)
    print(f"Task done: {identified}/{total} identified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())