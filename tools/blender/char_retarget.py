# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - retarget senza interfaccia sul rig Quaternius UBC (dalla prova spike-anim, retarget.py).

Headless motion retargeting onto the Quaternius UBC rig (Blender 4.5, bpy only).

No add-on needed. Method ("reference-pose world-delta" retarget, what Rokoko / Auto-Rig Pro do internally):
  1. reference pose: every mapped target bone is swung (minimal rotation) so its rest direction matches
     the rest direction of its source segment  -> both skeletons share one T-pose-ish reference
  2. per frame: world rotation of target bone = (source world rotation delta from ITS rest) @ reference
  3. root: the target hip centre follows the source hip centre scaled by leg-length ratio;
     grounding = constant ankle offset ('ankle') or per-frame lowest skinned vertex at z=0 ('clamp')
  4. local pose rotations are solved parent->child and keyed (quaternions, sign-continuous)
Sources:
  --amc  ASF/AMC (CMU database)          --src_glb / --src_fbx  any armature+action with UE bone names
Outputs: actions in a .blend library (own file, loaded by render_anim.py), JSON metrics (foot slide etc).

Run: blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python retarget.py -- <args>
"""
import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import char_asfamc as asfamc  # noqa: E402

# osso di destinazione (nomi del manichino UE, come in Quaternius UBC) <- segmento ASF CMU
CMU_MAP = {
    "pelvis": "root",
    "spine_01": "lowerback", "spine_02": "upperback", "spine_03": "thorax",
    "neck_01": "upperneck", "Head": "head",
    "clavicle_l": "lclavicle", "upperarm_l": "lhumerus", "lowerarm_l": "lradius", "hand_l": "lhand",
    "clavicle_r": "rclavicle", "upperarm_r": "rhumerus", "lowerarm_r": "rradius", "hand_r": "rhand",
    "thigh_l": "lfemur", "calf_l": "ltibia", "foot_l": "lfoot", "ball_l": "ltoes",
    "thigh_r": "rfemur", "calf_r": "rtibia", "foot_r": "rfoot", "ball_r": "rtoes",
}
UE_CORE = list(CMU_MAP.keys())
FINGERS = ("index", "middle", "pinky", "ring", "thumb")
# nome del manichino UE -> nome breve Mixamo / HumanIK (il prefisso, per esempio "mixamorig:" o "Character1_", si ignora)
MIXAMO = {"pelvis": "Hips", "spine_01": "Spine", "spine_02": "Spine1", "spine_03": "Spine2", "neck_01": "Neck",
          "Head": "Head"}
for _s, _S in (("l", "Left"), ("r", "Right")):
    MIXAMO.update({"clavicle_" + _s: _S + "Shoulder", "upperarm_" + _s: _S + "Arm", "lowerarm_" + _s: _S + "ForeArm",
                   "hand_" + _s: _S + "Hand", "thigh_" + _s: _S + "UpLeg", "calf_" + _s: _S + "Leg",
                   "foot_" + _s: _S + "Foot", "ball_" + _s: _S + "ToeBase", "middle_01_" + _s: _S + "HandMiddle1"})
# figlio del segmento usato per le direzioni di riposo (funziona anche se le ossa dell'FBX puntano tutte verso +Z, come negli export HumanIK)
SEG_CHILD = {"pelvis": "spine_01", "spine_01": "spine_02", "spine_02": "spine_03", "spine_03": "neck_01",
             "neck_01": "Head"}
for _s in "lr":
    SEG_CHILD.update({"clavicle_" + _s: "upperarm_" + _s, "upperarm_" + _s: "lowerarm_" + _s,
                      "lowerarm_" + _s: "hand_" + _s, "hand_" + _s: "middle_01_" + _s,
                      "thigh_" + _s: "calf_" + _s, "calf_" + _s: "foot_" + _s, "foot_" + _s: "ball_" + _s})
# mondo CMU (Y in alto, guarda verso +Z, sinistra +X) -> mondo Blender/UBC (Z in alto, guarda verso -Y, sinistra +X)
BM = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))


def parse():
    a = sys.argv[sys.argv.index("--") + 1:]
    p = argparse.ArgumentParser()
    p.add_argument("--body", required=True, help="UBC glTF (target)")
    p.add_argument("--asf")
    p.add_argument("--amc")
    p.add_argument("--src_glb", default="")
    p.add_argument("--src_fbx", default="")
    p.add_argument("--src_json", default="", help="anim_dump.py output")
    p.add_argument("--src_action", default="", help="action name in the source file (default: first)")
    p.add_argument("--src_naming", default="ue", choices=["ue", "mixamo", "hik"])
    p.add_argument("--range", default="", help="first,last source frame (inclusive)")
    p.add_argument("--src_fps", type=float, default=120.0, help="AMC frame rate")
    p.add_argument("--fps", type=float, default=30.0, help="output key rate")
    p.add_argument("--speed", type=float, default=1.0, help=">1 plays faster")
    p.add_argument("--face_frame", type=int, default=-1, help="AMC: source frame whose facing is turned to -Y")
    p.add_argument("--yaw", type=float, default=0.0, help="extra yaw (deg) after facing alignment")
    p.add_argument("--inplace", default="xy", help="remove horizontal root travel: xy | x | y | none")
    p.add_argument("--ground", default="ankle", choices=["ankle", "clamp", "none"])
    p.add_argument("--fist_fbx", default="", help="UAL FBX; copies the fist pose of Punch_Jab f1 to fingers")
    p.add_argument("--name", required=True, help="output action name")
    p.add_argument("--out_blend", required=True)
    p.add_argument("--out_json", required=True)
    p.add_argument("--mirror", action="store_true", help="swap left/right (kick with the other leg)")
    p.add_argument("--blend_from", default="", help="action in out_blend to cross-fade FROM (start pose)")
    p.add_argument("--blend_frames", type=int, default=0)
    p.add_argument("--footlock", type=int, default=1)
    p.add_argument("--origin", default="first", choices=["first", "world"],
                   help="first: hips start over the origin; world: keep capture-space position (paired clips)")
    p.add_argument("--world_offset", default="0,0", help="x,y metres added in world mode (Blender axes)")
    return p.parse_args(a)


# ------------------------------------------------------------------ aiuti
def swing(a, b):
    a, b = a.normalized(), b.normalized()
    return a.rotation_difference(b).to_matrix()


def new_objects(before):
    return [o for o in bpy.data.objects if o not in before]


def load_target(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    objs = new_objects(before)
    arm = [o for o in objs if o.type == "ARMATURE"][0]
    body = [o for o in objs if o.type == "MESH" and o.name.lower().startswith("superhero")]
    for o in objs:
        if o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o, do_unlink=True)
    return arm, (body[0] if body else None)


def bone_chain_order(arm):
    out = []

    def rec(b):
        out.append(b.name)
        for c in b.children:
            rec(c)
    for b in arm.data.bones:
        if b.parent is None:
            rec(b)
    return out


# ------------------------------------------------------------------ sorgenti
class AMCSource:
    def __init__(self, args):
        self.sk = asfamc.Skeleton(args.asf)
        frames = asfamc.read_amc(args.amc)
        f0, f1 = (0, len(frames) - 1)
        if args.range:
            f0, f1 = [int(v) for v in args.range.split(",")]
        step = args.src_fps / args.fps * args.speed
        n = int((f1 - f0) / step) + 1
        self.idx = [min(f1, int(round(f0 + i * step))) for i in range(n)]
        self.raw = frames
        mirror = args.mirror
        # allineamento della direzione (rotazione attorno a +Y di CMU) con la linea delle anche in face_frame
        ff = args.face_frame if args.face_frame >= 0 else f0
        G, P, r = asfamc.fk(self.sk, frames[ff])
        lat = Vector(P["lhipjoint"]) - Vector(P["rhipjoint"])
        fwd = lat.cross(Vector((0, 1, 0)))
        fwd.y = 0
        fwd.normalize()
        ang = math.atan2(fwd.x, fwd.z)                       # yaw of forward from +Z
        self.yaw = Matrix.Rotation(-ang + math.radians(args.yaw), 3, "Y")
        self.cache = {}
        self.mirror = mirror
        self.legs = (self.sk.bones["lfemur"].length + self.sk.bones["ltibia"].length) * self.sk.scale_m
        # direzioni di riposo nel mondo di Blender
        self.rest_dir = {}
        for n_ in self.sk.bones:
            d = Vector(self.sk.bones[n_].direction)
            self.rest_dir[n_] = (BM @ d).normalized() if d.length > 0 else Vector((0, 0, 1))
        # riferimento del suolo per le caviglie (la caviglia più bassa nell'intervallo)
        lows = []
        for fi in range(f0, f1 + 1, 4):
            G, P, r = asfamc.fk(self.sk, frames[fi])
            lows.append(min(P["ltibia"][1], P["rtibia"][1]))
        self.ankle_floor = min(lows)
        self.start_ankle = None

    def frames(self):
        return self.idx

    def eval(self, fi):
        """-> (rotazione delta nel mondo per segmento (mondo di Blender), centro delle anche (mondo di Blender, m), altezze delle caviglie)."""
        G, P, r = asfamc.fk(self.sk, self.raw[fi])
        Y = self.yaw
        D = {}
        for n_, g in G.items():
            gm = Matrix([list(row) for row in g])
            D[n_] = BM @ (Y @ gm) @ BM.transposed()
        hc = (Vector(P["lhipjoint"]) + Vector(P["rhipjoint"])) / 2
        hc = BM @ (Y @ hc)
        hc.z -= self.ankle_floor
        balls = {}
        for sd in ("l", "r"):
            v = BM @ (Y @ Vector(P[sd + "foot"]))
            v.z -= self.ankle_floor
            balls[sd] = v
        return D, hc, balls


class ArmatureSource:
    """Un'armatura qualsiasi con la sua azione (per esempio GLB Mesh2Motion, FBX UAL). I nomi delle ossa devono seguire quelli del manichino UE."""

    def __init__(self, args):
        before = set(bpy.data.objects)
        acts_before = set(bpy.data.actions)
        if args.src_fbx:
            bpy.ops.import_scene.fbx(filepath=args.src_fbx)
        else:
            bpy.ops.import_scene.gltf(filepath=args.src_glb)
        objs = new_objects(before)
        self.arm = [o for o in objs if o.type == "ARMATURE"][0]
        for o in objs:
            if o.type == "MESH":
                o.hide_render = True
        acts = [a for a in bpy.data.actions if a not in acts_before]
        cur = self.arm.animation_data.action if self.arm.animation_data else None
        act = next((a for a in acts if args.src_action and (a.name == args.src_action or a.name.endswith("|" + args.src_action))), None)
        act = act or cur or acts[0]          # FBX: the armature's own action, not an empty's
        ad = self.arm.animation_data or self.arm.animation_data_create()
        ad.action = act
        if hasattr(ad, "action_slot") and ad.action_slot is None and len(getattr(act, "slots", [])):
            ad.action_slot = act.slots[0]
        self.act = act
        f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
        if args.range:
            f0, f1 = [int(v) for v in args.range.split(",")]
        src_fps = bpy.context.scene.render.fps
        step = src_fps / args.fps * args.speed
        n = int((f1 - f0) / step) + 1
        self.idx = [f0 + i * step for i in range(n)]
        self.names = {b.name.lower(): b.name for b in self.arm.data.bones}
        if args.src_naming in ("mixamo", "hik"):
            short = {}
            for b in self.arm.data.bones:
                key = b.name.split(":")[-1]
                if args.src_naming == "hik" and "_" in key:
                    key = key.split("_", 1)[1]
                short[key.lower()] = b.name
            for ue, mx in MIXAMO.items():
                if mx.lower() in short:
                    self.names[ue.lower()] = short[mx.lower()]
        mw = self.arm.matrix_world
        self.mw = mw
        self.rest_rot = {}
        self.rest_dir = {}
        B0 = self.arm.data.bones
        for b in B0:
            self.rest_rot[b.name] = (mw.to_3x3() @ b.matrix_local.to_3x3()).normalized()
            self.rest_dir[b.name] = (mw.to_3x3() @ (b.tail_local - b.head_local)).normalized()
        # direzioni dei segmenti dalle posizioni delle articolazioni (testa -> testa del figlio mappato), dove si può
        for ue, ch in SEG_CHILD.items():
            a, c = self.n(ue), self.n(ch)
            if a in B0 and c in B0:
                v = mw.to_3x3() @ (B0[c].head_local - B0[a].head_local)
                if v.length > 1e-5:
                    self.rest_dir[a] = v.normalized()
        B = self.arm.data.bones
        self.legs = (B[self.n("thigh_l")].head_local - B[self.n("calf_l")].head_local).length + \
                    (B[self.n("calf_l")].head_local - B[self.n("foot_l")].head_local).length
        self.legs *= mw.to_scale()[0]
        self.ankle_floor = (mw @ B[self.n("foot_l")].head_local).z
        self.act_name = act.name

    def n(self, name):
        return self.names.get(name.lower(), name)

    def frames(self):
        return self.idx

    def lateral(self, fi):
        bpy.context.scene.frame_set(int(fi))
        return (self.mw @ self.arm.pose.bones[self.n("thigh_l")].head) - (self.mw @ self.arm.pose.bones[self.n("thigh_r")].head)

    def eval(self, fi):
        sc = bpy.context.scene
        sc.frame_set(int(math.floor(fi)), subframe=fi - math.floor(fi))
        D = {}
        for pb in self.arm.pose.bones:
            R = (self.mw.to_3x3() @ pb.matrix.to_3x3()).normalized()
            D[pb.name] = R @ self.rest_rot[pb.name].transposed()
        hl = self.mw @ self.arm.pose.bones[self.n("thigh_l")].head
        hr = self.mw @ self.arm.pose.bones[self.n("thigh_r")].head
        hc = (hl + hr) / 2
        hc.z -= self.ankle_floor
        balls = {}
        for sd in ("l", "r"):
            v = self.mw @ self.arm.pose.bones[self.n("ball_" + sd)].head
            v.z -= self.ankle_floor
            balls[sd] = v
        return D, hc, balls


