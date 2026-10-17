"""#258 port film: one continuous 20 s camera (480 frames at 24 fps) in Cycles, replacing the six Higgsfield clips.
  Blender -b scene-work/blends/port_v3.3.blend --python blender/port20.py -- build scene-work/port20/port20.blend
  Blender -b scene-work/port20/port20.blend --python blender/port20.py -- check scene-work/port20/check
  Blender -b scene-work/port20/port20.blend --python blender/port20.py -- preview <outdir> [frames...]   (low samples)
  Blender -b scene-work/port20/port20.blend --python blender/port20.py -- final <outdir> <first> <last>
Built on port_v3.3 (sklib_port quay, cranes, ship, yard; port_rhd right-hand-drive cabs). Beats:
  1 an Indian RHD tractor with a 40 ft reefer rolls out of the terminal gate, camera behind-left and above, beside the
    gate canopy, never over or under its roof;
  2 it turns right onto the quay beside the docked ship and brakes (pitch forward, settle) under a light-grey STS crane;
  3 the spreader comes down on its taut ropes, locks, lifts, trolleys out and sets the box flush in the empty deck slot;
  4 the ship pulls off the berth on its own thrusters and screw, the only vessel on the water, leaving a wake;
  5 the camera rises into an eased aerial of the port and coast and finishes looking out over calm open sea.
The gate is moved up to the apron edge and crane 2 (with the ship, one bollard pitch) 15 m west, so the drive fits the
pacing at believable speeds. Tugs, tow lines, the anchorage and basin ships, the ocean patch and the hull draft
numerals are removed. All vehicles, the box, the crane and the ship are baked per frame, so nothing pops."""
import math
import os
import random
import sys
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, Quaternion
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FPS, F0, F1 = 24, 1, 480
GATE = Vector((-37.5, -47.0, 3.0))       # moved up from (-40, -78): the canopy now ends at the apron edge
LANE_X = GATE.x + 2.25                   # the hero's lane through the gate (lane 2 of 4)
R_TURN = 16.0                            # right turn onto the quay lane
QUAY_Y = -12.5                           # truck lane under the crane
CRANE_X = -15.0                          # crane 2 (and the ship's empty slot) moved one bollard pitch west
DX = CRANE_X - 0.0
STOP_X = CRANE_X + 5.5                   # tractor rear-axle origin with the box centred under the spreader
LOCK = 1.175                             # headblock origin above the container roof with the twistlocks seated
CH = 2.59
SUN_EL, SUN_AZ = math.radians(15.0), math.radians(200.0)   # low evening sun from the south-south-west (land side)
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OB = bpy.data.objects


# ---------------------------------------------------------------------------------------------------- small helpers
def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def fcurves(o):
    ad = o.animation_data if o else None
    if not ad or not ad.action:
        return []
    a = ad.action
    out = []
    for l in getattr(a, 'layers', ()):
        for st in l.strips:
            for cb in st.channelbags:
                out += list(cb.fcurves)
    return out or list(getattr(a, 'fcurves', ()))


def bake(o, path, rows, frames):
    """Key data path `path` of o on every frame from rows (one tuple per frame), linear in between."""
    o.animation_data_create()
    if o.animation_data.action is None:
        o.animation_data.action = bpy.data.actions.new(o.name + '_P20')
    act = o.animation_data.action
    for fc in [fc for fc in fcurves(o) if fc.data_path == path]:
        for cb in [cb for l in act.layers for st in l.strips for cb in st.channelbags]:
            if fc in list(cb.fcurves):
                cb.fcurves.remove(fc)
    n = len(rows[0])
    for i in range(n):
        fc = act.fcurve_ensure_for_datablock(o, path, index=i)
        fc.keyframe_points.add(len(frames))
        co = []
        for f, r in zip(frames, rows):
            co += [f, r[i]]
        fc.keyframe_points.foreach_set('co', co)
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'
        fc.update()


def kill(names):
    gone = set()
    for n in names:
        o = OB.get(n)
        if o is None:
            continue
        for c in list(o.children_recursive) + [o]:
            if c.name not in gone:
                gone.add(c.name)
    for n in gone:
        o = OB.get(n)
        if o is not None:
            bpy.data.objects.remove(o, do_unlink=True)
    return len(gone)


def shift_x(o, dx):
    fcs = [fc for fc in fcurves(o) if fc.data_path == 'location' and fc.array_index == 0]
    if fcs:
        for k in fcs[0].keyframe_points:
            k.co[1] += dx
            k.handle_left[1] += dx
            k.handle_right[1] += dx
    else:
        o.location.x += dx


