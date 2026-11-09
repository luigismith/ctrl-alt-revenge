# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - pipeline v7: principi dell'animazione PRIMA della pixelatura (dalla prova spike-sprite-v7).

  * pose chiave scritte (stesso formato di char_poses) con anticipazione, overshoot e tenute;
  * una "traccia" per mossa: [(tick, chiave, easing)] -> la posa a qualunque tick (anche frazionario);
    gli intercalari fondono le chiavi: busto e gambe con IK si interpolano sulla specifica (i piedi
    restano piantati), le braccia con slerp delle rotazioni locali (il pugno segue un arco);
  * i fotogrammi da disegnare (il "foglio di esposizione") stanno nel JSON del personaggio:
    {"at": tick della traccia, "t": durata in tick, ...}, così la spaziatura è scelta e non uniforme;
  * molla sul codino (osso aggiunto): simulata a 60 Hz sul movimento continuo della testa;
  * scie (smear): per ogni fotogramma i punti di pugni e piedi nei sotto-istanti dal fotogramma prima.
"""
import copy
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

import char_poses as CP

V = CP.V


def guard(**kw):
    """guardia v7: come quella di char_poses ma con i piedi più larghi (sagoma più piantata, alla SoR2)."""
    d = CP.guard()
    d["leg_l"] = dict(ik=(0.16, -0.23, 0.086), pole=(0.3, -1, 0))
    d["leg_r"] = dict(ik=(-0.15, 0.26, 0.086), pole=(-0.15, -1, 0))
    d["hip"] = (0.0, 0.02, 0.885)
    d.update(kw)
    return d

ARM_BONES = [f"{b}_{s}" for s in "lr" for b in ("upperarm", "lowerarm", "hand")]
LEG_BONES = {s: [f"{b}_{s}" for b in ("thigh", "calf", "foot", "ball")] for s in "lr"}


# ============================================================== easing
def _snap(t):
    return t ** 3


EASE = {
    "lin": lambda t: t,
    "acc": lambda t: t * t,                       # parte piano, arriva veloce (colpo che parte)
    "dec": lambda t: 1 - (1 - t) ** 2,            # parte veloce, arriva piano (ritorno, assestamento)
    "smooth": lambda t: t * t * (3 - 2 * t),      # lento-veloce-lento (respiro, ritorni)
    "snap": _snap,                                 # tenuta lunga poi scatto (carica -> colpo)
    "hold": lambda t: 0.0,                        # resta sulla chiave di partenza fino alla prossima
    "step": lambda t: 1.0 if t >= 1.0 else 0.0,
}


# ============================================================== pose locali dalla specifica
def local_pose(rig, D, pos):
    """come char_poses.Rig.key ma senza chiavi: {osso: (quaternione locale, posizione locale)}."""
    posed, out = {}, {}
    for name in rig.order:
        b = rig.B[name]
        base = posed[b.parent.name] @ (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent \
            else b.matrix_local.copy()
        if name in D:
            Rw = D[name] @ rig.rest_rot[name]
            q = (base.to_3x3().normalized().inverted() @ Rw).to_quaternion()
        elif name in rig.fist:
            q = rig.fist[name].copy()
        else:
            q = Quaternion()
        loc = Vector()
        if name == "pelvis":
            loc = Vector(base.inverted() @ pos["pelvis"])
        posed[name] = base @ Matrix.Translation(loc) @ q.to_matrix().to_4x4()
        out[name] = (q, loc)
    return out


def apply_local(arm, L, skip=()):
    for name, (q, loc) in L.items():
        if name in skip or name not in arm.pose.bones:
            continue
        pb = arm.pose.bones[name]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = q
        pb.location = loc


def _lerp(a, b, t):
    return a + (b - a) * t


def _lerp3(a, b, t):
    return tuple(_lerp(x, y, t) for x, y in zip(a, b))


def lerp_spec(sa, sb, t):
    """interpolazione sulla specifica (busto, collo, anche, clavicole; gambe se entrambe in IK)."""
    s = copy.deepcopy(sa)
    for k in ("hip", "pelvis", "spine", "neck", "clav_l", "clav_r"):
        a = sa.get(k, (0, 0, 0) if k != "hip" else None)
        b = sb.get(k, (0, 0, 0) if k != "hip" else None)
        if a is None or b is None:
            continue
        s[k] = _lerp3(a, b, t)
    s["face"] = _lerp(sa.get("face", 0.0), sb.get("face", 0.0), t)
    lin_arms = []
    for side in "lr":
        k = "arm_" + side
        la, lb = sa.get(k, {}), sb.get(k, {})
        if "ik" in la and "ik" in lb:
            d = dict(la)
            d["ik"] = _lerp3(la["ik"], lb["ik"], t)
            d["pole"] = _lerp3(la.get("pole", (0, -1, 0)), lb.get("pole", (0, -1, 0)), t)
            s[k] = d
            lin_arms.append(side)
    slerp_legs = []
    for side in "lr":
        k = "leg_" + side
        la, lb = sa.get(k, {}), sb.get(k, {})
        if "ik" in la and "ik" in lb:
            d = dict(la)
            d["ik"] = _lerp3(la["ik"], lb["ik"], t)
            pa, pb_ = la.get("pole", (0, -1, 0)), lb.get("pole", (0, -1, 0))
            d["pole"] = _lerp3(pa, pb_, t)
            if "foot_world" in la or "foot_world" in lb:
                fa = Vector(la.get("foot_world", (0, 0, -1)))
                fb = Vector(lb.get("foot_world", (0, 0, -1)))
                d["foot_world"] = tuple(fa.lerp(fb, t).normalized())
            s[k] = d
        else:
            slerp_legs.append(side)
    return s, slerp_legs, lin_arms


class Track:
    """traccia di una mossa: chiavi (nome -> specifica) e [(tick, nome, easing)]."""

    def __init__(self, rig, keys, track, lin_arms=()):
        self.rig = rig
        self.lin_arms = tuple(lin_arms)
        self.keys = keys
        self.track = sorted(track, key=lambda e: e[0])
        self._cache = {}

    def _local(self, name):
        if name not in self._cache:
            D, pos = self.rig.deltas(self.keys[name])
            self._cache[name] = local_pose(self.rig, D, pos)
        return self._cache[name]

    def pose_at(self, t):
        tr = self.track
        if t <= tr[0][0]:
            return self._local(tr[0][1])
        if t >= tr[-1][0]:
            return self._local(tr[-1][1])
        for i in range(len(tr) - 1):
            t0, k0 = tr[i][0], tr[i][1]
            t1, k1, ez = tr[i + 1][0], tr[i + 1][1], (tr[i + 1][2] if len(tr[i + 1]) > 2 else "smooth")
            if t0 <= t <= t1:
                u = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
                e = EASE[ez](max(0.0, min(1.0, u)))
                return self.blend(k0, k1, e)
        return self._local(tr[-1][1])

    def blend(self, ka, kb, e):
        if e <= 0.0:
            return self._local(ka)
        if e >= 1.0:
            return self._local(kb)
        sa, sb = self.keys[ka], self.keys[kb]
        S, slerp_legs, lin = lerp_spec(sa, sb, e)
        D, pos = self.rig.deltas(S)
        LS = local_pose(self.rig, D, pos)
        LA, LB = self._local(ka), self._local(kb)
        lin_ok = [sd for sd in self.lin_arms if sd in lin]
        bones = [b for b in ARM_BONES if b[-1] not in lin_ok]
        for side in slerp_legs:
            bones += LEG_BONES[side]
        for b in bones:
            if b in LA and b in LB:
                qa, qb = LA[b][0], LB[b][0]
                LS[b] = (qa.slerp(qb, e), LS[b][1])
        return LS


# ============================================================== pose chiave della prova (GIG rivolto a destra)
def _g(**kw):
    return guard(**kw)


def keys_idle():
    g = guard()
    inhale = guard(hip=(0.0, 0.03, 0.905), pelvis=(0, 0, 12), spine=(5, 0, -14), neck=(-8, 0, 4),
                   arm_l=dict(up=V(0.30, -0.55, -0.78), lo=V(-0.04, -0.42, 0.91)),
                   arm_r=dict(up=V(-0.28, -0.25, -0.93), lo=V(0.12, -0.42, 0.90)))
    exhale = guard(hip=(0.0, 0.03, 0.885), pelvis=(0, 0, 12), spine=(11, 0, -14), neck=(-4, 0, 4),
                   arm_l=dict(up=V(0.30, -0.56, -0.77), lo=V(0.0, -0.50, 0.87)),
                   arm_r=dict(up=V(-0.28, -0.27, -0.92), lo=V(0.12, -0.50, 0.86)))
    return dict(guard=g, inhale=inhale, exhale=exhale)


def _fwd(yaw_chest_deg, up=0.0):
    """direzione (nel riferimento del petto) che nel mondo va dritta avanti (-Y), con il petto ruotato di yaw."""
    t = math.radians(yaw_chest_deg)
    return V(-math.sin(t), -math.cos(t), up)


def keys_jab1():
    """jab col braccio avanzato (sinistro, cibernetico): piccola anticipazione (pugno che rientra al mento, spalla
    indietro), colpo dritto (pugno su una linea, IK) con la spalla che viene avanti, overshoot, ritorno."""
    k = {}
    k["guard"] = guard()
    k["anti"] = guard(hip=(0.0, 0.05, 0.88), pelvis=(-2, 0, 18), spine=(4, 0, -2), neck=(-6, 0, -8),
                      arm_l=dict(ik=(0.10, -0.16, 1.40), pole=(1.0, 0.2, -0.7)))
    k["hit"] = guard(hip=(0.0, -0.05, 0.875), pelvis=(4, 0, 0), spine=(8, 0, -34), neck=(-6, 0, 28),
                     arm_l=dict(ik=(0.02, -0.80, 1.46), pole=(1.0, 0.0, -0.5)),
                     arm_r=dict(up=V(-0.30, -0.20, -0.93), lo=V(0.10, -0.50, 0.86)),
                     leg_l=dict(ik=(0.16, -0.27, 0.086), pole=(0.3, -1, 0)))
    k["over"] = guard(hip=(0.0, -0.07, 0.87), pelvis=(6, 0, -4), spine=(10, 0, -42), neck=(-6, 0, 34),
                      arm_l=dict(ik=(0.0, -0.88, 1.45), pole=(1.0, 0.0, -0.5)),
                      arm_r=dict(up=V(-0.30, -0.20, -0.93), lo=V(0.10, -0.50, 0.86)),
                      leg_l=dict(ik=(0.16, -0.27, 0.086), pole=(0.3, -1, 0)))
    k["back"] = guard(hip=(0.0, 0.0, 0.88), pelvis=(1, 0, 8), spine=(8, 0, -18), neck=(-6, 0, 8),
                      arm_l=dict(ik=(0.08, -0.45, 1.42), pole=(1.0, 0.1, -0.6)))
    return k


def keys_jab2():
    """diretto col braccio dietro (destro, vicino alla telecamera): il busto ruota a sinistra, la spalla destra
    va avanti, il tallone dietro si alza; pugno su una linea (IK), overshoot e ritorno."""
    k = {}
    k["guard"] = guard()
    k["anti"] = guard(hip=(0.0, 0.05, 0.875), pelvis=(-2, 0, 4), spine=(6, 0, -24), neck=(-6, 0, 18),
                      arm_r=dict(ik=(-0.16, -0.08, 1.40), pole=(-1.0, 0.2, -0.7)))
    k["hit"] = guard(hip=(0.0, -0.06, 0.865), pelvis=(6, 0, 30), spine=(8, 0, 8), neck=(-8, 0, -34),
                     arm_r=dict(ik=(-0.02, -0.84, 1.42), pole=(-1.0, 0.0, -0.5)),
                     arm_l=dict(up=V(0.40, -0.25, -0.88), lo=V(-0.10, -0.40, 0.91)),
                     leg_l=dict(ik=(0.16, -0.27, 0.086), pole=(0.3, -1, 0)),
                     leg_r=dict(ik=(-0.14, 0.22, 0.12), pole=(-0.1, -1, 0), foot_world=V(0, -0.45, -0.89)))
    k["over"] = guard(hip=(0.0, -0.08, 0.86), pelvis=(8, 0, 36), spine=(10, 0, 12), neck=(-8, 0, -40),
                      arm_r=dict(ik=(0.0, -0.90, 1.40), pole=(-1.0, 0.0, -0.5)),
                      arm_l=dict(up=V(0.40, -0.25, -0.88), lo=V(-0.10, -0.40, 0.91)),
                      leg_l=dict(ik=(0.16, -0.27, 0.086), pole=(0.3, -1, 0)),
                      leg_r=dict(ik=(-0.14, 0.22, 0.12), pole=(-0.1, -1, 0), foot_world=V(0, -0.45, -0.89)))
    k["back"] = guard(hip=(0.0, 0.0, 0.875), pelvis=(2, 0, 18), spine=(8, 0, -6), neck=(-6, 0, -6),
                      arm_r=dict(ik=(-0.10, -0.40, 1.38), pole=(-1.0, 0.1, -0.6)))
    return k


def keys_hook():
    """gancio cyber (braccio sinistro): carica con la spalla indietro e il gomito alto, colpo ad arco con
    il busto che ruota molto (la spalla sinistra viene avanti verso lo schermo), impatto con il braccio
    piegato a 90° all'altezza della spalla, overshoot oltre il bersaglio, ritorno con assestamento."""
    k = {}
    k["guard"] = guard()
    k["load"] = guard(hip=(0.0, 0.06, 0.87), pelvis=(4, 0, 30), spine=(4, 0, 34), neck=(-6, 0, -36),
                      arm_l=dict(ik=(0.40, 0.10, 1.40), pole=(0.6, 0.6, 0.4)),
                      arm_r=dict(up=V(-0.30, -0.30, -0.90), lo=V(0.10, -0.55, 0.83)),
                      leg_l=dict(ik=(0.14, -0.17, 0.086), pole=(0.4, -1, 0)),
                      leg_r=dict(ik=(-0.12, 0.22, 0.086), pole=(-0.1, -1, 0)))
    # sotto-chiave dell'arco: il pugno passa largo, fuori dalla spalla (la scia disegna l'arco)
    k["arc"] = guard(hip=(0.0, -0.02, 0.86), pelvis=(6, 0, 4), spine=(8, 0, -6), neck=(-6, 0, 0),
                     arm_l=dict(ik=(0.40, -0.40, 1.74), pole=(0.6, 0.2, 1.0)),
                     leg_l=dict(ik=(0.14, -0.22, 0.086), pole=(0.25, -1, 0)),
                     leg_r=dict(ik=(-0.12, 0.20, 0.10), pole=(-0.2, -1, 0)))
    # impatto: gancio "a ricciolo" (overhand) - corpo basso e proteso, gomito SOPRA la testa e pugno che scende
    # sul viso del bersaglio: il braccio fa una Λ sopra la sagoma, che non si confonde col jab (braccio orizzontale)
    k["impact"] = guard(hip=(0.0, -0.12, 0.81), pelvis=(14, 0, -24), spine=(24, 0, -36), neck=(-22, 0, 40),
                        arm_l=dict(ik=(0.04, -0.64, 1.36), pole=(0.45, -0.1, 1.0)),
                        arm_r=dict(up=V(-0.35, -0.10, -0.93), lo=V(0.20, -0.45, 0.87)),
                        leg_l=dict(ik=(0.16, -0.34, 0.086), pole=(0.1, -1, 0)),
                        leg_r=dict(ik=(-0.14, 0.24, 0.13), pole=(-0.3, -1, 0), foot_world=V(0, -0.3, -0.95)))
    k["over"] = guard(hip=(0.0, -0.13, 0.80), pelvis=(18, 0, -34), spine=(28, 0, -48), neck=(-24, 0, 52),
                      arm_l=dict(ik=(-0.18, -0.52, 1.18), pole=(0.5, 0.0, 1.0)),
                      arm_r=dict(up=V(-0.35, -0.05, -0.93), lo=V(0.20, -0.40, 0.89)),
                      leg_l=dict(ik=(0.16, -0.34, 0.086), pole=(0.1, -1, 0)),
                      leg_r=dict(ik=(-0.14, 0.24, 0.13), pole=(-0.3, -1, 0), foot_world=V(0, -0.3, -0.95)))
    k["back"] = guard(hip=(0.0, -0.03, 0.88), pelvis=(2, 0, 2), spine=(9, 0, -16), neck=(-6, 0, 12),
                      arm_l=dict(up=V(0.38, -0.60, -0.70), lo=V(-0.15, -0.50, 0.85)),
                      leg_l=dict(ik=(0.14, -0.20, 0.086), pole=(0.25, -1, 0)))
    return k