class JSONSource:
    """Animazione di un'armatura scaricata da anim_dump.py (per esempio i GLB Mesh2Motion decodificati con Blender 5.2)."""

    def __init__(self, args):
        d = json.load(open(args.src_json))
        self.d = d
        mw = Matrix(d["matrix_world"])
        self.mw = mw
        self.bones = d["bones"]
        self.names = {n.lower(): n for n in self.bones}
        self.rest_rot, self.rest_dir = {}, {}
        for n, b in self.bones.items():
            ml = Matrix(b["matrix_local"])
            self.rest_rot[n] = (mw.to_3x3() @ ml.to_3x3()).normalized()
            self.rest_dir[n] = (mw.to_3x3() @ (Vector(b["tail"]) - Vector(b["head"]))).normalized()
        f0, f1 = d["frame_range"]
        if args.range:
            f0, f1 = [int(v) for v in args.range.split(",")]
        step = d["fps"] / args.fps * args.speed
        n = int((f1 - f0) / step) + 1
        self.idx = [f0 + i * step for i in range(n)]
        self.f0 = d["frame_range"][0]
        hb = lambda nm: Vector(self.bones[self.n(nm)]["head"])
        self.legs = ((hb("thigh_l") - hb("calf_l")).length + (hb("calf_l") - hb("foot_l")).length) * mw.to_scale()[0]
        self.ankle_floor = (mw @ hb("foot_l")).z

    def n(self, name):
        return self.names.get(name.lower(), name)

    def frames(self):
        return self.idx

    def lateral(self, fi):
        return (self.mw @ self._mat(fi, self.n("thigh_l")).translation) - (self.mw @ self._mat(fi, self.n("thigh_r")).translation)

    def _mat(self, fi, bone):
        F = self.d["frames"]
        i0 = int(math.floor(fi)) - self.f0
        i0 = max(0, min(len(F) - 1, i0))
        i1 = min(len(F) - 1, i0 + 1)
        t = fi - math.floor(fi)
        m0, m1 = Matrix(F[i0][bone]), Matrix(F[i1][bone])
        if t <= 1e-6:
            return m0
        q = m0.to_quaternion().slerp(m1.to_quaternion(), t)
        loc = m0.translation.lerp(m1.translation, t)
        return Matrix.LocRotScale(loc, q, None)

    def eval(self, fi):
        D = {}
        for n in self.bones:
            R = (self.mw.to_3x3() @ self._mat(fi, n).to_3x3()).normalized()
            D[n] = R @ self.rest_rot[n].transposed()
        hl = self.mw @ self._mat(fi, self.n("thigh_l")).translation
        hr = self.mw @ self._mat(fi, self.n("thigh_r")).translation
        hc = (hl + hr) / 2
        hc.z -= self.ankle_floor
        balls = {}
        for sd in ("l", "r"):
            v = self.mw @ self._mat(fi, self.n("ball_" + sd)).translation
            v.z -= self.ankle_floor
            balls[sd] = v
        return D, hc, balls


