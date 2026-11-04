# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - lettore minimo ASF/AMC (database CMU) con cinematica diretta; dalla prova spike-anim.

Minimal Acclaim ASF/AMC reader + forward kinematics (CMU Graphics Lab Motion Capture Database).

numpy only, so it runs both inside Blender and in a plain venv.

Conventions (as in CMU's own viewer and the common AMCParser):
  C      = Rz(az) Ry(ay) Rx(ax)            (ASF 'axis ... XYZ')
  M      = Rz(rz) Ry(ry) Rx(rx)            (AMC values of the listed dofs, degrees)
  G_bone = G_parent @ C @ M @ C^-1         world-space rotation of the segment *relative to the rest pose*
  end    = start + length * G_bone @ direction
Root: position = TX TY TZ, G_root = C_root @ M_root @ C_root^-1.
Units: ASF lengths / root translation * (1/0.45) * 2.54/100 = metres (CMU FAQ).
CMU world: Y up; at rest the subject faces +Z and his LEFT is +X.
"""
import math

import numpy as np

CMU_TO_M = (1.0 / 0.45) * 2.54 / 100.0


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def euler_xyz(ax, ay, az):
    """Rotazione prima attorno a X, poi a Y, poi a Z (assi fissi) -> Rz @ Ry @ Rx. In gradi."""
    return _rz(math.radians(az)) @ _ry(math.radians(ay)) @ _rx(math.radians(ax))


class Bone:
    def __init__(self, name):
        self.name = name
        self.direction = np.zeros(3)
        self.length = 0.0
        self.axis = np.zeros(3)
        self.dof = []
        self.children = []
        self.parent = None
        self.C = np.eye(3)
        self.Cinv = np.eye(3)


class Skeleton:
    def __init__(self, path):
        self.bones = {}
        self.order = []          # parents before children
        self.length_unit = 1.0
        lines = [l.strip() for l in open(path, encoding="latin-1")]
        i = 0
        root = Bone("root")
        root.dof = ["tx", "ty", "tz", "rx", "ry", "rz"]
        self.bones["root"] = root
        section = None
        cur = None
        hier = []
        while i < len(lines):
            l = lines[i]
            i += 1
            if not l or l.startswith("#"):
                continue
            if l.startswith(":"):
                section = l.split()[0]
                continue
            tok = l.split()
            if section == ":units" and tok[0] == "length":
                self.length_unit = float(tok[1])
            elif section == ":root":
                if tok[0] == "axis":
                    root_axis_order = tok[1]
                elif tok[0] == "orientation":
                    root.axis = np.array([float(v) for v in tok[1:4]])
            elif section == ":bonedata":
                if tok[0] == "begin":
                    cur = None
                elif tok[0] == "name":
                    cur = Bone(tok[1])
                    self.bones[cur.name] = cur
                elif tok[0] == "direction":
                    cur.direction = np.array([float(v) for v in tok[1:4]])
                elif tok[0] == "length":
                    cur.length = float(tok[1])
                elif tok[0] == "axis":
                    cur.axis = np.array([float(v) for v in tok[1:4]])
                    if tok[4].upper() != "XYZ":
                        raise ValueError("only XYZ axis order supported, got " + tok[4])
                elif tok[0] == "dof":
                    cur.dof = [d.lower() for d in tok[1:]]
            elif section == ":hierarchy":
                if tok[0] in ("begin", "end"):
                    continue
                hier.append(tok)
        for tok in hier:
            par = self.bones[tok[0]]
            for c in tok[1:]:
                self.bones[c].parent = par
                par.children.append(self.bones[c])
        for b in self.bones.values():
            b.C = euler_xyz(*b.axis)
            b.Cinv = b.C.T
        stack = [root]
        while stack:
            b = stack.pop(0)
            self.order.append(b.name)
            stack.extend(b.children)
        self.scale_m = CMU_TO_M * 0.45 / self.length_unit   # == CMU FAQ factor when length unit is 0.45

    def rest_positions(self):
        """Posizioni delle articolazioni (fine dei segmenti) nella posa di riposo, in metri, nel mondo CMU."""
        pos = {"root": np.zeros(3)}
        for n in self.order[1:]:
            b = self.bones[n]
            pos[n] = pos[b.parent.name] + b.direction * b.length * self.scale_m
        return pos


def read_amc(path):
    """-> elenco di dizionari osso -> list[float]."""
    frames = []
    cur = None
    for l in open(path, encoding="latin-1"):
        l = l.strip()
        if not l or l.startswith("#") or l.startswith(":"):
            continue
        tok = l.split()
        if len(tok) == 1 and tok[0].isdigit():
            cur = {}
            frames.append(cur)
            continue
        cur[tok[0]] = [float(v) for v in tok[1:]]
    return frames


def fk(skel, frame):
    """-> (G: osso -> rotazione delta 3x3 nel mondo, P: osso -> posizione della FINE del segmento (m), posizione della radice (m))."""
    G, P = {}, {}
    rv = frame["root"]
    vals = dict(zip(skel.bones["root"].dof, rv))
    root = skel.bones["root"]
    M = euler_xyz(vals.get("rx", 0.0), vals.get("ry", 0.0), vals.get("rz", 0.0))
    G["root"] = root.C @ M @ root.Cinv
    P["root"] = np.array([vals.get("tx", 0.0), vals.get("ty", 0.0), vals.get("tz", 0.0)]) * skel.scale_m
    for n in skel.order[1:]:
        b = skel.bones[n]
        v = dict(zip(b.dof, frame.get(n, [])))
        M = euler_xyz(v.get("rx", 0.0), v.get("ry", 0.0), v.get("rz", 0.0))
        G[n] = G[b.parent.name] @ b.C @ M @ b.Cinv
        P[n] = P[b.parent.name] + b.length * skel.scale_m * (G[n] @ b.direction)
    return G, P, P["root"]
