#!/usr/bin/env python3
"""
rpi_server_with_bluetooth.py - Server with Bluetooth obstacle input

Modified version that receives obstacles from Android via Bluetooth
instead of using preset hardcoded values.
Used for Task 1. 

Usage:
    python rpi_server_with_bluetooth.py
"""

import socket
import json
import threading
import time
import serial
import io
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging
from bluetooth import BluetoothSocket, RFCOMM
from bt_message_mapper_2 import BTMessageMapper

import cv2

# Check if an OpenCV camera can be opened
cap_test = cv2.VideoCapture(0)
if cap_test.isOpened():
    CAMERA_AVAILABLE = True
    cap_test.release()
    print("[INFO] OpenCV camera detected and available.")
else:
    CAMERA_AVAILABLE = False
    print("[WARN] No OpenCV camera detected using mock camera.")


# =============================================================================
# Configuration
# =============================================================================
WLAN_HOST = '0.0.0.0'
WLAN_PORT = 5000
STM_PORT = '/dev/ttyACM0'
STM_BAUD = 115200
TASK_TIMEOUT = 300

# Bluetooth configuration
BT_CHANNEL = 1

# =============================================================================
# Logging Setup
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Global State
# =============================================================================
class RobotState:
    def __init__(self):
        # Start with empty obstacles - will be populated via Bluetooth
        self.obstacles = []
        self.robot_pos = {'x': 0.1, 'y': 0.125, 'heading': 90}
        self.task_start_time = None
        self.task_active = False
        self.last_stm_response = None
        self.identified_count = 0
        self.lock = threading.Lock()
        self.obstacles_ready = False
        self.grid_locked = False  # Lock grid after GRID_COMPLETE
        
        logger.info("Initialized with empty obstacles (waiting for Bluetooth)")
        
    def update_robot_pos(self, heading, x, y):
        with self.lock:
            self.robot_pos['heading'] = heading
            self.robot_pos['x'] = x / 100.0
            self.robot_pos['y'] = y / 100.0
            logger.info(f"Robot pos updated: {self.robot_pos}")
            
            # Send position update to Android via Bluetooth
            # Convert heading to direction (N/S/E/W)
            direction = self._heading_to_direction(heading)
            return (x, y, direction)
    
    def _heading_to_direction(self, heading):
        """Convert heading (0-360) to direction (N/S/E/W)"""
        # Normalize heading to 0-360
        heading = heading % 360
        
        # Map heading to nearest cardinal direction
        if 45 <= heading < 135:
            return 'E'
        elif 135 <= heading < 225:
            return 'S'
        elif 225 <= heading < 315:
            return 'W'
        else:  # 315-360 or 0-45
            return 'N'
    
    def add_or_update_obstacle(self, parsed_data):
        """
        Add or update obstacle from Android Bluetooth message
        
        Input: {'type': 'object_pos', 'object_id': 2, 'x': 10, 'y': 6, 'direction': 'N'}
        Converts to: {'id': '2', 'x': 0.60, 'y': 0.30, 'face': 'N', 'image_id': None}
        
        Note: Converts Android grid coordinates (0-19) to meters (multiply by 0.1m)
        Updates are allowed until GRID_COMPLETE is received
        """
        with self.lock:
            # Don't accept updates after grid is locked
            if self.grid_locked:
                logger.warning(f"Grid locked - ignoring obstacle update: {parsed_data}")
                return False
            
            obj_id = str(parsed_data['object_id'])
            x_meters = parsed_data['x'] * 0.1  # Convert grid units to meters
            y_meters = parsed_data['y'] * 0.1
            direction = parsed_data['direction']
            
            # Check if obstacle already exists
            existing = None
            for obs in self.obstacles:
                if obs['id'] == obj_id:
                    existing = obs
                    break
            
            if existing:
                # Update existing obstacle with latest values
                existing['x'] = x_meters
                existing['y'] = y_meters
                existing['face'] = direction
                logger.info(f"Updated obstacle {obj_id}: ({x_meters:.2f}m, {y_meters:.2f}m) facing {direction}")
            else:
                # Add new obstacle
                new_obstacle = {
                    'id': obj_id,
                    'x': x_meters,
                    'y': y_meters,
                    'face': direction,
                    'image_id': None
                }
                self.obstacles.append(new_obstacle)
                logger.info(f"Added obstacle {obj_id}: ({x_meters:.2f}m, {y_meters:.2f}m) facing {direction}")
            
            # Sort obstacles by ID for consistency
            self.obstacles.sort(key=lambda o: int(o['id']))
            return True
    
    def update_obstacle_target(self, parsed_data):
        """
        Update obstacle with target/image_id from Android
        
        Input: {'type': 'target', 'obstacle': 1, 'target_id': 15}
        """
        with self.lock:
            obj_id = str(parsed_data['obstacle'])
            target_id = parsed_data['target_id']
            
            for obs in self.obstacles:
                if obs['id'] == obj_id:
                    obs['image_id'] = target_id
                    logger.info(f"Obstacle {obj_id} assigned target {target_id}")
                    return True
            
            logger.warning(f"Cannot assign target - obstacle {obj_id} not found")
            return False
    
    def update_obstacle_image(self, obstacle_id, image_id):
        """Update obstacle with identified image_id (from PC image recognition)"""
        with self.lock:
            for obs in self.obstacles:
                if obs['id'] == obstacle_id:
                    obs['image_id'] = image_id
                    self.identified_count += 1
                    logger.info(f"Obstacle {obstacle_id} identified as {image_id}")
                    return True
        return False
    
    def set_obstacles_ready(self):
        """Mark that all obstacles have been received from Android (GRID_COMPLETE)"""
        with self.lock:
            self.obstacles_ready = True
            self.grid_locked = True  # Lock grid - no more updates allowed
            logger.info(f"GRID_COMPLETE received! Grid locked with {len(self.obstacles)} obstacles")
            logger.info("\n" + "="*70)
            logger.info("FINAL GRID - READY FOR ALGORITHM:")
            for obs in self.obstacles:
                target_info = f" -> Target {obs['image_id']}" if obs['image_id'] else ""
                logger.info(f"  Obstacle {obs['id']}: ({obs['x']:.2f}m, {obs['y']:.2f}m) facing {obs['face']}{target_info}")
            logger.info("="*70 + "\n")
    
    def clear_obstacles(self):
        """Clear all obstacles (for starting fresh)"""
        with self.lock:
            self.obstacles = []
            self.obstacles_ready = False
            self.grid_locked = False  # Unlock grid for new obstacle input
            logger.info("Obstacles cleared - ready for new grid")
    
    def get_state_dict(self):
        with self.lock:
            return {
                'obstacles': self.obstacles.copy(),
                'robot_pos': self.robot_pos.copy(),
                'task_active': self.task_active,
                'identified_count': self.identified_count,
                'obstacles_ready': self.obstacles_ready,
                'grid_locked': self.grid_locked,
                'elapsed_time': time.time() - self.task_start_time if self.task_start_time else 0
            }

