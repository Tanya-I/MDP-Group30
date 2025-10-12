"""
bt_message_mapper.py
----------------------------------------
Handles mapping between:
- RPi internal JSON/state format
- Android Bluetooth plain-text format:
    ROBOT, X, Y, DIRECTION
    OBJECT#, X, Y, DIRECTION
    TARGET, OBSTACLE_NUMBER, TARGET_ID
    GRID_COMPLETE
    WEEK8_TASK_DONE / WEEK9_TASK_DONE
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BTMessageMapper:
    """Utility class to map messages between Android and RPi formats"""
    
    # Valid directions
    VALID_DIRECTIONS = {'N', 'S', 'E', 'W', 'UNKNOWN'}
    
    # ==========================================================
    # RPi → Android (send)
    # ==========================================================
    
    @staticmethod
    def format_robot_position(x: int, y: int, direction: str) -> str:
        """Format robot position for Android"""
        if x == -1 and y == -1:
            return "ROBOT, UNKNOWN"
        return f"ROBOT, {x}, {y}, {direction}"
    
    @staticmethod
    def format_object_position(object_id: int, x: int, y: int, direction: str) -> str:
        """Format object position for Android"""
        if x == -1 and y == -1:
            return f"OBJECT{object_id}, UNKNOWN"
        return f"OBJECT{object_id}, {x}, {y}, {direction}"
    
    @staticmethod
    def format_target(obstacle_number: int, target_id: int) -> str:
        """Format target assignment for Android"""
        return f"TARGET, {obstacle_number}, {target_id}"
    
    @staticmethod
    def format_task_done(week: int) -> str:
        """Format task completion message for Android"""
        return f"WEEK{week}_TASK_DONE"
    
    @staticmethod
    def format_grid_complete() -> str:
        """Format grid complete message for Android"""
        return "GRID_COMPLETE"
    
    # ==========================================================
    # Android → RPi (receive)
    # ==========================================================
    
    @staticmethod
    def parse_android_message(msg: str) -> Optional[Dict[str, Any]]:
        """
        Converts Android message → dict
        Returns None if unrecognized.
        
        Examples:
            "ROBOT, 5, 10, N" -> {"type": "robot_pos", "x": 5, "y": 10, "direction": "N"}
            "OBJECT3, 15, 8, E" -> {"type": "object_pos", "object_id": 3, "x": 15, "y": 8, "direction": "E"}
            "TARGET, 2, 15" -> {"type": "target", "obstacle": 2, "target_id": 15}
            "GRID_COMPLETE" -> {"type": "grid_complete"}
            "WEEK8_TASK_DONE" -> {"type": "task_done", "week": 8}
        """
        try:
            msg = msg.strip()
            if not msg:
                return None
            
            # --- Grid Complete (no commas) ---
            if msg.upper() == "GRID_COMPLETE":
                return {"type": "grid_complete"}
            
            parts = [p.strip() for p in msg.split(",")]
            cmd = parts[0].upper()
            
            # --- Robot position ---
            if cmd == "ROBOT":
                if len(parts) == 2 and parts[1].upper() == "UNKNOWN":
                    return {
                        "type": "robot_pos",
                        "x": -1,
                        "y": -1,
                        "direction": "UNKNOWN"
                    }
                elif len(parts) == 4:
                    x, y = int(parts[1]), int(parts[2])
                    direction = parts[3].upper()
                    
                    # Validate
                    if not BTMessageMapper._validate_position(x, y, direction):
                        logger.warning(f"Invalid robot position: {msg}")
                        return None
                    
                    return {
                        "type": "robot_pos",
                        "x": x,
                        "y": y,
                        "direction": direction
                    }
            
            # --- Object position ---
            if cmd.startswith("OBJECT"):
                try:
                    object_id = int(cmd.replace("OBJECT", ""))
                    
                    # Validate object ID (1-8)
                    if object_id < 1 or object_id > 8:
                        logger.warning(f"Invalid object ID: {object_id}")
                        return None
                    
                    if len(parts) == 2 and parts[1].upper() == "UNKNOWN":
                        return {
                            "type": "object_pos",
                            "object_id": object_id,
                            "x": -1,
                            "y": -1,
                            "direction": "UNKNOWN"
                        }
                    elif len(parts) == 4:
                        x, y = int(parts[1]), int(parts[2])
                        direction = parts[3].upper()
                        
                        # Validate
                        if not BTMessageMapper._validate_position(x, y, direction):
                            logger.warning(f"Invalid object position: {msg}")
                            return None
                        
                        return {
                            "type": "object_pos",
                            "object_id": object_id,
                            "x": x,
                            "y": y,
                            "direction": direction
                        }
                except ValueError:
                    logger.warning(f"Cannot extract object ID from: {cmd}")
                    return None
            
            # --- Target mapping ---
            if cmd == "TARGET" and len(parts) == 3:
                obstacle_num = int(parts[1])
                target_id = int(parts[2])
                
                # Validate ranges
                if obstacle_num < 1 or obstacle_num > 8:
                    logger.warning(f"Invalid obstacle number: {obstacle_num}")
                    return None
                if target_id < 1 or target_id > 40:
                    logger.warning(f"Invalid target ID: {target_id}")
                    return None
                
                return {
                    "type": "target",
                    "obstacle": obstacle_num,
                    "target_id": target_id
                }
            
            # --- Task completion ---
            if "WEEK" in cmd and "TASK_DONE" in cmd:
                # Extract week number (WEEK8_TASK_DONE -> 8)
                try:
                    week_str = cmd.replace("WEEK", "").replace("_TASK_DONE", "")
                    week = int(week_str)
                    return {
                        "type": "task_done",
                        "week": week
                    }
                except ValueError:
                    logger.warning(f"Cannot extract week number from: {cmd}")
                    return None
            
            # Unrecognized message
            logger.debug(f"Unrecognized message format: {msg}")
            return None
            
        except Exception as e:
            logger.warning(f"[BTMapper] Parse failed for '{msg}': {e}")
            return None
    
    # ==========================================================
    # Validation helpers
    # ==========================================================
    
    @staticmethod
    def _validate_position(x: int, y: int, direction: str) -> bool:
        """Validate coordinates and direction"""
        # Check coordinate range (0-19 or -1 for unknown)
        if not ((0 <= x <= 19) or x == -1):
            return False
        if not ((0 <= y <= 19) or y == -1):
            return False
        
        # Check direction
        if direction not in BTMessageMapper.VALID_DIRECTIONS:
            return False
        
        return True
    
    # ==========================================================
    # Convenience methods for obstacle data conversion
    # ==========================================================
    
    @staticmethod
    def obstacles_to_android_format(obstacles: list) -> list:
        """
        Convert RPi obstacle list to Android format messages
        
        Input: [{"id": 1, "x": 5, "y": 10, "face": "N", "image_id": 15}, ...]
        Output: ["OBJECT1, 5, 10, N", "TARGET, 1, 15", ...]
        """
        messages = []
        for obs in obstacles:
            # Position message
            pos_msg = BTMessageMapper.format_object_position(
                obs['id'],
                obs.get('x', -1),
                obs.get('y', -1),
                obs.get('face', 'UNKNOWN')
            )
            messages.append(pos_msg)
            
            # Target message (if identified)
            if obs.get('image_id') is not None:
                target_msg = BTMessageMapper.format_target(
                    obs['id'],
                    obs['image_id']
                )
                messages.append(target_msg)
        
        return messages
    
    @staticmethod
    def android_obstacles_to_rpi_format(messages: list) -> list:
        """
        Convert Android format messages to RPi obstacle list
        
        Input: ["OBJECT1, 5, 10, N", "TARGET, 1, 15", ...]
        Output: [{"id": 1, "x": 5, "y": 10, "face": "N", "image_id": 15}, ...]
        """
        obstacles = {}
        
        for msg in messages:
            parsed = BTMessageMapper.parse_android_message(msg)
            if not parsed:
                continue
            
            if parsed['type'] == 'object_pos':
                obj_id = parsed['object_id']
                if obj_id not in obstacles:
                    obstacles[obj_id] = {'id': obj_id, 'image_id': None}
                
                obstacles[obj_id]['x'] = parsed['x']
                obstacles[obj_id]['y'] = parsed['y']
                obstacles[obj_id]['face'] = parsed['direction']
            
            elif parsed['type'] == 'target':
                obj_id = parsed['obstacle']
                if obj_id not in obstacles:
                    obstacles[obj_id] = {'id': obj_id}
                
                obstacles[obj_id]['image_id'] = parsed['target_id']
        
        return list(obstacles.values())
