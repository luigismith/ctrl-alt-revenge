# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - pipeline v7: stivali da picchiaduro 16-bit (al posto dell'inviluppo convesso del piede).

Lo stivale è fatto di tre pezzi chiusi che si sovrappongono:
  * suola: sagoma a "stadio" più larga in punta, spessa (davanti 0,036 m, tacco 0,05 m: a 48 px/m sono 2 px),
    sporge di 1,2 cm dalla tomaia, così il suo bordo superiore prende luce e a 1x si legge una riga;
  * puntale: mezzo ellissoide basso e largo sulla parte anteriore (la punta arrotondata, non a cuneo);
  * gambale: tubo dal tallone fino a top_z, con un collarino più largo in cima (stacco dai pantaloni).
Pesi: puntale sull'osso ball_* (si piega con le dita), suola e tacco su foot_*, gambale fra foot_* e calf_*.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

UP = Vector((0, 0, 1))


def _ring(bm, center, ax_u, ax_v, ru, rv, n, z_scale=None):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append(bm.verts.new(center + ax_u * (ru * math.cos(a)) + ax_v * (rv * math.sin(a))))
    return pts


def _bridge(bm, r0, r1, mi):
    n = len(r0)
    for i in range(n):
        f = bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
        f.material_index = mi


def _cap(bm, ring, mi, flip=False):
    f = bm.faces.new(list(reversed(ring)) if flip else ring)
    f.material_index = mi
    return f


def footprint(fwd, side, back, front, w_heel, w_toe, n=28):
    """contorno della suola nel piano (u avanti, v di lato): tallone a semicerchio, punta arrotondata più larga."""
    pts = []
    for i in range(n):
        t = i / n
        a = 2 * math.pi * t
        u, v = math.cos(a), math.sin(a)
        # u in [-1, 1] -> da tallone a punta; la larghezza cresce verso la punta
        x = (back + front) / 2 * u + (front - back) / 2
        wf = w_heel + (w_toe - w_heel) * (0.5 + 0.5 * u)
        y = v * wf / 2
        # punta più piena (meno a goccia): appiattisce l'ellisse davanti
        if u > 0:
            x = (front - back) / 2 + (back + front) / 2 * (u ** 0.75)
        pts.append((x, y))
    return pts