state = RobotState()

# =============================================================================
# Bluetooth Server
# =============================================================================
class BluetoothServer:
    def __init__(self):
        self.server_sock = None
        self.client_sock = None
        self.client_info = None
        self.running = False
        self.connected = False
        self.lock = threading.Lock()
        
    def start(self):
        """Start Bluetooth server in separate thread"""
        self.running = True
        thread = threading.Thread(target=self._server_loop, daemon=True)
        thread.start()
        logger.info("Bluetooth server thread started")
    
    def _server_loop(self):
        """Main Bluetooth server loop"""
        try:
            self.server_sock = BluetoothSocket(RFCOMM)
            self.server_sock.bind(("", BT_CHANNEL))
            self.server_sock.listen(1)
            
            port = self.server_sock.getsockname()[1]
            logger.info(f"Bluetooth server listening on RFCOMM channel {port}")
            logger.info("Waiting for Android to connect...")
            
            while self.running:
                try:
                    # Accept connection
                    client_sock, client_info = self.server_sock.accept()
                    
                    with self.lock:
                        self.client_sock = client_sock
                        self.client_info = client_info
                        self.connected = True
                    
                    logger.info(f"Android connected: {client_info}")
                    
                    # Handle messages from this client
                    self._handle_client(client_sock)
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"Bluetooth accept error: {e}")
                        time.sleep(1)
                        
        except Exception as e:
            logger.error(f"Bluetooth server error: {e}")
        finally:
            self._cleanup()
    
    def _handle_client(self, client_sock):
        """Handle messages from connected Android client"""
        try:
            while self.running and self.connected:
                data = client_sock.recv(1024).decode("utf-8")
                
                if not data:
                    logger.info("Android disconnected")
                    break
                
                # Process each message
                for msg in data.strip().split('\n'):
                    msg = msg.strip()
                    if not msg:
                        continue
                    
                    logger.info(f"[Android → RPi] Raw: {msg}")
                    
                    # Parse message using mapper
                    parsed = BTMessageMapper.parse_android_message(msg)
                    if parsed:
                        logger.info(f"[Android → RPi] Parsed: {parsed}")
                        self._process_message(parsed)
                    else:
                        logger.warning(f"[Android → RPi] Failed to parse: {msg}")
                        
        except OSError:
            logger.info("Android connection lost")
        except Exception as e:
            logger.error(f"Bluetooth receive error: {e}")
        finally:
            with self.lock:
                self.connected = False
            self._close_client()
    
    def _process_message(self, parsed):
        """Process parsed message and update state"""
        msg_type = parsed.get('type')
        
        if msg_type == 'object_pos':
            # Add/update obstacle position (allows updates until GRID_COMPLETE)
            state.add_or_update_obstacle(parsed)
            
        elif msg_type == 'target':
            # Update obstacle with target ID
            state.update_obstacle_target(parsed)
            
        elif msg_type == 'robot_pos':
            # Update robot position (if needed)
            logger.info(f"Received robot position: {parsed}")
        
        elif msg_type == 'grid_complete':
            # Lock grid and mark ready for algorithm
            state.set_obstacles_ready()
            # No need for extra log since set_obstacles_ready() already logs
            
        else:
            logger.warning(f"Unknown message type: {msg_type}")
    
    def send_message(self, msg):
        """Send message to Android"""
        with self.lock:
            if self.connected and self.client_sock:
                try:
                    self.client_sock.send(f"{msg}\n".encode("utf-8"))
                    logger.info(f"[RPi → Android] Sent: {msg}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to send to Android: {e}")
                    return False
        return False
    
    def _close_client(self):
        """Close client connection"""
        if self.client_sock:
            try:
                self.client_sock.close()
            except:
                pass
            self.client_sock = None
            logger.info("Client connection closed")
    
    def _cleanup(self):
        """Cleanup server resources"""
        self._close_client()
        if self.server_sock:
            try:
                self.server_sock.close()
            except:
                pass
            logger.info("Bluetooth server closed")
    
    def stop(self):
        """Stop Bluetooth server"""
        self.running = False
        self._cleanup()

