# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - pipeline v7: ciclo di render delle animazioni (dalla prova spike-sprite-v7).

Sorgenti di un'animazione (campo "src" del lavoro):
  "guard"        guardia con respiro (come prima, GuardIdle di char_build)
  "tl:<mossa>"   traccia di pose chiave di anim_v7 (pose_at(tick)); i fotogrammi hanno "at" (tick della traccia)
  "<clip>"       clip UAL/M2M; i fotogrammi hanno "f" anche frazionario (sotto-fotogrammi di Blender)
Opzioni per animazione: "upper": "guard" (braccia in guardia sopra la clip), "stride": s (passo allungato di s
con IK sui piedi), "period" (periodo della sorgente nei cicli), "loop", "spring" (molla del codino).
Per fotogramma: "smear": ["fist_l", ...] -> punti dei sotto-istanti fra il fotogramma prima e questo ("trail").
"""
import json
import math
import os
import time

import bpy
from mathutils import Quaternion, Vector

import char_anim as A7
import char_poses

ARM_ROT = ("upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r", "hand_r")


def extra_points(ns, arm, cam, L, fd):
    """punti del viso e del codino per i timbri e le misure (aggiunti a fd["points"])."""
    pbH = arm.pose.bones["Head"]
    Mh = arm.matrix_world @ pbH.matrix @ arm.data.bones["Head"].matrix_local.inverted() @ arm.matrix_world.inverted()
    pts = fd.setdefault("points", {})
    brow_r = L["eye_r"] + Vector((0.0, -0.004, 0.026))
    brow_l = L["eye_l"] + Vector((0.0, -0.004, 0.026))
    for name, P in (("eye_r", L["eye_r"]), ("eye_l", L["eye_l"]), ("nose", L["nose"]), ("mouth", L["mouth"]),
                    ("chin", L["chin"]), ("brow_r", brow_r), ("brow_l", brow_l)):
        u, v, d = cam.project(Mh @ P)
        pts[name] = [round(u, 3), round(v, 3), round(d, 4)]
    if "topknot" in arm.pose.bones:
        pb = arm.pose.bones["topknot"]
        for nm, P in (("topknot_base", arm.matrix_world @ pb.head), ("topknot_tip", arm.matrix_world @ pb.tail)):
            u, v, d = cam.project(P)
            pts[nm] = [round(u, 3), round(v, 3), round(d, 4)]
    # centro dei pugni (per i timbri delle mani)
    for side in ("l", "r"):
        h, t = ns["bone_world"](arm, "hand_" + side)
        c = h + (t - h).normalized() * 0.06
        u, v, d = cam.project(c)
        pts["fistc_" + side] = [round(u, 3), round(v, 3), round(d, 4)]


def trail_points(ns, arm, cam, names):
    out = {}
    pts = {}
    for side in ("l", "r"):
        h, t = ns["bone_world"](arm, "hand_" + side)
        pts["fist_" + side] = h + (t - h).normalized() * 0.08
        fh, ft = ns["bone_world"](arm, "ball_" + side)
        pts["toe_" + side] = ft
        pts["heel_" + side] = ns["bone_world"](arm, "foot_" + side)[0]
    for n in names:
        if n in pts:
            u, v, d = cam.project(pts[n])
            out[n] = [round(u, 3), round(v, 3), round(d, 4)]
    return out


class StrideIK:
    """passo allungato: ogni piede va dove la clip lo mette, con la distanza avanti-dietro dal bacino moltiplicata
    per s (IK a due ossa, rotazione del piede copiata dalla clip). Serve a camminare a 1,5 px per tick con una
    cadenza da camminata e senza scivolare."""

    def __init__(self, ns, arm, s):
        self.ns, self.arm, self.s = ns, arm, s
        self.empties, self.cons = [], []
        for side in ("l", "r"):
            e = ns["link"](bpy.data.objects.new("SIK_" + side, None))
            self.empties.append(e)

    def solve(self, scene):
        arm = self.arm
        bpy.context.view_layer.update()
        pel = (arm.matrix_world @ arm.pose.bones["pelvis"].head)
        fwd = Vector((0, -1, 0))
        mws = []
        for side in ("l", "r"):
            fb = arm.pose.bones["foot_" + side]
            mws.append((arm.matrix_world @ fb.matrix).copy())
        for (side, e, mw) in zip("lr", self.empties, mws):
            P = mw.to_translation()
            off = (P - pel).dot(fwd)
            newP = P + fwd * (off * (self.s - 1.0))
            m = mw.copy()
            m.translation = newP
            e.matrix_world = m
        if not self.cons:
            for side, e in zip("lr", self.empties):
                ik = arm.pose.bones["calf_" + side].constraints.new("IK")
                ik.target = e
                ik.chain_count = 2
                ik.use_tail = True
                cr = arm.pose.bones["foot_" + side].constraints.new("COPY_ROTATION")
                cr.target = e
                self.cons += [(arm.pose.bones["calf_" + side], ik), (arm.pose.bones["foot_" + side], cr)]
        for pb, c in self.cons:
            c.mute = False
        bpy.context.view_layer.update()

    def off(self):
        for pb, c in self.cons:
            c.mute = True
        bpy.context.view_layer.update()

    def end(self):
        for pb, c in self.cons:
            pb.constraints.remove(c)
        self.cons = []
        self.ns["delete_objects"](self.empties)


# ============================================================== braccio morto (GIG prima del riavvio)
FWD = Vector((0.0, -1.0, 0.0))     # davanti del personaggio nel render (guarda -Y)
UP = Vector((0.0, 0.0, 1.0))


def chest_axes(ns, arm):
    """spalla sinistra (mondo), asse delle spalle verso sinistra (X) e alto del busto (U)."""
    bw = ns["bone_world"]
    S = bw(arm, "upperarm_l")[0]
    X = (S - bw(arm, "upperarm_r")[0]).normalized()
    up = bw(arm, "neck_01")[0] - bw(arm, "spine_01")[0]
    U = (up - X * up.dot(X)).normalized()
    return S, X, U


def _vel_at(v, tau):
    """velocità del corpo nel gioco (avanti, su) in m/s, cioè px/tick: [a, b] fissa, oppure
    [[tick, avanti, su], ...] a tratti lineari."""
    if not v or not isinstance(v[0], (list, tuple)):
        return (float(v[0]), float(v[1])) if v else (0.0, 0.0)
    if tau <= v[0][0]:
        return float(v[0][1]), float(v[0][2])
    for a, b in zip(v, v[1:]):
        if a[0] <= tau <= b[0]:
            u = (tau - a[0]) / max(b[0] - a[0], 1e-6)
            return a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u
    return float(v[-1][1]), float(v[-1][2])


def dead_timeline(dd, picks, times, ticks, starts, total, loop, src_time, pick_at):
    """passi della simulazione: [(tempo della posa, fotogramma, (avanti, su), posa tenuta)] e {passo: fotogramma}
    dei campioni. Con "arc" (jump_arc) i fotogrammi si scelgono dalla velocità verticale, come nel gioco."""
    pre = int(dd.get("pre", 0))
    keyed_until = dd.get("keyed_until")
    steps = []
    if "arc" in dd:
        a = dd["arc"]
        vy, vx = a["vy0"], a.get("vx", 0.0)
        steps += [(times[0], 0, (vx, 0.0), False)] * pre
        first, count, last, n_last = {}, {}, len(picks) - 1, 0
        while n_last < a.get("fall_ticks", 12):
            fr = min(sum(1 for t in a["thr"] if vy > t), last)
            g = a["g_apex"] if abs(vy) <= a["apex_band"] else (a["g_up"] if vy < 0 else a["g_down"])
            # in aria il braccio cade come il corpo, con la gravità del gioco (1 px/tick² = 60 m/s²): conta l'aria
            steps.append((times[fr], fr, (vx, -vy), False, g * 60.0))
            first.setdefault(fr, len(steps) - 1)
            count[fr] = count.get(fr, 0) + 1
            if fr == last:
                n_last += 1
            vy = min(vy + g, a["max_fall"])
        return steps, {first[k] + count[k] // 2: k for k in first}
    cycles = 3 if loop else 1
    n = total * cycles if loop else total + 1
    v = dd.get("v")
    steps += [(times[0], 0, _vel_at(v, 0), keyed_until is not None and times[0] < keyed_until)] * pre
    for tau in range(n):
        st = src_time(tau)
        steps.append((st, pick_at(tau), _vel_at(v, tau % total if loop else tau),
                      keyed_until is not None and st < keyed_until))
    want = {}
    for i in range(len(picks)):
        want[pre + starts[i] + ticks[i] // 2 + (total * (cycles - 1) if loop else 0)] = i
    return steps, want


def dead_arm_dirs(ns, arm, name, dd, dcfg, steps, want, set_pose, ground_z, finals):
    """simula il braccio morto lungo i passi; ritorna {fotogramma: (braccio, avambraccio)} in coordinate mondo."""
    bw = ns["bone_world"]
    S, X, U = chest_axes(ns, arm)
    l1 = (bw(arm, "lowerarm_l")[0] - S).length
    l2 = (bw(arm, "hand_l")[0] - bw(arm, "lowerarm_l")[0]).length
    cfg = {**dcfg, **dd}
    sim = A7.DeadArm(l1, l2, cfg)
    g0 = sim.g
    # la simulazione sente la spalla con un poco di ritardo (anchor_k per tick, 1 = subito): le pose chiave molto
    # secche (un diretto in 4 tick) non frustano il braccio come una fune; i movimenti lenti restano uguali
    ak = cfg.get("anchor_k", 1.0)
    off = Vector()
    out = {}
    was_keyed = False
    As = None
    for si, step in enumerate(steps):
        pt, pi, (vf, vu), keyed = step[:4]
        sim.g = step[4] if len(step) > 4 else g0
        set_pose(pt, pi)
        bpy.context.view_layer.update()
        S, X, U = chest_axes(ns, arm)
        vel = FWD * vf + UP * vu
        if si > 0:
            off = off + vel / 60.0
        As = (S + off) if (As is None or keyed) else As + (S + off - As) * ak
        A = As
        # appeso alla sporgenza il braccio non entra nel muro, che sta all'altezza della mano che tiene
        wall_y = bw(arm, dd["wall"])[0].y + off.y + dd.get("wall_gap", 0.05) if dd.get("wall") else None
        if keyed:
            sim.drive(A, bw(arm, "lowerarm_l")[0] + off, bw(arm, "hand_l")[0] + off)
            was_keyed = True
        elif sim.E is None:
            if dd.get("from") in finals:
                sim.restore(finals[dd["from"]], A, X, U)
            else:
                iv = dd.get("init_v", (vf, vu))
                sim.place(A, X, dd.get("swing_deg", 0.0), vel=tuple(FWD * iv[0] + UP * iv[1]))
        else:
            if was_keyed:
                sim.release(A, X, ground_z, dd.get("release_v", 0.3))
                was_keyed = False
            sim.step(A, X, ground_z, wall_y)
        # i fotogrammi con il braccio tenuto dalla posa restano come sono (la destra stringe il polso)
        if si in want and not keyed:
            out[want[si]] = sim.dirs()
            u_, f_ = out[want[si]]
            ns["log"](f"    braccio morto {name}/{want[si]}: braccio {math.degrees(math.acos(max(-1.0, min(1.0, -u_.z)))):.0f}°, "
                      f"avambraccio {math.degrees(math.acos(max(-1.0, min(1.0, -f_.z)))):.0f}° dal basso, "
                      f"avanti {-u_.y:+.2f}/{-f_.y:+.2f}")
    finals[name] = sim.state(X, U)
    return out


def apply_dead_arm(ns, arm, dirs, fist, dcfg):
    """posa il braccio sinistro sulle direzioni simulate: polso un poco piegato, dita mezze aperte."""
    u, f = dirs
    A7.spring_rotation(arm, "upperarm_l", u)
    bpy.context.view_layer.update()
    A7.spring_rotation(arm, "lowerarm_l", f)
    bpy.context.view_layer.update()
    _, X, _ = chest_axes(ns, arm)
    h = X - f * X.dot(f)
    h = h.normalized() if h.length > 1e-6 else X
    q = f.cross(h)
    w = math.radians(dcfg.get("wrist_deg", 18.0))
    A7.spring_rotation(arm, "hand_l", (f * math.cos(w) + q * math.sin(w)).normalized())
    relax = dcfg.get("relax", 0.35)
    for bn, qf in fist.items():
        if bn.endswith("_l") and bn in arm.pose.bones:
            pb = arm.pose.bones[bn]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = Quaternion().slerp(qf, relax)
    bpy.context.view_layer.update()


def run(ns, job, scene, arm, actions, objs, cam, L, aux_mat, meta, camc, p1, ground_z, t0):
    use_action, find_action = ns["use_action"], ns["find_action"]
    apply_frame_scale, render_gbuffer, frame_data = ns["apply_frame_scale"], ns["render_gbuffer"], ns["frame_data"]
    strip_channels, log = ns["strip_channels"], ns["log"]
    fist = ns["fist_pose"](arm, actions)
    rig = char_poses.Rig(arm, fist)
    guard_local = A7.local_pose(rig, *rig.deltas(A7.guard()))
    spring_on = job.get("topknot_spring", False) and "topknot" in arm.pose.bones
    dcfg = job.get("dead_arm") or None
    finals = {}
    # ossa del braccio morto: le clip non le devono muovere (la posa la mette la simulazione)
    dead_bones = ["upperarm_l", "lowerarm_l", "hand_l"] + [b for b in fist if b.endswith("_l")]
    idle = None
    bones_only = job.get("bones_only", False)
    for an in job["anims"]:
        name = an["name"]
        d = os.path.join(job["out"], name)
        os.makedirs(d, exist_ok=True)
        src = an["src"]
        picks = an["picks"]
        fdata = []
        if src == "guard":
            # come la pipeline attuale
            if idle is None:
                idle = ns["GuardIdle"](arm, actions, scene)
            idle.begin()
            n = len(picks)
            bob_px = an.get("bob_px", 2)
            for i, pk in enumerate(picks):
                ph = (1 - math.cos(2 * math.pi * (pk["f"] - 1) / n)) / 2
                k = round(bob_px * ph)
                dz = k * p1 / math.cos(math.radians(camc["pitch_deg"]))
                idle.set(dz)
                apply_frame_scale(arm, pk.get("scale"))
                if not bones_only:
                    render_gbuffer(scene, aux_mat, os.path.join(d, f"p{i:02d}"))
                fd = frame_data(arm, cam, L, ground_z)
                extra_points(ns, arm, cam, L, fd)
                fd.update(frame=pk["f"], pick=i, file=f"p{i:02d}.npz")
                fdata.append(fd)
            apply_frame_scale(arm, None)
            idle.end()
        else:
            tl = src.startswith("tl:")
            stride = an.get("stride")
            period = an.get("period")
            sik = None
            if tl:
                track = A7.make_track(rig, src[3:])
                use_action(arm, None)
                times = [float(pk["at"]) for pk in picks]

                def set_pose(t, i=None):
                    A7.apply_local(arm, track.pose_at(t))
            else:
                acts = {}

                def action_for(i):
                    # ogni fotogramma può prendere la posa da un'altra azione (campo "src" del fotogramma)
                    name_ = picks[i].get("src") or src
                    if name_ not in acts:
                        a_ = find_action(actions, name_)
                        strip = []
                        if an.get("upper") == "guard" and name_ == src:
                            strip += list(ARM_ROT)
                        if dcfg and an.get("dead") is not False:
                            strip += dead_bones
                        if strip:
                            a_ = a_.copy()
                            a_.name = name_ + "_v7" + name
                            strip_channels(a_, strip, ("rotation_quaternion", "rotation_euler"))
                        acts[name_] = a_
                    return acts[name_]
                times = [float(pk["f"]) for pk in picks]
                if stride:
                    sik = StrideIK(ns, arm, stride)

                def set_pose(t, i=None):
                    fi = int(math.floor(t))
                    if sik is not None:
                        sik.off()
                    use_action(arm, action_for(0 if i is None else i))
                    scene.frame_set(fi, subframe=t - fi)
                    if an.get("upper") == "guard":
                        for b in ARM_ROT:
                            q, _ = guard_local[b]
                            pb = arm.pose.bones[b]
                            pb.rotation_mode = "QUATERNION"
                            pb.rotation_quaternion = q
                        tw = an.get("twist_deg", 0.0)
                        if tw and period:
                            # spalle che controruotano rispetto alle anche (sinusoide sul ciclo della clip)
                            ph = 2 * math.pi * (t - times[0]) / period + math.radians(an.get("twist_phase", 0.0))
                            for b, w in (("spine_02", 0.4), ("spine_03", 0.6)):
                                pb = arm.pose.bones[b]
                                pb.rotation_mode = "QUATERNION"
                                pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion(
                                    (0.0, 1.0, 0.0), math.radians(tw * w) * math.sin(ph))
                    if sik is not None:
                        sik.solve(scene)
            ticks = [int(pk.get("t", 4)) for pk in picks]
            loop = bool(an.get("loop", False))
            # tempo della sorgente in funzione del tick di schermo (fra due fotogrammi si interpola)
            starts = [sum(ticks[:i]) for i in range(len(ticks))]
            total = sum(ticks)

            def pick_at(tau):
                tau_c = tau % total if loop else min(tau, total)
                for i in range(len(starts)):
                    if starts[i] <= tau_c < starts[i] + ticks[i]:
                        return i
                return len(starts) - 1

            def src_time(tau):
                tau_c = tau % total if loop else min(tau, total)
                for i in range(len(starts)):
                    s0, s1 = starts[i], starts[i] + ticks[i]
                    if s0 <= tau_c < s1 or i == len(starts) - 1:
                        a = times[i]
                        if i + 1 < len(times) and (picks[i + 1].get("src") or src) != (picks[i].get("src") or src):
                            b = times[i]                      # azioni diverse: niente interpolazione
                        elif i + 1 < len(times):
                            b = times[i + 1]
                        elif loop and period:
                            b = times[0] + period
                        else:
                            b = times[i]
                        u = (tau_c - s0) / max(ticks[i], 1)
                        return a + (b - a) * max(0.0, min(1.0, u))
                return times[-1]
            # molla del codino sul movimento continuo
            spring_dirs = {}
            if spring_on and an.get("spring", True):
                sp = A7.Spring(**job.get("spring_cfg", {}))
                cycles = 3 if loop else 1
                n_sim = total * cycles if loop else total + 1
                want = {}
                for i in range(len(picks)):
                    tau = starts[i] + max(0, ticks[i] // 2)
                    want[(tau + (total * (cycles - 1) if loop else 0))] = i
                for tau in range(n_sim):
                    set_pose(src_time(tau), pick_at(tau))
                    arm.pose.bones["topknot"].rotation_quaternion = (1, 0, 0, 0)
                    bpy.context.view_layer.update()
                    Apos, rest_dir = A7.topknot_rest_dir(arm, "topknot")
                    dirw = sp.step(Apos, rest_dir)
                    if tau in want:
                        spring_dirs[want[tau]] = dirw.copy()
            # braccio morto: simulato su tutti i tick dell'animazione (con il moto del gioco, se c'è)
            dead_dirs = {}
            dd = an.get("dead")
            if dcfg and dd is not False:
                dd = dd or {}
                steps, dwant = dead_timeline(dd, picks, times, ticks, starts, total, loop, src_time, pick_at)
                dead_dirs = dead_arm_dirs(ns, arm, name, dd, dcfg, steps, dwant, set_pose, ground_z, finals)
            for i, pk in enumerate(picks):
                # punti della scia: sotto-istanti dal fotogramma prima a questo
                trail = None
                if pk.get("smear"):
                    t_prev = pk.get("smear_from")
                    if t_prev is None:
                        t_prev = times[i - 1] if i > 0 else times[i] - 1.0
                    trail = []
                    for k in range(7):
                        tt = t_prev + (times[i] - t_prev) * k / 6.0
                        set_pose(tt, i)
                        bpy.context.view_layer.update()
                        trail.append(trail_points(ns, arm, cam, pk["smear"]))
                set_pose(times[i], i)
                if spring_on:
                    arm.pose.bones["topknot"].rotation_quaternion = (1, 0, 0, 0)
                    bpy.context.view_layer.update()
                    if i in spring_dirs:
                        A7.spring_rotation(arm, "topknot", spring_dirs[i])
                if i in dead_dirs:
                    apply_dead_arm(ns, arm, dead_dirs[i], fist, dcfg)
                apply_frame_scale(arm, pk.get("scale"))
                if not bones_only:
                    render_gbuffer(scene, aux_mat, os.path.join(d, f"p{i:02d}"))
                fd = frame_data(arm, cam, L, ground_z)
                extra_points(ns, arm, cam, L, fd)
                fd.update(frame=pk.get("f", pk.get("at")), pick=i, file=f"p{i:02d}.npz")
                if trail is not None:
                    fd["trail"] = trail
                fdata.append(fd)
            apply_frame_scale(arm, None)
            if sik is not None:
                sik.end()
            if spring_on:
                arm.pose.bones["topknot"].rotation_quaternion = (1, 0, 0, 0)
            use_action(arm, None)
            for pb in arm.pose.bones:
                pb.location = (0, 0, 0)
                pb.rotation_mode = "QUATERNION"
                pb.rotation_quaternion = (1, 0, 0, 0)
        with open(os.path.join(d, "frames.json"), "w") as fh:
            json.dump(fdata, fh)
        meta["anims"][name] = dict(src=src, picks=[pk.get("f", pk.get("at")) for pk in picks])
        log(f"animazione {name}: {len(fdata)} fotogrammi  t={time.time() - t0:.1f}s")