def make_boots_v7(body, arm, mats, L, cfg, rigid_object, skinned_object, set_part_attr, link):
    sole_z = cfg.get("sole_z", -0.024)
    top_z = cfg.get("top_z", 0.27)
    s = cfg.get("size", 1.0)
    out = []
    for side in ("l", "r"):
        ank = L["foot_" + side].copy()
        ball = L["ball_" + side].copy()
        fwd = Vector((ball.x - ank.x, ball.y - ank.y, 0.0))
        if fwd.length < 1e-6:
            fwd = Vector((0, -1, 0))
        fwd.normalize()
        sv = fwd.cross(UP).normalized()
        L_ab = (ball - ank).to_2d().length
        back = cfg.get("heel_back", 0.075) * s
        front = (L_ab + cfg.get("toe_front", 0.095)) * s
        w_heel, w_toe = cfg.get("w_heel", 0.088) * s, cfg.get("w_toe", 0.122) * s
        base = Vector((ank.x, ank.y, sole_z))
        mats_order = ["BOOT_SOLE", "BOOTS", "BOOT_CUFF"]
        # ---------------- suola (con tacco)
        bm = bmesh.new()
        fp = footprint(fwd, sv, back, front, w_heel + 0.024, w_toe + 0.024)
        t_front, t_heel = cfg.get("sole_t", 0.036), cfg.get("heel_t", 0.05)
        bot, top = [], []
        for (x, y) in fp:
            p = base + fwd * x + sv * y
            k = max(0.0, min(1.0, (x + back) / (back + front)))       # 0 tallone -> 1 punta
            th = t_heel + (t_front - t_heel) * min(1.0, k * 2.2)
            bot.append(bm.verts.new(p))
            top.append(bm.verts.new(p + UP * th))
        _cap(bm, bot, 0, flip=True)
        _cap(bm, top, 0)
        _bridge(bm, bot, top, 0)
        bm.normal_update()
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        sole = rigid_object("BootSole_" + side, bm, "foot_" + side, arm, ["BOOT_SOLE"], mats, part="foot_" + side,
                            smooth=False)
        out.append(sole)
        # ---------------- puntale: mezzo ellissoide sulla parte anteriore
        bm = bmesh.new()
        cx = (front - 0.02) * 0.55
        c = base + fwd * (cx * 0.85) + UP * (t_front + 0.002)
        ru, rv, rz = (front - cx * 0.85) - 0.010, w_toe / 2, cfg.get("toe_h", 0.072) * s
        # anelli dall'alto in basso
        rings = []
        nr, ns = 7, 22
        for j in range(nr + 1):
            ph = (math.pi / 2) * (1 - j / nr)                  # pi/2 = cima, 0 = base
            zz = rz * math.sin(ph)
            rr = math.cos(ph)
            if j == 0:
                rings.append([bm.verts.new(c + UP * rz)])
                continue
            ring = []
            for i in range(ns):
                a = 2 * math.pi * i / ns
                # dietro (a ~ pi) il puntale si allunga verso la caviglia e si alza: si fonde col gambale
                uu = math.cos(a) * (ru if math.cos(a) > 0 else ru * 1.25)
                ring.append(bm.verts.new(c + fwd * (uu * rr) + sv * (rv * rr * math.sin(a)) + UP * zz))
            rings.append(ring)
        # ventaglio in cima
        top_v = rings[0][0]
        for i in range(ns):
            f = bm.faces.new((top_v, rings[1][i], rings[1][(i + 1) % ns]))
            f.material_index = 0
        for j in range(1, nr):
            _bridge(bm, rings[j], rings[j + 1], 0)
        _cap(bm, rings[nr], 0, flip=True)
        bm.normal_update()
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        ball_bone = "ball_" + side

        def w_toe_fn(co, ank=ank, fwd=fwd):
            u = (co - ank).dot(fwd)
            k = max(0.0, min(1.0, (u - 0.06) / 0.08))
            return {ball_bone: k, "foot_" + side: 1.0 - k} if k > 0 else {"foot_" + side: 1.0}
        toe = skinned_object("BootToe_" + side, bm, w_toe_fn, arm, ["BOOTS"], mats, lambda c: "foot_" + side)
        out.append(toe)
        # ---------------- gambale con collarino
        bm = bmesh.new()
        c0 = base + fwd * cfg.get("shaft_fwd", 0.012) * s
        n = 20
        levels = [(t_heel - 0.004, cfg.get("r_ankle", 0.064) * s, 1.12, 1),
                  (0.10, cfg.get("r_ankle", 0.064) * s * 0.96, 1.0, 1),
                  (top_z - sole_z - 0.034, cfg.get("r_top", 0.066) * s, 0.98, 1),
                  (top_z - sole_z - 0.030, cfg.get("r_top", 0.066) * s + 0.010, 1.0, 2),
                  (top_z - sole_z, cfg.get("r_top", 0.066) * s + 0.010, 1.0, 2)]
        rings = []
        for (zz, r, elong, mi) in levels:
            rings.append((_ring(bm, c0 + UP * zz, fwd, sv, r * elong, r, n), mi))
        _cap(bm, rings[0][0], 1, flip=True)
        for (r0, _), (r1, mi) in zip(rings, rings[1:]):
            _bridge(bm, r0, r1, mi)
        _cap(bm, rings[-1][0], 2)
        bm.normal_update()
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        z_ank = ank.z

        def w_shaft(co, z_ank=z_ank):
            k = max(0.0, min(1.0, (co.z - (z_ank + 0.02)) / 0.12))
            return {"calf_" + side: k, "foot_" + side: 1.0 - k} if k > 0 else {"foot_" + side: 1.0}
        shaft = skinned_object("BootShaft_" + side, bm, w_shaft, arm, ["BOOT_SOLE", "BOOTS", "BOOT_CUFF"], mats,
                               lambda c: "foot_" + side)
        out.append(shaft)
    return out
