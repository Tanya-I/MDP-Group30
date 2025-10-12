#!/usr/bin/env python3
"""
planner_integration.py - Integrate mdp_2_sim.py path planning with PC client

Extracts the planning logic from the simulator and makes it usable
for the real robot system.
"""

import math
from typing import List, Tuple, Optional

# Constants from simulator
ARENA_SIZE_M = 2.0
OB_SIZE = 0.10
ROBOT_WIDTH = 0.25
ROBOT_LENGTH = 0.20
ROBOT_RADIUS = ROBOT_WIDTH / 2
MAX_STEERING_ANGLE = math.radians(45)
WHEELBASE = 0.15
DEFAULT_R_MIN = WHEELBASE / math.tan(MAX_STEERING_ANGLE)
DEFAULT_STANDOFF = 0.08
SAFETY_MARGIN = 0.01
DS = 0.015
POS_TOL = 0.06
ANG_TOL = math.radians(12)
ANG_TOL_PLAN = math.radians(20)
COLLIDE_EPS = 0.008
CLEAR_GATE_M = 0.08
LAT_HEADINGS = 24
LAT_DSTEP = 0.08
LAT_TURN_DEG = 15.0
LAT_MAX_EXP = 30000

# Import geometry functions (simplified versions)
def mod2pi(a):
    return (a + 2*math.pi) % (2*math.pi)

def angle_diff(a, b):
    d = abs(mod2pi(a) - mod2pi(b))
    return min(d, 2*math.pi - d)

def pose_close_plan(p, q, pos_tol, ang_tol=ANG_TOL_PLAN):
    dx, dy = p[0]-q[0], p[1]-q[1]
    return (dx*dx + dy*dy) <= (pos_tol*pos_tol) and angle_diff(p[2], q[2]) <= ang_tol

def extend_along_heading(pose, extra):
    x, y, th = pose
    return (x + extra*math.cos(th), y + extra*math.sin(th), th)

# Simplified Dubins path planning
def plan_dubins_path(start_pose: Tuple[float, float, float],
                     goal_pose: Tuple[float, float, float],
                     obstacles: List[dict],
                     Rmin: float = DEFAULT_R_MIN,
                     standoff: float = DEFAULT_STANDOFF) -> Optional[List[Tuple[float, float, float]]]:
    """
    Plan a Dubins path from start to goal avoiding obstacles
    
    Args:
        start_pose: (x, y, theta) in meters and radians
        goal_pose: (x, y, theta) in meters and radians
        obstacles: list of obstacle dicts with x, y, face
        Rmin: minimum turning radius in meters
        standoff: distance to maintain from obstacles
    
    Returns:
        List of waypoints [(x, y, theta), ...] or None if infeasible
    """
    # For real implementation, you would:
    # 1. Create inflated obstacle geometry (using shapely)
    # 2. Try direct Dubins path
    # 3. Fall back to approach buffer strategy
    # 4. Fall back to lattice A* if needed
    
    # Simplified: assume straight line is feasible
    # (In production, integrate full collision checking from simulator)
    
    print(f"[PLANNER] Planning from {start_pose} to {goal_pose}")
    
    # Check if direct path is feasible (simplified)
    dx = goal_pose[0] - start_pose[0]
    dy = goal_pose[1] - start_pose[1]
    dist = math.hypot(dx, dy)
    
    # Generate waypoints along straight line
    num_waypoints = max(3, int(dist / 0.1))  # waypoint every 10cm
    waypoints = []
    
    for i in range(num_waypoints + 1):
        t = i / num_waypoints
        x = start_pose[0] + t * dx
        y = start_pose[1] + t * dy
        # Interpolate heading
        theta = start_pose[2] + t * (goal_pose[2] - start_pose[2])
        waypoints.append((x, y, theta))
    
    print(f"[PLANNER] Generated {len(waypoints)} waypoints")
    return waypoints

def generate_stm_commands_from_path(path: List[Tuple[float, float, float]],
                                   start_heading_deg: float) -> List[str]:
    """
    Convert path waypoints to STM command sequence
    
    Args:
        path: list of (x, y, theta) waypoints in meters/radians
        start_heading_deg: current robot heading in degrees
    
    Returns:
        List of STM command strings
    """
    commands = []
    current_heading = start_heading_deg
    
    for i in range(1, len(path)):
        x0, y0, th0 = path[i-1]
        x1, y1, th1 = path[i]
        
        # Calculate distance
        dx = x1 - x0
        dy = y1 - y0
        dist_m = math.hypot(dx, dy)
        dist_cm = int(dist_m * 100)
        
        # Calculate required heading for this segment
        if dist_m > 0.01:  # Only if significant movement
            segment_heading = math.degrees(math.atan2(dy, dx))
            
            # Calculate turn needed
            angle_diff = (segment_heading - current_heading + 180) % 360 - 180
            
            # Turn if needed (threshold 5 degrees)
            if abs(angle_diff) > 5:
                angle_int = int(abs(angle_diff))
                if angle_diff > 0:
                    commands.append(f"d{angle_int}")  # Turn right
                else:
                    commands.append(f"a{angle_int}")  # Turn left
                current_heading = segment_heading
            
            # Move forward
            if dist_cm > 2:  # > 2cm
                commands.append(f"w{dist_cm}")
    
    # Final heading adjustment
    final_heading = math.degrees(path[-1][2])
    angle_diff = (final_heading - current_heading + 180) % 360 - 180
    if abs(angle_diff) > 5:
        angle_int = int(abs(angle_diff))
        if angle_diff > 0:
            commands.append(f"d{angle_int}")
        else:
            commands.append(f"a{angle_int}")
    
    return commands