bt_server = BluetoothServer()

# =============================================================================
# STM Serial Communication
# =============================================================================
class STMComm:
    def __init__(self, port=STM_PORT, baud=STM_BAUD):
        self.port = port
        self.baud = baud
        self.ser = None
        self.response_buffer = ""
        self.response_ready = threading.Event()
        self.lock = threading.Lock()
        
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)
            logger.info(f"Connected to STM on {self.port} @ {self.baud}")
            threading.Thread(target=self._listen_responses, daemon=True).start()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to STM: {e}")
            return False
    
    def _listen_responses(self):
        while self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('ascii', errors='ignore').strip()
                    if line:
                        logger.info(f"STM << {line}")
                        self._process_response(line)
            except Exception as e:
                logger.error(f"Error reading STM: {e}")
            time.sleep(0.01)
    
    def _process_response(self, line):
        try:
            parts = line.split(',')
            if len(parts) == 3:
                heading = int(parts[0].strip())
                x_cm = int(parts[1].strip())
                y_cm = int(parts[2].strip())
                
                # Update state and get position info
                pos_info = state.update_robot_pos(heading, x_cm, y_cm)
                
                # Send position update to Android via Bluetooth
                # Convert cm to grid coordinates (divide by 10 to get grid units)
                if pos_info:
                    x_val, y_val, direction = pos_info
                    x_grid = int(x_val / 10)  # Convert cm to grid units (0-19)
                    y_grid = int(y_val / 10)
                    msg = BTMessageMapper.format_robot_position(x_grid, y_grid, direction)
                    bt_server.send_message(msg)
                
                with self.lock:
                    self.response_buffer = line
                    self.response_ready.set()
        except Exception as e:
            logger.warning(f"Failed to parse STM response: {line} - {e}")
    
    def send_command(self, cmd, timeout=120):
        if not self.ser or not self.ser.is_open:
            logger.error("STM not connected")
            return None
        
        try:
            self.response_ready.clear()
            msg = f"{cmd}\n"
            self.ser.write(msg.encode('ascii'))
            logger.info(f"STM >> {cmd}")
            
            if self.response_ready.wait(timeout):
                with self.lock:
                    return self.response_buffer
            else:
                logger.error(f"STM command timeout: {cmd}")
                return None
        except Exception as e:
            logger.error(f"Error sending STM command: {e}")
            return None
    
    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("STM connection closed")

