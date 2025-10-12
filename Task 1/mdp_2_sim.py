#!/usr/bin/env python3
"""
mdp_simulator.py – Forward-only (Dubins) planner with robust lattice fallback and troubleshooting.

Controls
  P : plan (non-blocking)        A : animate          E : execute (simulate-only safe)
  T : toggle simulate-only       G : toggle grid      O : probe feasibility (no DP)
  N : add obstacle at mouse      Del/Backspace : remove nearest obstacle
  LMB drag: move obstacle        RMB click: rotate face (N/E/S/W)

Tuning
  + / -  : Rmin tighter/looser
  [ / ]  : inflation radius (robot) -/+
  ; / '  : standoff -/+
  , / .  : position tolerance -/+
  < / >  : angle tolerance -/+

Requires: pygame, shapely (pyserial optional)
"""

import pygame, math, time, argparse, heapq
from dataclasses import dataclass
try:
    import serial
except Exception:
    serial = None
from shapely.geometry import Polygon, MultiPolygon, LineString, Point
from shapely.ops import unary_union

# -------------------
# Config (defaults)
# -------------------
ARENA_SIZE_M = 2.0
OB_SIZE      = 0.10

# Robot physical dimensions (Ackermann vehicle)
ROBOT_WIDTH  = 0.25   # 25cm width (side-to-side)
ROBOT_LENGTH = 0.20   # 20cm length (front-to-back)
# For inflation, use half the width (radius of inscribed circle)
# This is more conservative than the diagonal
ROBOT_RADIUS = ROBOT_WIDTH / 2  # 12.5cm radius for collision checking

# Ackermann steering constraints
MAX_STEERING_ANGLE = math.radians(45)  # Maximum wheel angle
WHEELBASE = 0.15  # Distance between front and rear axle (approximate, ~75% of length)

# Calculate minimum turning radius from Ackermann geometry
# R_min = wheelbase / tan(max_steering_angle)
DEFAULT_R_MIN = WHEELBASE / math.tan(MAX_STEERING_ANGLE)  # ≈0.15m

DEFAULT_STANDOFF      = 0.08
DEFAULT_ROBOT_RADIUS  = ROBOT_RADIUS  # Use actual robot size
SAFETY_MARGIN         = 0.01  # Additional safety buffer

WIN_W, WIN_H = 1280, 860
M2PX         = 360
FPS          = 60
PHOTO_PAUSE  = 0.5

# Sampling + tolerances
DS       = 0.015  # FIXED: Reduced from 0.02 for smoother paths
POS_TOL  = 0.06
ANG_TOL  = math.radians(12)
ANG_TOL_PLAN = math.radians(20)

# Start zone - robot starts with right back wheel at origin
# Robot center needs to be offset by half-width right and half-length forward
START_ZONE = (0.0, 0.0, 0.40, 0.40)
START_OFFSET_X = ROBOT_WIDTH / 2   # Half width to the right
START_OFFSET_Y = ROBOT_LENGTH / 2  # Half length forward
START = (START_OFFSET_X, START_OFFSET_Y, math.pi/2)  # Facing North (+Y axis)

# Collision tolerance
COLLIDE_EPS   = 0.008   # FIXED: Increased from 0.003 to 8mm
CLEAR_GATE_M  = 0.08    # FIXED: Increased from 0.06

# Lattice fallback (forward-only) parameters
LAT_HEADINGS = 24                  # FIXED: Reduced from 36 for faster search
LAT_DSTEP    = 0.08                # FIXED: Increased from 0.06 for coarser search
LAT_TURN_DEG = 15.0
LAT_MAX_EXP  = 30000               # FIXED: Increased from 20000

# Colors
C_BG      = (16, 17, 20)
C_BORDER  = (120,120,120)
C_GRID    = (46, 48, 53)
C_AXES    = (90, 95, 105)
C_START   = (120,180,255)
C_INFL    = (250, 86, 86)
C_PATH    = (0, 200, 120)
C_TEXT    = (230,230,255)
C_OB      = (64,64,64)
C_WARN    = (255,200,80)
C_ERR     = (255,120,120)

# -------------------
# Model
# -------------------
@dataclass
class Obstacle:
    id: str
    x: float
    y: float
    face: str  # 'N','E','S','W'
    def rect(self):
        return Polygon([(self.x,self.y),
                        (self.x+OB_SIZE,self.y),
                        (self.x+OB_SIZE,self.y+OB_SIZE),
                        (self.x,self.y+OB_SIZE)])
    def center(self):
        return (self.x + OB_SIZE/2, self.y + OB_SIZE/2)
    def image_pose(self, standoff: float):
        cx, cy = self.center()
        if self.face == 'N': return (cx, self.y + OB_SIZE + standoff, -math.pi/2)
        if self.face == 'S': return (cx, self.y - standoff,  math.pi/2)
        if self.face == 'E': return (self.x + OB_SIZE + standoff, cy, math.pi)
        return (self.x - standoff, cy, 0.0)

def inflate_obstacles(obs, robot_radius):
    if not obs:
        return Polygon()
    polys = [o.rect() for o in obs]
    # FIXED: Now properly uses positive margin
    buffer_dist = robot_radius + SAFETY_MARGIN
    return unary_union(polys).buffer(max(0.0, buffer_dist), join_style=2)

# -------------------
# Geometry helpers
# -------------------
def mod2pi(a): return (a + 2*math.pi) % (2*math.pi)
def angle_diff(a,b):
    d = abs(mod2pi(a)-mod2pi(b))
    return min(d, 2*math.pi - d)
def pose_close(p,q,pos_tol=POS_TOL,ang_tol=ANG_TOL):
    dx,dy = p[0]-q[0], p[1]-q[1]
    return (dx*dx+dy*dy) <= (pos_tol*pos_tol) and angle_diff(p[2], q[2]) <= ang_tol
def pose_close_plan(p,q,pos_tol,ang_tol=ANG_TOL_PLAN):
    dx,dy = p[0]-q[0], p[1]-q[1]
    return (dx*dx+dy*dy) <= (pos_tol*pos_tol) and angle_diff(p[2], q[2]) <= ang_tol