def pchip(xs, ys):
    """Monotone cubic (Fritsch-Carlson) through (xs, ys): never overshoots a key. Returns f(x)."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0] = m[-1] = 0.0                                   # ease in and out of the first and last key

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t
        h01, h11 = -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


def gauss(vals, sigma):
    """Gaussian smoothing of a per-frame list (of floats or Vectors), ends held by reflection-free clamping."""
    if sigma <= 0:
        return list(vals)
    r = int(3 * sigma)
    w = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-r, r + 1)]
    out = []
    n = len(vals)
    for i in range(n):
        acc, ws = None, 0.0
        for k, wk in zip(range(-r, r + 1), w):
            v = vals[min(n - 1, max(0, i + k))]
            acc = v * wk if acc is None else acc + v * wk
            ws += wk
        out.append(acc / ws)
    return out


# ---------------------------------------------------------------------------------------------------- 1. clean-up
def cleanup():
    s = bpy.context.scene
    dead = [o.name for o in OB if o.parent is None and o.name.startswith(
        ('TUG', 'TOW_', 'BASIN_Ship', 'FARSHIP', 'Harbour', 'AHEAD0', 'QUEUE2.001', 'Camera_Portrait'))]
    dead += [o.name for o in OB if o.type == 'FONT']                         # hull draft numerals: no text
    dead += [o.name for o in OB if o.name.endswith(('_Driver', '_Driver_mesh'))]   # pre-RHD drivers, hidden anyway
    dead += [n for n in ('SHIP_Wake', 'SHIP_BowWave', 'TOW_Ship0', 'TOW_Ship1') if n in OB]
    print('P20 removed', kill(dead), 'objects')
    for o in OB:                                                  # nothing else may be keyed to pop in or out
        for fc in [fc for fc in fcurves(o) if fc.data_path.startswith('hide_')]:
            for cb in [cb for l in o.animation_data.action.layers for st in l.strips for cb in st.channelbags]:
                if fc in list(cb.fcurves):
                    cb.fcurves.remove(fc)
        if o.name.startswith('MOOR_'):
            o.hide_render = o.hide_viewport = False
    import still_fixes
    still_fixes.apply()                                           # dark steel reefer racks
    s.frame_start, s.frame_end = F0, F1


# ---------------------------------------------------------------------------------------------------- 2. layout moves
def relayout():
    g = OB['GATE']
    g.location = GATE
    for i in range(4):
        b = OB.get('GATE_Barrier%d' % i)
        if b is not None:
            b.animation_data_clear()
            b.rotation_euler = (0, 0, 0)
    OB['Crane_2'].location.x = CRANE_X
    shift_x(OB['SHIP'], DX)
    for o in OB:
        if o.parent is None and o.name.startswith(('MOOR_', 'BANKSMAN0')):
            shift_x(o, DX)
    shift_x(OB['AHEAD1'], 40.0)       # the truck ahead on the outer lane is already past the hero's turn
    sea = OB['SeaFull']
    sea.location.z = -0.05            # water surface at z 0, the hulls' waterline (the ocean patch is gone)


# ---------------------------------------------------------------------------------------------------- 3. hero truck
def hero_path():
    """Rear-axle path: straight out of the gate, R16 right turn, straight along the quay lane to the stop. Densified and
    Gaussian-smoothed over arc length, so curvature (and steering) builds up instead of snapping."""
    ds = 0.05
    pts = []
    y0, yt = GATE.y + 1.0 - 20.0, QUAY_Y - R_TURN
    y = y0
    while y < yt:
        pts.append(Vector((LANE_X, y)))
        y += ds
    c = Vector((LANE_X + R_TURN, yt))
    n = int((math.pi / 2 * R_TURN) / ds)
    for k in range(n):
        a = math.pi - (math.pi / 2) * k / n
        pts.append(c + R_TURN * Vector((math.cos(a), math.sin(a))))
    x = LANE_X + R_TURN
    while x < STOP_X + 20.0:
        pts.append(Vector((x, QUAY_Y)))
        x += ds
    sig = int(2.6 / ds)
    sm = []
    r = 3 * sig
    w = [math.exp(-0.5 * (k / sig) ** 2) for k in range(-r, r + 1, 4)]
    ks = list(range(-r, r + 1, 4))
    for i in range(len(pts)):
        acc, ws = Vector((0, 0)), 0.0
        for k, wk in zip(ks, w):
            acc += pts[min(len(pts) - 1, max(0, i + k))] * wk
            ws += wk
        sm.append(acc / ws)
    cum = [0.0]
    for i in range(1, len(sm)):
        cum.append(cum[-1] + (sm[i] - sm[i - 1]).length)
    i_start = min(range(len(sm)), key=lambda i: abs(sm[i].y - (GATE.y + 1.0)) + (99 if sm[i].x > LANE_X + 0.01 else 0))
    i_stop = min(range(len(sm)), key=lambda i: abs(sm[i].x - STOP_X) + (99 if abs(sm[i].y - QUAY_Y) > 0.01 else 0))
    return sm, cum, i_start, i_stop


def path_at(sm, cum, s):
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= s:
            lo = mid
        else:
            hi = mid
    t = (s - cum[lo]) / max(1e-9, cum[hi] - cum[lo])
    p = sm[lo].lerp(sm[hi], t)
    a, b = sm[max(0, lo - 10)], sm[min(len(sm) - 1, hi + 10)]
    tang = (b - a).normalized()
    a2, b2 = sm[max(0, lo - 40)], sm[min(len(sm) - 1, hi + 40)]
    h1, h2 = (sm[lo] - a2), (b2 - sm[hi])
    dpsi = math.atan2(h1.x * h2.y - h1.y * h2.x, h1.dot(h2))
    kappa = dpsi / max(1e-6, (h1.length + h2.length))          # signed curvature, left turn positive
    return p, tang, kappa


def sim_truck():
    """Driver model at 240 Hz: accelerate out of the gate, a curvature speed limit (2.9 m/s2 lateral) for the turn,
    then brake to stop exactly on the mark (constant-deceleration solve once it needs >= 2.6 m/s2). Pitch and roll
    come from a damped spring on the longitudinal and lateral acceleration, so the cab dips under braking and
    rocks back and settles when the truck stops."""
    sm, cum, i0, i1 = hero_path()
    s0, s_stop = cum[i0], cum[i1]
    dt = 1 / 240.0
    t, s, v, a = 0.0, s0, 4.6, 0.0
    braking, t_trig = False, None
    th = thd = ph = phd = 0.0
    w, z = 2 * math.pi * 1.15, 0.32
    rows = []
    stopped_at = None
    while t <= (F1 - F0) / FPS + 1e-6:
        p, tang, kap = path_at(sm, cum, s)
        if stopped_at is None:
            look = [path_at(sm, cum, s + d)[2] for d in (2, 5, 8, 11, 14)]
            km = max(abs(k) for k in look + [kap])
            vlim = 8.0 if km < 1e-3 else min(8.0, math.sqrt(2.9 / km))
            a_des = max(-1.6, min(1.25, (vlim - v) * 1.4))
            rem = s_stop - s
            a_req = v * v / (2 * rem) if rem > 1e-3 else 99.0
            if not braking and a_req >= 2.6:
                braking, t_trig = True, t
            if braking:
                a_des = -a_req
                a = a_des
            else:
                a += max(-5 * dt, min(5 * dt, a_des - a))
            v = max(0.0, v + a * dt)
            s += v * dt
            if rem < 0.002 or v < 0.03:
                s, v, a, stopped_at = s_stop, 0.0, 0.0, t
        lat = v * v * kap
        th_t = -math.radians(0.42) * a          # nose down under braking (+), up under acceleration
        ph_t = math.radians(0.28) * lat         # lean out of the turn
        thd += (w * w * (th_t - th) - 2 * z * w * thd) * dt
        th += thd * dt
        phd += (w * w * (ph_t - ph) - 2 * z * w * phd) * dt
        ph += phd * dt
        rows.append((t, s - s0, v, a, p.copy(), math.atan2(tang.y, tang.x), kap, th, ph))
        t += dt
    print('P20 truck: path %.1f m, braking from t=%.2f s, stopped at t=%.2f s (frame %.0f)' %
          (s_stop - s0, t_trig or -1, stopped_at or -1, 1 + (stopped_at or 0) * FPS))
    return rows, stopped_at


def animate_hero(rows):
    """Bake the tractor (root pose, body pitch/roll, front-wheel steer, wheel spin), the articulated trailer (tractrix
    with a 10.4 m kingpin-to-axle length, straightened over the last metres so the box is square under the spreader)
    and the trailer wheels. Returns per-frame trailer world matrices for the box."""
    s = bpy.context.scene
    root = OB['HERO']
    body = OB['HERO_Body']
    trailer = OB['HERO_Trailer']
    frames = list(range(F0, F1 + 1))
    per = [rows[min(len(rows) - 1, int(round((f - F0) / FPS * 240)))] for f in frames]
    s.frame_set(F0)
    z0 = root.location.z
    wheels = [c for c in root.children if 'Wheel' in c.name]
    twheels = [c for c in trailer.children if 'Wheel' in c.name]
    for o in [root, body, trailer] + wheels + twheels:
        o.animation_data_clear()
    LT = 10.4
    kp_local = trailer.location.copy()
    s_end = per[-1][1]
    loc_rows, rot_rows, tr_rows, wr, twr = [], [], [], [], []
    body_rows = []
    P = None
    dist_tr = 0.0
    prev_heading = None
    for (t, sd, v, a, p, hd, kap, th, ph) in per:
        if prev_heading is not None:
            while hd - prev_heading > math.pi:
                hd -= 2 * math.pi
            while hd - prev_heading < -math.pi:
                hd += 2 * math.pi
        prev_heading = hd
        K = Vector((p.x, p.y)) + Vector((math.cos(hd), math.sin(hd))) * kp_local.x
        if P is None:
            P = K - Vector((math.cos(hd), math.sin(hd))) * LT
        newP = K - (K - P).normalized() * LT
        dist_tr += (newP - P).length
        P = newP
        psi = math.atan2((K - P).y, (K - P).x)
        rel = (psi - hd + math.pi) % (2 * math.pi) - math.pi
        rel *= 1.0 - smoothstep(s_end - 15.0, s_end - 2.5, sd)
        P = K - Vector((math.cos(hd + rel), math.sin(hd + rel))) * LT
        loc_rows.append((p.x, p.y, z0))
        rot_rows.append((0.0, 0.0, hd))
        body_rows.append((ph, th, 0.0))
        tr_rows.append((0.0, 0.0, rel))
        wr.append((sd, math.atan(4.0 * kap)))
        twr.append(dist_tr)
    bake(root, 'location', loc_rows, frames)
    bake(root, 'rotation_euler', rot_rows, frames)
    bake(body, 'delta_rotation_euler', body_rows, frames)
    bake(trailer, 'rotation_euler', tr_rows, frames)
    for wobj in wheels:
        front = wobj.location.x > 2.0
        bake(wobj, 'rotation_euler', [(0.0, d / 0.52, st if front else 0.0) for d, st in wr], frames)
    for wobj in twheels:
        bake(wobj, 'rotation_euler', [(0.0, d / 0.52, 0.0) for d in twr], frames)
    # the gate barrier of the hero's lane is up as it rolls through and comes down once the trailer has cleared it
    bar = OB.get('GATE_Barrier2')
    if bar is not None:
        by = GATE.y - 2.0
        clear = next(f for f, r in zip(frames, per) if r[4].y - 13.0 > by)
        for f, ang in ((F0, -80.0), (clear + 10, -80.0), (clear + 40, 0.0)):
            bar.rotation_euler = (0, math.radians(ang), 0)
            bar.keyframe_insert('rotation_euler', index=1, frame=f)
        for fc in fcurves(bar):
            for k in fc.keyframe_points:
                k.interpolation = 'BEZIER'
                k.handle_left_type = k.handle_right_type = 'AUTO_CLAMPED'
    s.frame_set(F0)
    return per


# ---------------------------------------------------------------------------------------------------- 4. crane + box
def measure():
    """The box's seat on the trailer and its deck slot, from the base scene's own baked box (before anything moves)."""
    s = bpy.context.scene
    box, trailer, ship = OB['HERO_Reefer'], OB['HERO_Trailer'], OB['SHIP']
    s.frame_set(F0)
    m_tr = trailer.matrix_world.inverted() @ box.matrix_world
    s.frame_set(479)
    m_slot = ship.matrix_world.inverted() @ box.matrix_world
    s.frame_set(F0)
    return m_tr, m_slot


def crane_and_box(f_stop, m_tr, m_slot):
    """Crane 2 cycle and the box. Trolley (crane-local Y) and headblock (trolley-local Z) follow monotone keys, so the
    spreader eases between holds. The box is baked: on the trailer until the twistlocks lock, rigidly on the spreader
    until it is set down, then riding in its deck slot with the ship."""
    s = bpy.context.scene
    frames = list(range(F0, F1 + 1))
    box = OB['HERO_Reefer']
    trailer = OB['HERO_Trailer']
    ship = OB['SHIP']
    crane = OB['Crane_2']
    trol = OB['Crane_2_Trolley']
    head = OB['Crane_2_Headblock']
    sp = OB['Crane_2_Spreader']
    box.animation_data_clear()
    for o in (trol, head):
        o.animation_data_clear()
    # crane geometry
    gz = trol.location.z                                  # trolley rail height, crane local
    cz = crane.location.z
    s.frame_set(F0)
    ship0 = ship.matrix_world.copy()                      # docked pose (keys from 1 to the departure)
    slot_w = ship0 @ m_slot
    y_slot = slot_w.translation.y - crane.location.y
    z_slot = slot_w.translation.z + CH + LOCK - (cz + gz)
    assert abs(slot_w.translation.x - CRANE_X) < 0.05, ('slot not under crane 2', slot_w.translation.x)
    y_lane = QUAY_Y - crane.location.y
    box_top_truck = cz + 1.33 + CH                        # trailer deck height + box height, z of the roof on the truck
    z_truck = box_top_truck + LOCK - (cz + gz)
    z_up = -13.65
    z_clear = 32.2 + CH + LOCK - (cz + gz)                # box bottom 32.2 m: 2 m over the highest tier it passes
    fl = int(round(f_stop)) + 18                          # spreader seats on the box after the truck has settled
    keys = [(F0, 30.0, z_up), (34, 30.0, z_up), (150, y_lane, -30.0), (fl - 26, y_lane, z_truck + 3.2),
            (fl - 8, y_lane, z_truck + 0.6), (fl, y_lane, z_truck), (fl + 6, y_lane, z_truck),
            (fl + 22, y_lane + 1.0, z_truck + 6.0), (fl + 48, y_slot - 5.0, z_clear),
            (fl + 60, y_slot, z_slot + 3.0), (fl + 76, y_slot, z_slot), (fl + 84, y_slot, z_slot),
            (fl + 100, y_slot, z_slot + 6.5), (fl + 140, y_lane, z_up), (F1, y_lane, z_up)]
    fy = pchip([k[0] for k in keys], [k[1] for k in keys])
    fz = pchip([k[0] for k in keys], [k[2] for k in keys])
    bake(trol, 'location', [(0.0, fy(f), gz) for f in frames], frames)
    bake(head, 'location', [(0.0, 0.0, fz(f)) for f in frames], frames)
    f_lock, f_rel = fl + 3, fl + 79
    # boom of crane 2 tops up once its trolley is back over the quay (the other two cranes already have)
    hinge = OB['Crane_2_BoomHinge']
    hinge.animation_data_clear()
    fb = fl + 146
    hinge.rotation_euler = (0, 0, 0)
    hinge.keyframe_insert('rotation_euler', index=0, frame=fb)
    hinge.rotation_euler = (1.4, 0, 0)
    hinge.keyframe_insert('rotation_euler', index=0, frame=fb + 50)
    # box
    rows_l, rows_r = [], []
    s.frame_set(f_lock)
    m_sp = sp.matrix_world.inverted() @ (trailer.matrix_world @ m_tr)
    seq = []
    for f in frames:
        s.frame_set(f)
        if f < f_lock:
            mw = trailer.matrix_world @ m_tr
        elif f < f_rel:
            mw = sp.matrix_world @ m_sp
        else:
            mw = ship.matrix_world @ m_slot
        seq.append(mw)
    prev = None
    for mw in seq:
        l, q, _sc = mw.decompose()
        e = q.to_euler('XYZ', prev) if prev is not None else q.to_euler('XYZ')
        prev = e
        rows_l.append(tuple(l))
        rows_r.append(tuple(e))
    bake(box, 'location', rows_l, frames)
    bake(box, 'rotation_euler', rows_r, frames)
    print('P20 crane: seat f%d lock f%d release f%d boom up f%d-%d; slot y %.2f z %.2f' %
          (fl, f_lock, f_rel, fb, fb + 50, y_slot, z_slot))
    return {'f_land': fl, 'f_lock': f_lock, 'f_rel': f_rel, 'm_slot': m_slot, 'm_sp': m_sp}


# ---------------------------------------------------------------------------------------------------- 5. ship + wake
def depart(f_dep):
    """The ship leaves on its own: bow and stern thrusters walk it off the berth (+Y), the screw takes it ahead (+X),
    and it comes a few degrees to port. Keys from the base file are dropped after f_dep and the move is baked."""
    ship = OB['SHIP']
    s = bpy.context.scene
    s.frame_set(F0)
    p0 = ship.location.copy()
    frames = list(range(F0, F1 + 1))
    ship.animation_data_clear()
    locs, rots = [], []
    for f in frames:
        u = max(0.0, (f - f_dep) / FPS)
        lat = 2.6 * (u - 1.6 * (1 - math.exp(-u / 1.6)))            # thrusters: ~2.6 m/s off the berth after 3 s
        fwd = 1.15 * (u * u / 2) / (1 + u / 9.0)                    # screw: gathering way, ~7 m/s by the end
        yaw = math.radians(5.0) * smoothstep(0.0, 7.0, u)
        locs.append((p0.x + fwd, p0.y + lat, p0.z))
        rots.append((0.0, 0.0, yaw))
    bake(ship, 'location', locs, frames)
    bake(ship, 'rotation_euler', rots, frames)
    return locs, rots


def wake_material():
    """Foam on a ribbon laid along the stern's track. Each vertex carries the frame the stern passed it (tpass); the
    shader turns age = now - tpass into churned white water right behind the screw that spreads, breaks into streaks and
    fades over half a minute. Nothing exists ahead of the stern (age < 0), so the wake grows with the ship's motion."""
    m = bpy.data.materials.new('P20_Wake')
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    p = N['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.82, 0.86, 0.87, 1)
    p.inputs['Roughness'].default_value = 0.5

    def node(t, **kw):
        n = N.new(t)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def math_(op, a, b=None):
        n = node('ShaderNodeMath', operation=op)
        for i, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[i].default_value = x
            else:
                L.new(x, n.inputs[i])
        return n.outputs[0]
    now = node('ShaderNodeValue')
    now.label = 'frame'
    d = now.outputs[0].driver_add('default_value')
    d.driver.expression = 'frame'
    tp = node('ShaderNodeAttribute', attribute_name='tpass')
    ac = node('ShaderNodeAttribute', attribute_name='across')
    age = math_('DIVIDE', math_('SUBTRACT', now.outputs[0], tp.outputs['Fac']), float(FPS))     # seconds
    alive = math_('GREATER_THAN', age, 0.0)
    across = math_('ABSOLUTE', ac.outputs['Fac'])                     # metres from the track centre
    width = math_('ADD', 9.0, math_('MULTIPLY', age, 1.6))            # spreading turbulent wake
    edge = node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    L.new(across, edge.inputs['Value'])
    L.new(width, edge.inputs['From Min'])
    L.new(math_('MULTIPLY', width, 0.35), edge.inputs['From Max'])
    tc = node('ShaderNodeTexCoord')
    mp = node('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (0.09, 0.09, 0.09)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    nz = node('ShaderNodeTexNoise', noise_dimensions='4D')
    nz.inputs['Scale'].default_value = 3.0
    nz.inputs['Detail'].default_value = 10.0
    nz.inputs['Roughness'].default_value = 0.65
    L.new(mp.outputs[0], nz.inputs['Vector'])
    L.new(math_('MULTIPLY', now.outputs[0], 0.01), nz.inputs['W'])
    vr = node('ShaderNodeTexVoronoi', feature='F1')
    vr.inputs['Scale'].default_value = 28.0
    L.new(mp.outputs[0], vr.inputs['Vector'])
    foam = node('ShaderNodeMapRange')
    foam.inputs['From Min'].default_value, foam.inputs['From Max'].default_value = 0.40, 0.68
    L.new(math_('ADD', nz.outputs['Fac'], math_('MULTIPLY', vr.outputs['Distance'], 0.35)), foam.inputs['Value'])
    churn = node('ShaderNodeMapRange')                                # solid white water for the first seconds
    churn.inputs['From Min'].default_value, churn.inputs['From Max'].default_value = 1.0, 9.0
    churn.inputs['To Min'].default_value, churn.inputs['To Max'].default_value = 0.9, 0.0
    L.new(age, churn.inputs['Value'])
    fade = node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    fade.inputs['From Min'].default_value, fade.inputs['From Max'].default_value = 3.0, 40.0
    fade.inputs['To Min'].default_value, fade.inputs['To Max'].default_value = 0.85, 0.0
    L.new(age, fade.inputs['Value'])
    born = node('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
    born.inputs['From Min'].default_value, born.inputs['From Max'].default_value = 0.0, 0.6
    L.new(age, born.inputs['Value'])
    a = math_('MAXIMUM', math_('MULTIPLY', foam.outputs[0], fade.outputs[0]),
              math_('MULTIPLY', churn.outputs[0], math_('ADD', 0.35, math_('MULTIPLY', foam.outputs[0], 0.65))))
    a = math_('MULTIPLY', math_('MULTIPLY', a, edge.outputs[0]), math_('MULTIPLY', alive, born.outputs[0]))
    L.new(a, p.inputs['Alpha'])
    # churned water is also lighter, rougher green-white under the foam
    m.surface_render_method = 'BLENDED'
    return m


def wake(locs, rots, f_dep):
    """Ribbon along the stern track (one cross-section per frame from the departure, 80 m wide)."""
    stern = Vector((-112.0, 0.0, 0.0))
    W = 40.0
    bm = bmesh.new()
    tl = bm.verts.layers.float.new('tpass')
    al = bm.verts.layers.float.new('across')
    prev = None
    rows = []
    track = []
    for f, l, r in zip(range(F0, F1 + 1), locs, rots):
        if f < f_dep - 2:
            continue
        mw = Matrix.Translation(l) @ Euler(r).to_matrix().to_4x4()
        track.append((f, (mw @ stern).to_2d(), Euler(r).z))
    # extend the track back behind the stern (water the screw throws aft before the ship moves)
    f_a, p_a, h_a = track[0]
    back = [(f_a - 0.5 * k, p_a - Vector((math.cos(h_a), math.sin(h_a))) * (2.0 * k), h_a) for k in range(12, 0, -1)]
    for f, p, h in back + track:
        if prev is not None and (p - prev).length < 0.4 and f != track[-1][0]:
            continue
        prev = p
        nrm = Vector((-math.sin(h), math.cos(h)))
        row = []
        for j in range(9):
            acr = (j / 8 - 0.5) * 2 * W
            v = bm.verts.new((p.x + nrm.x * acr, p.y + nrm.y * acr, 0.03))
            v[tl] = f
            v[al] = acr
            row.append(v)
        rows.append(row)
    for i in range(len(rows) - 1):
        for j in range(8):
            bm.faces.new((rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]))
    me = bpy.data.meshes.new('P20_Wake')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(wake_material())
    o = bpy.data.objects.new('P20_Wake', me)
    bpy.context.scene.collection.objects.link(o)
    o.visible_shadow = False
    return o


# ---------------------------------------------------------------------------------------------------- 6. look
def antitile(m, seed_attr=None):
    """Break up image tiling: every image node gets a twin sampled through a rotated, offset, rescaled copy of its
    coordinates, blended in by a low-frequency noise mask (a few tiles across). With seed_attr (the per-container colour)
    the coordinates are also offset per box, so neighbouring containers never show the same patch."""
    if m is None or m.get('p20_antitile') or not m.node_tree:
        return
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    imgs = [n for n in N if n.type == 'TEX_IMAGE' and n.inputs['Vector'].links]
    if not imgs:
        return
    srcs = {}
    for n in imgs:
        srcs.setdefault(n.inputs['Vector'].links[0].from_socket, []).append(n)
    for src, nodes in srcs.items():
        vec = src
        if seed_attr:
            at = N.new('ShaderNodeAttribute')
            at.attribute_name = seed_attr
            sc = N.new('ShaderNodeVectorMath')
            sc.operation = 'SCALE'
            sc.inputs['Scale'].default_value = 23.7
            L.new(at.outputs['Vector'], sc.inputs[0])
            ad = N.new('ShaderNodeVectorMath')
            ad.operation = 'ADD'
            L.new(src, ad.inputs[0])
            L.new(sc.outputs[0], ad.inputs[1])
            vec = ad.outputs[0]
            for n in nodes:
                L.new(vec, n.inputs['Vector'])
        mb = N.new('ShaderNodeMapping')
        mb.inputs['Location'].default_value = (0.371, 0.613, 0.0)
        mb.inputs['Rotation'].default_value = (0.0, 0.0, 1.13)
        mb.inputs['Scale'].default_value = (1.17, 1.17, 1.17)
        L.new(vec, mb.inputs['Vector'])
        mk = N.new('ShaderNodeTexNoise')
        mk.inputs['Scale'].default_value = 0.33
        mk.inputs['Detail'].default_value = 3.0
        L.new(vec, mk.inputs['Vector'])
        mr = N.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value, mr.inputs['From Max'].default_value = 0.44, 0.56
        L.new(mk.outputs['Fac'], mr.inputs['Value'])
        for n in nodes:
            twin = N.new('ShaderNodeTexImage')
            twin.image = n.image
            twin.interpolation = n.interpolation
            twin.projection = n.projection
            twin.projection_blend = n.projection_blend
            twin.extension = n.extension
            L.new(mb.outputs[0], twin.inputs['Vector'])
            for out in ('Color', 'Alpha'):
                links = list(n.outputs[out].links)
                if not links:
                    continue
                mx = N.new('ShaderNodeMix')
                mx.data_type = 'RGBA' if out == 'Color' else 'FLOAT'
                ia, ib = (6, 7) if out == 'Color' else (2, 3)
                L.new(mr.outputs[0], mx.inputs[0])
                L.new(n.outputs[out], mx.inputs[ia])
                L.new(twin.outputs[out], mx.inputs[ib])
                o_s = mx.outputs[2] if out == 'Color' else mx.outputs[0]
                for lk in links:
                    to = lk.to_socket
                    L.remove(lk)
                    L.new(o_s, to)
    m['p20_antitile'] = True


def look():
    s = bpy.context.scene
    from sklib import pbr
    grey = pbr('P20_CraneGrey', (0.66, 0.68, 0.69), 0.42, 0.12, var=0.06, bump=0.04, scale=0.12, grime=0.12)
    dgrey = pbr('P20_CraneGreyDark', (0.42, 0.44, 0.46), 0.45, 0.15, var=0.07, bump=0.04, scale=0.2, grime=0.12)
    for o in OB:
        if o.type == 'MESH' and o.name.startswith('Crane_'):
            for sl in o.material_slots:
                if sl.material and 'CraneWhite' in sl.material.name:
                    sl.material = grey
                elif sl.material and 'CraneBlue' in sl.material.name:
                    sl.material = dgrey
    keys = ('concrete_floor', 'asphalt', 'aerial_grass', 'painted_concrete', 'container_side', 'Metal009', 'PaintedMetal')
    for m in bpy.data.materials:
        if m.node_tree and any(n.type == 'TEX_IMAGE' and n.image and n.image.name.startswith(keys) for n in m.node_tree.nodes):
            antitile(m, 'col' if 'Container' in m.name else None)
    water()
    # sky, sun and grade
    d = Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))
    sun = OB['Sun']
    sun.rotation_mode = 'QUATERNION'
    sun.rotation_quaternion = (-d).to_track_quat('-Z', 'Y')
    sun.data.energy = 4.2
    sun.data.color = (1.0, 0.77, 0.56)
    sun.data.angle = math.radians(1.6)
    w = bpy.data.worlds.new('P20_World')
    w.use_nodes = True
    nt = w.node_tree
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_disc = False
    sky.sun_elevation = SUN_EL
    sky.sun_rotation = math.atan2(d.x, d.y)
    for attr, v in (('altitude', 30.0), ('air_density', 1.0), ('aerosol_density', 2.2), ('dust_density', 2.2),
                    ('ozone_density', 1.0)):
        if hasattr(sky, attr):
            setattr(sky, attr, v)
    bg = nt.nodes['Background']
    bg.inputs['Strength'].default_value = 0.32
    nt.links.new(sky.outputs['Color'], bg.inputs['Color'])
    s.world = w
    w.mist_settings.falloff = 'LINEAR'
    vs = s.view_settings
    vs.view_transform = 'AgX'
    vs.look = 'AgX - Medium High Contrast'
    vs.exposure = 0.0


