#!/usr/bin/env python3
"""
vision_3.py - Offline YOLO Inference Module

This module is designed for offline/embedded environments (e.g., Raspberry Pi).
Key differences from vision_2.py:
  - Forces YOLO offline mode (no internet connectivity required)
  - Module-based design (import and use functions, no CLI)
  - Same gallery features: individual frames + tiled gallery
  - Optimized for integration into larger systems
  
Use vision_2.py for standalone CLI inference with internet access.
Use vision_3.py for embedded/offline systems or when importing as a module.
"""
import os
os.environ["YOLO_OFFLINE"] = "True"
import ultralytics.utils
ultralytics.utils.is_online = lambda : False

import re
import math
import cv2
import numpy as np
import datetime
from ultralytics import YOLO

# ──────────────────────────────────────────────────────────────
# ID Mapping
# ──────────────────────────────────────────────────────────────
BASE_ID_MAP = {
    "1": 11, "2": 12, "3": 13, "4": 14, "5": 15, "6": 16, "7": 17, "8": 18, "9": 19,
    "A": 20, "B": 21, "C": 22, "D": 23, "E": 24, "F": 25, "G": 26, "H": 27,
    "S": 28, "T": 29, "U": 30, "V": 31, "W": 32, "X": 33, "Y": 34, "Z": 35,
    "up": 36, "down": 37, "right": 38, "left": 39, "stop": 40,
}

ID_TO_PRETTY = {v: k for k, v in BASE_ID_MAP.items()}
WORDS_TO_DIGITS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9"
}

def _normalize_label(raw) -> str:
    if raw is None:
        return ""
    s = str(raw).strip()
    if s.isdigit(): return s
    m = re.match(r"^alphabet[\s_:\-]*([a-zA-Z])$", s, flags=re.IGNORECASE)
    if m: return m.group(1).upper()
    s = re.sub(r"[\s_-]*arrow$", "", s, flags=re.IGNORECASE).strip()
    lw = s.lower()
    if lw in WORDS_TO_DIGITS: return WORDS_TO_DIGITS[lw]
    if len(s) == 1 and s.isalpha(): return s.upper()
    if lw in {"up","down","left","right","stop"}: return lw
    s2 = re.sub(r"[^a-zA-Z0-9]", "", s).lower()
    if s2 in WORDS_TO_DIGITS: return WORDS_TO_DIGITS[s2]
    if s2 in {"uparrow","downarrow","leftarrow","rightarrow"}:
        return s2.replace("arrow","")
    if s2 == "stop": return "stop"
    return ""

def class_to_id(cls):
    key = _normalize_label(cls)
    if not key: return "NA"
    if key.isdigit(): return int(key)
    return BASE_ID_MAP.get(key, "NA")

# ──────────────────────────────────────────────────────────────
# YOLO Inference
# ──────────────────────────────────────────────────────────────
def call_local_yolo(model_path, image_path, conf=0.6, imgsz=640, device=None):
    model = YOLO(model_path)
    results = model.predict(source=image_path, imgsz=imgsz, conf=conf, verbose=False, device=device)
    return results

# ──────────────────────────────────────────────────────────────
# Gallery Helpers
# ──────────────────────────────────────────────────────────────
def save_rep_frame(img_bgr, save_dir, symbol_key):
    """Save individual detection frame."""
    os.makedirs(save_dir, exist_ok=True)
    cv2.imwrite(os.path.join(save_dir, f"{symbol_key}.jpg"), img_bgr)

def make_tiled_gallery(src_dir, out_path, tile_w=360, cols=3, pad=8):
    """Create a tiled gallery from individual frames."""
    files = [os.path.join(src_dir, f) for f in os.listdir(src_dir)
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    if not files:
        return False
    
    # Sort files to maintain order
    files.sort()
    
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
        for c in range(cols):
            if idx >= len(imgs):
                break
            _, im = imgs[idx]
            h, w = im.shape[:2]
            canvas[y:y+h, x:x+w] = im
            x += tile_w + pad
            idx += 1
        y += max_h_per_row[r] + pad
    
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    cv2.imwrite(out_path, canvas)
    return True

# ──────────────────────────────────────────────────────────────
# Drawing + Saving Annotated
# ──────────────────────────────────────────────────────────────
def draw_predictions(image_path, results, conf_thresh=0.6,
                     gallery_dir="./rpi_downloads/annotated/raw_clips",
                     gallery_out="./rpi_downloads/annotated/gallery.jpg"):
    base = cv2.imread(image_path)
    if base is None:
        raise RuntimeError(f"Cannot read {image_path}")
    recognised_ids = []
    detection_counter = {}  # Track how many times each symbol is detected
    os.makedirs(gallery_dir, exist_ok=True)

    for r in results:
        boxes, names = r.boxes, r.names
        if boxes is None or len(boxes) == 0: continue
        for i in range(len(boxes)):
            conf = float(boxes.conf[i].item())
            if conf < conf_thresh: continue
            cls_id = int(boxes.cls[i].item())
            cls_name = names.get(cls_id, str(cls_id))
            obj_id = class_to_id(cls_name)
            pretty = ID_TO_PRETTY.get(obj_id, str(cls_name)) if isinstance(obj_id, int) else str(cls_name)
            
            if obj_id != "NA":
                recognised_ids.append(obj_id)

            x1,y1,x2,y2 = map(int, boxes.xyxy[i].cpu().numpy().tolist())
            
            # Clamp coordinates
            H, W = base.shape[:2]
            x1 = max(0, min(x1, W - 1))
            x2 = max(0, min(x2, W - 1))
            y1 = max(0, min(y1, H - 1))
            y2 = max(0, min(y2, H - 1))
            
            cv2.rectangle(base,(x1,y1),(x2,y2),(0,255,0),2)
            label=f"{obj_id}_{pretty}_{conf:.2f}"
            cv2.putText(base,label,(x1,y1-8),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)
            
            # Save individual frame for EACH detection (even duplicates)
            # Use counter to create unique filenames
            symbol_base = f"{obj_id}_{pretty}"
            
            # Increment counter for this symbol
            if symbol_base not in detection_counter:
                detection_counter[symbol_base] = 0
            detection_counter[symbol_base] += 1
            
            # Create unique filename with counter
            symbol_key = f"{symbol_base}_{detection_counter[symbol_base]:02d}"
            
            # Create individual annotated frame
            single = base.copy()
            cv2.rectangle(single, (x1, y1), (x2, y2), (0, 255, 0), 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            y_top = max(0, y1 - th - 8)
            cv2.rectangle(single, (x1, y_top), (x1 + tw + 6, y1), (0, 255, 0), -1)
            cv2.putText(single, label, (x1 + 3, max(0, y1 - 6)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            save_rep_frame(single, gallery_dir, symbol_key)

    annotated_path = os.path.join(os.path.dirname(gallery_out), os.path.basename(image_path))
    cv2.imwrite(annotated_path, base)
    print(f"[VISION] Annotated saved → {annotated_path}")
    
    # Create tiled gallery if we saved any frames
    if detection_counter:
        total_detections = sum(detection_counter.values())
        success = make_tiled_gallery(gallery_dir, gallery_out)
        if success:
            print(f"[VISION] Tiled gallery saved → {gallery_out} ({total_detections} detections)")
    
    return recognised_ids