def polyline_length(pts):
    s=0.0
    for i in range(1,len(pts)):
        dx=pts[i][0]-pts[i-1][0]; dy=pts[i][1]-pts[i-1][1]
        s += math.hypot(dx,dy)
    return s
def extend_along_heading(pose, extra):
    x,y,th = pose
    return (x + extra*math.cos(th), y + extra*math.sin(th), th)

# -------------------
# Dubins shortest (forward-only, analytic)
# -------------------
def _dubins_all(start, goal, R):
    x0,y0,th0 = start; x1,y1,th1 = goal
    dx = x1 - x0; dy = y1 - y0
    c,s = math.cos(th0), math.sin(th0)
    x = ( c*dx + s*dy) / R
    y = (-s*dx + c*dy) / R
    phi = mod2pi(th1 - th0)

    def LSL():
        tmp = math.hypot(x - math.sin(phi), y - 1 + math.cos(phi))
        if tmp < 1e-9: return None
        t = mod2pi(math.atan2(y - 1 + math.cos(phi), x - math.sin(phi)))
        p = tmp
        q = mod2pi(phi - t)
        return (t+p+q,(t,p,q),"LSL")

    def RSR():
        xx = x + math.sin(phi); yy = y + 1 - math.cos(phi)
        tmp = math.hypot(xx, yy)
        if tmp < 1e-9: return None
        t = mod2pi(-math.atan2(yy, xx))
        p = tmp
        q = mod2pi(-mod2pi(phi) + t)
        return (t+p+q,(t,p,q),"RSR")

    def LSR():
        xx = x + math.sin(phi); yy = y - 1 + math.cos(phi)
        tmp2 = xx*xx + yy*yy
        if tmp2 < 4.0: return None
        p = math.sqrt(tmp2 - 4.0)
        theta = math.atan2(2.0, p)
        t = mod2pi(math.atan2(yy, xx) + theta)
        q = mod2pi(t - phi)
        return (t+p+q,(t,p,q),"LSR")

    def RSL():
        xx = x - math.sin(phi); yy = y + 1 - math.cos(phi)
        tmp2 = xx*xx + yy*yy
        if tmp2 < 4.0: return None
        p = math.sqrt(tmp2 - 4.0)
        theta = math.atan2(2.0, p)
        t = mod2pi(-math.atan2(yy, xx) + theta)
        q = mod2pi(phi - t)
        return (t+p+q,(t,p,q),"RSL")

    def RLR():
        tmp = (6. - (x*x + y*y) + 2*math.cos(phi) + 2*(x*math.sin(phi) - y*math.cos(phi))) / 8.
        if abs(tmp) > 1.0: return None
        p = mod2pi(2*math.pi - math.acos(tmp))
        t = mod2pi(math.atan2(y - math.cos(phi), x + math.sin(phi)) - p/2)
        q = mod2pi(mod2pi(phi) - t + p)
        return (t+p+q,(t,p,q),"RLR")

    def LRL():
        tmp = (6. - (x*x + y*y) + 2*math.cos(phi) + 2*(-x*math.sin(phi) + y*math.cos(phi))) / 8.
        if abs(tmp) > 1.0: return None
        p = mod2pi(2*math.pi - math.acos(tmp))
        t = mod2pi(-math.atan2(y + math.cos(phi), x - math.sin(phi)) + p/2)
        q = mod2pi(-mod2pi(phi) + t - p)
        return (t+p+q,(t,p,q),"LRL")

    cands = [f() for f in (LSL,RSR,LSR,RSL,RLR,LRL)]
    cands = [c for c in cands if c is not None]
    if not cands: return None
    return min(cands, key=lambda z: z[0]), R, (x0,y0,th0)

def _sample_dubins(best_pack, ds):
    """Sample a Dubins path with smooth, dense sampling to avoid sharp changes."""
    (Lscaled,(t,p,q), typ), R, (x0,y0,th0) = best_pack
    segs = []
    if typ == "LSL": segs = [("L",t),("S",p),("L",q)]
    elif typ == "RSR": segs = [("R",t),("S",p),("R",q)]
    elif typ == "LSR": segs = [("L",t),("S",p),("R",q)]
    elif typ == "RSL": segs = [("R",t),("S",p),("L",q)]
    elif typ == "RLR": segs = [("R",t),("L",p),("R",q)]
    elif typ == "LRL": segs = [("L",t),("R",p),("L",q)]
    else: raise RuntimeError("unknown dubins type")

    x,y,th = x0,y0,th0
    pts = [(x,y,th)]
    step_ang = ds / max(1e-6, R)

    for seg_type, seg_len in segs:
        if seg_type == "S":
            # Straight segment - ensure smooth sampling
            seg_len_m = seg_len * R
            m = max(2, int(math.ceil(seg_len_m / ds)))
            for i in range(1, m+1):
                s = (i/m) * seg_len_m
                xx = x + s * math.cos(th)
                yy = y + s * math.sin(th)
                pts.append((xx, yy, th))
            x, y = pts[-1][0], pts[-1][1]
        else:
            # Arc segment - ensure smooth sampling
            dir_sign = +1 if seg_type == "L" else -1
            total_ang = dir_sign * seg_len
            m = max(3, int(math.ceil(abs(total_ang) / step_ang)))
            cx = x - R * math.sin(th) * dir_sign
            cy = y + R * math.cos(th) * dir_sign
            for i in range(1, m+1):
                a = (i/m) * total_ang
                th_i = mod2pi(th + a)
                xx = cx + R * math.sin(th_i) * dir_sign
                yy = cy - R * math.cos(th_i) * dir_sign
                pts.append((xx, yy, th_i))
            x, y, th = pts[-1]
    return pts