def water():
    """The sea: the base procedural water, its ripple noises made 4D and driven by time so the surface moves."""
    m = bpy.data.materials.get('MAT_Water_Port')
    if m is None:
        return
    for n in m.node_tree.nodes:
        if n.type == 'TEX_NOISE':
            n.noise_dimensions = '4D'
            dr = n.inputs['W'].driver_add('default_value')
            rate = 0.5 * min(2.0, 1.25 * math.sqrt(n.inputs['Scale'].default_value))    # small ripples change fastest
            dr.driver.expression = 'frame/24*%.4f' % rate


def haze_grade(mist_keys):
    """Aerial perspective from the mist pass (keyed: start and depth grow as the camera climbs), a warm-highlight /
    cool-shadow balance and a soft vignette."""
    s = bpy.context.scene
    vl = s.view_layers[0]
    vl.use_pass_mist = True
    w = s.world
    for f, st, dp in mist_keys:
        w.mist_settings.start, w.mist_settings.depth = st, dp
        w.mist_settings.keyframe_insert('start', frame=f)
        w.mist_settings.keyframe_insert('depth', frame=f)
    ng = bpy.data.node_groups.new('P20_Comp', 'CompositorNodeTree')
    N, L = ng.nodes, ng.links
    rl = N.new('CompositorNodeRLayers')
    out = N.new('NodeGroupOutput')
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    mix = N.new('ShaderNodeMix')
    mix.data_type = 'RGBA'
    fac = N.new('ShaderNodeMath')
    fac.operation = 'MULTIPLY'
    fac.inputs[1].default_value = 0.55
    L.new(rl.outputs['Mist'], fac.inputs[0])
    L.new(fac.outputs[0], mix.inputs[0])
    L.new(rl.outputs['Image'], mix.inputs[6])
    mix.inputs[7].default_value = (0.62, 0.62, 0.66, 1.0)
    cb = N.new('CompositorNodeColorBalance')
    cin = next(i for i in cb.inputs if i.type == 'RGBA' and i.name in ('Image', 'Color'))
    L.new(mix.outputs[2], cin)
    print('P20 colour balance inputs', [(i.name, i.type) for i in cb.inputs])
    for i in cb.inputs:                                   # lift / gamma / gain: warm highlights, a touch cooler shadows
        if i.type == 'RGBA' and i.name == 'Gain':
            i.default_value = (1.025, 1.0, 0.965, 1)
        elif i.type == 'RGBA' and i.name == 'Lift':
            i.default_value = (0.99, 1.0, 1.02, 1)
    L.new(next(o for o in cb.outputs if o.type == 'RGBA'), out.inputs['Image'])
    s.compositing_node_group = ng
    s.render.use_compositing = True