def keys_hurt_high():
    """colpo alto: scatto della testa all'indietro (impatto), massimo contraccolpo con overshoot, rimbalzo."""
    k = {}
    k["guard"] = guard()
    k["snap"] = guard(hip=(0.0, 0.08, 0.895), pelvis=(-10, 0, 14), spine=(-20, 0, -2), neck=(-30, 0, 10),
                      arm_l=dict(up=V(0.65, 0.25, -0.72), lo=V(0.55, -0.35, -0.76)),
                      arm_r=dict(up=V(-0.60, 0.30, -0.74), lo=V(-0.45, -0.25, -0.86)),
                      leg_l=dict(ik=(0.13, -0.17, 0.11), pole=(0.25, -1, 0)))
    k["max"] = guard(hip=(0.0, 0.12, 0.88), pelvis=(-12, 0, 16), spine=(-24, 0, 0), neck=(-26, 0, 14),
                     arm_l=dict(up=V(0.70, 0.35, -0.62), lo=V(0.60, 0.10, -0.79)),
                     arm_r=dict(up=V(-0.65, 0.40, -0.65), lo=V(-0.50, 0.10, -0.86)))
    # i piedi restano piantati: nel colpo subito la specifica vuole la reazione sul posto (validate_sprites)
    k["rebound"] = guard(hip=(0.0, 0.05, 0.875), pelvis=(4, 0, 12), spine=(16, 0, -10), neck=(4, 0, 4),
                         arm_l=dict(up=V(0.40, -0.30, -0.86), lo=V(0.15, -0.55, 0.82)),
                         arm_r=dict(up=V(-0.35, -0.10, -0.93), lo=V(0.10, -0.50, 0.86)))
    return k


def keys_double_jump():
    """doppio salto: in aria GIG si raccoglie col pugno cyber caricato sopra la testa, poi lo spara in basso
    DAVANTI al corpo (ginocchia ancora alte: si legge come una spinta sull'aria), il corpo parte verso l'alto
    allungato, si apre all'apice e si richiude pronto a cadere. Ancora all'altezza del bacino (pelvis_h)."""
    k = {}
    tuck_legs = dict(leg_l=dict(up=V(0.10, -0.92, -0.38), lo=V(0.06, 0.20, -0.98)),
                     leg_r=dict(up=V(-0.08, -0.82, -0.57), lo=V(-0.05, 0.50, -0.86)))
    k["air"] = guard(hip=(0.0, 0.02, 0.94), pelvis=(-4, 0, 8), spine=(6, 0, -8), neck=(-4, 0, 0),
                     leg_l=dict(up=V(0.10, -0.55, -0.83), lo=V(0.06, 0.45, -0.89)),
                     leg_r=dict(up=V(-0.08, -0.25, -0.96), lo=V(-0.05, 0.62, -0.78)))
    k["coil"] = guard(hip=(0.0, 0.02, 0.96), pelvis=(-16, 0, 14), spine=(18, 0, -6), neck=(-4, 0, -6),
                      arm_l=dict(ik=(0.26, -0.12, 1.78), pole=(0.8, 0.4, 0.2)),
                      arm_r=dict(up=V(-0.55, 0.25, -0.80), lo=V(-0.35, -0.30, -0.89)), **tuck_legs)
    k["thrust"] = guard(hip=(0.0, 0.02, 0.96), pelvis=(-14, 0, 10), spine=(24, 0, -8), neck=(14, 0, 0),
                        arm_l=dict(ik=(0.16, -0.40, 0.46), pole=(0.6, -0.2, 0.8)),
                        arm_r=dict(up=V(-0.70, 0.35, -0.62), lo=V(-0.55, 0.20, -0.81)), **tuck_legs)
    k["launch"] = guard(hip=(0.0, 0.02, 0.94), pelvis=(-4, 0, 8), spine=(4, 0, -6), neck=(-10, 0, 0),
                        arm_l=dict(ik=(0.16, -0.30, 0.50), pole=(0.6, -0.2, 0.8)),
                        arm_r=dict(up=V(-0.60, 0.30, -0.74), lo=V(-0.45, 0.35, -0.82)),
                        leg_l=dict(up=V(0.10, -0.38, -0.92), lo=V(0.06, 0.50, -0.86), foot=V(0, 0.5, -0.87)),
                        leg_r=dict(up=V(-0.08, -0.12, -0.99), lo=V(-0.05, 0.62, -0.78), foot=V(0, 0.6, -0.80)))
    k["open"] = guard(hip=(0.0, 0.02, 0.94), pelvis=(-6, 0, 8), spine=(8, 0, -8), neck=(-6, 0, 0),
                      arm_l=dict(up=V(0.60, -0.30, -0.74), lo=V(0.30, -0.60, 0.74)),
                      arm_r=dict(up=V(-0.60, -0.10, -0.79), lo=V(-0.10, -0.55, 0.83)),
                      leg_l=dict(up=V(0.10, -0.45, -0.89), lo=V(0.06, 0.25, -0.97)),
                      leg_r=dict(up=V(-0.08, -0.05, -1.0), lo=V(-0.05, 0.45, -0.89)))
    k["tuck"] = guard(hip=(0.0, 0.02, 0.96), pelvis=(-18, 0, 8), spine=(16, 0, -8), neck=(2, 0, 0),
                      arm_l=dict(up=V(0.55, -0.45, -0.70), lo=V(0.25, -0.60, 0.76)),
                      arm_r=dict(up=V(-0.55, -0.20, -0.81), lo=V(-0.10, -0.60, 0.79)),
                      leg_l=dict(up=V(0.10, -0.92, -0.38), lo=V(0.06, 0.30, -0.95)),
                      leg_r=dict(up=V(-0.08, -0.62, -0.78), lo=V(-0.05, 0.62, -0.78)))
    # caduta: ginocchio avanti su, l'altra gamba sotto pronta all'atterraggio, braccia aperte per l'equilibrio
    k["fall"] = guard(hip=(0.0, 0.02, 0.95), pelvis=(-8, 0, 8), spine=(6, 0, -8), neck=(-10, 0, 0),
                      arm_l=dict(up=V(0.75, -0.25, -0.61), lo=V(0.45, -0.55, 0.70)),
                      arm_r=dict(up=V(-0.75, 0.05, -0.66), lo=V(-0.35, -0.45, 0.82)),
                      leg_l=dict(up=V(0.10, -0.75, -0.65), lo=V(0.06, 0.35, -0.94)),
                      leg_r=dict(up=V(-0.08, -0.05, -1.0), lo=V(-0.05, 0.50, -0.86), foot=V(0, -0.2, -0.98)))
    return k


