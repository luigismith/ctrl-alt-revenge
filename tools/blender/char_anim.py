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


KEYSETS = dict(idle=keys_idle, jab1=keys_jab1, jab2=keys_jab2, hook=keys_hook, hurt_high=keys_hurt_high, double_jump=keys_double_jump, ledge_hang=keys_ledge_hang)

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
    hurt_high=[(0, "snap"), (5, "max", "dec"), (10, "rebound", "smooth"), (16, "guard", "smooth")],
    double_jump=[(0, "air"), (3, "coil", "dec"), (5, "coil", "hold"), (6.5, "thrust", "acc"), (9, "launch", "dec"),
                 (14, "open", "smooth"), (19, "tuck", "smooth"), (26, "fall", "smooth")],
)


LIN_ARMS = dict(jab1=("l",), jab2=("r",))


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