# tolerant collision + gates
def _line_collides(line_xy, inflated, start_xy=None, goal_xy=None, gate_radius=CLEAR_GATE_M):
    """Check if a path collides with inflated obstacles.
    Returns True if collision detected, False if path is clear."""
    if inflated is None or inflated.is_empty:
        return False
    
    if len(line_xy) < 2:
        return False
    
    # Create the path line
    line = LineString(line_xy)
    
    # Start with inflated obstacles
    collision_zone = inflated
    
    # Apply erosion for tolerance (shrink obstacles slightly)
    try:
        collision_zone = collision_zone.buffer(-COLLIDE_EPS)
        if collision_zone.is_empty:
            return False
    except Exception:
        pass
    
    # Remove clearance gates around start/goal
    try:
        if start_xy is not None:
            collision_zone = collision_zone.difference(Point(start_xy).buffer(gate_radius))
        if goal_xy is not None:
            collision_zone = collision_zone.difference(Point(goal_xy).buffer(gate_radius))
        if collision_zone.is_empty:
            return False
    except Exception:
        pass
    
    # Check if line intersects the collision zone
    # A collision occurs if the line crosses or touches the obstacle
    return line.intersects(collision_zone)

def dubins_path(start, goal, inflated, Rmin, ds=DS):
    """Compute collision-free Dubins path from start to goal."""
    best = _dubins_all(start, goal, Rmin)
    if best is None:
        return None
    pts = _sample_dubins(best, ds)
    xy = [(x, y) for (x, y, _) in pts]
    
    # Debug: check collision
    collides = _line_collides(xy, inflated, (start[0], start[1]), (goal[0], goal[1]))
    
    if collides:
        return None
    return pts

# -------------------
# Lattice A* fallback (forward-only, curvature-constrained)
# -------------------
def _arc_end(x, y, th, radius, delta):
    cx = x - radius*math.sin(th)
    cy = y + radius*math.cos(th)
    th2 = mod2pi(th + delta)
    x2  = cx + radius*math.sin(th2)
    y2  = cy - radius*math.cos(th2)
    return x2, y2, th2

def lattice_forward_astar(start, goal, inflated, Rmin,
                          dstep=LAT_DSTEP, headings=LAT_HEADINGS,
                          turn_deg=LAT_TURN_DEG, max_exp=LAT_MAX_EXP):
    sx,sy,sth = start; gx,gy,gth = goal
    dtheta = 2*math.pi / headings
    turn_rad = math.radians(turn_deg)
    arc_len = Rmin * turn_rad

    def snap_th(th): return int(round(mod2pi(th)/dtheta)) % headings
    def unsnap_th(k): return k * dtheta

    start_k = snap_th(sth)
    goal_k  = snap_th(gth)

    def h(x,y,thk):
        d = math.hypot(gx - x, gy - y)
        ang = angle_diff(unsnap_th(thk), gth)
        return d + 0.2*Rmin*ang  # FIXED: Reduced multiplier from 0.25 to 0.2

    def primitives(x,y,thk):
        th = unsnap_th(thk)
        # straight
        xs = x + dstep*math.cos(th)
        ys = y + dstep*math.sin(th)
        yield xs, ys, thk, dstep, "S", (x,y,th)
        # left arc (+turn_rad)
        xl, yl, thL = _arc_end(x, y, th, Rmin, +turn_rad)
        kL = snap_th(thL)
        yield xl, yl, kL, arc_len, "L", (x,y,th)
        # right arc (-turn_rad)
        xr, yr, thR = _arc_end(x, y, th, Rmin, -turn_rad)
        kR = snap_th(thR)
        yield xr, yr, kR, arc_len, "R", (x,y,th)

    openh=[]; push=heapq.heappush; pop=heapq.heappop
    nid=0
    parents={}
    seen={}

    def new_id():
        nonlocal nid; nid += 1; return nid

    sid = new_id()
    push(openh, (h(sx,sy,start_k), 0.0, sx, sy, start_k, sid))
    parents[sid] = None

    expansions=0
    while openh and expansions < max_exp:
        f,g,x,y,k, idcur = pop(openh)
        key=(round(x,3), round(y,3), k)
        if key in seen and seen[key] <= g: continue
        seen[key]=g

        # goal test - FIXED: More lenient
        if ( (x-gx)**2 + (y-gy)**2 <= POS_TOL*POS_TOL and
             angle_diff(unsnap_th(k), gth) <= ANG_TOL_PLAN ):
            # reconstruct
            chain=[]
            cur = idcur
            cur_state=(x,y,unsnap_th(k))
            chain.append(cur_state)
            while parents[cur] is not None:
                pid, prev_state, action = parents[cur]
                px,py,pk = prev_state
                chain.append((px,py,unsnap_th(pk)))
                cur = pid
            chain.reverse()

            # densify
            dense=[]
            for i in range(1, len(chain)):
                x0,y0,th0 = chain[i-1]
                x1,y1,th1 = chain[i]
                if angle_diff(th0, th1) < 1e-4:
                    steps = max(1, int(math.ceil(math.hypot(x1-x0,y1-y0)/DS)))
                    for t in range(steps):
                        u = t/steps
                        dense.append((x0+(x1-x0)*u, y0+(y1-y0)*u, th0))
                else:
                    raw = mod2pi(th1 - th0)
                    signed = raw if raw <= math.pi else raw - 2*math.pi
                    steps = max(3, int(math.ceil(abs(Rmin*signed)/DS)))
                    for t in range(steps):
                        u = t/steps
                        th_u = mod2pi(th0 + u*signed)
                        cx = x0 - Rmin*math.sin(th0)
                        cy = y0 + Rmin*math.cos(th0)
                        xu = cx + Rmin*math.sin(th_u)
                        yu = cy - Rmin*math.cos(th_u)
                        dense.append((xu,yu,th_u))
            dense.append(chain[-1])
            if not _line_collides([(px,py) for (px,py,_) in dense], inflated, (sx,sy), (gx,gy)):
                return dense

        expansions+=1
        for xn, yn, kn, cost, action, parent_state in primitives(x,y,k):
            if not (0.0 <= xn <= ARENA_SIZE_M and 0.0 <= yn <= ARENA_SIZE_M):
                continue
            pts = []
            if action == "S":
                samples = max(2, int(math.ceil(cost/DS)))
                for t in range(samples+1):
                    u = t/samples
                    pts.append((x + (xn-x)*u, y + (yn-y)*u))
            else:
                th0 = (k * dtheta)
                signed = +turn_rad if action=="L" else -turn_rad
                samples = max(3, int(math.ceil(abs(arc_len)/DS)))
                for t in range(samples+1):
                    u = t/samples
                    th_u = mod2pi(th0 + u*signed)
                    cx = x - Rmin*math.sin(th0)
                    cy = y + Rmin*math.cos(th0)
                    xu = cx + Rmin*math.sin(th_u)
                    yu = cy - Rmin*math.cos(th_u)
                    pts.append((xu,yu))
            if _line_collides(pts, inflated, (sx,sy), (gx,gy)):
                continue

            nid2 = new_id()
            parents[nid2] = (idcur, (x,y,k), action)
            g2 = g + cost
            f2 = g2 + h(xn,yn,kn)
            heapq.heappush(openh, (f2, g2, xn, yn, kn, nid2))

    return None