# ---------------------------------------------------------------------------------------------------- 7. camera
def hero_xy(per, f):
    r = per[f - F0]
    return r[4], r[5]


def camera(per, cr, f_dep):
    """One camera. Keys are (frame, position, look-at); each channel is a monotone cubic through its keys (no
    overshoot), then the whole move is Gaussian-smoothed (sigma 5 frames) so velocity and acceleration have no
    corners; orientation is a roll-free look-at, baked per frame as a quaternion."""
    s = bpy.context.scene

    def tr(f, fwd=0.0, side=0.0, z=0.0):            # a point on the truck: metres ahead, to its left, height
        p, h = hero_xy(per, f)
        return Vector((p.x + math.cos(h) * fwd - math.sin(h) * side, p.y + math.sin(h) * fwd + math.cos(h) * side, 3.0 + z))
    fl, fr = cr['f_land'], cr['f_rel']
    slot = (OB['SHIP'].matrix_world @ cr['m_slot']).translation
    K = [
        (F0, Vector((-51.6, -64.0, 8.6)), tr(F0, 2.0, 0.0, 2.6)),
        (36, Vector((-51.4, -52.0, 9.0)), tr(36, 2.5, 0.0, 2.4)),
        (70, Vector((-49.5, -37.0, 11.0)), tr(70, 4.0, 0.0, 2.0)),
        (105, Vector((-45.0, -27.0, 12.0)), tr(105, 6.0, 0.0, 2.0)),
        (140, Vector((-39.0, -21.5, 11.6)), tr(140, 6.0, 0.0, 2.0)),
        (175, Vector((-33.5, -19.5, 10.4)), tr(175, 4.0, 0.0, 2.5)),
        (fl - 20, Vector((-31.0, -20.0, 9.0)), tr(fl - 20, -2.0, 0.0, 3.5)),
        (fl + 4, Vector((-31.5, -21.0, 8.4)), Vector((CRANE_X, QUAY_Y, 11.0))),
        (fl + 30, Vector((-33.0, -17.0, 13.0)), Vector((CRANE_X, QUAY_Y + 3.0, 19.0))),
        (fl + 55, Vector((-36.0, -9.0, 25.0)), Vector((CRANE_X, slot.y - 6.0, 31.0))),
        (fr, Vector((-38.0, -2.0, 36.0)), Vector((CRANE_X, slot.y, slot.z + 1.5))),
        (f_dep + 6, Vector((-44.0, -12.0, 52.0)), Vector((CRANE_X + 4.0, 22.0, 16.0))),
        (f_dep + 36, Vector((-70.0, -95.0, 150.0)), Vector((0.0, 32.0, 4.0))),
        (400, Vector((-30.0, -120.0, 420.0)), Vector((0.0, 10.0, 0.0))),
        (436, Vector((0.0, -50.0, 860.0)), Vector((0.0, -28.0, 0.0))),
        (456, Vector((0.0, 60.0, 1000.0)), Vector((0.0, 250.0, 0.0))),
        (F1, Vector((0.0, 380.0, 1150.0)), Vector((0.0, 1530.0, 0.0))),
    ]
    K.sort(key=lambda k: k[0])
    frames = list(range(F0, F1 + 1))
    xs = [k[0] for k in K]
    pos = [Vector([pchip(xs, [k[1][i] for k in K])(f) for i in range(3)]) for f in frames]
    tgt = [Vector([pchip(xs, [k[2][i] for k in K])(f) for i in range(3)]) for f in frames]
    pos = gauss(pos, 5.0)
    tgt = gauss(tgt, 5.0)
    cam = OB.get('Camera')
    cam.animation_data_clear()
    for c in list(cam.constraints):
        cam.constraints.remove(c)
    cam.data.lens = 28.0
    cam.data.clip_start, cam.data.clip_end = 0.1, 20000.0
    cam.data.dof.use_dof = False
    cam.data.sensor_width = 36.0
    cam.rotation_mode = 'QUATERNION'
    qs = []
    prev = None
    for p, t in zip(pos, tgt):
        q = (t - p).to_track_quat('-Z', 'Y')
        if prev is not None and prev.dot(q) < 0:
            q.negate()
        prev = q
        qs.append(tuple(q))
    bake(cam, 'location', [tuple(p) for p in pos], frames)
    bake(cam, 'rotation_quaternion', qs, frames)
    s.camera = cam
    return pos, tgt