stm = STMComm()

# =============================================================================
# Camera Interface
# =============================================================================
class CameraInterface:
    def __init__(self):
        """Initialize camera - just verify it exists, don't keep it open"""
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("[ERROR] Could not open camera. Check connection or enable via raspi-config.")
            self.available = False
        else:
            logger.info("[INFO] OpenCV camera initialized successfully.")
            self.available = True
        cap.release()

    def capture_image(self):
        """Capture one fresh frame and return as base64 JPEG."""
        if not self.available:
            logger.warning("[WARN] Camera not available, returning mock image.")
            mock_jpeg = base64.b64encode(b'\xff\xd8\xff\xe0\x00\x10JFIF').decode('utf-8')
            return mock_jpeg
            
        try:
            # Open camera fresh for each capture
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.error("[ERROR] Could not open camera for capture.")
                return None

            # Allow camera to warm up and auto-expose
            time.sleep(0.3)

            # Flush buffer by reading a few frames
            for _ in range(3):
                cap.read()
            
            # Capture the actual frame
            success, frame = cap.read()
            
            # Release immediately
            cap.release()

            if not success:
                logger.warning("[WARN] Failed to read new frame.")
                return None

            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                logger.error("[ERROR] JPEG encoding failed.")
                return None

            # Convert to base64
            img_b64 = base64.b64encode(buffer).decode('utf-8')
            logger.info(f"[INFO] Captured OpenCV frame ({len(buffer)} bytes).")
            return img_b64

        except Exception as e:
            logger.error(f"[ERROR] OpenCV capture failed: {e}")
            return None

    def close(self):
        """Cleanup - nothing to do since we don't keep camera open"""
        logger.info("Camera interface closed.")

camera = CameraInterface()