# -------------------
# Planning wrapper
# -------------------
def plan_leg_with_fallback(start_pose, goal_pose, inflated, Rmin, ds, pos_tol, ang_tol_exact, dbg):
    # FIXED: Try direct first with more lenient approach
    direct = dubins_path(start_pose, goal_pose, inflated, Rmin, ds=ds)
    if direct and pose_close_plan(direct[-1], goal_pose, pos_tol, ANG_TOL_PLAN):
        dbg.append("[fallback] direct analytic succeeded")
        return direct

    # (a) Approach buffer
    approach_extra = 0.08  # FIXED: Increased from 0.06
    goal_approach  = extend_along_heading(goal_pose, +approach_extra)
    p1 = dubins_path(start_pose, goal_approach, inflated, Rmin, ds=ds)
    p2 = dubins_path(goal_approach, goal_pose, inflated, Rmin, ds=ds) if p1 else None
    if p1 and p2:
        merged = p1[:-1] + p2
        if pose_close(merged[-1], goal_pose, pos_tol, ang_tol_exact):
            dbg.append("[fallback(a)] approach buffer succeeded")
            return merged

    # (c) midpoint analytic
    sx,sy,_ = start_pose; gx,gy,_ = goal_pose
    mx,my   = 0.5*(sx+gx), 0.5*(sy+gy)
    mth     = math.atan2(gy - sy, gx - sx)
    mid     = (mx, my, mth)
    pA = dubins_path(start_pose, mid, inflated, Rmin, ds=ds)
    pB = dubins_path(mid, goal_pose, inflated, Rmin, ds=ds)
    if pA and pB:
        merged = pA[:-1] + pB
        if pose_close_plan(merged[-1], goal_pose, pos_tol, ANG_TOL_PLAN):
            dbg.append("[fallback(c)] midpoint analytic succeeded")
            return merged

    # (d) lattice fallback
    dbg.append("[fallback] trying lattice A*...")
    lat = lattice_forward_astar(start_pose, goal_pose, inflated, Rmin)
    if lat and pose_close_plan(lat[-1], goal_pose, pos_tol, ANG_TOL_PLAN):
        dbg.append("[fallback(d)] lattice A* succeeded")
        return lat

    dbg.append("[fallback] all strategies failed")
    return None

# -------------------
# Held–Karp DP
# -------------------
def held_karp(cost):
    n = len(cost)
    dp = {}
    for j in range(1, n):
        dp[(1<<j, j)] = (cost[0][j], 0)
    for mask in range(1, 1<<n):
        for j in range(1, n):
            if not (mask & (1<<j)): continue
            cur = dp.get((mask, j))
            if cur is None: continue
            cur_len, _ = cur
            for k in range(1, n):
                if mask & (1<<k): continue
                nk = (mask | (1<<k), k)
                val = cur_len + cost[j][k]
                if val < dp.get(nk, (float("inf"), None))[0]:
                    dp[nk] = (val, j)
    full_mask = 0
    for j in range(1, n): full_mask |= (1<<j)
    best = float("inf"); end = None
    for j in range(1, n):
        v = dp.get((full_mask, j))
        if v and v[0] < best:
            best = v[0]; end = j
    return best, end, dp, full_mask

def reconstruct_order(end, dp, full_mask):
    order = [end]; mask = full_mask; j = end
    while mask:
        cur = dp[(mask, j)]
        prev = cur[1]
        if prev == 0: break
        order.append(prev)
        mask ^= (1<<j)
        j = prev
    order.reverse()
    return [0] + order

# -------------------
# Camera / serial
# -------------------
class Camera:
    def __init__(self, m2px=M2PX):
        self.scale = m2px
        self.tx = WIN_W/2 - ARENA_SIZE_M/2 * self.scale
        self.ty = WIN_H/2 + ARENA_SIZE_M/2 * self.scale
    def w2s(self,x,y): return int(self.tx + x*self.scale), int(self.ty - y*self.scale)
    def s2w(self,sx,sy): return (sx - self.tx)/self.scale, (self.ty - sy)/self.scale

class STMComm:
    def __init__(self, port="/dev/ttyUSB0", baud=115200, unit_scale=100.0, enabled=False):
        self.port=port; self.baud=baud; self.unit_scale=unit_scale
        self.enabled = enabled and (serial is not None)
        self.ser = None
    def open(self):
        if not self.enabled:
            print("[STM] serial disabled"); return
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"[STM] opened {self.port} @ {self.baud}")
        except Exception as e:
            print("[STM] open failed:", e); self.enabled = False
    def send_cmd(self, ch, value=None):
        msg = f"{ch}{int(round(value))}\n" if value is not None else f"{ch}\n"
        print("[STM SEND]" if self.enabled else "[STM NOSEND]", msg.strip())
        if self.enabled and self.ser and self.ser.is_open:
            try: self.ser.write(msg.encode('ascii'))
            except Exception as e: print("[STM] write error:", e)