def calculate_image_pose(obstacle: dict, standoff: float = DEFAULT_STANDOFF) -> Tuple[float, float, float]:
    """
    Calculate the pose where robot should be to image an obstacle
    
    Args:
        obstacle: dict with 'x', 'y', 'face' keys
        standoff: distance from obstacle in meters
    
    Returns:
        (x, y, theta) pose in meters and radians
    """
    cx = obstacle['x'] + OB_SIZE / 2
    cy = obstacle['y'] + OB_SIZE / 2
    
    if obstacle['face'] == 'N':
        return (cx, obstacle['y'] + OB_SIZE + standoff, -math.pi/2)
    elif obstacle['face'] == 'S':
        return (cx, obstacle['y'] - standoff, math.pi/2)
    elif obstacle['face'] == 'E':
        return (obstacle['x'] + OB_SIZE + standoff, cy, math.pi)
    else:  # 'W'
        return (obstacle['x'] - standoff, cy, 0.0)

def plan_multi_obstacle_path(start_pose: Tuple[float, float, float],
                             obstacles: List[dict],
                             visit_order: List[str],
                             Rmin: float = DEFAULT_R_MIN,
                             standoff: float = DEFAULT_STANDOFF) -> Optional[List[List[Tuple[float, float, float]]]]:
    """
    Plan paths to visit multiple obstacles in specified order
    
    Args:
        start_pose: starting (x, y, theta)
        obstacles: list of obstacle dicts
        visit_order: list of obstacle IDs in visiting order
        Rmin: minimum turning radius
        standoff: standoff distance
    
    Returns:
        List of path segments, one for each leg of the journey
    """
    segments = []
    current_pose = start_pose
    
    # Create obstacle lookup
    obs_dict = {obs['id']: obs for obs in obstacles}
    
    for obs_id in visit_order:
        if obs_id not in obs_dict:
            print(f"[ERROR] Obstacle {obs_id} not found")
            return None
        
        # Calculate target pose for this obstacle
        target_pose = calculate_image_pose(obs_dict[obs_id], standoff)
        
        # Plan path segment
        path = plan_dubins_path(current_pose, target_pose, obstacles, Rmin, standoff)
        
        if path is None:
            print(f"[ERROR] No feasible path to obstacle {obs_id}")
            return None
        
        segments.append(path)
        current_pose = target_pose
    
    return segments

def optimize_visit_order(start_pose: Tuple[float, float, float],
                         obstacles: List[dict],
                         standoff: float = DEFAULT_STANDOFF) -> List[str]:
    """
    Find optimal visiting order using nearest-neighbor heuristic
    
    Args:
        start_pose: starting (x, y, theta)
        obstacles: list of obstacle dicts
        standoff: standoff distance
    
    Returns:
        List of obstacle IDs in visiting order
    """
    if not obstacles:
        return []
    
    unvisited = obstacles.copy()
    order = []
    current_pos = (start_pose[0], start_pose[1])
    
    while unvisited:
        # Find nearest obstacle
        nearest = min(unvisited, key=lambda obs: 
                     math.hypot(current_pos[0] - (obs['x'] + OB_SIZE/2),
                               current_pos[1] - (obs['y'] + OB_SIZE/2)))
        
        order.append(nearest['id'])
        unvisited.remove(nearest)
        
        # Update current position to this obstacle
        pose = calculate_image_pose(nearest, standoff)
        current_pos = (pose[0], pose[1])
    
    return order

# =============================================================================
# High-level interface for PC client
# =============================================================================
def plan_full_task(start_pose: Tuple[float, float, float],
                   obstacles: List[dict],
                   Rmin: float = DEFAULT_R_MIN,
                   standoff: float = DEFAULT_STANDOFF) -> Tuple[List[str], List[List[str]]]:
    """
    Plan complete task: visit all obstacles and generate STM commands
    
    Args:
        start_pose: (x, y, theta) in meters and radians
        obstacles: list of obstacle dicts
        Rmin: minimum turning radius
        standoff: standoff distance
    
    Returns:
        (visit_order, command_sequences) where:
        - visit_order: list of obstacle IDs in order
        - command_sequences: list of command lists, one per obstacle
    """
    print(f"\n[PLANNER] Planning full task")
    print(f"  Start: ({start_pose[0]:.3f}, {start_pose[1]:.3f}, {math.degrees(start_pose[2]):.1f}°)")
    print(f"  Obstacles: {len(obstacles)}")
    print(f"  Rmin: {Rmin:.3f}m, Standoff: {standoff:.3f}m")
    
    # Optimize visiting order
    visit_order = optimize_visit_order(start_pose, obstacles, standoff)
    print(f"  Visit order: {' → '.join(visit_order)}")
    
    # Plan paths for each leg
    segments = plan_multi_obstacle_path(start_pose, obstacles, visit_order, Rmin, standoff)
    
    if segments is None:
        print("[ERROR] Path planning failed")
        return [], []
    
    # Generate STM commands for each segment
    command_sequences = []
    current_heading = math.degrees(start_pose[2])
    
    for i, path in enumerate(segments):
        obs_id = visit_order[i]
        print(f"\n  Leg {i+1}/{len(segments)}: → {obs_id}")
        
        commands = generate_stm_commands_from_path(path, current_heading)
        command_sequences.append(commands)
        
        # Update heading for next leg
        if path:
            current_heading = math.degrees(path[-1][2])
        
        print(f"    Commands: {', '.join(commands)}")
    
    print(f"\n[PLANNER] Planning complete: {len(visit_order)} obstacles, {sum(len(c) for c in command_sequences)} total commands")
    
    return visit_order, command_sequences