def keys_ledge_hang():
    """appeso alla sporgenza (prova): mani sopra la testa sul bordo, corpo appeso, gambe che oscillano piano
    avanti e indietro (ciclo). Il punto "grip" del JSON dice dove stanno le mani, per allinearle allo spigolo."""
    k = {}
    arms = dict(arm_l=dict(ik=(0.16, -0.10, 2.16), pole=(0.5, 0.4, 0.2)),
                arm_r=dict(ik=(-0.16, -0.10, 2.16), pole=(-0.5, 0.4, 0.2)))
    k["a"] = dict(hip=(0.0, 0.0, 1.06), pelvis=(-6, 0, 0), spine=(-4, 0, 0), neck=(-14, 0, 0),
                  leg_l=dict(up=V(0.06, -0.25, -0.97), lo=V(0.04, 0.15, -0.99), foot=V(0, -0.3, -0.95)),
                  leg_r=dict(up=V(-0.06, 0.05, -1.0), lo=V(-0.04, 0.35, -0.94), foot=V(0, -0.2, -0.98)), **arms)
    k["b"] = dict(hip=(0.0, 0.03, 1.06), pelvis=(6, 0, 0), spine=(2, 0, 0), neck=(-10, 0, 0),
                  leg_l=dict(up=V(0.06, 0.10, -0.99), lo=V(0.04, 0.35, -0.94), foot=V(0, -0.1, -0.99)),
                  leg_r=dict(up=V(-0.06, 0.20, -0.98), lo=V(-0.04, 0.45, -0.89), foot=V(0, 0.0, -1.0)), **arms)
    return k


def keys_wall_slide():
    """freno col braccio (stanza di prova): GIG guarda il muro, che ha davanti; il braccio cyber (il sinistro,
    lontano) è piantato nel muro all'altezza della testa, la gamba vicina puntata contro il muro, l'altra
    piegata. Due chiavi appena diverse: il braccio che vibra frenando."""
    k = {}
    k["a"] = guard(hip=(0.0, 0.05, 0.95), pelvis=(-6, 0, 10), spine=(8, 0, -6), neck=(-14, 0, 0),
                   arm_l=dict(ik=(0.12, -0.26, 1.60), pole=(0.6, 0.3, -0.3)),
                   arm_r=dict(up=V(-0.55, 0.15, -0.82), lo=V(-0.25, -0.55, 0.80)),
                   leg_l=dict(up=V(0.08, -0.62, -0.78), lo=V(0.05, 0.15, -0.99), foot=V(0, -0.6, -0.8)),
                   leg_r=dict(up=V(-0.08, -0.35, -0.94), lo=V(-0.05, -0.30, -0.95), foot=V(0, -0.95, -0.3)))
    k["b"] = guard(hip=(0.0, 0.05, 0.94), pelvis=(-5, 0, 10), spine=(9, 0, -6), neck=(-12, 0, 0),
                   arm_l=dict(ik=(0.12, -0.26, 1.58), pole=(0.6, 0.3, -0.3)),
                   arm_r=dict(up=V(-0.55, 0.20, -0.81), lo=V(-0.25, -0.50, 0.83)),
                   leg_l=dict(up=V(0.08, -0.58, -0.81), lo=V(0.05, 0.18, -0.98), foot=V(0, -0.6, -0.8)),
                   leg_r=dict(up=V(-0.08, -0.37, -0.93), lo=V(-0.05, -0.28, -0.96), foot=V(0, -0.95, -0.3)))
    return k


def keys_wall_run():
    """corsa sul muro (stanza di prova), rifatta dopo il giudizio di Luigi (5 novembre 2026): il muro è davanti
    e GIG ci sale sopra. Quattro chiavi per ciclo, due per passo:
      contatto: il piede di testa si pianta sulla parete all'altezza delle anche, con la suola piatta sul
                muro e il ginocchio piegato verso il muro; l'altra gamba ha appena spinto ed è distesa sotto;
      passaggio: la gamba che ha spinto risale piegata sotto il corpo, quella piantata spinge in giù.
    Il bacino sta indietro, lontano dal muro, e lo sguardo va in su; le braccia vanno a braccia e gambe
    opposte, e la mano che sale si allunga lungo la parete. Più la posa di fine corsa ("top"), quando GIG
    si stacca dal muro: le due gambe piegate contro la parete, il braccio cyber in alto."""
    k = {}
    plant = dict(up=V(0.0, -0.92, 0.25), lo=V(0.0, 0.05, -1.0), foot=V(0, -0.15, 0.99))
    trail = dict(up=V(0.0, -0.15, -0.99), lo=V(0.0, 0.35, -0.94), foot=V(0, -0.5, -0.87))
    swing_ = dict(up=V(0.0, -0.65, -0.76), lo=V(0.0, 0.55, -0.83), foot=V(0, 0.1, -0.99))
    press = dict(up=V(0.0, -0.70, -0.71), lo=V(0.0, -0.25, -0.97), foot=V(0, -0.35, 0.94))

    def L(d, x):
        return dict(up=V(x, *d["up"][1:]), lo=V(x * 0.6, *d["lo"][1:]), foot=d["foot"])

    reach = (-0.45, 0.86)
    def arm(x, kind):
        if kind == "reach":
            return dict(up=V(x, -0.45, 0.86), lo=V(x * 0.4, -0.50, 0.86))
        if kind == "back":
            return dict(up=V(x, 0.45, -0.84), lo=V(x * 0.5, -0.40, 0.90))
        return dict(up=V(x * 1.2, 0.05, -0.95), lo=V(x * 0.6, -0.70, 0.68))

    body = dict(hip=(0.0, 0.12, 0.90), pelvis=(-24, 0, 6), spine=(10, 0, -4), neck=(-26, 0, 0))
    k["ca"] = guard(**body, leg_l=L(plant, 0.08), leg_r=L(trail, -0.08), arm_l=arm(0.25, "back"), arm_r=arm(-0.25, "reach"))
    k["pa"] = guard(**dict(body, hip=(0.0, 0.12, 0.92)), leg_l=L(press, 0.08), leg_r=L(swing_, -0.08),
                    arm_l=arm(0.25, "mid"), arm_r=arm(-0.25, "mid"))
    k["cb"] = guard(**body, leg_l=L(trail, 0.08), leg_r=L(plant, -0.08), arm_l=arm(0.25, "reach"), arm_r=arm(-0.25, "back"))
    k["pb"] = guard(**dict(body, hip=(0.0, 0.12, 0.92)), leg_l=L(swing_, 0.08), leg_r=L(press, -0.08),
                    arm_l=arm(0.25, "mid"), arm_r=arm(-0.25, "mid"))
    k["top"] = guard(hip=(0.0, 0.14, 0.90), pelvis=(-30, 0, 6), spine=(12, 0, -4), neck=(-20, 0, 0),
                     leg_l=L(plant, 0.08), leg_r=L(press, -0.08),
                     arm_l=dict(up=V(0.25, -0.30, 0.92), lo=V(0.10, -0.35, 0.93)),
                     arm_r=dict(up=V(-0.50, 0.40, -0.77), lo=V(-0.30, -0.20, 0.93)))
    return k


def keys_air_dash():
    """scatto in aria (stanza di prova): il braccio cyber spara all'indietro e GIG schizza in avanti, il busto
    lanciato, le gambe raccolte dietro, il pugno destro avanti. Poi il corpo si rilassa appena."""
    k = {}
    k["kick"] = guard(hip=(0.0, 0.02, 0.94), pelvis=(18, 0, 8), spine=(30, 0, -6), neck=(-24, 0, 0),
                      arm_l=dict(up=V(0.15, 0.80, -0.58), lo=V(0.10, 0.90, -0.42)),
                      arm_r=dict(up=V(-0.30, -0.70, -0.65), lo=V(-0.10, -0.92, 0.38)),
                      leg_l=dict(up=V(0.10, 0.35, -0.93), lo=V(0.06, 0.92, -0.38)),
                      leg_r=dict(up=V(-0.08, 0.10, -0.99), lo=V(-0.05, 0.85, -0.52)))
    k["glide"] = guard(hip=(0.0, 0.02, 0.94), pelvis=(14, 0, 8), spine=(24, 0, -6), neck=(-18, 0, 0),
                       arm_l=dict(up=V(0.25, 0.70, -0.67), lo=V(0.15, 0.80, -0.58)),
                       arm_r=dict(up=V(-0.35, -0.60, -0.72), lo=V(-0.10, -0.85, 0.52)),
                       leg_l=dict(up=V(0.10, 0.20, -0.97), lo=V(0.06, 0.85, -0.52)),
                       leg_r=dict(up=V(-0.08, -0.10, -0.99), lo=V(-0.05, 0.75, -0.66)))
    return k


def keys_hack():
    """hacking (stanza di prova, «Collega e corri»): la cassetta del pannello è sul muro sopra la testa; GIG
    alza il braccio cyber (il sinistro) teso verso di lei, guarda in su, l'altro braccio resta raccolto al petto.
    Due chiavi appena diverse: il braccio che vibra mentre forza il pannello."""
    k = {}
    k["a"] = guard(hip=(0.0, 0.02, 0.89), pelvis=(-2, 0, 10), spine=(-5, 0, -10), neck=(-26, 0, 6),
                   arm_l=dict(ik=(0.18, -0.12, 2.02), pole=(0.6, 0.3, 0.2)),
                   arm_r=dict(up=V(-0.30, -0.20, -0.93), lo=V(0.10, -0.50, 0.86)))
    k["b"] = guard(hip=(0.0, 0.02, 0.885), pelvis=(-2, 0, 11), spine=(-4, 0, -12), neck=(-24, 0, 8),
                   arm_l=dict(ik=(0.20, -0.10, 1.99), pole=(0.6, 0.3, 0.2)),
                   arm_r=dict(up=V(-0.30, -0.22, -0.92), lo=V(0.10, -0.52, 0.85)))
    return k


