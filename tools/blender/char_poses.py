# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - pose scritte a mano (dati) e loro risoluzione sul rig UBC (bpy, senza interfaccia).

Deriva da author.py della prova spike-anim. Specifica di una posa (angoli in gradi, direzioni nel
riferimento del CORPO: x = sinistra del personaggio, y = la sua schiena, z = su; a riposo guarda -Y):
  hip=(x,y,z)        posizione del centro delle anche (fra le teste dei femori), metri per il corpo UBC
  face=gradi         rotazione del corpo attorno a Z          pelvis=(pitch,roll,yaw) sopra face
  spine=(p,r,y)      distribuito su spine_01..03 (0.3/0.35/0.35); +pitch = in avanti, +roll = a sinistra
  neck=(p,r,y)       distribuito su neck_01/Head
  arm_l / arm_r      dict(up=dir, lo=dir[, hand=dir]) nel riferimento del petto, oppure dict(ik=pos, pole=dir)
  leg_l / leg_r      dict(up=dir, lo=dir[, foot=dir]) nel riferimento del bacino ruotato (face), oppure
                     dict(ik=pos, pole=dir); frame='body'|'facing'|'chest' cambia il riferimento dell'arto
Le posizioni sono scalate con l'altezza delle anche del rig (corpi rimodellati del punk e del bruto).
Ogni posa diventa un fotogramma chiave con interpolazione costante (una posa = un fotogramma dello sprite).
Le scale di "smear" non si mettono qui: le applica char_build.py per fotogramma.