# ---------------------------------------------------------------------------------------------------- 8. render setup
def cycles(samples=96, pct=100, mblur=True):
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    pr = bpy.context.preferences.addons['cycles'].preferences
    pr.compute_device_type = 'METAL'
    pr.get_devices()
    for d in pr.devices:
        d.use = d.type == 'METAL'
    c = s.cycles
    c.device = 'GPU'
    c.samples = samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.03
    c.adaptive_min_samples = 16
    c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'
    c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.denoising_prefilter = 'ACCURATE'
    c.denoising_use_gpu = True
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 6, 3, 3
    c.transmission_bounces, c.transparent_max_bounces, c.volume_bounces = 4, 16, 0
    c.sample_clamp_direct, c.sample_clamp_indirect = 0.0, 4.0
    c.caustics_reflective = c.caustics_refractive = False
    c.blur_glossy = 1.0
    r = s.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, pct
    r.fps, r.fps_base = FPS, 1.0
    r.use_motion_blur = mblur
    r.motion_blur_shutter = 0.4
    r.use_persistent_data = True
    r.film_transparent = False
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    r.image_settings.color_depth = '16'
    r.image_settings.compression = 15
    r.use_overwrite = False
    r.use_placeholder = True


def build(out):
    s = bpy.context.scene
    cleanup()
    m_tr, m_slot = measure()
    print('P20 seat', [round(v, 3) for v in m_tr.translation], 'slot', [round(v, 3) for v in m_slot.translation],
          [round(math.degrees(v), 2) for v in m_slot.to_euler()])
    relayout()
    rows, t_stop = sim_truck()
    per = animate_hero(rows)
    f_stop = 1 + t_stop * FPS
    cr = crane_and_box(f_stop, m_tr, m_slot)
    f_dep = cr['f_rel'] + 14
    locs, rots = depart(f_dep)
    # re-bake the box on its deck slot now that the ship's departure is final
    cr = crane_and_box(f_stop, m_tr, m_slot)
    wake(locs, rots, f_dep)
    look()
    pos, tgt = camera(per, cr, f_dep)
    haze_grade([(F0, 120.0, 2200.0), (f_dep, 160.0, 2600.0), (420, 700.0, 5200.0), (F1, 1000.0, 7000.0)])
    cycles()
    s['p20'] = {'f_stop': f_stop, 'f_land': cr['f_land'], 'f_lock': cr['f_lock'], 'f_rel': cr['f_rel'], 'f_dep': f_dep}
    print('P20 beats', dict(s['p20']))
    s.frame_set(F0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    print('P20 OUT', out)


def render_frames(outdir, frames, samples, pct=100, mblur=True):
    s = bpy.context.scene
    cycles(samples, pct, mblur)
    s.render.use_overwrite = True
    s.render.use_placeholder = False
    os.makedirs(outdir, exist_ok=True)
    import time
    for f in frames:
        t = time.time()
        s.frame_set(f)
        s.render.filepath = os.path.join(os.path.abspath(outdir), 'f%04d.png' % f)
        bpy.ops.render.render(write_still=True)
        print('P20 frame %d %.1fs' % (f, time.time() - t), flush=True)


# ---------------------------------------------------------------------------------------------------- 9. checks
def _dynamic(o):
    """Moves during the shot: keyed, constrained or armature-deformed, itself or through a parent."""
    p = o
    while p is not None:
        if fcurves(p) or p.constraints or any(m.type == 'ARMATURE' for m in getattr(p, 'modifiers', ())):
            return True
        p = p.parent
    return False


def _world_bvh(objs, dg):
    from mathutils.bvhtree import BVHTree
    vs, ps = [], []
    for o in objs:
        ev = o.evaluated_get(dg)
        try:
            me = ev.to_mesh()
        except RuntimeError:
            continue
        if me is None:
            continue
        mw = ev.matrix_world
        b = len(vs)
        vs += [mw @ v.co for v in me.vertices]
        ps += [tuple(b + i for i in p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(vs, ps, all_triangles=False) if ps else None


def _near(o, pts, r):
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector([min(v[i] for v in bb) for i in range(3)]) - Vector((r, r, r))
    hi = Vector([max(v[i] for v in bb) for i in range(3)]) + Vector((r, r, r))
    return any(lo.x <= p.x <= hi.x and lo.y <= p.y <= hi.y and lo.z <= p.z <= hi.z for p in pts)


def check(outdir):
    """Programmatic checks, per frame: camera clearance (nearest surface, up/down rays for being inside a closed mesh,
    the segment to the next frame's position against everything), the box rigidly on the trailer / spreader / ship and
    never inside anything, no vessel but the ship, no text or logo, nothing keyed to pop, people on screen moving,
    camera speed / acceleration / jerk and turn rate."""
    import json
    from bpy_extras.object_utils import world_to_camera_view as w2c
    s = bpy.context.scene
    os.makedirs(outdir, exist_ok=True)
    b = dict(s['p20'])
    cam = s.camera
    frames = list(range(F0, F1 + 1))
    cps = []
    for f in frames:
        s.frame_set(f)
        cps.append(cam.matrix_world.translation.copy())
    low = [p for p in cps if p.z < 200]
    rend = [o for o in OB if o.type == 'MESH' and not o.hide_render and o.visible_get() is not None]
    dyn = [o for o in rend if _dynamic(o)]
    sta = [o for o in rend if o not in dyn and _near(o, low, 30.0)]
    dg = bpy.context.evaluated_depsgraph_get()
    s.frame_set(F0)
    static = _world_bvh(sta, dg)
    print('P20 check: %d static meshes near the low camera path, %d dynamic' % (len(sta), len(dyn)))
    box, sp, tr, ship = OB['HERO_Reefer'], OB['Crane_2_Spreader'], OB['HERO_Trailer'], OB['SHIP']
    rel0 = {}
    res = []
    prev = None
    for i, f in enumerate(frames):
        s.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        p = cps[i]
        near_dyn = [o for o in dyn if _near(o, [p], 25.0) and o != box]
        dbvh = _world_bvh(near_dyn, dg) if near_dyn else None
        clear, inside, cross = 1e9, [], False
        for name, t in (('static', static), ('dynamic', dbvh)):
            if t is None:
                continue
            hit = t.find_nearest(p)
            if hit[0] is not None:
                clear = min(clear, hit[3])
            for d in (Vector((0, 0, 1)), Vector((0, 0, -1))):
                h = t.ray_cast(p, d, 500.0)
                if h[0] is not None and h[1].dot(d) > 0:
                    inside.append((name, tuple(d)))
            if prev is not None and (p - prev).length > 1e-6:
                h = t.ray_cast(prev, (p - prev).normalized(), (p - prev).length)
                if h[0] is not None:
                    cross = True
        # the box: which phase, and its pose relative to what carries it
        ph = 'trailer' if f < b['f_lock'] else 'spreader' if f < b['f_rel'] else 'ship'
        carrier = {'trailer': tr, 'spreader': sp, 'ship': ship}[ph]
        rel = carrier.matrix_world.inverted() @ box.matrix_world
        if ph not in rel0:
            rel0[ph] = rel
        drift = max(abs(a - c) for ra, rc in zip(rel, rel0[ph]) for a, c in zip(ra, rc))
        # people on screen that do not move over +-12 frames
        frozen = []
        for o in OB:
            if o.type != 'ARMATURE' or o.parent is not None or not any(not c.hide_render for c in o.children):
                continue
            q = w2c(s, cam, o.matrix_world.translation)
            dist = (o.matrix_world.translation - p).length
            if 0 < q.z and -0.05 < q.x < 1.05 and -0.05 < q.y < 1.05 and dist < 160:
                frozen.append(o.name)
        res.append({'f': f, 'cam': [round(v, 2) for v in p], 'clear': round(clear, 2), 'inside': inside, 'cross': cross,
                    'box': ph, 'drift': drift, 'people': frozen})
        prev = p
        if f % 24 == 1:
            print('P20 check f%d clear %.2f inside %s cross %s box %s drift %.2e' % (f, clear, inside, cross, ph, drift),
                  flush=True)
    # people: pose change around each on-screen frame
    pose_sig = {}
    for f in frames[::4]:
        s.frame_set(f)
        for o in OB:
            if o.type == 'ARMATURE' and o.parent is None:
                pose_sig.setdefault(o.name, {})[f] = sum((pb.matrix.to_translation()).length +
                                                        sum(abs(x) for x in pb.matrix.to_euler()) for pb in o.pose.bones)
    froz = set()
    for r in res:
        for n in r['people']:
            sig = pose_sig.get(n, {})
            near = [v for k, v in sig.items() if abs(k - r['f']) <= 12]
            if near and max(near) - min(near) < 0.02:
                froz.add((n, r['f']))
    # box flush on the deck and never inside the stacks
    s.frame_set(b['f_rel'])
    dg = bpy.context.evaluated_depsgraph_get()
    stacks = _world_bvh([OB['SHIP_Stacks']], dg)
    mw = box.matrix_world
    flush = []
    for sx in (-5.5, 5.5):
        for sy in (-0.9, 0.9):
            c = mw @ Vector((sx, sy, 0.0))
            h = stacks.ray_cast(c + Vector((0, 0, 0.5)), Vector((0, 0, -1)), 3.0)
            flush.append(round(h[3] - 0.5, 4) if h[0] is not None else None)
    lo, hi = Vector((-6.0, -1.17, 0.03)), Vector((6.0, 1.17, CH - 0.03))
    inter = []
    from mathutils.bvhtree import BVHTree
    bv = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    bf = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    for f in range(b['f_lock'] - 30, min(F1, b['f_rel'] + 40)):
        s.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        bb = BVHTree.FromPolygons([box.matrix_world @ v for v in bv], bf)
        others = [OB['SHIP_Stacks'], OB['SHIP_Hull'], OB['HERO_Trailer_Chassis'], OB['SHIP_Superstructure']]
        others += [o for o in OB if o.name.startswith('Crane_2_') and o.type == 'MESH' and 'Spreader' not in o.name]
        ob = _world_bvh(others, dg)
        if bb.overlap(ob):
            inter.append(f)
    # vessels, text, logos, pop keys
    vessels = [o.name for o in OB if o.parent is None and not o.hide_render and
               any(k in o.name.upper() for k in ('TUG', 'BOAT', 'VESSEL', 'FARSHIP', 'BASIN', 'TOW_'))]
    fonts = [o.name for o in OB if o.type == 'FONT']
    logos = [i.name for i in bpy.data.images if any(k in i.name.lower() for k in ('logo', 'text', 'brand', 'plate', 'sign'))]
    pops = [(o.name, fc.data_path) for o in OB for fc in fcurves(o) if fc.data_path.startswith(('hide_', 'scale'))
            and o.name != 'P20_Wake']
    # camera dynamics
    v = [(cps[i + 1] - cps[i]) * FPS for i in range(len(cps) - 1)]
    a = [(v[i + 1] - v[i]) * FPS for i in range(len(v) - 1)]
    j = [(a[i + 1] - a[i]) * FPS for i in range(len(a) - 1)]
    dirs = []
    for f in frames:
        s.frame_set(f)
        dirs.append(cam.matrix_world.to_quaternion() @ Vector((0, 0, -1)))
    turn = [math.degrees(dirs[i].angle(dirs[i + 1])) * FPS for i in range(len(dirs) - 1)]
    dyn_rows = [{'f': F0 + i, 'speed': round(v[i].length, 2), 'acc': round(a[i].length, 2) if i < len(a) else None,
                 'jerk': round(j[i].length, 2) if i < len(j) else None, 'turn_dps': round(turn[i], 2)}
                for i in range(len(v))]
    report = {'beats': b, 'per_frame': res, 'frozen_people': sorted(froz), 'flush_gaps_m': flush,
              'box_intersections': inter, 'vessels': vessels, 'fonts': fonts, 'logo_images': logos, 'pop_keys': pops,
              'camera_dynamics': dyn_rows,
              'max': {'speed': max(r['speed'] for r in dyn_rows), 'acc': max(r['acc'] or 0 for r in dyn_rows),
                      'jerk': max(r['jerk'] or 0 for r in dyn_rows), 'turn_dps': max(r['turn_dps'] for r in dyn_rows),
                      'min_clear': min(r['clear'] for r in res),
                      'max_drift': max(r['drift'] for r in res)},
              'inside_frames': [r['f'] for r in res if r['inside']], 'cross_frames': [r['f'] for r in res if r['cross']]}
    with open(os.path.join(outdir, 'checks.json'), 'w') as fh:
        json.dump(report, fh, indent=1, default=str)
    print('P20 CHECK', json.dumps({k: report[k] for k in ('max', 'inside_frames', 'cross_frames', 'flush_gaps_m',
                                                          'box_intersections', 'vessels', 'fonts', 'logo_images',
                                                          'pop_keys', 'frozen_people')}, default=str))


if __name__ == '__main__':
    mode = ARGS[0] if ARGS else 'build'
    if mode == 'check':
        check(ARGS[1])
    if mode == 'build':
        build(ARGS[1])
    elif mode == 'preview':
        fr = [int(x) for x in ARGS[2:]] or list(range(1, 482, 24))
        render_frames(ARGS[1], [min(F1, f) for f in fr], int(os.environ.get('P20_SAMPLES', 24)),
                      int(os.environ.get('P20_PCT', 100)), os.environ.get('P20_MBLUR', '1') == '1')
    elif mode == 'final':
        fr = [f for f in range(int(ARGS[2]), int(ARGS[3]) + 1)
              if not os.path.exists(os.path.join(ARGS[1], 'f%04d.png' % f))]           # resumable
        render_frames(ARGS[1], fr, int(os.environ.get('P20_SAMPLES', 96)))