# -------------------
# Planner manager
# -------------------
class PlannerManager:
    def __init__(self, app):
        self.app = app
        self.reset()
    def reset(self):
        self.active=False; self.stage=None
        self.nodes=[]; self.edge_paths={}; self.cost=None
        self.todo=[]; self.idx_map={}
        self.progress=0; self.total=0
        self.result=None; self.msg=""
        self.last_error=""; self.last_bad_leg=None
        self.debug_log=[]
    def start(self):
        self.reset()
        self.nodes = [("start", START)] + [(o.id, o.image_pose(self.app.standoff)) for o in self.app.obstacles]
        self.idx_map = {name:i for i,(name,_) in enumerate(self.nodes)}
        n = len(self.nodes)
        self.cost = [[float("inf")]*n for _ in range(n)]
        self.edge_paths.clear()
        self.todo = [(i,j) for i in range(n) for j in range(n) if i!=j]
        self.total = len(self.todo); self.progress=0
        self.active=True; self.stage="pairwise"
        self.msg = "Computing pairwise curvature-constrained legs…"
        self.debug_log.append(f"[start] nodes={self.nodes} Rmin={self.app.Rmin:.3f} rad={self.app.robot_radius:.3f} stand={self.app.standoff:.3f}")
    def step(self, budget_ms=12):
        if not self.active: return False
        t0 = time.time()
        if self.stage=="pairwise":
            while self.todo and (time.time()-t0)*1000.0 < budget_ms:
                i,j = self.todo.pop()
                name_i, pose_i = self.nodes[i]
                name_j, pose_j = self.nodes[j]
                dbg=[]
                path = plan_leg_with_fallback(
                    pose_i, pose_j, self.app.inflated, self.app.Rmin, ds=DS,
                    pos_tol=self.app.pos_tol, ang_tol_exact=self.app.ang_tol, dbg=dbg
                )
                if path:
                    self.edge_paths[(i,j)] = path
                    self.cost[i][j] = polyline_length(path)
                else:
                    self.edge_paths[(i,j)] = None
                    self.cost[i][j] = float("inf")
                    self.last_error = f"infeasible: {name_i} → {name_j}"
                    self.last_bad_leg = (name_i, name_j)
                    print(f"[INF] infeasible {name_i}->{name_j}  "
                          f"Rmin={self.app.Rmin:.3f}  infl.rad={self.app.robot_radius:.3f}  stand={self.app.standoff:.3f}  "
                          f"pos_tol={self.app.pos_tol:.3f}  ang_tol={math.degrees(self.app.ang_tol):.1f}°")
                    for m in dbg: print("       ", m)
                    print("       HINTS: '[' reduce inflation, ';' reduce standoff, '+' tighter Rmin, or nudge obstacle.")
                self.progress += 1
            if not self.todo:
                self.stage="dp"; self.msg="Solving visit order (DP)…"
        if self.stage=="dp":
            best, end, dp, full = held_karp(self.cost)
            if end is None or best==float("inf"):
                self.result=("error", "No feasible Hamiltonian path – tweak params (see panel/console).")
            else:
                seq_idx = reconstruct_order(end, dp, full)
                names = [name for (name,_) in self.nodes]
                seq_names = [names[i] for i in seq_idx]
                edges={}
                for k in range(len(seq_idx)-1):
                    i,j = seq_idx[k], seq_idx[k+1]
                    edges[(names[i], names[j])] = self.edge_paths[(i,j)]
                self.result=("ok",(seq_names,best,edges,self.app.standoff))
            self.active=False
            return False
        return True
    def progress_ratio(self):
        return 0.0 if self.total==0 else self.progress/self.total