# ============================================================== GIG col braccio morto (prima del riavvio)
# braccio morto appeso nella guardia (busto chino di 8°: nel riferimento del petto il "giù" del mondo è un poco
# in avanti)
DEAD_HANG = dict(up=V(0.12, -0.12, -0.99), lo=V(0.10, -0.25, -0.96))


def keys_ledge_hang_one():
    """appeso con la sola destra: la mano destra sopra la testa sullo spigolo, il busto che pende un poco verso
    sinistra (la spalla destra su, la sinistra giù), le gambe che oscillano piano. Il braccio sinistro lo muove
    la simulazione del braccio morto: qui c'è solo una posa di partenza lungo il fianco."""
    k = {}
    arm_r = dict(ik=(-0.06, -0.10, 2.16), pole=(-0.6, 0.4, 0.2))
    k["a"] = dict(hip=(0.0, 0.0, 1.05), pelvis=(-6, 5, 0), spine=(-4, 9, 0), neck=(-14, -6, 0),
                  leg_l=dict(up=V(0.06, -0.25, -0.97), lo=V(0.04, 0.15, -0.99), foot=V(0, -0.3, -0.95)),
                  leg_r=dict(up=V(-0.06, 0.05, -1.0), lo=V(-0.04, 0.35, -0.94), foot=V(0, -0.2, -0.98)),
                  arm_r=arm_r, arm_l=dict(DEAD_HANG))
    k["b"] = dict(hip=(0.0, 0.03, 1.05), pelvis=(6, 6, 0), spine=(2, 10, 0), neck=(-10, -6, 0),
                  leg_l=dict(up=V(0.06, 0.10, -0.99), lo=V(0.04, 0.35, -0.94), foot=V(0, -0.1, -0.99)),
                  leg_r=dict(up=V(-0.06, 0.20, -0.98), lo=V(-0.04, 0.45, -0.89), foot=V(0, 0.0, -1.0)),
                  arm_r=arm_r, arm_l=dict(DEAD_HANG))
    return k


def keys_mazza():
    """la mazza: col braccio morto come arma. La destra afferra il polso sinistro davanti alla pancia, solleva il
    braccio sopra la testa inarcando la schiena (carica lenta, il braccio pesa), lo abbatte in avanti con un
    affondo e lo lascia andare: da lì il braccio torna alla simulazione e ciondola, mentre la destra torna in
    guardia. Il colpo si legge di lato, nel piano dello schermo."""
    k = {}
    k["set"] = guard(arm_l=dict(DEAD_HANG))
    k["grab"] = guard(hip=(0.0, 0.02, 0.875), pelvis=(4, 0, 6), spine=(16, 0, -16), neck=(-6, 0, 10),
                      arm_l=dict(ik=(0.07, -0.26, 0.98), pole=(1.0, 0.4, -0.3)),
                      arm_r=dict(ik=(0.03, -0.30, 1.03), pole=(-1.0, 0.3, -0.5)))
    # le mani salgono insieme davanti alla faccia (le IK si interpolano in linea: restano unite)
    k["raise"] = guard(hip=(0.0, 0.03, 0.885), pelvis=(0, 0, 8), spine=(4, 0, -10), neck=(-8, 0, 4),
                       arm_l=dict(ik=(0.07, -0.32, 1.62), pole=(1.0, 0.2, -0.4)),
                       arm_r=dict(ik=(0.01, -0.34, 1.57), pole=(-1.0, 0.2, -0.5)))
    wide = dict(leg_l=dict(ik=(0.16, -0.27, 0.086), pole=(0.3, -1, 0)),
                leg_r=dict(ik=(-0.15, 0.29, 0.086), pole=(-0.15, -1, 0)))
    k["lift"] = guard(hip=(0.0, 0.07, 0.895), pelvis=(-6, 0, 8), spine=(-14, 0, -6), neck=(-12, 0, 0),
                      arm_l=dict(ik=(0.07, 0.15, 2.00), pole=(1.0, -0.5, 0.3)),
                      arm_r=dict(ik=(0.0, 0.11, 1.94), pole=(-1.0, -0.5, 0.3)), **wide)
    k["hold"] = guard(hip=(0.0, 0.09, 0.89), pelvis=(-8, 0, 8), spine=(-19, 0, -4), neck=(-14, 0, 0),
                      arm_l=dict(ik=(0.07, 0.22, 1.97), pole=(1.0, -0.5, 0.3)),
                      arm_r=dict(ik=(0.0, 0.18, 1.91), pole=(-1.0, -0.5, 0.3)), **wide)
    k["smash"] = guard(hip=(0.0, -0.07, 0.855), pelvis=(10, 0, 4), spine=(28, 0, -10), neck=(2, 0, 0),
                       arm_l=dict(ik=(0.10, -0.74, 1.30), pole=(0.6, 0.3, -0.7)),
                       arm_r=dict(ik=(0.05, -0.66, 1.27), pole=(-0.6, 0.3, -0.7)),
                       leg_l=dict(ik=(0.16, -0.36, 0.11), pole=(0.3, -1, 0)),
                       leg_r=dict(ik=(-0.15, 0.30, 0.086), pole=(-0.15, -1, 0)))
    k["follow"] = guard(hip=(0.0, -0.08, 0.845), pelvis=(12, 0, 4), spine=(36, 0, -10), neck=(8, 0, 0),
                        arm_l=dict(ik=(0.12, -0.62, 0.84), pole=(0.6, 0.3, -0.7)),
                        arm_r=dict(ik=(0.07, -0.56, 0.88), pole=(-0.6, 0.3, -0.7)),
                        leg_l=dict(ik=(0.16, -0.36, 0.11), pole=(0.3, -1, 0)),
                        leg_r=dict(ik=(-0.15, 0.30, 0.086), pole=(-0.15, -1, 0)))
    # la destra molla: il braccio morto cade di peso e va un poco indietro, il busto è ancora chino
    k["drop"] = guard(hip=(0.0, -0.07, 0.85), pelvis=(10, 0, 6), spine=(30, 0, -10), neck=(4, 0, 2),
                      arm_l=dict(up=V(0.12, -0.50, -0.86), lo=V(0.10, -0.62, -0.78)),
                      leg_l=dict(ik=(0.16, -0.36, 0.11), pole=(0.3, -1, 0)),
                      leg_r=dict(ik=(-0.15, 0.30, 0.086), pole=(-0.15, -1, 0)))
    k["recover"] = guard(hip=(0.0, -0.02, 0.875), pelvis=(4, 0, 10), spine=(14, 0, -12), neck=(-4, 0, 4),
                         arm_l=dict(DEAD_HANG))
    return k


class DeadArm:
    """braccio morto: gomito e polso sono particelle (Verlet a 60 Hz, con sotto-passi) appese alla spalla.
    Contano la gravità, il moto del corpo (anche quello del gioco, che il render sul posto non ha), l'aria e uno
    smorzamento forte; niente muscoli. Il gomito si piega solo in avanti, fra flex_min e flex_max; braccio e
    polso restano fuori dal busto (dal lato sinistro) e sopra il pavimento. Unità: metri e secondi."""

    def __init__(self, l1, l2, cfg):
        self.l1, self.l2 = l1, l2
        self.g = cfg.get("g", 14.0)
        self.damp = cfg.get("damp", 0.012)
        self.drag = cfg.get("drag", 1.2)
        self.sub = int(cfg.get("substeps", 4))
        # attrito nella spalla e nel gomito (per sotto-passo): la velocità del braccio va verso quella della spalla,
        # così un busto che ruota di scatto (il diretto) trascina il braccio invece di frustarlo. 0 = pendolo libero
        self.follow = cfg.get("follow", 0.0)
        self.flex_min = math.radians(cfg.get("flex_min_deg", 8.0))
        self.flex_max = math.radians(cfg.get("flex_max_deg", 125.0))
        self.twist = math.radians(cfg.get("twist_deg", 20.0))
        self.out = math.sin(math.radians(cfg.get("out_deg", 6.0)))
        self.out_max = math.sin(math.radians(cfg.get("out_max_deg", 25.0)))
        # cono attorno al "giù" del mondo: un braccio morto non sale oltre swing_max_deg (l'avambraccio un poco di
        # più), se no si legge come un braccio che si muove da solo. null = senza limite.
        sm = cfg.get("swing_max_deg", 65.0)
        self.cone = None if sm is None else math.cos(math.radians(sm))
        self.cone_f = None if sm is None else math.cos(math.radians(min(sm + 25.0, 180.0)))
        self.floor_r = cfg.get("floor_r", 0.04)
        m1, m2 = cfg.get("mass", (1.0, 1.5))
        self.wE = m2 / (m1 + m2)
        self.A = None
        self.E = self.Ep = self.W = self.Wp = None

    def place(self, A, X, swing_deg=0.0, vel=(0.0, 0.0, 0.0)):
        """braccio appeso fermo (o alzato in avanti di swing_deg), che si muove con il corpo a vel (m/s)."""
        down, fwd = Vector((0.0, 0.0, -1.0)), X.cross(Vector((0.0, 0.0, 1.0))).normalized()
        a = math.radians(swing_deg)
        u = (down * math.cos(a) + fwd * math.sin(a) + X * self.out).normalized()
        h = (X - u * X.dot(u)).normalized()
        q = u.cross(h)
        f = u * math.cos(self.flex_min * 1.5) + q * math.sin(self.flex_min * 1.5)
        self.A = A.copy()
        self.E = A + u * self.l1
        self.W = self.E + f * self.l2
        dv = Vector(vel) / (60.0 * self.sub)
        self.Ep, self.Wp = self.E - dv, self.W - dv

    def drive(self, A, E, W):
        """braccio mosso dalla posa (tenuto dalla mano destra): le particelle seguono, con la loro velocità."""
        if self.E is None:
            self.Ep, self.Wp = E.copy(), W.copy()
        else:
            # velocità per sotto-passo, come nello step
            self.Ep = E - (E - self.E) / self.sub
            self.Wp = W - (W - self.W) / self.sub
        self.A, self.E, self.W = A.copy(), E.copy(), W.copy()

    def state(self, X, U):
        """posizione e velocità (per sotto-passo) di gomito e polso nel riferimento del petto, per ripartire
        da qui in un'altra animazione."""
        F = X.cross(U)

        def loc(v):
            return (v.dot(X), v.dot(F), v.dot(U))
        return dict(E=loc(self.E - self.A), W=loc(self.W - self.A), vE=loc(self.E - self.Ep), vW=loc(self.W - self.Wp))

    def restore(self, st, A, X, U):
        F = X.cross(U)

        def glob(t):
            return X * t[0] + F * t[1] + U * t[2]
        self.A = A.copy()
        self.E, self.W = A + glob(st["E"]), A + glob(st["W"])
        self.Ep, self.Wp = self.E - glob(st["vE"]), self.W - glob(st["vW"])

    def release(self, a, X, floor_z, k):
        """la destra lo lascia: il braccio ha appena colpito e tiene solo una parte (k) della sua velocità. La posa
        tenuta può stare fuori dai limiti (le mani unite davanti al corpo): si riporta dentro, e il salto della
        correzione non diventa velocità."""
        vE, vW = (self.E - self.Ep) * k, (self.W - self.Wp) * k
        for _ in range(4):
            self._constrain(a, X, floor_z)
        self.Ep, self.Wp = self.E - vE, self.W - vW

    def step(self, A, X, floor_z, wall_y=None):
        A0 = self.A if self.A is not None else A
        dt = 1.0 / (60.0 * self.sub)
        gv = Vector((0.0, 0.0, -self.g))
        va = (A - A0) / self.sub
        for s in range(self.sub):
            a = A0.lerp(A, (s + 1) / self.sub)
            for nm in ("E", "W"):
                P, Pp = getattr(self, nm), getattr(self, nm + "p")
                v = (P - Pp) * (1.0 - self.damp)
                v = v + (va - v) * self.follow
                acc = gv - (v / dt) * self.drag
                setattr(self, nm + "p", P)
                setattr(self, nm, P + v + acc * dt * dt)
            for _ in range(3):
                self._constrain(a, X, floor_z, wall_y)
        self.A = A.copy()

    def _constrain(self, a, X, floor_z, wall_y=None):
        d = self.E - a
        self.E = a + (d.normalized() if d.length > 1e-6 else Vector((0, 0, -1))) * self.l1
        d = self.W - self.E
        L = max(d.length, 1e-6)
        corr = d * ((L - self.l2) / L)
        self.E = self.E + corr * self.wE
        self.W = self.W - corr * (1.0 - self.wE)
        d = self.E - a
        u = d.normalized() if d.length > 1e-6 else Vector((0, 0, -1))
        # fuori dal busto: il braccio non passa al lato interno della spalla, e non si apre troppo di lato
        # (di lato non si vedrebbe: nello sprite sembrerebbe solo accorciato)
        lat = u.dot(X)
        if lat < self.out:
            u = (u + X * (self.out - lat)).normalized()
        elif lat > self.out_max:
            u = (u - X * (lat - self.out_max)).normalized()
        u = self._cone(u, self.cone)
        self.E = a + u * self.l1
        # gomito a cerniera: si piega solo in avanti
        h = X - u * X.dot(u)
        if h.length < 1e-6:
            h = Vector((0.0, -1.0, 0.0))
        h.normalize()
        q = u.cross(h)
        f = self.W - self.E
        f = f.normalized() if f.length > 1e-6 else u.copy()
        th = math.atan2(f.dot(q), f.dot(u))
        ph = math.asin(max(-1.0, min(1.0, f.dot(h))))
        th = min(max(th, self.flex_min), self.flex_max)
        ph = min(max(ph, -self.twist), self.twist)
        f = (u * math.cos(th) + q * math.sin(th)) * math.cos(ph) + h * math.sin(ph)
        f = self._cone(f, self.cone_f)
        W = self.E + f * self.l2
        w = W - a
        lat = w.dot(X)
        if lat < self.out * w.length:
            W = W + X * (self.out * w.length - lat)
        self.W = W
        for nm in ("E", "W"):
            P = getattr(self, nm)
            if P.z < floor_z + self.floor_r:
                P = Vector((P.x, P.y, floor_z + self.floor_r))
            # il muro davanti (appeso alla sporgenza): il personaggio guarda -Y, il muro sta a wall_y
            if wall_y is not None and P.y < wall_y:
                P = Vector((P.x, wall_y, P.z))
            setattr(self, nm, P)

    @staticmethod
    def _cone(d, c):
        """d dentro il cono di coseno c attorno al giù del mondo (la direzione orizzontale resta quella)."""
        if c is None or -d.z >= c:
            return d
        hz = Vector((d.x, d.y, 0.0))
        if hz.length < 1e-6:
            hz = Vector((0.0, -1.0, 0.0))
        hz.normalize()
        return hz * math.sqrt(max(0.0, 1.0 - c * c)) + Vector((0.0, 0.0, -c))

    def dirs(self):
        """direzioni (mondo) di braccio e avambraccio, e il "davanti" del gomito per il polso."""
        u = (self.E - self.A).normalized()
        f = (self.W - self.E).normalized()
        return u, f