# =============================================================================
# HTTP Server for PC Communication
# =============================================================================
class RPIRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == '/status':
            self._send_json(state.get_state_dict())
        
        elif parsed.path == '/obstacles':
            self._send_json({'obstacles': state.obstacles})
        
        elif parsed.path == '/bt_status':
            self._send_json({
                'connected': bt_server.connected,
                'client_info': str(bt_server.client_info) if bt_server.client_info else None
            })
        
        else:
            self._send_json({'error': 'Unknown endpoint'}, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({'error': 'Invalid JSON'}, 400)
            return
        
        parsed = urlparse(self.path)
        
        if parsed.path == '/start_task':
            state.task_start_time = time.time()
            state.task_active = True
            state.identified_count = 0
            logger.info("Task started")
            self._send_json({'status': 'started'})
        
        elif parsed.path == '/stm_command':
            cmd = data.get('command', '')
            if not cmd:
                self._send_json({'error': 'No command provided'}, 400)
                return
            
            response = stm.send_command(cmd)
            if response:
                self._send_json({'status': 'ok', 'response': response})
            else:
                self._send_json({'status': 'timeout'}, 408)
        
        elif parsed.path == '/capture':
            obstacle_id = data.get('obstacle_id')
            img_b64 = camera.capture_image()
            
            if img_b64:
                self._send_json({
                    'status': 'ok',
                    'obstacle_id': obstacle_id,
                    'image': img_b64
                })
            else:
                self._send_json({'status': 'error', 'message': 'Capture failed'}, 500)
        
        elif parsed.path == '/update_image':
            obstacle_id = data.get('obstacle_id')
            image_id = data.get('image_id')
            
            if state.update_obstacle_image(obstacle_id, image_id):
                # Send target update to Android
                bt_server.send_message(
                    BTMessageMapper.format_target(int(obstacle_id), image_id)
                )
                self._send_json({'status': 'ok'})
            else:
                self._send_json({'error': 'Obstacle not found'}, 404)
        
        elif parsed.path == '/stop_task':
            state.task_active = False
            elapsed = time.time() - state.task_start_time if state.task_start_time else 0
            logger.info(f"Task stopped. Elapsed: {elapsed:.1f}s, Identified: {state.identified_count}")
            self._send_json({'status': 'stopped', 'elapsed': elapsed})
        
        elif parsed.path == '/clear_obstacles':
            state.clear_obstacles()
            self._send_json({'status': 'ok', 'message': 'Obstacles cleared'})
        
        else:
            self._send_json({'error': 'Unknown endpoint'}, 404)

def start_http_server():
    server = HTTPServer((WLAN_HOST, WLAN_PORT), RPIRequestHandler)
    logger.info(f"HTTP server listening on {WLAN_HOST}:{WLAN_PORT}")
    server.serve_forever()

# =============================================================================
# Task Monitor
# =============================================================================
def task_monitor():
    while True:
        if state.task_active and state.task_start_time:
            elapsed = time.time() - state.task_start_time
            if elapsed > TASK_TIMEOUT:
                logger.warning(f"Task timeout ({TASK_TIMEOUT}s exceeded)")
                state.task_active = False
                stm.send_command('s')
        time.sleep(1)

# =============================================================================
# Main
# =============================================================================
# =============================================================================
# Main
# =============================================================================
def main():
    logger.info("=== RPI MDP Server (BLUETOOTH MODE) ===")
    logger.info("Waiting for obstacles from Android via Bluetooth...")

    # Connect to STM
    if not stm.connect():
        logger.error("Failed to connect to STM, exiting")
        return

    # Start Bluetooth server
    bt_server.start()

    # Start task monitor
    threading.Thread(target=task_monitor, daemon=True).start()

    # Start HTTP server in a background thread
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    try:
        # Keep main thread alive (acts as supervisor)
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n[Main] Keyboard interrupt detected, shutting down gracefully...")

    except Exception as e:
        logger.error(f"[Main] Unexpected error: {e}", exc_info=True)

    finally:
        # Ensure all components shut down cleanly
        bt_server.stop()
        stm.close()
        camera.close()
        logger.info("[Main] Shutdown complete")

if __name__ == '__main__':
    main()