GIG guarda a destra con il lato DESTRO verso la telecamera: la gamba vicina (ben visibile) è la destra,
il braccio cibernetico (sinistro) è quello lontano ma in guardia sta davanti, come braccio avanzato.
Le vittime si scrivono nel loro riferimento (rivolte a destra come tutti gli sprite): il gioco le specchia
quando guardano GIG, e gli offset della coppia si calcolano in 2D sugli sprite già fatti.
"""
import copy
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

UBC_HIP_Z = 0.971


def V(*a):
    return Vector(a).normalized()


def swing(a, b):
    return a.normalized().rotation_difference(b.normalized()).to_matrix()


def eul(p, r, y):
    """rotazione nel riferimento del personaggio: yaw attorno a Z, poi pitch attorno a X (+ = in avanti),
    roll attorno a Y (+ = verso la sua sinistra)."""
    return (Matrix.Rotation(math.radians(y), 3, "Z") @ Matrix.Rotation(math.radians(p), 3, "X")
            @ Matrix.Rotation(math.radians(-r), 3, "Y"))


class Rig:
    def __init__(self, arm, fist):
        self.arm = arm
        self.B = arm.data.bones
        mw = arm.matrix_world
        self.rest_rot = {b.name: (mw.to_3x3() @ b.matrix_local.to_3x3()).normalized() for b in self.B}
        self.rest_dir = {b.name: (mw.to_3x3() @ (b.tail_local - b.head_local)).normalized() for b in self.B}
        self.rest_head = {b.name: mw @ b.head_local for b in self.B}
        self.order = []

        def rec(b):
            self.order.append(b.name)
            for c in b.children:
                rec(c)
        for b in self.B:
            if b.parent is None:
                rec(b)
        self.hip_rest = (self.rest_head["thigh_l"] + self.rest_head["thigh_r"]) / 2
        self.k = self.hip_rest.z / UBC_HIP_Z
        self.ankle_z = self.rest_head["foot_l"].z
        self.fist = fist
        self.len = {n: (self.rest_head[c] - self.rest_head[n]).length for n, c in
                    (("upperarm_l", "lowerarm_l"), ("lowerarm_l", "hand_l"), ("upperarm_r", "lowerarm_r"),
                     ("lowerarm_r", "hand_r"), ("thigh_l", "calf_l"), ("calf_l", "foot_l"),
                     ("thigh_r", "calf_r"), ("calf_r", "foot_r"))}

    def P(self, p):
        """posizione UBC -> posizione per questo corpo (scala delle anche)."""
        return Vector((p[0] * self.k, p[1] * self.k, p[2] * self.k))

    def PF(self, p):
        """bersaglio di un piede: la quota resta quella della caviglia del rig."""
        return Vector((p[0] * self.k, p[1] * self.k, self.ankle_z + (p[2] - 0.086) * self.k))

    def deltas(self, spec):
        D = {}
        C = Matrix.Rotation(math.radians(spec.get("face", 0.0)), 3, "Z")
        D["root"] = Matrix.Identity(3)
        D["pelvis"] = C @ eul(*spec.get("pelvis", (0, 0, 0)))
        sp = spec.get("spine", (0, 0, 0))
        prev = D["pelvis"]
        for n, w in (("spine_01", 0.3), ("spine_02", 0.35), ("spine_03", 0.35)):
            prev = prev @ eul(sp[0] * w, sp[1] * w, sp[2] * w)
            D[n] = prev
        nk = spec.get("neck", (0, 0, 0))
        D["neck_01"] = D["spine_03"] @ eul(nk[0] * 0.5, nk[1] * 0.5, nk[2] * 0.5)
        D["Head"] = D["neck_01"] @ eul(nk[0] * 0.5, nk[1] * 0.5, nk[2] * 0.5)
        for s in "lr":
            D["clavicle_" + s] = D["spine_03"] @ eul(*spec.get("clav_" + s, (0, 0, 0)))
        hip = self.P(spec["hip"]) if "hip" in spec else self.hip_rest.copy()
        pel_head = hip - D["pelvis"] @ (self.hip_rest - self.rest_head["pelvis"])
        pos = {"pelvis": pel_head}

        def head_of(bone, parent):
            return pos[parent] + D[parent] @ (self.rest_head[bone] - self.rest_head[parent])
        for n, par in (("spine_01", "pelvis"), ("spine_02", "spine_01"), ("spine_03", "spine_02"),
                       ("neck_01", "spine_03"), ("Head", "neck_01"), ("clavicle_l", "spine_03"),
                       ("clavicle_r", "spine_03"), ("thigh_l", "pelvis"), ("thigh_r", "pelvis")):
            pos[n] = head_of(n, par)
        for s in "lr":
            pos["upperarm_" + s] = head_of("upperarm_" + s, "clavicle_" + s)
        for s in "lr":
            for kind, a, b, c in (("arm", "upperarm_", "lowerarm_", "hand_"), ("leg", "thigh_", "calf_", "foot_")):
                L = spec.get(f"{kind}_{s}", {})
                fr = L.get("frame", "facing" if kind == "leg" else "chest")
                F = {"facing": C, "body": D["pelvis"], "chest": D["spine_03"]}[fr]
                ua, lo, en = a + s, b + s, c + s
                if "ik" in L:
                    root = pos[ua]
                    tgt = self.PF(L["ik"]) if kind == "leg" else self.P(L["ik"])
                    pole = Vector(L.get("pole", (0, -1, 0)))
                    l1, l2 = self.len[ua], self.len[lo]
                    dv = tgt - root
                    d = min(max(dv.length, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
                    u = dv.normalized()
                    v = pole - pole.dot(u) * u
                    v.normalize()
                    ang = math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
                    knee = root + l1 * (math.cos(ang) * u + math.sin(ang) * v)
                    D[ua] = swing(self.rest_dir[ua], knee - root)
                    D[lo] = swing(self.rest_dir[lo], root + u * d - knee)
                else:
                    up_b = Vector(L.get("up", self.rest_dir[ua]))
                    lo_b = Vector(L.get("lo", up_b))
                    D[ua] = F @ swing(self.rest_dir[ua], up_b)
                    D[lo] = F @ swing(self.rest_dir[lo], lo_b)
                if "hand" in L or "foot" in L:
                    D[en] = F @ swing(self.rest_dir[en], Vector(L.get("hand", L.get("foot"))))
                elif "foot_world" in L or "hand_world" in L:
                    # orientata nel mondo (riferimento "facing"): il piede piatto, o la mano che tiene dritto un
                    # bastone qualunque cosa faccia il busto (il bordone dei perdoni)
                    D[en] = C @ swing(self.rest_dir[en], Vector(L.get("foot_world", L.get("hand_world"))))
                elif kind == "leg":
                    D[en] = C @ Matrix.Identity(3)
                else:
                    D[en] = D[lo]
                pos[lo] = pos[ua] + D[ua] @ (self.rest_head[lo] - self.rest_head[ua])
                pos[en] = pos[lo] + D[lo] @ (self.rest_head[en] - self.rest_head[lo])
        for s in "lr":
            D["ball_" + s] = D["foot_" + s]
        return D, pos

    def key(self, spec, frame):
        D, pos = self.deltas(spec)
        posed = {}
        for name in self.order:
            b = self.B[name]
            base = posed[b.parent.name] @ (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent \
                else b.matrix_local.copy()
            pb = self.arm.pose.bones[name]
            if name in D:
                Rw = D[name] @ self.rest_rot[name]
                q = (base.to_3x3().normalized().inverted() @ Rw).to_quaternion()
            elif name in self.fist:
                q = self.fist[name].copy()
            else:
                q = Quaternion()
            loc = Vector()
            if name == "pelvis":
                loc = Vector(base.inverted() @ pos["pelvis"])
            posed[name] = base @ Matrix.Translation(loc) @ q.to_matrix().to_4x4()
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = q
            pb.location = loc
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            pb.keyframe_insert("location", frame=frame)
        return pos


def set_constant(act):
    owners = []
    for L in getattr(act, "layers", []):
        for st in L.strips:
            for cb in getattr(st, "channelbags", []):
                owners.append(cb)
    if not owners:
        owners = [act]
    for o in owners:
        for fc in o.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


# ====================================================================== pose di base
GUARD = dict(
    hip=(0.0, 0.03, 0.90), pelvis=(0, 0, 12), spine=(8, 0, -14), neck=(-6, 0, 4),
    arm_l=dict(up=V(0.30, -0.55, -0.78), lo=V(-0.02, -0.45, 0.89)),        # braccio cyber: pugno avanzato
    arm_r=dict(up=V(-0.28, -0.25, -0.93), lo=V(0.12, -0.45, 0.88)),        # pugno dietro, al mento
    leg_l=dict(ik=(0.13, -0.17, 0.086), pole=(0.25, -1, 0)),
    leg_r=dict(ik=(-0.12, 0.22, 0.086), pole=(-0.1, -1, 0)),
)


def guard(**kw):
    d = copy.deepcopy(GUARD)
    d.update(kw)
    return d


def stance(**kw):
    """posizione dei nemici (rivolti a destra): guardia più bassa e sciatta."""
    d = dict(hip=(0.0, 0.02, 0.91), pelvis=(0, 0, 10), spine=(10, 0, -10), neck=(-8, 0, 0),
             arm_l=dict(up=V(0.35, -0.35, -0.87), lo=V(0.05, -0.75, 0.66)),
             arm_r=dict(up=V(-0.30, -0.15, -0.94), lo=V(0.05, -0.70, 0.71)),
             leg_l=dict(ik=(0.12, -0.15, 0.086), pole=(0.25, -1, 0)),
             leg_r=dict(ik=(-0.12, 0.20, 0.086), pole=(-0.1, -1, 0)))
    d.update(kw)
    return d


# ====================================================================== GIG
def gig_air_kick():
    """calcio volante: raccolta, calcio teso con la gamba vicina (destra), ritorno (tenuto fino a terra)."""
    P = []
    P.append(("tuck", guard(hip=(0.0, 0.02, 0.92), pelvis=(-14, 0, 8), spine=(14, 0, -8), neck=(-6, 0, 0),
                            leg_l=dict(up=V(0.10, -0.95, -0.30), lo=V(0.06, 0.20, -0.98)),
                            leg_r=dict(up=V(-0.08, -0.80, -0.60), lo=V(-0.05, 0.62, -0.78)))))
    P.append(("kick", guard(hip=(0.0, 0.06, 0.92), pelvis=(-32, 0, 4), spine=(-6, 0, -10), neck=(16, 0, 0),
                            arm_l=dict(up=V(0.45, -0.30, -0.84), lo=V(0.15, -0.80, 0.58)),
                            arm_r=dict(up=V(-0.50, 0.45, -0.74), lo=V(-0.30, 0.70, -0.65)),
                            leg_l=dict(up=V(0.10, -0.92, -0.38), lo=V(0.06, 0.62, -0.78)),
                            leg_r=dict(up=V(-0.04, -0.97, -0.22), lo=V(-0.03, -0.98, -0.18), foot=V(0, -0.4, 0.92)))))
    P.append(("retract", guard(hip=(0.0, 0.03, 0.92), pelvis=(-16, 0, 6), spine=(8, 0, -8), neck=(-2, 0, 0),
                               leg_l=dict(up=V(0.10, -0.70, -0.71), lo=V(0.06, 0.40, -0.92)),
                               leg_r=dict(up=V(-0.08, -0.62, -0.78), lo=V(-0.05, 0.45, -0.89)))))
    return P


def gig_hook():
    """gancio cyber: gancio largo col braccio sinistro (cibernetico, braccio avanzato della guardia ortodossa).
    Carica con la spalla sinistra tirata indietro (bacino e busto ruotati verso sinistra, gomito alto e fuori,
    pugno vicino all'orecchio), impatto con il busto ruotato verso destra, gomito piegato a circa 90° all'altezza
    della spalla e pugno che attraversa davanti al viso del bersaglio, proseguimento e ritorno in guardia.
    Così la sagoma non somiglia al jab (braccio teso). Il piccolo passo in avanti dell'impatto (dx 3) compensa
    la portata del braccio piegato senza avvicinare troppo il nemico al calcio finale della combo."""
    P = []
    P.append(("load", guard(hip=(0.0, 0.04, 0.88), pelvis=(2, 0, 20), spine=(8, 0, 16), neck=(-6, 0, -14),
                            arm_l=dict(up=V(0.75, 0.10, -0.65), lo=V(0.05, -0.55, 0.83)),
                            leg_l=dict(ik=(0.14, -0.17, 0.086), pole=(0.35, -1, 0)),
                            leg_r=dict(ik=(-0.12, 0.22, 0.086), pole=(-0.1, -1, 0)))))
    P.append(("cock", guard(hip=(0.0, 0.05, 0.87), pelvis=(4, 0, 28), spine=(6, 0, 30), neck=(-6, 0, -30),
                            arm_l=dict(ik=(0.38, 0.06, 1.48), pole=(0.7, 0.3, 0.6)),
                            leg_l=dict(ik=(0.14, -0.17, 0.086), pole=(0.4, -1, 0)),
                            leg_r=dict(ik=(-0.12, 0.22, 0.086), pole=(-0.1, -1, 0)))))
    # impatto: spalla sinistra molto avanti, braccio piegato in orizzontale, pugno davanti al viso del bersaglio
    P.append(("impact", guard(hip=(0.0, -0.10, 0.86), pelvis=(8, 0, -26), spine=(10, 0, -42), neck=(-6, 0, 46),
                              arm_l=dict(ik=(0.06, -0.64, 1.44), pole=(1.0, 0.05, 0.3)),
                              leg_l=dict(ik=(0.14, -0.26, 0.086), pole=(0.1, -1, 0)),
                              leg_r=dict(ik=(-0.12, 0.18, 0.13), pole=(-0.3, -1, 0), foot_world=V(0, -0.3, -0.95)))))
    P.append(("follow", guard(hip=(0.0, -0.08, 0.87), pelvis=(6, 0, -30), spine=(10, 0, -48), neck=(-4, 0, 50),
                              arm_l=dict(ik=(-0.16, -0.50, 1.40), pole=(1.0, 0.1, 0.3)),
                              leg_l=dict(ik=(0.14, -0.26, 0.086), pole=(0.1, -1, 0)),
                              leg_r=dict(ik=(-0.12, 0.18, 0.13), pole=(-0.3, -1, 0), foot_world=V(0, -0.3, -0.95)))))
    P.append(("return", guard(hip=(0.0, -0.02, 0.88), pelvis=(2, 0, -4), spine=(10, 0, -14), neck=(-6, 0, 10),
                              arm_l=dict(up=V(0.40, -0.60, -0.69), lo=V(-0.25, -0.55, 0.80)),
                              leg_l=dict(ik=(0.14, -0.20, 0.086), pole=(0.25, -1, 0)))))
    return P


def gig_jump():
    """salto: spinta, raccolta in salita, apice, discesa con le gambe pronte."""
    P = []
    P.append(("takeoff", guard(hip=(0.0, 0.02, 0.96), pelvis=(-4, 0, 8), spine=(4, 0, -10), neck=(-2, 0, 0),
                               arm_l=dict(up=V(0.35, -0.55, -0.76), lo=V(0.0, -0.40, 0.92)),
                               arm_r=dict(up=V(-0.35, -0.30, -0.89), lo=V(0.1, -0.50, 0.86)),
                               leg_l=dict(up=V(0.08, -0.10, -0.99), lo=V(0.06, 0.25, -0.97), foot=V(0, -0.2, -0.98)),
                               leg_r=dict(up=V(-0.08, 0.25, -0.97), lo=V(-0.05, 0.45, -0.89), foot=V(0, 0.1, -0.99)))))
    P.append(("rise", guard(hip=(0.0, 0.02, 0.94), pelvis=(-8, 0, 8), spine=(8, 0, -8), neck=(-4, 0, 0),
                            leg_l=dict(up=V(0.10, -0.80, -0.60), lo=V(0.06, 0.45, -0.89)),
                            leg_r=dict(up=V(-0.08, -0.40, -0.91), lo=V(-0.05, 0.75, -0.66)))))
    P.append(("apex", guard(hip=(0.0, 0.02, 0.94), pelvis=(-4, 0, 8), spine=(6, 0, -8), neck=(-4, 0, 0),
                            leg_l=dict(up=V(0.10, -0.60, -0.79), lo=V(0.06, 0.30, -0.95)),
                            leg_r=dict(up=V(-0.08, -0.20, -0.98), lo=V(-0.05, 0.55, -0.83)))))
    P.append(("fall", guard(hip=(0.0, 0.02, 0.94), pelvis=(0, 0, 8), spine=(4, 0, -8), neck=(-6, 0, 0),
                            arm_l=dict(up=V(0.45, -0.45, -0.77), lo=V(0.15, -0.55, 0.82)),
                            arm_r=dict(up=V(-0.45, -0.20, -0.87), lo=V(0.05, -0.55, 0.83)),
                            leg_l=dict(up=V(0.10, -0.30, -0.95), lo=V(0.06, 0.10, -0.99)),
                            leg_r=dict(up=V(-0.08, 0.10, -0.99), lo=V(-0.05, 0.30, -0.95)))))
    P.append(("land", guard(hip=(0.0, 0.05, 0.78), pelvis=(6, 0, 12), spine=(16, 0, -12), neck=(-10, 0, 4),
                            leg_l=dict(ik=(0.14, -0.17, 0.086), pole=(0.25, -1, 0)),
                            leg_r=dict(ik=(-0.13, 0.22, 0.086), pole=(-0.1, -1, 0)))))
    return P


SUP = dict(leg_l=dict(ik=(0.14, -0.14, 0.086), pole=(0.25, -1, 0)), leg_r=dict(ik=(-0.12, 0.20, 0.086), pole=(-0.1, -1, 0)))


def clinch(y=-0.40, z=1.25, w=0.085):
    """mani dietro il collo della vittima (presa thai), gomiti in basso."""
    return dict(arm_l=dict(ik=(w, y, z), pole=(1, 0.2, -0.8)), arm_r=dict(ik=(-w, y, z), pole=(-1, 0.2, -0.8)))


def gig_grab():
    P = []
    P.append(("reach", guard(hip=(0.0, 0.0, 0.90), pelvis=(6, 0, 4), spine=(10, 0, 0), neck=(0, 0, 0),
                             arm_l=dict(ik=(0.12, -0.48, 1.32), pole=(1, 0.3, -0.6)),
                             arm_r=dict(ik=(-0.10, -0.46, 1.30), pole=(-1, 0.3, -0.6)), **SUP)))
    P.append(("hold", guard(hip=(0.0, 0.0, 0.89), pelvis=(8, 0, 0), spine=(14, 0, 0), neck=(4, 0, 0),
                            **clinch(-0.40, 1.24), **SUP)))
    return P


def gig_knee():
    P = []
    P.append(("windup", guard(hip=(0.0, 0.03, 0.89), pelvis=(-2, 0, 0), spine=(24, 0, 0), neck=(6, 0, 0),
                              **clinch(-0.38, 1.12),
                              leg_l=dict(ik=(0.14, -0.14, 0.086), pole=(0.25, -1, 0)),
                              leg_r=dict(up=V(-0.08, 0.32, -0.94), lo=V(-0.05, 0.70, -0.71)))))
    P.append(("hit", guard(hip=(0.0, -0.01, 0.95), pelvis=(-16, 0, 0), spine=(22, 0, 0), neck=(8, 0, 0),
                           **clinch(-0.37, 1.05),
                           leg_l=dict(ik=(0.14, -0.14, 0.086), pole=(0.25, -1, 0)),
                           leg_r=dict(up=V(-0.06, -0.72, 0.69), lo=V(-0.03, 0.28, -0.96)))))
    P.append(("back", guard(hip=(0.0, 0.0, 0.91), pelvis=(0, 0, 0), spine=(18, 0, 0), neck=(4, 0, 0),
                            **clinch(-0.39, 1.16),
                            leg_l=dict(ik=(0.14, -0.14, 0.086), pole=(0.25, -1, 0)),
                            leg_r=dict(up=V(-0.08, -0.20, -0.98), lo=V(-0.05, 0.45, -0.89)))))
    P.append(("settle", guard(hip=(0.0, 0.0, 0.89), pelvis=(8, 0, 0), spine=(14, 0, 0), neck=(4, 0, 0),
                              **clinch(-0.40, 1.24), **SUP)))
    return P


def gig_throw():
    P = []
    P.append(("dip", guard(hip=(0.0, 0.0, 0.80), pelvis=(10, 0, 0), spine=(22, 0, 0), neck=(4, 0, 0),
                           arm_l=dict(ik=(0.16, -0.40, 1.02), pole=(1, 0.3, -0.6)),
                           arm_r=dict(ik=(-0.16, -0.40, 1.00), pole=(-1, 0.3, -0.6)),
                           leg_l=dict(ik=(0.16, -0.20, 0.086), pole=(0.3, -1, 0)),
                           leg_r=dict(ik=(-0.15, 0.22, 0.086), pole=(-0.2, -1, 0)))))
    P.append(("heave", guard(hip=(0.0, 0.02, 0.88), pelvis=(-8, 0, 0), spine=(-6, 0, 0), neck=(-14, 0, 0),
                             arm_l=dict(ik=(0.15, -0.42, 1.30), pole=(1, 0.4, -0.5)),
                             arm_r=dict(ik=(-0.15, -0.42, 1.28), pole=(-1, 0.4, -0.5)),
                             leg_l=dict(ik=(0.16, -0.20, 0.086), pole=(0.3, -1, 0)),
                             leg_r=dict(ik=(-0.15, 0.22, 0.086), pole=(-0.2, -1, 0)))))
    P.append(("release", guard(hip=(0.0, -0.16, 0.90), pelvis=(-4, 0, -4), spine=(6, 0, -6), neck=(-6, 0, 0),
                               arm_l=dict(up=V(0.20, -0.85, 0.48), lo=V(0.10, -0.85, 0.52)),
                               arm_r=dict(up=V(-0.25, -0.88, 0.40), lo=V(-0.08, -0.85, 0.52)),
                               leg_l=dict(ik=(0.16, -0.40, 0.086), pole=(0.3, -1, 0.2)),
                               leg_r=dict(ik=(-0.14, 0.28, 0.15), pole=(-0.2, -1, 0), foot_world=V(0, -0.5, -0.86)))))
    P.append(("recover", guard(hip=(0.0, -0.06, 0.89), pelvis=(2, 0, 8), spine=(8, 0, -10), neck=(-6, 0, 2),
                               leg_l=dict(ik=(0.14, -0.30, 0.086), pole=(0.25, -1, 0)),
                               leg_r=dict(ik=(-0.12, 0.18, 0.086), pole=(-0.1, -1, 0)))))
    return P


# ====================================================================== vittime (rivolte a destra)
VLEGS = dict(leg_l=dict(ik=(0.12, -0.10, 0.086), pole=(0.25, -1, 0)), leg_r=dict(ik=(-0.13, 0.26, 0.086), pole=(-0.1, -1, 0)))


def victim_grabbed():
    P = []
    P.append(("pulled", stance(hip=(0.0, 0.05, 0.88), pelvis=(8, 0, 0), spine=(34, 0, 0), neck=(4, 0, 0),
                               arm_l=dict(up=V(0.30, -0.65, -0.70), lo=V(0.10, -0.85, 0.52)),
                               arm_r=dict(up=V(-0.30, -0.60, -0.74), lo=V(-0.10, -0.85, 0.52)), **VLEGS)))
    P.append(("held", stance(hip=(0.0, 0.07, 0.86), pelvis=(12, 0, 0), spine=(46, 0, 0), neck=(10, 0, 0),
                             arm_l=dict(up=V(0.35, -0.75, -0.56), lo=V(0.05, -0.80, 0.60)),
                             arm_r=dict(up=V(-0.35, -0.70, -0.62), lo=V(-0.05, -0.80, 0.60)), **VLEGS)))
    return P


def victim_kneed():
    P = []
    P.append(("pulled_down", stance(hip=(0.0, 0.08, 0.84), pelvis=(18, 0, 0), spine=(56, 0, 0), neck=(16, 0, 0),
                                    arm_l=dict(up=V(0.35, -0.60, -0.72), lo=V(0.15, -0.30, -0.94)),
                                    arm_r=dict(up=V(-0.35, -0.55, -0.76), lo=V(-0.15, -0.30, -0.94)), **VLEGS)))
    P.append(("impact", stance(hip=(0.0, 0.10, 0.90), pelvis=(14, 0, 0), spine=(40, 0, 0), neck=(-30, 0, 0),
                               arm_l=dict(up=V(0.60, 0.45, -0.66), lo=V(0.50, 0.65, -0.57)),
                               arm_r=dict(up=V(-0.60, 0.45, -0.66), lo=V(-0.50, 0.65, -0.57)),
                               leg_l=dict(ik=(0.12, -0.08, 0.13), pole=(0.25, -1, 0)),
                               leg_r=dict(ik=(-0.13, 0.30, 0.10), pole=(-0.1, -1, 0)))))
    P.append(("sag", stance(hip=(0.0, 0.08, 0.85), pelvis=(16, 0, 0), spine=(52, 0, 0), neck=(12, 0, 0),
                            arm_l=dict(up=V(0.30, -0.40, -0.87), lo=V(0.10, -0.20, -0.97)),
                            arm_r=dict(up=V(-0.30, -0.35, -0.89), lo=V(-0.10, -0.20, -0.97)), **VLEGS)))
    return P


def victim_thrown():
    P = []
    P.append(("gripped", stance(hip=(0.0, 0.06, 0.90), pelvis=(10, 0, 0), spine=(30, 0, 0), neck=(6, 0, 0),
                                arm_l=dict(up=V(0.45, -0.50, -0.74), lo=V(0.20, -0.75, 0.63)),
                                arm_r=dict(up=V(-0.45, -0.45, -0.77), lo=V(-0.20, -0.75, 0.63)),
                                leg_l=dict(ik=(0.12, -0.06, 0.12), pole=(0.25, -1, 0)),
                                leg_r=dict(ik=(-0.13, 0.24, 0.10), pole=(-0.1, -1, 0)))))
    P.append(("lifted", dict(hip=(0.0, 0.0, 0.98), pelvis=(-30, 0, 0), spine=(-10, 0, 0), neck=(-20, 0, 0),
                             arm_l=dict(up=V(0.85, -0.10, 0.52), lo=V(0.60, -0.30, 0.74)),
                             arm_r=dict(up=V(-0.85, -0.10, 0.52), lo=V(-0.60, -0.30, 0.74)),
                             leg_l=dict(frame="body", up=V(0.10, -0.40, -0.91), lo=V(0.08, 0.40, -0.91)),
                             leg_r=dict(frame="body", up=V(-0.10, -0.15, -0.98), lo=V(-0.08, 0.50, -0.86)))))
    P.append(("released", dict(hip=(0.0, 0.0, 0.66), pelvis=(-70, 0, 0), spine=(-10, 0, 0), neck=(-20, 0, 0),
                               arm_l=dict(up=V(0.90, 0.10, 0.42), lo=V(0.70, 0.40, 0.59)),
                               arm_r=dict(up=V(-0.90, 0.20, 0.39), lo=V(-0.60, 0.50, 0.62)),
                               leg_l=dict(frame="body", up=V(0.20, -0.60, -0.77), lo=V(0.10, 0.50, -0.86)),
                               leg_r=dict(frame="body", up=V(-0.15, -0.25, -0.96), lo=V(-0.10, 0.35, -0.93)))))
    P.append(("flying", dict(hip=(0.0, 0.0, 0.46), pelvis=(-92, 0, 0), spine=(-8, 0, 0), neck=(-18, 0, 0),
                             arm_l=dict(up=V(0.85, 0.20, 0.49), lo=V(0.55, 0.30, 0.78)),
                             arm_r=dict(up=V(-0.85, 0.10, 0.52), lo=V(-0.50, 0.20, 0.84)),
                             leg_l=dict(frame="body", up=V(0.15, -0.35, -0.92), lo=V(0.08, 0.50, -0.86)),
                             leg_r=dict(frame="body", up=V(-0.12, -0.10, -0.99), lo=V(-0.08, 0.15, -0.99)))))
    return P


def hurt_high():
    """colpo alto: testa buttata indietro, busto inarcato, braccia che si aprono; poi ritorno verso la guardia.
    Le clip UAL Hit_Head/Hit_Chest si muovono di 1 px a 48 px/m (poco di più a 60): troppo poco per leggersi in combattimento."""
    P = []
    P.append(("snap", guard(hip=(0.0, 0.07, 0.89), pelvis=(-8, 0, 10), spine=(-18, 0, -4), neck=(-40, 0, 6),
                            arm_l=dict(up=V(0.62, 0.25, -0.74), lo=V(0.45, -0.35, -0.82)),
                            arm_r=dict(up=V(-0.55, 0.30, -0.78), lo=V(-0.35, -0.20, -0.91)))))
    P.append(("recoil", guard(hip=(0.0, 0.06, 0.89), pelvis=(-5, 0, 10), spine=(-10, 0, -8), neck=(-24, 0, 4),
                              arm_l=dict(up=V(0.50, 0.0, -0.87), lo=V(0.25, -0.55, 0.20)),
                              arm_r=dict(up=V(-0.45, 0.10, -0.89), lo=V(-0.10, -0.50, 0.30)))))
    P.append(("recover", guard(hip=(0.0, 0.04, 0.89), pelvis=(-1, 0, 12), spine=(2, 0, -12), neck=(-10, 0, 4))))
    return P


def hurt_low():
    """colpo basso: piegato in due con le mani alla pancia, poi si raddrizza."""
    P = []
    P.append(("fold", guard(hip=(0.0, 0.09, 0.86), pelvis=(16, 0, 8), spine=(38, 0, -4), neck=(14, 0, 0),
                            arm_l=dict(up=V(0.22, -0.30, -0.93), lo=V(-0.50, -0.65, 0.57)),
                            arm_r=dict(up=V(-0.22, -0.35, -0.91), lo=V(0.50, -0.65, 0.57)))))
    P.append(("bent", guard(hip=(0.0, 0.08, 0.87), pelvis=(12, 0, 8), spine=(28, 0, -6), neck=(8, 0, 0),
                            arm_l=dict(up=V(0.25, -0.35, -0.90), lo=V(-0.40, -0.70, 0.59)),
                            arm_r=dict(up=V(-0.25, -0.35, -0.90), lo=V(0.40, -0.70, 0.59)))))
    P.append(("recover", guard(hip=(0.0, 0.05, 0.89), pelvis=(5, 0, 10), spine=(14, 0, -10), neck=(-2, 0, 2))))
    return P


def windups():
    """cariche dei nemici, da mettere prima dei colpi UAL (che partono dalla guardia senza preavviso):
    1 jab_load = pugno avanzato tirato indietro alla spalla, busto un po' all'indietro;
    2-3 cross_load = busto avvitato all'indietro, pugno dietro all'altezza dell'orecchio (montante del bruto)."""
    P = []
    P.append(("jab_load", guard(hip=(0.0, 0.06, 0.89), pelvis=(-4, 0, 18), spine=(0, 0, -6), neck=(-4, 0, -8),
                                arm_l=dict(up=V(0.45, 0.35, -0.82), lo=V(0.05, -0.45, 0.89)))))
    P.append(("cross_load1", guard(hip=(0.0, 0.07, 0.88), pelvis=(-2, 0, -8), spine=(2, 0, -24), neck=(-6, 0, 20),
                                   arm_r=dict(ik=(-0.26, 0.16, 1.48), pole=(-1, 0.2, -0.5)))))
    P.append(("cross_load2", guard(hip=(0.0, 0.09, 0.86), pelvis=(-4, 0, -14), spine=(-2, 0, -34), neck=(-8, 0, 30),
                                   arm_r=dict(ik=(-0.28, 0.24, 1.55), pole=(-1, 0.1, -0.4)),
                                   leg_l=dict(ik=(0.14, -0.17, 0.10), pole=(0.25, -1, 0)))))
    return P


def knock_recoil():
    """primo fotogramma di knock_air (tutti i personaggi): contraccolpo all'indietro. Testa e busto buttati
    indietro, bacino sopra l'ancora (che in knock_air è il punto a terra sotto il bacino), braccia che restano
    avanti perché il colpo arriva da davanti, la gamba avanzata che si stacca da terra. Il baricentro cade
    dietro l'ancora: il corpo è respinto, non si piega verso chi colpisce."""
    P = []
    P.append(("recoil", guard(hip=(0.0, 0.0, 0.93), pelvis=(-16, 0, 6), spine=(-30, 0, -4), neck=(-36, 0, 4),
                              arm_l=dict(up=V(0.55, -0.50, -0.67), lo=V(0.30, -0.88, 0.37)),
                              arm_r=dict(up=V(-0.50, -0.40, -0.77), lo=V(-0.25, -0.88, 0.40)),
                              leg_l=dict(up=V(0.10, -0.42, -0.90), lo=V(0.06, 0.18, -0.98)),
                              leg_r=dict(ik=(-0.12, 0.24, 0.10), pole=(-0.1, -1, 0)))))
    return P


def punk_haymaker():
    """gancio caricato del punk (braccio destro, quello vicino alla telecamera), dopo la carica a braccia aperte
    delle clip UAL: impatto con un gancio largo all'altezza del viso (busto ruotato verso sinistra, peso sul
    piede avanti, gomito piegato a circa 90° e alto, pugno che attraversa), proseguimento e ritorno."""
    P = []
    P.append(("impact", stance(hip=(0.0, -0.12, 0.86), pelvis=(6, 0, 22), spine=(12, 0, 34), neck=(-8, 0, -34),
                               arm_r=dict(ik=(0.04, -0.66, 1.42), pole=(-1.0, 0.05, 0.35)),
                               arm_l=dict(up=V(0.30, 0.15, -0.94), lo=V(0.10, -0.55, 0.83)),
                               leg_l=dict(ik=(0.14, -0.32, 0.086), pole=(0.25, -1, 0)),
                               leg_r=dict(ik=(-0.12, 0.24, 0.13), pole=(-0.1, -1, 0), foot_world=V(0, -0.35, -0.94)))))
    P.append(("follow", stance(hip=(0.0, -0.10, 0.86), pelvis=(8, 0, 30), spine=(16, 0, 44), neck=(-8, 0, -40),
                               arm_r=dict(ik=(0.22, -0.48, 1.36), pole=(-1.0, 0.1, 0.3)),
                               arm_l=dict(up=V(0.30, 0.20, -0.93), lo=V(0.10, -0.50, 0.86)),
                               leg_l=dict(ik=(0.14, -0.32, 0.086), pole=(0.25, -1, 0)),
                               leg_r=dict(ik=(-0.12, 0.24, 0.13), pole=(-0.1, -1, 0), foot_world=V(0, -0.35, -0.94)))))
    P.append(("recover", stance(hip=(0.0, -0.04, 0.89), pelvis=(4, 0, 14), spine=(10, 0, 8), neck=(-8, 0, -8),
                                leg_l=dict(ik=(0.13, -0.24, 0.086), pole=(0.25, -1, 0)))))
    return P


def bruiser_punch():
    """diretto del bruto con tutto il corpo: spinta (spalla destra che parte, passo avanti), impatto con il busto
    in avanti e il braccio teso all'altezza del petto di GIG, poi il braccio che rientra. Il passo lo dà il dx
    dei fotogrammi (6-10 px in tutto); l'impatto si ripete nel recupero, così resta tenuto."""
    P = []
    P.append(("drive", stance(hip=(0.0, -0.06, 0.88), pelvis=(4, 0, 12), spine=(12, 0, 16), neck=(-10, 0, -14),
                              arm_r=dict(ik=(-0.22, -0.20, 1.40), pole=(-0.6, 0.6, -0.5)),
                              arm_l=dict(up=V(0.30, -0.20, -0.93), lo=V(0.10, -0.65, 0.75)),
                              leg_l=dict(ik=(0.13, -0.30, 0.10), pole=(0.25, -1, 0)),
                              leg_r=dict(ik=(-0.12, 0.22, 0.086), pole=(-0.1, -1, 0)))))
    P.append(("impact", stance(hip=(0.0, -0.17, 0.85), pelvis=(8, 0, 22), spine=(18, 0, 30), neck=(-14, 0, -28),
                               arm_r=dict(ik=(-0.02, -0.84, 1.34), pole=(-0.5, 0.3, -0.8)),
                               arm_l=dict(up=V(0.25, 0.20, -0.95), lo=V(0.05, -0.55, 0.83)),
                               leg_l=dict(ik=(0.14, -0.42, 0.086), pole=(0.25, -1, 0)),
                               leg_r=dict(ik=(-0.12, 0.30, 0.13), pole=(-0.1, -1, 0), foot_world=V(0, -0.4, -0.92)))))
    P.append(("retract", stance(hip=(0.0, -0.12, 0.87), pelvis=(6, 0, 14), spine=(14, 0, 16), neck=(-12, 0, -14),
                                arm_r=dict(ik=(-0.12, -0.52, 1.30), pole=(-0.6, 0.3, -0.8)),
                                leg_l=dict(ik=(0.14, -0.36, 0.086), pole=(0.25, -1, 0)),
                                leg_r=dict(ik=(-0.12, 0.26, 0.10), pole=(-0.1, -1, 0)))))
    return P


SETS = dict(gig_air_kick=gig_air_kick, gig_jump=gig_jump, gig_grab=gig_grab, gig_knee=gig_knee, gig_throw=gig_throw,
            gig_hook=gig_hook, victim_grabbed=victim_grabbed, victim_kneed=victim_kneed, victim_thrown=victim_thrown,
            hurt_high=hurt_high, hurt_low=hurt_low, windups=windups, knock_recoil=knock_recoil,
            punk_haymaker=punk_haymaker, bruiser_punch=bruiser_punch)


def tweak(spec, params):
    """ritocchi per corpo (dal JSON del personaggio): bend = gradi di busto in più, hip_dz = metri di anche."""
    s = copy.deepcopy(spec)
    if "bend" in params and "spine" in s:
        p, r, y = s["spine"]
        s["spine"] = (p + params["bend"], r, y)
    if "hip_dz" in params and "hip" in s:
        x, y, z = s["hip"]
        s["hip"] = (x, y, z + params["hip_dz"])
    return s


def make_action(rig, set_name, act_name, params):
    poses = SETS[set_name]()
    pp = params.get(set_name, {})
    poses = [(lab, tweak(spec, pp.get(lab, pp.get("*", {})))) for lab, spec in poses]
    act = bpy.data.actions.new(act_name)
    ad = rig.arm.animation_data or rig.arm.animation_data_create()
    ad.action = act
    for i, (lab, spec) in enumerate(poses):
        rig.key(spec, i + 1)
    set_constant(act)
    ad.action = None
    for pb in rig.arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    act["labels"] = [lab for lab, _ in poses]
    print("[poses]", act_name, [lab for lab, _ in poses], flush=True)
    return act