# ============================================================== l'esattore (corpo del bruto, rivolto a destra)
def _st(**kw):
    return CP.stance(**kw)


def keys_esa_block():
    """guardia dell'esattore: avambracci alzati a scudo davanti alla faccia, mento giù, spalle chiuse, ginocchia
    piegate. "hit" è la stessa guardia spinta indietro dal pugno parato; "up" la guardia ferma."""
    k = {}
    arms = dict(arm_l=dict(ik=(0.04, -0.34, 1.38), pole=(0.6, -0.3, -1.0)),
                arm_r=dict(ik=(-0.04, -0.30, 1.32), pole=(-0.6, -0.3, -1.0)))
    k["up"] = _st(hip=(0.0, 0.04, 0.86), pelvis=(2, 0, 8), spine=(16, 0, -8), neck=(10, 0, 0), **arms)
    k["hit"] = _st(hip=(0.0, 0.09, 0.86), pelvis=(-4, 0, 10), spine=(4, 0, -6), neck=(0, 0, 4),
                   arm_l=dict(ik=(0.04, -0.26, 1.42), pole=(0.6, -0.3, -1.0)),
                   arm_r=dict(ik=(-0.04, -0.22, 1.36), pole=(-0.6, -0.3, -1.0)),
                   leg_l=dict(ik=(0.12, -0.15, 0.10), pole=(0.25, -1, 0)))
    return k


def keys_esa_charge_wind():
    """preparazione della spallata: si abbassa sulle gambe larghe, avvita il busto con la spalla sinistra avanti,
    l'avambraccio sinistro chiuso davanti al petto, il pugno destro tirato indietro, la testa bassa che guarda
    avanti. "set" è la discesa, "coil" la tenuta tesa, "coil2" il fremito."""
    k = {}
    legs = dict(leg_l=dict(ik=(0.14, -0.34, 0.086), pole=(0.25, -1, 0)),
                leg_r=dict(ik=(-0.13, 0.34, 0.086), pole=(-0.1, -1, 0)))
    k["set"] = _st(hip=(0.0, 0.04, 0.82), pelvis=(8, 0, 0), spine=(18, 0, -20), neck=(-12, 0, 10),
                   arm_l=dict(up=V(0.30, -0.30, -0.90), lo=V(-0.50, -0.55, 0.67)),
                   arm_r=dict(up=V(-0.35, 0.40, -0.85), lo=V(-0.05, -0.30, 0.95)), **legs)
    k["coil"] = _st(hip=(0.0, 0.07, 0.78), pelvis=(14, 0, -4), spine=(28, 0, -34), neck=(-26, 0, 18),
                    arm_l=dict(up=V(0.30, -0.45, -0.84), lo=V(-0.55, -0.60, 0.58)),
                    arm_r=dict(up=V(-0.40, 0.60, -0.70), lo=V(-0.10, -0.10, 0.99)), **legs)
    k["coil2"] = _st(hip=(0.0, 0.07, 0.775), pelvis=(15, 0, -5), spine=(29, 0, -36), neck=(-27, 0, 19),
                     arm_l=dict(up=V(0.30, -0.46, -0.84), lo=V(-0.56, -0.60, 0.57)),
                     arm_r=dict(up=V(-0.40, 0.62, -0.68), lo=V(-0.10, -0.12, 0.99)), **legs)
    return k


def keys_esa_charge_run():
    """corsa della spallata: piegato in avanti, la spalla sinistra davanti a fare da ariete con l'avambraccio
    chiuso, il braccio destro che pompa. Quattro chiavi per ciclo, due per passo (contatto e passaggio)."""
    k = {}
    reach = dict(up=V(0.0, -0.62, -0.78), lo=V(0.0, -0.20, -0.98), foot=V(0, -0.5, -0.87))
    push = dict(up=V(0.0, 0.55, -0.84), lo=V(0.0, 0.85, -0.53), foot=V(0, 0.6, -0.80))
    knee = dict(up=V(0.0, -0.80, -0.60), lo=V(0.0, 0.30, -0.95), foot=V(0, -0.2, -0.98))
    stand = dict(up=V(0.0, 0.15, -0.99), lo=V(0.0, 0.30, -0.95), foot=V(0, 0.1, -0.99))

    def L(d, x):
        return dict(up=V(x, *d["up"][1:]), lo=V(x * 0.6, *d["lo"][1:]), foot=d["foot"])

    ram = dict(up=V(0.30, -0.40, -0.87), lo=V(-0.55, -0.55, 0.63))
    body = dict(pelvis=(24, 0, -2), spine=(36, 0, -32), neck=(-40, 0, 16))
    k["ca"] = _st(hip=(0.0, 0.0, 0.84), **body, leg_l=L(reach, 0.10), leg_r=L(push, -0.10), arm_l=ram,
                  arm_r=dict(up=V(-0.35, -0.55, -0.76), lo=V(-0.10, -0.65, 0.75)))
    k["pa"] = _st(hip=(0.0, 0.0, 0.88), **body, leg_l=L(stand, 0.10), leg_r=L(knee, -0.10), arm_l=ram,
                  arm_r=dict(up=V(-0.35, 0.05, -0.94), lo=V(-0.10, -0.55, 0.83)))
    k["cb"] = _st(hip=(0.0, 0.0, 0.84), **body, leg_l=L(push, 0.10), leg_r=L(reach, -0.10), arm_l=ram,
                  arm_r=dict(up=V(-0.35, 0.60, -0.72), lo=V(-0.10, -0.20, 0.97)))
    k["pb"] = _st(hip=(0.0, 0.0, 0.88), **body, leg_l=L(knee, 0.10), leg_r=L(stand, -0.10), arm_l=ram,
                  arm_r=dict(up=V(-0.35, 0.05, -0.94), lo=V(-0.10, -0.55, 0.83)))
    return k


def keys_esa_dizzy():
    """stordito dopo la carica a vuoto: ginocchia molli, braccia che pendono, il corpo che ondeggia avanti e
    indietro e la testa che ciondola in ritardo sul busto."""
    k = {}
    legs = dict(leg_l=dict(ik=(0.13, -0.14, 0.086), pole=(0.25, -1, 0)),
                leg_r=dict(ik=(-0.12, 0.18, 0.086), pole=(-0.1, -1, 0)))
    hang_l = dict(up=V(0.25, -0.05, -0.97), lo=V(0.15, -0.20, -0.97))
    hang_r = dict(up=V(-0.25, 0.05, -0.97), lo=V(-0.15, -0.15, -0.98))
    k["back"] = _st(hip=(0.0, 0.07, 0.85), pelvis=(-6, 0, 12), spine=(-10, 0, -6), neck=(-24, 0, 14),
                    arm_l=dict(up=V(0.30, 0.10, -0.95), lo=V(0.20, -0.05, -0.98)),
                    arm_r=dict(up=V(-0.30, 0.20, -0.93), lo=V(-0.20, 0.05, -0.98)), **legs)
    k["mid"] = _st(hip=(0.0, 0.03, 0.83), pelvis=(2, 0, 10), spine=(8, 0, -10), neck=(-4, 0, -8),
                   arm_l=hang_l, arm_r=hang_r, **legs)
    k["fwd"] = _st(hip=(0.0, -0.01, 0.84), pelvis=(8, 0, 8), spine=(22, 0, -14), neck=(26, 0, -14),
                   arm_l=dict(up=V(0.20, -0.20, -0.96), lo=V(0.10, -0.40, -0.91)),
                   arm_r=dict(up=V(-0.20, -0.10, -0.97), lo=V(-0.10, -0.35, -0.93)), **legs)
    return k