# -------------------
# App
# -------------------
class App:
    def __init__(self, serial_port="/dev/ttyUSB0"):
        pygame.init(); pygame.font.init()
        self.win = pygame.display.set_mode((WIN_W,WIN_H))
        pygame.display.set_caption("Dubins Planner (Grid/Add/Remove/Coords) + Robust Fallbacks")
        self.clock = pygame.time.Clock()
        self.font  = pygame.font.Font(None, 18)
        self.font_sm= pygame.font.Font(None, 16)
        self.cam   = Camera()

        self.obstacles = [
            Obstacle("A", 0.40, 1.55, "S"),
            Obstacle("B", 1.55, 1.40, "W"),
            Obstacle("C", 0.30, 0.50, "E"),
        ]

        self.robot_radius = DEFAULT_ROBOT_RADIUS
        self.Rmin         = DEFAULT_R_MIN
        self.standoff     = DEFAULT_STANDOFF
        self.pos_tol      = POS_TOL
        self.ang_tol      = ANG_TOL
        self.simulate_only= True
        self.unit_scale   = 100.0
        self.show_grid    = True

        self.serial = STMComm(serial_port, 115200, self.unit_scale, enabled=(not self.simulate_only))
        self.serial.open()

        self.inflated = inflate_obstacles(self.obstacles, self.robot_radius)
        self.plan     = None
        self.drag     = None
        self.running  = True
        self.planner  = PlannerManager(self)

        self.status_msg = ""; self.status_color = C_WARN; self.status_timer = 0.0

    def next_label(self):
        got = {o.id for o in self.obstacles}
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if c not in got: return c
        i=1
        while True:
            if f"A{i}" not in got: return f"A{i}"
            i+=1

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT: self.running=False
                elif ev.type == pygame.KEYDOWN: self.handle_key(ev)
                elif ev.type == pygame.MOUSEBUTTONDOWN: self.handle_mouse_down(ev)
                elif ev.type == pygame.MOUSEBUTTONUP: self.drag=None
                elif ev.type == pygame.MOUSEMOTION and self.drag: self.handle_drag(ev)

            if self.planner.active:
                more = self.planner.step(budget_ms=10)
                if not more:
                    status = self.planner.result[0]
                    if status=="ok":
                        self.plan = self.planner.result[1]
                        seq,total,_,_ = self.plan
                        self.flash_status(f"Planned: {' → '.join(seq)}  L≈{total:.2f} m", C_TEXT)
                    else:
                        self.plan=None
                        self.flash_status("Plan failed (see console & panel).", C_ERR)

            self.draw()
            pygame.display.flip()
        pygame.quit()

    def handle_key(self, ev):
        k=ev.key
        if k in (pygame.K_ESCAPE, pygame.K_q): self.running=False; return
        if k == pygame.K_g: self.show_grid = not self.show_grid; return
        if k == pygame.K_n:
            mx,my = pygame.mouse.get_pos(); wx,wy = self.cam.s2w(mx,my)
            wx = max(0.0, min(ARENA_SIZE_M-OB_SIZE, wx - OB_SIZE/2))
            wy = max(0.0, min(ARENA_SIZE_M-OB_SIZE, wy - OB_SIZE/2))
            self.obstacles.append(Obstacle(self.next_label(), wx, wy, "N"))
            self.plan=None; self.inflated = inflate_obstacles(self.obstacles, self.robot_radius); return
        if k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            mx,my = pygame.mouse.get_pos(); wx,wy = self.cam.s2w(mx,my)
            if self.obstacles:
                o = min(self.obstacles, key=lambda ob: (ob.center()[0]-wx)**2 + (ob.center()[1]-wy)**2)
                self.obstacles.remove(o); self.plan=None; self.inflated = inflate_obstacles(self.obstacles, self.robot_radius)
            return

        if k == pygame.K_p:
            self.inflated = inflate_obstacles(self.obstacles, self.robot_radius)
            self.planner.start(); self.plan=None; return
        if k == pygame.K_a and self.plan: self.animate(self.plan); return
        if k == pygame.K_e and self.plan:
            if self.simulate_only: self.flash_status("Simulate-only: not sending to STM", C_WARN)
            else: self.execute_on_stm(self.plan)
            return
        if k == pygame.K_t:
            self.simulate_only = not self.simulate_only
            self.serial.enabled = (not self.simulate_only) and (serial is not None)
            if self.serial.enabled: self.serial.open()
            self.flash_status(f"Simulate-only: {'ON' if self.simulate_only else 'OFF'}", C_TEXT); return
        if k == pygame.K_o: self.probe_feasibility(); return

        # tuning
        if k in (pygame.K_PLUS, pygame.K_EQUALS):
            # Respect Ackermann minimum
            min_allowed = WHEELBASE / math.tan(MAX_STEERING_ANGLE)
            self.Rmin = max(min_allowed, self.Rmin - 0.01); self.plan=None
            if self.Rmin == min_allowed:
                self.flash_status(f"Rmin at Ackermann limit: {self.Rmin:.3f} m", C_WARN)
            else:
                self.flash_status(f"Rmin -> {self.Rmin:.3f} m", C_TEXT)
            return
        if k == pygame.K_MINUS:
            self.Rmin += 0.01; self.plan=None
            self.flash_status(f"Rmin -> {self.Rmin:.3f} m", C_TEXT); return
        if k == pygame.K_LEFTBRACKET:
            self.robot_radius = max(0.02, self.robot_radius - 0.005); self.plan=None
            self.inflated = inflate_obstacles(self.obstacles, self.robot_radius)
            self.flash_status(f"inflation -> {self.robot_radius:.3f} m", C_TEXT); return
        if k == pygame.K_RIGHTBRACKET:
            self.robot_radius += 0.005; self.plan=None
            self.inflated = inflate_obstacles(self.obstacles, self.robot_radius)
            self.flash_status(f"inflation -> {self.robot_radius:.3f} m", C_TEXT); return
        if k == pygame.K_SEMICOLON:
            self.standoff = max(0.02, self.standoff - 0.01); self.plan=None
            self.flash_status(f"standoff -> {self.standoff:.3f} m", C_TEXT); return
        if k == pygame.K_QUOTE:
            self.standoff += 0.01; self.plan=None
            self.flash_status(f"standoff -> {self.standoff:.3f} m", C_TEXT); return
        if k == pygame.K_COMMA:
            self.pos_tol = max(0.01, self.pos_tol - 0.005); self.plan=None
            self.flash_status(f"pos tol -> {self.pos_tol:.3f} m", C_TEXT); return
        if k == pygame.K_PERIOD:
            self.pos_tol += 0.005; self.plan=None
            self.flash_status(f"pos tol -> {self.pos_tol:.3f} m", C_TEXT); return
        if k == pygame.K_LESS:
            self.ang_tol = max(math.radians(1), self.ang_tol - math.radians(1)); self.plan=None
            self.flash_status(f"ang tol -> {math.degrees(self.ang_tol):.1f}°", C_TEXT); return
        if k == pygame.K_GREATER:
            self.ang_tol += math.radians(1); self.plan=None
            self.flash_status(f"ang tol -> {math.degrees(self.ang_tol):.1f}°", C_TEXT); return

    def handle_mouse_down(self, ev):
        wx,wy = self.cam.s2w(*ev.pos)
        if ev.button == 1:
            if self.obstacles:
                self.drag = min(self.obstacles, key=lambda o: (o.center()[0]-wx)**2 + (o.center()[1]-wy)**2)
        elif ev.button == 3:
            if self.obstacles:
                o = min(self.obstacles, key=lambda ob: (ob.center()[0]-wx)**2 + (ob.center()[1]-wy)**2)
                o.face = {'N':'E','E':'S','S':'W','W':'N'}[o.face]
                self.plan=None; self.inflated = inflate_obstacles(self.obstacles, self.robot_radius)

    def handle_drag(self, ev):
        wx,wy = self.cam.s2w(*ev.pos)
        self.drag.x = max(0.0, min(ARENA_SIZE_M-OB_SIZE, wx - OB_SIZE/2))
        self.drag.y = max(0.0, min(ARENA_SIZE_M-OB_SIZE, wy - OB_SIZE/2))
        self.plan=None; self.inflated = inflate_obstacles(self.obstacles, self.robot_radius)

    def flash_status(self, msg, color, dur=2.0):
        self.status_msg = msg; self.status_color = color; self.status_timer = time.time() + dur

    def probe_feasibility(self):
        """Test all pairwise paths and report issues."""
        print("\n" + "="*80)
        print("FEASIBILITY PROBE")
        print("="*80)
        print(f"Rmin={self.Rmin:.3f}m, Robot_radius={self.robot_radius:.3f}m, Standoff={self.standoff:.3f}m")
        print(f"Effective inflation: {self.robot_radius + SAFETY_MARGIN:.3f}m")
        print(f"Pos_tol={self.pos_tol:.3f}m, Ang_tol={math.degrees(self.ang_tol):.1f}°")
        print("-"*80)
        
        nodes = [("start", START)] + [(o.id, o.image_pose(self.standoff)) for o in self.obstacles]
        bad=[]
        good=0
        
        for i in range(len(nodes)):
            for j in range(len(nodes)):
                if i==j: continue
                name_i, pose_i = nodes[i]
                name_j, pose_j = nodes[j]
                
                # Calculate straight-line distance
                dist = math.hypot(pose_j[0]-pose_i[0], pose_j[1]-pose_i[1])
                
                dbg=[]
                path = plan_leg_with_fallback(pose_i, pose_j,
                                              self.inflated, self.Rmin, ds=DS,
                                              pos_tol=self.pos_tol, ang_tol_exact=self.ang_tol, dbg=dbg)
                if not path:
                    bad.append((name_i, name_j))
                    print(f"✗ {name_i:5s} → {name_j:5s}  dist={dist:.3f}m  INFEASIBLE")
                    for m in dbg:
                        print(f"    {m}")
                else:
                    good += 1
                    path_len = polyline_length(path)
                    print(f"✓ {name_i:5s} → {name_j:5s}  dist={dist:.3f}m  path={path_len:.3f}m")
        
        print("-"*80)
        print(f"Results: {good} feasible, {len(bad)} infeasible out of {len(nodes)*(len(nodes)-1)} total")
        
        if bad:
            print("\nSuggestions:")
            print("  '[' - Reduce inflation radius")
            print("  ';' - Reduce standoff distance")
            print("  '+' - Reduce Rmin (tighter turns)")
            print("  '.' - Increase position tolerance")
            print("  '>' - Increase angle tolerance")
            print("  Or drag obstacles to different positions")
            self.flash_status(f"{len(bad)} infeasible legs (see console)", C_WARN, dur=3.0)
        else:
            print("\n✓ All pairwise legs are feasible!")
            self.flash_status("All pairwise legs feasible!", C_TEXT, dur=2.0)
        print("="*80 + "\n")

    def draw_robot(self,x,y,th):
        """Draw Ackermann robot with proper dimensions."""
        # Robot dimensions
        w = ROBOT_WIDTH
        h = ROBOT_LENGTH
        
        # Calculate corners of robot rectangle in world space
        cos_th = math.cos(th)
        sin_th = math.sin(th)
        
        # Corners relative to center (robot front is along heading)
        corners_local = [
            (-w/2, -h/2),  # rear left
            ( w/2, -h/2),  # rear right
            ( w/2,  h/2),  # front right
            (-w/2,  h/2),  # front left
        ]
        
        # Transform to world coordinates
        corners_world = []
        for lx, ly in corners_local:
            wx = x + lx * cos_th - ly * sin_th
            wy = y + lx * sin_th + ly * cos_th
            corners_world.append(self.cam.w2s(wx, wy))
        
        # Draw robot body
        pygame.draw.polygon(self.win, (80, 200, 255), corners_world)
        pygame.draw.polygon(self.win, (60, 160, 220), corners_world, 2)
        
        # Draw heading indicator (front of robot)
        front_x = x + (h/2) * cos_th
        front_y = y + (h/2) * sin_th
        sx, sy = self.cam.w2s(x, y)
        fx, fy = self.cam.w2s(front_x, front_y)
        pygame.draw.line(self.win, (255, 255, 100), (sx, sy), (fx, fy), 3)
        
        # Draw center point
        pygame.draw.circle(self.win, (255, 200, 0), (sx, sy), 4)

    def animate(self, plan):
        seq,total,edges,standoff = plan
        for i in range(len(seq)-1):
            pts = edges[(seq[i], seq[i+1])]
            for (x,y,th) in pts:
                self.draw(); self.draw_robot(x,y,th)
                pygame.display.flip(); time.sleep(1.0/FPS)
            time.sleep(PHOTO_PAUSE)
        print("[Animate] complete")

    def execute_on_stm(self, plan):
        seq,total,edges,standoff = plan
        for i in range(len(seq)-1):
            pts = edges[(seq[i], seq[i+1])]
            if len(pts) < 2: continue
            for j in range(1, len(pts)):
                x0,y0,th0 = pts[j-1]; x1,y1,th1 = pts[j]
                dx,dy = x1-x0, y1-y0
                dist_m = math.hypot(dx,dy)
                if dist_m <= 1e-4: continue
                proj = math.cos(th0)*dx + math.sin(th0)*dy
                units = dist_m * self.serial.unit_scale
                if self.simulate_only: print("[NOSEND]", "w" if proj>=0 else "x", int(round(units)))
                else: self.serial.send_cmd('w' if proj>=0 else 'x', units)
                time.sleep(0.004)
            if not self.simulate_only: self.serial.send_cmd('s', None)
            time.sleep(PHOTO_PAUSE)
        print("[Exec] done")

    def draw_grid(self):
        if not self.show_grid: return
        step = 0.10
        x=0.0
        while x <= ARENA_SIZE_M + 1e-9:
            sx0,sy0 = self.cam.w2s(x, 0.0); sx1,sy1 = self.cam.w2s(x, ARENA_SIZE_M)
            pygame.draw.line(self.win, C_GRID, (sx0,sy0), (sx1,sy1), 1); x += step
        y=0.0
        while y <= ARENA_SIZE_M + 1e-9:
            sx0,sy0 = self.cam.w2s(0.0, y); sx1,sy1 = self.cam.w2s(ARENA_SIZE_M, y)
            pygame.draw.line(self.win, C_GRID, (sx0,sy0), (sx1,sy1), 1); y += step
        a,b = self.cam.w2s(0,0); c,d = self.cam.w2s(ARENA_SIZE_M,ARENA_SIZE_M)
        pygame.draw.rect(self.win, C_AXES, pygame.Rect(a,d,c-a,b-d), 1)
        for i in range(0, int(ARENA_SIZE_M*10)+1, 5):
            x=i/10.0; sx,sy = self.cam.w2s(x, 0.0)
            self.win.blit(self.font_sm.render(f"{x:.1f}", True, (170,170,170)), (sx-8, sy+4))
        for i in range(0, int(ARENA_SIZE_M*10)+1, 5):
            y=i/10.0; sx,sy = self.cam.w2s(0.0, y)
            self.win.blit(self.font_sm.render(f"{y:.1f}", True, (170,170,170)), (sx-28, sy-10))

    def draw(self):
        self.win.fill(C_BG)
        self.draw_grid()

        a,b = self.cam.w2s(0,0); c,d = self.cam.w2s(ARENA_SIZE_M,ARENA_SIZE_M)
        pygame.draw.rect(self.win, C_BORDER, pygame.Rect(a,d,c-a,b-d), 2)

        x,y,w,h = START_ZONE
        a,b = self.cam.w2s(x,y); c,d = self.cam.w2s(x+w,y+h)
        pygame.draw.rect(self.win, C_START, pygame.Rect(a,d,c-a,b-d), 2)
        
        # Draw origin marker (where right back wheel starts)
        origin_sx, origin_sy = self.cam.w2s(0, 0)
        pygame.draw.circle(self.win, (255, 100, 100), (origin_sx, origin_sy), 5)
        pygame.draw.line(self.win, (255, 100, 100), (origin_sx-8, origin_sy), (origin_sx+8, origin_sy), 2)
        pygame.draw.line(self.win, (255, 100, 100), (origin_sx, origin_sy-8), (origin_sx, origin_sy+8), 2)
        self.win.blit(self.font_sm.render("Origin", True, (255, 100, 100)), (origin_sx+8, origin_sy-15))

        if self.inflated and not self.inflated.is_empty:
            polys = self.inflated.geoms if hasattr(self.inflated, "geoms") else [self.inflated]
            for poly in polys:
                pts = [self.cam.w2s(px,py) for px,py in poly.exterior.coords]
                pygame.draw.lines(self.win, C_INFL, True, pts, 1)

        if self.plan:
            seq,total,edges,standoff = self.plan
            for i in range(len(seq)-1):
                pts = edges[(seq[i], seq[i+1])]
                if len(pts)>1:
                    scr = [self.cam.w2s(x,y) for x,y,_ in pts]
                    pygame.draw.lines(self.win, C_PATH, False, scr, 2)
            hud = f"Curvature-constrained | Order: {'→'.join(seq)} | L≈{total:.2f}m"
            self.win.blit(self.font.render(hud, True, C_TEXT), (10,10))
        else:
            self.win.blit(self.font.render("P=Plan  N=Add  Del=Remove  LMB=Drag  RMB=Rotate  G=Grid  O=Probe", True, C_TEXT), (10,10))

        for o in self.obstacles:
            a,b = self.cam.w2s(o.x,o.y); c,d = self.cam.w2s(o.x+OB_SIZE,o.y+OB_SIZE)
            rect = pygame.Rect(a,d,c-a,b-d)
            pygame.draw.rect(self.win, C_OB, rect); pygame.draw.rect(self.win, (0,0,0), rect, 2)
            cx,cy = o.center()
            label = f"{o.id} ({cx:.2f},{cy:.2f}) {o.face}"
            self.win.blit(self.font_sm.render(label, True, (240,240,240)), (a+4, d+4))
            tx,ty,th = o.image_pose(self.standoff); sx,sy = self.cam.w2s(tx,ty)
            pygame.draw.circle(self.win,(255,140,0),(sx,sy),4)
            hx,hy = self.cam.w2s(tx+0.08*math.cos(th), ty+0.08*math.sin(th))
            pygame.draw.line(self.win,(255,140,0),(sx,sy),(hx,hy),2)

        px = WIN_W - 450
        lines = [
            f"SIMULATE-ONLY: {'ON' if self.simulate_only else 'OFF'} (T)",
            f"Grid: {'ON' if self.show_grid else 'OFF'} (G)",
            f"",
            f"ACKERMANN ROBOT (no point turns):",
            f"  Size: {ROBOT_WIDTH*100:.0f}cm × {ROBOT_LENGTH*100:.0f}cm",
            f"  Max steering: {math.degrees(MAX_STEERING_ANGLE):.0f}°",
            f"  Wheelbase: {WHEELBASE*100:.0f}cm",
            f"  Min turn radius: {self.Rmin:.3f}m",
            f"",
            f"Rmin: {self.Rmin:.3f} m  (+/-)  [Ackermann-limited]",
            f"Inflation radius: {self.robot_radius:.3f} m  ([/])",
            f"Standoff: {self.standoff:.3f} m  (; / ')",
            f"Pos tol: {self.pos_tol:.3f} m  (, / .)",
            f"Ang tol: {math.degrees(self.ang_tol):.1f}°  (< / >)",
            f"DS={DS:.3f} | Lattice: {LAT_HEADINGS} hdg, {LAT_DSTEP*1000:.0f} mm, {LAT_TURN_DEG:.1f}°",
            "P=plan  A=animate  E=execute  T=simulate",
            "N=add at mouse   Del/Backspace=remove nearest   O=probe",
        ]
        for i,l in enumerate(lines):
            self.win.blit(self.font.render(l, True, (220,220,220)), (px, 20+22*i))

        if self.planner.active:
            ratio = self.planner.progress_ratio()
            bar_w = 320; bar_h = 10; x0,y0 = 10, 38
            pygame.draw.rect(self.win, (60,60,60), pygame.Rect(x0,y0,bar_w,bar_h), 1)
            pygame.draw.rect(self.win, (80,200,120), pygame.Rect(x0,y0,int(bar_w*ratio),bar_h))
            self.win.blit(self.font.render(self.planner.msg, True, (200,200,200)), (10, 55))
        if self.planner.last_error:
            txt = f"Last infeasible leg: {self.planner.last_error}   (try '[' ';' '+' or nudge obstacle)"
            self.win.blit(self.font.render(txt, True, C_WARN), (10, 75))

        if self.status_msg and time.time() < self.status_timer:
            self.win.blit(self.font.render(self.status_msg, True, self.status_color), (10, 95))

# -------------------
# main
# -------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serial", default="/dev/ttyUSB0", help="STM serial device (ignored when simulate-only is ON)")
    args = parser.parse_args()
    App(serial_port=args.serial).run()

if __name__ == "__main__":
    main()