# ------------------------------------------------------------------ principale
def main():
    args = parse()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = int(args.fps)
    arm, body = load_target(args.body)
    mw = arm.matrix_world
    B = arm.data.bones
    order = bone_chain_order(arm)

    if args.amc:
        src = AMCSource(args)
        mapping = dict(CMU_MAP)
        src_rest = src.rest_dir
        src_rest["root"] = Vector((0, 0, 1))
    else:
        src = JSONSource(args) if args.src_json else ArmatureSource(args)
        have = src.bones if args.src_json else src.arm.data.bones
        mapping = {b: src.n(b) for b in UE_CORE if src.n(b) in have}
        src_rest = src.rest_dir
        mapping["pelvis"] = src.n("pelvis")
    if args.mirror:
        # l'osso X di destinazione prende il movimento dell'ALTRO lato della sorgente, riflesso sul piano sagittale
        def msrc(s):
            if args.amc:
                other = ("r" if s[0] == "l" else "l") + s[1:]
                if s[0] in "lr" and other in src.sk.bones and s not in ("lowerback", "lowerneck"):
                    return other
                return s
            if s.endswith("_l"):
                return s[:-2] + "_r"
            if s.endswith("_r"):
                return s[:-2] + "_l"
            return s
        mapping = {t: msrc(s) for t, s in mapping.items()}
    print("[map]", mapping)

    # dati di riposo della destinazione (mondo)
    rest_rot = {b.name: (mw.to_3x3() @ b.matrix_local.to_3x3()).normalized() for b in B}
    rest_dir = {b.name: (mw.to_3x3() @ (b.tail_local - b.head_local)).normalized() for b in B}
    M = mw.to_3x3()
    MX = Matrix(((-1, 0, 0), (0, 1, 0), (0, 0, 1)))       # mirror across the sagittal plane
    ref = {}
    for t, s in mapping.items():
        sd = src_rest[s]
        if args.mirror:
            sd = MX @ sd
        ref[t] = rest_rot[t] if t == "pelvis" else (swing(rest_dir[t], sd) @ rest_rot[t])
    hip_rest = (mw @ (B["thigh_l"].head_local + B["thigh_r"].head_local) / 2)
    pelvis_rest = mw @ B["pelvis"].head_local
    hip_from_pelvis = hip_rest - pelvis_rest
    ankle_rest_z = (mw @ B["foot_l"].head_local).z
    legs_t = (B["thigh_l"].head_local - B["calf_l"].head_local).length + (B["calf_l"].head_local - B["foot_l"].head_local).length
    k = legs_t / src.legs
    print(f"[scale] target legs {legs_t:.3f} m / source legs {src.legs:.3f} m -> k {k:.3f}")

    # posa facoltativa del pugno per le dita (dal fotogramma 1 di Punch_Jab di UAL, applicata come rotazioni locali)
    fist = {}
    if args.fist_fbx:
        before = set(bpy.data.objects)
        acts_before = set(bpy.data.actions)
        bpy.ops.import_scene.fbx(filepath=args.fist_fbx)
        objs = new_objects(before)
        jab = next(a for a in bpy.data.actions if a not in acts_before and a.name.endswith("Punch_Jab"))
        ad = arm.animation_data or arm.animation_data_create()
        ad.action = jab
        if hasattr(ad, "action_slot") and ad.action_slot is None and len(jab.slots):
            ad.action_slot = jab.slots[0]
        sc.frame_set(int(jab.frame_range[0]))
        for pb in arm.pose.bones:
            if pb.name.split("_")[0] in FINGERS:
                fist[pb.name] = pb.rotation_quaternion.copy() if pb.rotation_mode == "QUATERNION" else pb.rotation_euler.to_quaternion()
        ad.action = None
        for o in objs:
            bpy.data.objects.remove(o, do_unlink=True)
        for a in [a for a in bpy.data.actions if a not in acts_before]:
            bpy.data.actions.remove(a)
        print("[fist] finger bones", len(fist))
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.scale = (1, 1, 1)

    frames = src.frames()
    RZ = None
    if not args.amc and (args.face_frame >= 0 or args.yaw):
        ang = 0.0
        if args.face_frame >= 0:
            lat = src.lateral(args.face_frame)
            fwd = lat.cross(Vector((0, 0, 1)))
            fwd.z = 0
            ang = math.atan2(fwd.x, -fwd.y)          # angle of forward from -Y (towards +X)
        RZ = Matrix.Rotation(-ang + math.radians(args.yaw), 3, "Z")
        print("[face] yaw correction %.1f deg" % math.degrees(-ang + math.radians(args.yaw)))
    L1 = {sd: (B["thigh_" + sd].head_local - B["calf_" + sd].head_local).length for sd in "lr"}
    L2 = {sd: (B["calf_" + sd].head_local - B["foot_" + sd].head_local).length for sd in "lr"}
    YAX = Vector((0, 1, 0))

    def solve(desired, tgt_hip, ik=None):
        """soluzione locale da padre a figlio. ik: {lato: (bersaglio della caviglia nel mondo, peso)} -> IK analitica della gamba a 2 ossa."""
        posed, q_local = {}, {}
        desired = dict(desired)
        for name in order:
            b = B[name]
            if b.parent:
                base = posed[b.parent.name] @ (b.parent.matrix_local.inverted() @ b.matrix_local)
            else:
                base = b.matrix_local.copy()
            sd = name[-1] if name.startswith("thigh_") else None
            if ik and sd in ik and name in desired:
                A_t, w = ik[sd]
                H = (M @ base.translation)
                Rt, Rc = desired[name], desired["calf_" + sd]
                K0 = H + L1[sd] * (Rt @ YAX)
                A0 = K0 + L2[sd] * (Rc @ YAX)
                A_t = A0.lerp(A_t, w)
                dv = A_t - H
                d = min(max(dv.length, abs(L1[sd] - L2[sd]) + 1e-4), L1[sd] + L2[sd] - 1e-4)
                u = dv.normalized()
                v = (K0 - H) - (K0 - H).dot(u) * u
                if v.length < 1e-5:
                    v = Vector((0, -1, 0)) - Vector((0, -1, 0)).dot(u) * u
                v.normalize()
                a = math.acos(max(-1.0, min(1.0, (L1[sd] ** 2 + d * d - L2[sd] ** 2) / (2 * L1[sd] * d))))
                K = H + L1[sd] * (math.cos(a) * u + math.sin(a) * v)
                sw_t = swing(K0 - H, K - H)
                desired[name] = (sw_t @ Rt).normalized()
                Rc_tmp = sw_t @ Rc
                desired["calf_" + sd] = (swing(Rc_tmp @ YAX, (H + u * d) - K) @ Rc_tmp).normalized()
            if name in desired:
                q = (base.to_3x3().normalized().inverted() @ (M.inverted() @ desired[name])).to_quaternion()
            elif name in fist:
                q = fist[name].copy()
            else:
                q = Quaternion()
            loc = Vector()
            if name == "pelvis":
                head_arm = M.inverted() @ (tgt_hip - (desired["pelvis"] @ rest_rot["pelvis"].transposed()) @ hip_from_pelvis)
                loc = Vector(base.inverted() @ head_arm)
            q_local[name] = (loc, q)
            posed[name] = base @ Matrix.Translation(loc) @ q.to_matrix().to_4x4()
        return q_local, posed

    poses = []
    hip_track, src_balls, desireds, hips, ankles, balls_t = [], [], [], [], [], []
    # distanza della pianta dalla caviglia nel riferimento di riposo dell'osso del piede (perno sulla pianta, come fanno le persone)
    ball_in_foot = {sd: rest_rot['foot_' + sd].transposed() @ (mw @ B['ball_' + sd].head_local - mw @ B['foot_' + sd].head_local) for sd in 'lr'}
    for fi in frames:
        D, hc, balls = src.eval(fi)
        if RZ is not None:
            D = {n_: RZ @ d @ RZ.transposed() for n_, d in D.items()}
            hc = RZ @ hc
            balls = {k_: RZ @ v_ for k_, v_ in balls.items()}
        if args.mirror:
            D = {n: MX @ d @ MX for n, d in D.items()}
            hc = MX @ hc
            balls = {"l": MX @ balls["r"], "r": MX @ balls["l"]}
        src_balls.append(balls)
        desired = {}
        for t, s_ in mapping.items():
            if s_ in D:
                desired[t] = (D[s_] @ ref[t]).normalized()
        hip_track.append(hc.copy())
        if len(hip_track) == 1:
            hc0 = hc.copy()                  # clip starts with the hip centre over the origin
            if args.origin == "world":
                wx, wy = [float(v) for v in args.world_offset.split(",")]
                hc0 = Vector((-wx / k, -wy / k, 0.0))
        tgt_hip = Vector(((hc.x - hc0.x) * k, (hc.y - hc0.y) * k, hc.z * k + ankle_rest_z))
        q_local, posed = solve(desired, tgt_hip)
        desireds.append(desired)
        hips.append(tgt_hip)
        ankles.append({sd: M @ posed["foot_" + sd].translation for sd in "lr"})
        balls_t.append({sd: M @ posed["ball_" + sd].translation for sd in "lr"})
        poses.append(q_local)

    # -------- piedi bloccati: tratti d'appoggio dalle piante della SORGENTE (entro 2,5 cm dalla loro quota più bassa,
    # più lente di 1,5 cm per fotogramma); la caviglia di destinazione resta ferma dove inizia il tratto (con raccordo)
    locks = {"l": [], "r": []}
    if args.footlock:
        for sd in "lr":
            zs = [b[sd].z for b in src_balls]
            zmin = min(zs)
            planted = []
            for i in range(len(zs)):
                sp = (src_balls[i][sd] - src_balls[i - 1][sd]).length if i else 0.0
                planted.append(zs[i] < zmin + 0.025 and sp < 0.015 * (120.0 / args.fps if args.amc else 1.0) * 0 + 0.02)
            runs, cur = [], []
            for i, pl in enumerate(planted):
                if pl:
                    cur.append(i)
                elif cur:
                    runs.append(cur)
                    cur = []
            if cur:
                runs.append(cur)
            for r in [r for r in runs if len(r) >= 3]:
                ball_anchor = Vector(balls_t[r[0]][sd])
                for j, i in enumerate(r):
                    w = min(1.0, (j + 1) / 2.0, (len(r) - j) / 2.0)
                    # bersaglio della caviglia che tiene ferma la PIANTA, dato l'orientamento del piede in questo fotogramma
                    anchor = ball_anchor - desireds[i]["foot_" + sd] @ ball_in_foot[sd]
                    locks[sd].append((i, anchor, w))
        per_frame = {}
        for sd in "lr":
            for i, anchor, w in locks[sd]:
                per_frame.setdefault(i, {})[sd] = (anchor, w)
        dev = 0.0
        for i, ik in per_frame.items():
            poses[i], pz = solve(desireds[i], hips[i], ik)
            for sd, (anchor, w) in ik.items():
                if w >= 1.0:
                    dev = max(dev, ((M @ pz["foot_" + sd].translation) - anchor).length)
        print("[footlock] max ankle deviation from anchor on fully-locked frames: %.4f m" % dev)
        print("[footlock] runs", {sd: sorted(set(i for i, _, _ in locks[sd]))[:3] for sd in "lr"})
        print("[footlock] locked frames", {sd: len(locks[sd]) for sd in "lr"})

    # sul posto: si toglie lo spostamento orizzontale (la posizione del bacino è nello spazio del suo padre; si lavora nel mondo sulla traccia delle anche)
    # -> il modo più semplice: ogni fotogramma sposta il bacino di -(hip_xy(t) - hip_xy(0)), espresso come scostamento dell'osso radice
    travel = [Vector((h.x - hip_track[0].x, h.y - hip_track[0].y, 0)) * k for h in hip_track]

    # -------- dissolvenza facoltativa dall'ULTIMO fotogramma di un'altra azione (per esempio caduta -> rialzo)
    if args.blend_from and args.blend_frames > 0 and os.path.exists(args.out_blend):
        with bpy.data.libraries.load(args.out_blend) as (df, dt):
            dt.actions = [a for a in df.actions if a == args.blend_from]
        prev = dt.actions[0]
        ad0 = arm.animation_data or arm.animation_data_create()
        ad0.action = prev
        if hasattr(ad0, "action_slot") and ad0.action_slot is None and len(prev.slots):
            ad0.action_slot = prev.slots[0]
        sc.frame_set(int(prev.frame_range[1]))
        last = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in arm.pose.bones}
        ad0.action = None
        bpy.data.actions.remove(prev)
        for pb in arm.pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
        nb = min(args.blend_frames, len(poses))
        for i in range(nb):
            w = (i + 1) / (nb + 1)
            w = w * w * (3 - 2 * w)
            for name, (loc, q) in poses[i].items():
                l0, q0 = last.get(name, (loc, q))
                if q0.dot(q) < 0:
                    q0 = -q0
                poses[i][name] = (l0.lerp(loc, w), q0.slerp(q, w))
        print("[blend_from]", args.blend_from, "frames", nb)

    # -------- fotogrammi chiave per tutto
    act = bpy.data.actions.new(args.name)
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    prevq = {}
    root_off = []
    for i, q_local in enumerate(poses):
        f = i + 1
        off = Vector(travel[i])
        if args.inplace == "none":
            off = Vector()
        elif args.inplace == "x":
            off.y = 0
        elif args.inplace == "y":
            off.x = 0
        root_off.append(off.copy())
        for name, (loc, q) in q_local.items():
            pb = arm.pose.bones[name]
            if name in prevq and q.dot(prevq[name]) < 0:
                q = -q
            prevq[name] = q
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=f)
            if name == "pelvis":
                pb.location = loc
                pb.keyframe_insert("location", frame=f)
        rb = arm.pose.bones["root"]
        # osso radice: si sottrae lo spostamento (il riposo della radice porta la sua Y locale sulla +Y del mondo? si risolve con le matrici)
        base = B["root"].matrix_local
        rb.location = (base.to_3x3().inverted() @ (M.inverted() @ (-off)))
        rb.keyframe_insert("location", frame=f)
    n_frames = len(poses)

    # -------- appoggio a terra
    deps = bpy.context.evaluated_depsgraph_get()
    import numpy as np
    lows = []
    feet = {"l": [], "r": []}
    for i in range(n_frames):
        sc.frame_set(i + 1)
        deps = bpy.context.evaluated_depsgraph_get()
        if body is not None:
            ev = body.evaluated_get(deps)
            me = ev.to_mesh()
            co = np.empty(len(me.vertices) * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            z = (np.c_[co, np.ones(len(co))] @ np.array(body.matrix_world).T)[:, 2]
            lows.append(float(z.min()))
            ev.to_mesh_clear()
        for s in ("l", "r"):
            pb = arm.pose.bones["ball_" + s]
            feet[s].append((mw @ pb.head).copy())
    if args.ground == "clamp" and lows:
        # per fotogramma: il punto più basso della pelle sul suolo (con un leggero smussamento)
        corr = [-v for v in lows]
        sm = [sum(corr[max(0, j - 1):j + 2]) / len(corr[max(0, j - 1):j + 2]) for j in range(len(corr))]
    elif args.ground == "ankle" and lows:
        sm = [-min(lows)] * n_frames     # constant: lowest point over the clip touches the floor
    else:
        sm = [0.0] * n_frames
    rb = arm.pose.bones["root"]
    base = B["root"].matrix_local
    for i in range(n_frames):
        off = root_off[i]
        v = M.inverted() @ (Vector((-off.x, -off.y, sm[i])))
        rb.location = base.to_3x3().inverted() @ v
        rb.keyframe_insert("location", frame=i + 1)
    for s in ("l", "r"):
        feet[s] = [p + Vector((root_off[i].x, root_off[i].y, sm[i])) for i, p in enumerate(feet[s])]   # world, with travel

    # -------- misura dello scivolamento dei piedi: un piede è in appoggio finché la pianta resta entro 2,5 cm dalla sua quota più bassa
    # nella clip; deriva = distanza orizzontale massima dal punto d'inizio del tratto. Destinazione contro sorgente (in scala).
    px = 1.0 / 48.0        # metri per pixel dello sprite a 1x (48 px/m, vedi tools/sprites/camera.json)

    def runs_of(P):
        zmin = min(p.z for p in P)
        runs, cur = [], []
        for i, p in enumerate(P):
            if p.z < zmin + 0.025 and (i == 0 or (P[i].xy - P[i - 1].xy).length < 0.02):
                cur.append(i)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        return [r for r in runs if len(r) >= 3]

    def drift(P, runs):
        worst = 0.0
        for r in runs:
            xy0 = P[r[0]].xy
            worst = max(worst, max((P[j].xy - xy0).length for j in r))
        return worst

    slide = {}
    hc0s = hip_track[0]
    for sd in ("l", "r"):
        sp = [Vector(((b[sd].x - hc0s.x) * k, (b[sd].y - hc0s.y) * k, b[sd].z * k)) for b in src_balls]
        runs = runs_of(sp)              # planted runs defined on the SOURCE, measured on both
        wt, ws = drift(feet[sd], runs), drift(sp, runs)
        slide[sd] = dict(source_planted_runs=[[r[0], r[-1]] for r in runs], target_drift_m=round(wt, 4),
                         target_drift_px_1x=round(wt / px, 2), source_drift_px_1x=round(ws / px, 2))
    act.use_fake_user = True
    meta = dict(name=args.name, source=(args.amc or args.src_json or args.src_glb or args.src_fbx), frames=n_frames,
                src_frames=[float(f) for f in frames], fps=args.fps, scale_k=k, ground=args.ground,
                inplace=args.inplace, foot_slide=slide, lowest_point_range=[min(lows), max(lows)] if lows else None,
                root_offset_m=[[round(o.x, 4), round(o.y, 4), round(s, 4)] for o, s in zip(root_off, sm)],
                travel_m=[[round(t.x, 4), round(t.y, 4)] for t in travel])
    # si unisce al file della libreria esistente
    existing = []
    if os.path.exists(args.out_blend):
        with bpy.data.libraries.load(args.out_blend) as (df, dt):
            dt.actions = [a for a in df.actions if a != args.name]
        existing = [a for a in dt.actions if a]
        for a in existing:
            a.use_fake_user = True
    bpy.data.libraries.write(args.out_blend, set([act] + existing), fake_user=True)
    js = {}
    if os.path.exists(args.out_json):
        js = json.load(open(args.out_json))
    js[args.name] = meta
    json.dump(js, open(args.out_json, "w"), indent=1)
    print("[retarget] fatto", args.name, n_frames, "frames; foot slide", slide, "-> ", args.out_blend)


if __name__ == "__main__":
    main()