# ============================================================== Esattori (char_enemies): rider e messo
def keys_rider_pignora():
    """pignoramento del rider: afferra con le due mani il braccio di GIG davanti a sé, all'altezza del petto, e tira
    indietro col peso del corpo, i piedi puntati. "a" e "b" sono lo strattone."""
    legs = dict(leg_l=dict(ik=(0.12, -0.30, 0.086), pole=(0.25, -1, 0)),
                leg_r=dict(ik=(-0.12, 0.16, 0.086), pole=(-0.1, -1, 0)))
    k = {}
    k["a"] = _st(hip=(0.0, 0.05, 0.88), pelvis=(-6, 0, 6), spine=(-2, 0, -6), neck=(8, 0, 0),
                 arm_l=dict(ik=(0.05, -0.47, 1.18), pole=(0.6, 0.2, -1.0)),
                 arm_r=dict(ik=(-0.05, -0.42, 1.12), pole=(-0.6, 0.2, -1.0)), **legs)
    k["b"] = _st(hip=(0.0, 0.09, 0.87), pelvis=(-12, 0, 6), spine=(-8, 0, -6), neck=(14, 0, 0),
                 arm_l=dict(ik=(0.05, -0.41, 1.16), pole=(0.6, 0.2, -1.0)),
                 arm_r=dict(ik=(-0.05, -0.36, 1.10), pole=(-0.6, 0.2, -1.0)), **legs)
    return k


MESSO_LEGS = dict(leg_l=dict(ik=(0.10, -0.05, 0.086), pole=(0.2, -1, 0)),
                  leg_r=dict(ik=(-0.10, 0.07, 0.086), pole=(-0.2, -1, 0)))
# il tablet stretto al petto nella sinistra (l'oggetto si scrive su questa posa: vedi char_enemies.make_tablet)
MESSO_TABLET = dict(up=V(0.32, -0.22, -0.92), lo=V(-0.66, -0.44, 0.61), hand=V(-0.40, -0.22, 0.89))
MESSO_PEN_DOWN = dict(up=V(-0.16, 0.06, -0.98), lo=V(-0.08, -0.34, -0.94))


def _messo(**kw):
    d = dict(hip=(0.0, 0.0, 0.95), pelvis=(-4, 0, -6), spine=(-6, 0, -2), neck=(-10, 0, 0),
             arm_l=dict(MESSO_TABLET), arm_r=dict(MESSO_PEN_DOWN), **MESSO_LEGS)
    d.update(kw)
    return _st(**d)


def keys_messo_idle():
    """il messo fermo (decisione 63: non picchia, sta dietro ai suoi): dritto e impettito, la pancia in fuori e il
    mento alto, il tablet stretto al petto nella sinistra, la penna laser nella destra lungo il fianco. "base" e
    "breath" (il respiro corto di chi non si muove)."""
    return dict(base=_messo(), breath=_messo(hip=(0.0, 0.0, 0.953), spine=(-9, 0, -2), neck=(-12, 0, 0)))


def keys_messo_read():
    """legge l'atto: alza il tablet davanti al petto e china la testa a leggere; la destra con la penna resta giù.
    "a" e "b": la testa che segue le righe."""
    arm_l = dict(up=V(0.22, -0.62, -0.75), lo=V(-0.50, -0.62, 0.60), hand=V(-0.30, -0.45, 0.84))
    return dict(a=_messo(neck=(14, 0, 0), spine=(-2, 0, -2), arm_l=arm_l),
                b=_messo(neck=(9, 0, 3), spine=(-4, 0, -2), arm_l=dict(arm_l)))


def keys_messo_laser():
    """segna il braccio col laser: il tablet resta al petto, il braccio destro si tende in avanti all'altezza della
    spalla e la penna prosegue l'avambraccio, appena verso il basso (il braccio di GIG). "aim" alza, "point" tende."""
    return dict(aim=_messo(spine=(-4, 0, 8), neck=(-4, 0, -6),
                           arm_r=dict(up=V(-0.30, -0.80, -0.52), lo=V(-0.14, -0.94, -0.30))),
                point=_messo(spine=(-2, 0, 18), neck=(-2, 0, -14),
                             arm_r=dict(up=V(-0.22, -0.97, 0.02), lo=V(-0.10, -0.98, -0.14),
                                        hand=V(-0.10, -0.98, -0.14))))


def keys_messo_call():
    """chiama i rinforzi: alza il braccio destro con la penna accesa sopra la testa, il mento in alto (gridato); il
    tablet resta al petto. "up_a" e "up_b": il braccio che sventola."""
    return dict(up_a=_messo(neck=(-18, 0, 0), spine=(-8, 0, -2),
                            arm_r=dict(up=V(-0.38, -0.14, 0.91), lo=V(-0.12, -0.22, 0.97))),
                up_b=_messo(neck=(-16, 0, 3), spine=(-9, 0, -2),
                            arm_r=dict(up=V(-0.42, -0.02, 0.91), lo=V(-0.30, 0.10, 0.95))))


# ============================================================== i perdoni del Carmine (processione del Giovedì santo)
# Il bordone nella destra (il braccio vicino alla telecamera), dritto: si scrive sulla posa ferma (perdono_fermo/base,
# vedi char_enemies.make_bordone). La sinistra pende lungo il fianco. Testa china sotto il cappuccio.
PERDONO_BORDONE = dict(up=V(-0.12, -0.38, -0.92), lo=V(-0.08, -0.88, 0.46), hand_world=V(0.0, -1.0, 0.0))
PERDONO_GIU = dict(up=V(0.12, -0.04, -0.99), lo=V(0.06, -0.28, -0.96))
PERDONO_LEGS = dict(leg_l=dict(ik=(0.10, -0.02, 0.086), pole=(0.2, -1, 0)),
                    leg_r=dict(ik=(-0.10, 0.03, 0.086), pole=(-0.2, -1, 0)))
PERDONO_STRIDE = 0.427     # passo doppio (un ciclo, due passi) a 0,2 m/s in 128 tick: i 12 px/s della Processione
PERDONO_DUTY = 0.625       # piede a terra per 80 tick su 128, in volo per 48: il passo lento, mai di corsa


def _perdono(**kw):
    d = dict(hip=(0.0, 0.0, 0.94), pelvis=(0, 0, 0), spine=(4, 0, 0), neck=(12, 0, 0),
             arm_l=dict(PERDONO_GIU), arm_r=dict(PERDONO_BORDONE), **PERDONO_LEGS)
    d.update(kw)
    return _st(**d)


def keys_perdono_fermo():
    """il perdono fermo in fila: dritto, la testa china, il bordone dritto nella destra. "base" e "breath"."""
    return dict(base=_perdono(), breath=_perdono(hip=(0.0, 0.0, 0.943), spine=(2, 0, 0), neck=(10, 0, 0)))


def _foot(p, x, lift):
    """piede nel ciclo della nazzicata (p in [0, 1)): a terra scivola indietro a velocità costante, in volo torna
    avanti appena alzato (piedi scalzi: il passo è basso, quasi strisciato)."""
    s = PERDONO_STRIDE * PERDONO_DUTY
    if p < PERDONO_DUTY:
        u = p / PERDONO_DUTY
        return dict(ik=(x, -s / 2 + s * u, 0.086), pole=(0.2 if x > 0 else -0.2, -1, 0))
    u = (p - PERDONO_DUTY) / (1 - PERDONO_DUTY)
    return dict(ik=(x, s / 2 - s * u, 0.086 + lift * math.sin(math.pi * u)), pole=(0.2 if x > 0 else -0.2, -1, 0))


def keys_perdono_nazzica():
    """la nazzicata: il passo lento della processione, che dondola da un piede all'altro. Il peso va sul piede a terra
    (anca di lato e bacino che si inclina), le spalle rispondono al contrario e il cappuccio segue il busto. Otto
    chiavi ogni 16 tick sul ciclo di 128 (due passi); il piede sinistro tocca terra a 0, il destro a 64."""
    k = {}
    for i in range(8):
        p = i / 8
        w = math.sin(2 * math.pi * (p - 0.06))            # +1 peso sul sinistro, -1 sul destro
        bob = -math.cos(4 * math.pi * (p - 0.06))         # su a metà appoggio, giù quando i piedi si scambiano
        k["n%d" % i] = _perdono(hip=(0.030 * w, 0.0, 0.94 + 0.006 * bob), pelvis=(0, -5 * w, 3 * w),
                                spine=(4 + 1.0 * bob, 7 * w, -4 * w), neck=(12, -3 * w, 0),
                                arm_l=dict(up=V(0.12, -0.04 + 0.05 * w, -0.99), lo=V(0.06, -0.28 + 0.06 * w, -0.96)),
                                leg_l=_foot(p, 0.10, 0.045), leg_r=_foot((p + 0.5) % 1.0, -0.10, 0.045))
    return k


def keys_perdono_barcollo():
    """lo spintone: GIG passa di corsa e il confratello di coda, preso da dietro, pende in avanti; il destro fa un
    passo per non cadere, la sinistra si apre a cercare l'equilibrio, il bordone si inclina. Poi si riprende e torna
    in fila (45 tick, come l'apertura della Processione)."""
    k = {}
    k["hit"] = _perdono(hip=(0.0, -0.05, 0.93), pelvis=(10, 0, 0), spine=(16, 0, 0), neck=(-14, 0, 0),
                        arm_l=dict(up=V(0.55, 0.30, -0.78), lo=V(0.60, 0.10, -0.79)),
                        arm_r=dict(PERDONO_BORDONE, hand_world=V(0.0, -1.0, 0.0)),
                        leg_l=dict(ik=(0.10, -0.02, 0.086), pole=(0.2, -1, 0)),
                        leg_r=dict(ik=(-0.10, 0.10, 0.12), pole=(-0.2, -1, 0)))
    k["lurch"] = _perdono(hip=(0.0, -0.13, 0.88), pelvis=(16, 0, -4), spine=(26, 0, -4), neck=(-8, 0, 0),
                          arm_l=dict(up=V(0.75, -0.25, -0.61), lo=V(0.80, -0.40, -0.45)),
                          arm_r=dict(up=V(-0.30, -0.55, -0.78), lo=V(-0.10, -0.66, 0.74), hand_world=V(0.0, -1.0, 0.0)),
                          leg_l=dict(ik=(0.10, 0.02, 0.086), pole=(0.2, -1, 0)),
                          leg_r=dict(ik=(-0.11, -0.22, 0.086), pole=(-0.2, -1, 0)))
    k["catch"] = _perdono(hip=(0.0, -0.10, 0.90), pelvis=(6, 0, -2), spine=(8, 0, -2), neck=(6, 0, 0),
                          arm_l=dict(up=V(0.45, -0.10, -0.89), lo=V(0.40, -0.35, -0.85)),
                          leg_l=dict(ik=(0.10, 0.02, 0.086), pole=(0.2, -1, 0)),
                          leg_r=dict(ik=(-0.11, -0.20, 0.086), pole=(-0.2, -1, 0)))
    k["settle"] = _perdono(hip=(0.0, -0.06, 0.93), pelvis=(0, 0, 0), spine=(2, 0, 0), neck=(14, 0, 0),
                           leg_l=dict(ik=(0.10, -0.02, 0.086), pole=(0.2, -1, 0)),
                           leg_r=dict(ik=(-0.10, -0.12, 0.10), pole=(-0.2, -1, 0)))
    k["base"] = _perdono()
    return k


def keys_perdono_scansa():
    """la fila che si apre: il confratello si tira indietro col busto e fa un passo dietro per lasciar passare,
    il bordone stretto al corpo e la sinistra al petto; resta fermo finché GIG è passato, poi torna in fila."""
    back = _perdono(hip=(0.0, 0.07, 0.93), pelvis=(-8, 0, 0), spine=(-12, 0, 0), neck=(-2, 0, 0),
                    arm_l=dict(up=V(0.25, -0.15, -0.95), lo=V(-0.75, -0.45, 0.48)),
                    arm_r=dict(up=V(-0.10, -0.05, -0.99), lo=V(-0.05, -0.75, 0.66), hand_world=V(0.0, -1.0, 0.0)),
                    leg_l=dict(ik=(0.10, 0.02, 0.086), pole=(0.2, -1, 0)),
                    leg_r=dict(ik=(-0.11, 0.24, 0.086), pole=(-0.2, -1, 0)))
    hold = _perdono(hip=(0.0, 0.08, 0.935), pelvis=(-6, 0, 0), spine=(-9, 0, 0), neck=(4, 0, 0),
                    arm_l=dict(back["arm_l"]), arm_r=dict(back["arm_r"]),
                    leg_l=dict(back["leg_l"]), leg_r=dict(back["leg_r"]))
    return dict(base=_perdono(), back=back, hold=hold)


# ============================================================== le due persone del prologo che chiedono aiuto a GIG
# La signora del cimitero (A4): curva, la borsa appesa all'avambraccio sinistro, che resta in avanti e orizzontale in
# tutte le pose (la borsa si scrive su signora_ferma/base, vedi char_enemies.make_borsa); nella sinistra il lumino,
# nella destra il mazzo di crisantemi stretto al petto. Dopo (signora_dopo) ha le mani vuote.
SIG_HIP = 0.81
SIG_BORSA = dict(up=V(0.10, -0.14, -0.985), lo=V(-0.20, -0.975, 0.10))
SIG_FIORI = dict(up=V(-0.06, -0.30, -0.95), lo=V(0.22, -0.66, 0.72), hand_world=V(0.0, -1.0, 0.0))
SIG_PETTO = dict(up=V(-0.04, -0.22, -0.97), lo=V(0.42, -0.50, 0.76))
SIG_LEGS = dict(leg_l=dict(ik=(0.08, -0.03, 0.086), pole=(0.2, -1, 0)),
                leg_r=dict(ik=(-0.08, 0.04, 0.086), pole=(-0.2, -1, 0)))


def _signora(**kw):
    d = dict(hip=(0.0, 0.03, SIG_HIP), pelvis=(6, 0, 0), spine=(22, 0, 0), neck=(-10, 0, 0),
             arm_l=dict(SIG_BORSA), arm_r=dict(SIG_FIORI), **SIG_LEGS)
    d.update(kw)
    return _st(**d)


def keys_signora_ferma():
    """la signora ferma davanti alla lapide (A4): curva, il mento avanti, i fiori al petto. "base" e "breath"."""
    return dict(base=_signora(), breath=_signora(hip=(0.0, 0.03, SIG_HIP + 0.004), spine=(20, 0, 0), neck=(-11, 0, 0)))


def keys_signora_porge():
    """porge a GIG fiori e lumino: si sporge, le due braccia in avanti all'altezza del petto. "reach" è lo slancio,
    "hold" la tenuta."""
    arms = dict(arm_r=dict(up=V(-0.14, -0.84, -0.52), lo=V(-0.04, -0.99, 0.10), hand_world=V(0.0, -1.0, 0.0)),
                arm_l=dict(up=V(0.10, -0.80, -0.59), lo=V(-0.10, -0.99, 0.06)))
    return dict(base=_signora(),
                reach=_signora(hip=(0.0, -0.01, SIG_HIP - 0.006), spine=(22, 0, 0), neck=(-8, 0, 0), **arms),
                hold=_signora(hip=(0.0, 0.0, SIG_HIP - 0.003), spine=(19, 0, 0), neck=(-6, 0, 0), **arms))


def keys_signora_guarda_su():
    """dopo: guarda su verso la quinta fila, dove GIG è salito, con la destra al petto (mani vuote). "a" e "b": la
    testa che cerca."""
    return dict(a=_signora(spine=(6, 0, 0), neck=(-30, 0, 0), arm_r=dict(SIG_PETTO)),
                b=_signora(spine=(5, 0, 2), neck=(-34, 0, -4), arm_r=dict(SIG_PETTO)))


def keys_signora_taralli():
    """dopo, i taralli: la destra fruga nella borsa e poi porge in avanti (il premio lo mostra il gioco)."""
    give = dict(up=V(-0.14, -0.84, -0.52), lo=V(-0.04, -0.99, 0.12))
    return dict(base=_signora(arm_r=dict(SIG_PETTO)),
                dig=_signora(spine=(20, 0, 6), neck=(10, 0, 4),
                             arm_r=dict(ik=(0.06, -0.26, 0.86), pole=(-0.6, -0.4, -1.0))),
                dig2=_signora(spine=(21, 0, 7), neck=(12, 0, 4),
                              arm_r=dict(ik=(0.08, -0.25, 0.84), pole=(-0.6, -0.4, -1.0))),
                give=_signora(spine=(16, 0, 0), neck=(-6, 0, 0), arm_r=dict(give)))


# Il fruttivendolo dei Tamburi (B2): robusto, sotto la pioggia, accanto alla bici col sigillo PIGNORATO.
FR_HIP = 0.925
FR_GIU_L = dict(up=V(0.14, -0.02, -0.99), lo=V(0.08, -0.24, -0.97))
FR_GIU_R = dict(up=V(-0.14, -0.02, -0.99), lo=V(-0.08, -0.24, -0.97))
FR_LEGS = dict(leg_l=dict(ik=(0.12, -0.04, 0.086), pole=(0.25, -1, 0)),
               leg_r=dict(ik=(-0.12, 0.06, 0.086), pole=(-0.25, -1, 0)))


def _frutt(**kw):
    d = dict(hip=(0.0, 0.0, FR_HIP), pelvis=(0, 0, 0), spine=(2, 0, 0), neck=(0, 0, 0),
             arm_l=dict(FR_GIU_L), arm_r=dict(FR_GIU_R), **FR_LEGS)
    d.update(kw)
    return _st(**d)


def keys_frutt_ansia():
    """fermo in ansia accanto alla bici sigillata: la destra si gratta la nuca, la sinistra sul fianco, il peso che
    passa da un piede all'altro. "a" sul sinistro, "b" sul destro."""
    fianco = dict(ik=(0.20, -0.02, 1.00), pole=(1.0, 0.4, 0.0))
    return dict(a=_frutt(hip=(0.025, 0.0, FR_HIP - 0.004), pelvis=(0, -4, 2), spine=(6, 4, -2), neck=(10, 0, 6),
                         arm_r=dict(ik=(-0.05, 0.07, 1.56), pole=(-1.0, -0.4, 0.2)), arm_l=dict(fianco)),
                b=_frutt(hip=(-0.025, 0.0, FR_HIP - 0.004), pelvis=(0, 4, -2), spine=(6, -4, 2), neck=(8, 0, -6),
                         arm_r=dict(ik=(-0.06, 0.05, 1.58), pole=(-1.0, -0.4, 0.2)), arm_l=dict(fianco)))


def keys_frutt_sollievo():
    """il sollievo del grazie, che si legga di profilo: "open" le braccia su sopra la testa e la testa indietro (il
    peso che se ne va), "bob" giù di un poco, le mani giunte davanti al petto e un mezzo inchino verso GIG (grazie,
    compà). Le braccia aperte di lato, di profilo, sembravano uno slancio in avanti."""
    up = dict(arm_l=dict(up=V(0.30, -0.18, 0.94), lo=V(0.16, -0.24, 0.96)),
              arm_r=dict(up=V(-0.30, -0.18, 0.94), lo=V(-0.16, -0.24, 0.96)))
    giunte = dict(arm_l=dict(ik=(0.035, -0.30, 1.22), pole=(1.0, 0.2, -0.6)),
                  arm_r=dict(ik=(-0.035, -0.30, 1.22), pole=(-1.0, 0.2, -0.6)))
    return dict(still=_frutt(),
                open=_frutt(hip=(0.0, 0.01, FR_HIP + 0.01), spine=(-8, 0, 0), neck=(-18, 0, 0), **up),
                bob=_frutt(hip=(0.0, -0.005, FR_HIP - 0.025), spine=(10, 0, 0), neck=(8, 0, 0), **giunte))


def keys_frutt_botola():
    """si china, afferra la maniglia della botola della cantina e la alza: "chin" giù con le mani a terra davanti,
    "alza" a metà, "su" in piedi con le braccia alte che tengono l'anta."""
    legs = dict(leg_l=dict(ik=(0.15, -0.06, 0.086), pole=(0.35, -1, 0)),
                leg_r=dict(ik=(-0.15, 0.12, 0.086), pole=(-0.35, -1, 0)))
    pl, pr = (0.6, 0.2, -1.0), (-0.6, 0.2, -1.0)
    return dict(still=_frutt(),
                chin=_frutt(hip=(0.0, 0.08, 0.54), pelvis=(42, 0, 0), spine=(30, 0, 0), neck=(-30, 0, 0),
                            arm_l=dict(ik=(0.08, -0.46, 0.16), pole=pl), arm_r=dict(ik=(-0.08, -0.46, 0.16), pole=pr),
                            **legs),
                alza=_frutt(hip=(0.0, 0.05, 0.74), pelvis=(26, 0, 0), spine=(12, 0, 0), neck=(-14, 0, 0),
                            arm_l=dict(ik=(0.08, -0.44, 0.70), pole=pl), arm_r=dict(ik=(-0.08, -0.44, 0.70), pole=pr),
                            **legs),
                su=_frutt(hip=(0.0, 0.03, FR_HIP - 0.01), pelvis=(2, 0, 0), spine=(-4, 0, 0), neck=(-10, 0, 0),
                          arm_l=dict(ik=(0.09, -0.40, 1.40), pole=pl), arm_r=dict(ik=(-0.09, -0.40, 1.40), pole=pr),
                          **legs))


def keys_frutt_diqua():
    """di qua, svelto: il braccio destro indica avanti, verso la cantina, poi fa il gesto di venire."""
    return dict(point=_frutt(spine=(4, 0, 10), neck=(-4, 0, -8),
                             arm_r=dict(up=V(-0.24, -0.90, -0.36), lo=V(-0.12, -0.99, 0.02))),
                call=_frutt(spine=(4, 0, 8), neck=(-4, 0, -6),
                            arm_r=dict(up=V(-0.26, -0.80, -0.54), lo=V(-0.10, -0.40, 0.91))))


KEYSETS = dict(hack=keys_hack, idle=keys_idle, jab1=keys_jab1, jab2=keys_jab2, hook=keys_hook, hurt_high=keys_hurt_high, double_jump=keys_double_jump, ledge_hang=keys_ledge_hang,
               wall_slide=keys_wall_slide, wall_run=keys_wall_run, air_dash=keys_air_dash,
               esa_block=keys_esa_block, esa_charge_wind=keys_esa_charge_wind, esa_charge_run=keys_esa_charge_run,
               esa_dizzy=keys_esa_dizzy, ledge_hang_one=keys_ledge_hang_one, mazza=keys_mazza,
               rider_pignora=keys_rider_pignora, messo_idle=keys_messo_idle, messo_read=keys_messo_read,
               messo_laser=keys_messo_laser, messo_call=keys_messo_call,
               perdono_fermo=keys_perdono_fermo, perdono_nazzica=keys_perdono_nazzica,
               perdono_barcollo=keys_perdono_barcollo, perdono_scansa=keys_perdono_scansa,
               signora_ferma=keys_signora_ferma, signora_porge=keys_signora_porge,
               signora_guarda_su=keys_signora_guarda_su, signora_taralli=keys_signora_taralli,
               frutt_ansia=keys_frutt_ansia, frutt_sollievo=keys_frutt_sollievo, frutt_botola=keys_frutt_botola,
               frutt_diqua=keys_frutt_diqua)

# tracce: (tick, chiave, easing verso questa chiave). Le stesse tracce valgono per tutti i corpi.
TRACKS = dict(
    idle=[(0, "exhale"), (21, "inhale", "smooth"), (42, "exhale", "smooth")],
    jab1=[(0, "guard"), (2, "anti", "dec"), (4, "hit", "acc"), (6, "over", "dec"), (10, "back", "smooth"),
          (14, "guard", "smooth")],
    jab2=[(0, "guard"), (2, "anti", "dec"), (4, "hit", "acc"), (6, "over", "dec"), (10, "back", "smooth"),
          (14, "guard", "smooth")],
    hook=[(0, "guard"), (3, "load", "dec"), (6, "load", "hold"), (7.2, "arc", "acc"), (8, "impact", "lin"),
          (11, "impact", "hold"), (14, "over", "dec"), (21, "back", "smooth"), (27, "guard", "smooth")],
    ledge_hang=[(0, "a"), (24, "b", "smooth"), (48, "a", "smooth")],
    wall_slide=[(0, "a"), (6, "b", "smooth"), (12, "a", "smooth")],
    hack=[(0, "a"), (4, "b", "smooth"), (8, "a", "smooth")],
    wall_run=[(0, "ca"), (6, "pa", "smooth"), (12, "cb", "smooth"), (18, "pb", "smooth"), (24, "ca", "smooth"),
              (30, "top", "step")],
    air_dash=[(0, "kick"), (6, "glide", "dec")],
    esa_block=[(0, "hit"), (6, "up", "dec")],
    esa_charge_wind=[(0, "set"), (8, "coil", "dec"), (12, "coil2", "smooth"), (16, "coil", "smooth")],
    esa_charge_run=[(0, "ca"), (5, "pa", "smooth"), (10, "cb", "smooth"), (15, "pb", "smooth"), (20, "ca", "smooth")],
    esa_dizzy=[(0, "back"), (12, "mid", "smooth"), (24, "fwd", "smooth"), (36, "mid", "smooth"), (48, "back", "smooth")],
    hurt_high=[(0, "snap"), (5, "max", "dec"), (10, "rebound", "smooth"), (16, "guard", "smooth")],
    double_jump=[(0, "air"), (3, "coil", "dec"), (5, "coil", "hold"), (6.5, "thrust", "acc"), (9, "launch", "dec"),
                 (14, "open", "smooth"), (19, "tuck", "smooth"), (26, "fall", "smooth")],
    ledge_hang_one=[(0, "a"), (24, "b", "smooth"), (48, "a", "smooth")],
    mazza=[(0, "set"), (4, "grab", "smooth"), (7, "raise", "smooth"), (10, "lift", "dec"), (13, "hold", "smooth"),
           (15.5, "smash", "acc"), (18, "follow", "dec"), (20.5, "drop", "dec"), (26, "recover", "smooth"),
           (33, "set", "smooth")],
    rider_pignora=[(0, "a"), (8, "b", "dec"), (16, "a", "smooth")],
    messo_idle=[(0, "base"), (30, "breath", "smooth"), (60, "base", "smooth")],
    messo_read=[(0, "a"), (24, "b", "smooth"), (48, "a", "smooth")],
    messo_laser=[(0, "aim"), (6, "point", "dec")],
    messo_call=[(0, "up_a"), (10, "up_b", "smooth"), (20, "up_a", "smooth")],
    perdono_fermo=[(0, "base"), (40, "breath", "smooth"), (80, "base", "smooth")],
    perdono_nazzica=[(0, "n0")] + [(16 * i, "n%d" % (i % 8), "lin") for i in range(1, 9)],
    perdono_barcollo=[(0, "hit"), (6, "lurch", "dec"), (15, "catch", "smooth"), (27, "settle", "smooth"),
                      (45, "base", "smooth")],
    perdono_scansa=[(0, "base"), (8, "back", "dec"), (14, "hold", "smooth"), (32, "hold", "hold"),
                    (45, "base", "smooth")],
    signora_ferma=[(0, "base"), (40, "breath", "smooth"), (80, "base", "smooth")],
    signora_porge=[(0, "base"), (10, "reach", "dec"), (18, "hold", "smooth"), (40, "hold", "hold")],
    signora_guarda_su=[(0, "a"), (36, "b", "smooth"), (72, "a", "smooth")],
    signora_taralli=[(0, "base"), (8, "dig", "smooth"), (16, "dig2", "smooth"), (24, "dig", "smooth"),
                     (34, "give", "dec"), (50, "give", "hold")],
    frutt_ansia=[(0, "a"), (32, "b", "smooth"), (64, "a", "smooth")],
    frutt_sollievo=[(0, "still"), (6, "open", "dec"), (12, "bob", "smooth"), (18, "open", "smooth"),
                    (24, "bob", "smooth"), (32, "open", "smooth")],
    frutt_botola=[(0, "still"), (10, "chin", "smooth"), (16, "chin", "hold"), (26, "alza", "smooth"),
                  (36, "su", "dec"), (48, "su", "hold")],
    frutt_diqua=[(0, "point"), (8, "call", "smooth"), (16, "point", "smooth"), (24, "call", "smooth"),
                 (32, "point", "smooth")],
)


LIN_ARMS = dict(jab1=("l",), jab2=("r",), mazza=("l", "r"))


def make_track(rig, name):
    return Track(rig, KEYSETS[name](), TRACKS[name], LIN_ARMS.get(name, ()))


# ============================================================== molla del codino
class Spring:
    """punta del codino come particella (Verlet a 60 Hz, 2 sotto-passi) attaccata alla testa: segue la posa
    di riposo con una molla, ha inerzia e smorzamento; l'angolo dal riposo è limitato."""

    def __init__(self, length=0.10, k=0.10, damp=0.16, g=0.6, max_deg=40.0):
        self.l, self.k, self.damp, self.g, self.max = length, k, damp, g, math.radians(max_deg)
        self.P = None
        self.Pp = None

    def step(self, A, rest_dir):
        rest_tip = A + rest_dir * self.l
        if self.P is None:
            self.P, self.Pp = rest_tip.copy(), rest_tip.copy()
            return rest_dir.copy()
        dt = 1.0 / 120.0
        for _ in range(2):
            vel = (self.P - self.Pp) * (1.0 - self.damp)
            acc = (rest_tip - self.P) * self.k / (dt * dt) * 0.5 + Vector((0, 0, -self.g))
            nP = self.P + vel + acc * dt * dt
            d = nP - A
            if d.length < 1e-6:
                d = rest_dir.copy()
            d.normalize()
            ang = d.angle(rest_dir) if d.length > 0 else 0.0
            if ang > self.max:
                axis = rest_dir.cross(d)
                if axis.length > 1e-8:
                    d = Matrix.Rotation(self.max, 3, axis.normalized()) @ rest_dir
            nP = A + d * self.l
            self.Pp, self.P = self.P, nP
        return (self.P - A).normalized()


def add_topknot_bone(arm, ob_topknot, base, tip):
    """osso 'topknot' figlio di Head (base -> punta del codino, coordinate mondo di riposo) e il codino legato
    a quello: così la molla lo può ruotare."""
    vl = bpy.context.view_layer
    for o in bpy.context.selected_objects:
        o.select_set(False)
    vl.objects.active = arm
    arm.select_set(True)
    with bpy.context.temp_override(active_object=arm, object=arm, selected_objects=[arm]):
        bpy.ops.object.mode_set(mode="EDIT")
        eb = arm.data.edit_bones
        inv = arm.matrix_world.inverted()
        b = eb.new("topknot")
        b.head = inv @ base
        b.tail = inv @ tip
        b.parent = eb["Head"]
        b.use_connect = False
        bpy.ops.object.mode_set(mode="OBJECT")
    vg = ob_topknot.vertex_groups.get("Head")
    if vg is not None:
        vg.name = "topknot"
    return "topknot"


def spring_rotation(arm, bone, dir_world):
    """quaternione locale dell'osso perché il suo asse Y punti verso dir_world (posa corrente del padre)."""
    pb = arm.pose.bones[bone]
    b = arm.data.bones[bone]
    par = arm.pose.bones[b.parent.name]
    M_rest = (arm.matrix_world @ par.matrix @ (b.parent.matrix_local.inverted() @ b.matrix_local)).to_3x3()
    M_rest_n = M_rest.normalized()
    y_rest = (M_rest_n @ Vector((0, 1, 0))).normalized()
    Rd = y_rest.rotation_difference(dir_world.normalized()).to_matrix()
    q = (M_rest_n.inverted() @ Rd @ M_rest_n).to_quaternion()
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = q


def topknot_rest_dir(arm, bone):
    b = arm.data.bones[bone]
    par = arm.pose.bones[b.parent.name]
    M = (arm.matrix_world @ par.matrix @ (b.parent.matrix_local.inverted() @ b.matrix_local))
    A = M.to_translation()
    y = (M.to_3x3().normalized() @ Vector((0, 1, 0))).normalized()
    return A, y
