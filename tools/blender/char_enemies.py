# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - costumi degli Esattori (decisione 63): il rider, l'esattore di professione e il messo;
e, con gli stessi pezzi, Totò adulto (2107): felpa scura col cappuccio su, jeans, zainetto con le bombolette;
e Addolorata in casa (2087, 75 anni), sul corpo femminile: abito blu scuro, cardigan abbottonato con lo scollo a V,
crocchia bassa, occhiali appesi al cordino e metro da sarta al collo, scarpe basse;
e Mimmo (2086, 49 anni): la tuta da turno grigia di SIDERA col cappuccio abbassato, il filtro sotto il mento e il
MANODOPERA n. 2 al braccio destro, con gli anelli rossi.

Stesso corpo UBC rimodellato dei nemici dello slice (build_thug di char_build.py), con i pezzi dei fogli di
riferimento del 6 novembre 2026 (fuori dal repository):
  * rider: casco jet con gli adesivi, occhiali da polvere con le lenti arancioni, scaldacollo, giacca da consegne
    senape con i profili catarifrangenti e i polsini a costine, pantaloni della tuta con la striscia, scarpe da
    ginnastica, zaino termico squadrato con un braccio pignorato che esce dal coperchio;
  * esattore: pettorina arancione ad alta visibilità con due strisce argento e l'emblema rosso di SIDERA sul petto,
    camicia da lavoro scura con le maniche arrotolate al gomito, pantaloni cargo con le ginocchiere, guanti senza
    dita, occhiali da polvere chiari;
  * messo: giacca a vento rossa di SIDERA con polsini e orlo a costine, colletto bianco e cravatta, cordino rosso
    col tesserino, pantaloni grigi, scarpe nere, occhiali da polvere chiari, tablet nella sinistra e penna laser
    con la punta rossa nella destra.
Le funzioni comuni (tubi, scatole, gusci dal corpo, oggetti rigidi) sono quelle di char_build.py, passate in `ns`
(le globali del modulo principale, come per char_render). Gli oggetti tenuti in mano (tablet, penna) si
scrivono nella posa di riferimento della loro animazione e si riportano a riposo sull'osso della mano.
"""
import math
import types

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

UP = Vector((0, 0, 1))
TORSO = ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r")
SIDES = (("l", 1.0), ("r", -1.0))


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ============================================================== misure del corpo a riposo
def body_points(B, body):
    """vertici del corpo (già in coordinate del mondo) con l'osso dominante."""
    return [(v.co.copy(), b) for v, b in zip(body.data.vertices, B.vert_bones(body))]


def head_section(pts, z, dz=0.012):
    """centro e semiassi (x, y) della sezione della testa alla quota z."""
    ps = [p for p, b in pts if b == "Head" and abs(p.z - z) < dz]
    rx = max(abs(p.x) for p in ps)
    y0, y1 = min(p.y for p in ps), max(p.y for p in ps)
    return Vector((0.0, (y0 + y1) / 2, z)), rx, (y1 - y0) / 2


def limb_radius(pts, bone, a, b, t, dt=0.10):
    """raggio medio dell'arto (osso `bone`, asse a->b) attorno al punto t dell'asse."""
    d = b - a
    rs = []
    for p, bn in pts:
        if bn != bone:
            continue
        tt = (p - a).dot(d) / max(d.length_squared, 1e-9)
        if abs(tt - t) < dt:
            rs.append((p - (a + d * tt)).length)
    return sum(rs) / len(rs) if rs else 0.045


def surface_y(pts, x, z, front=True, r=0.03, bones=TORSO + ("pelvis", "neck_01")):
    """y della superficie del busto davanti (o dietro) al punto (x, z)."""
    ps = [p.y for p, b in pts if b in bones and abs(p.x - x) < r and abs(p.z - z) < r]
    if not ps:
        return None
    return min(ps) if front else max(ps)


def surface_top(pts, x, y, r=0.03, bones=TORSO + ("neck_01",)):
    ps = [p.z for p, b in pts if b in bones and abs(p.x - x) < r and abs(p.y - y) < r]
    return max(ps) if ps else None


# ============================================================== primitive in più
def ring_verts(bm, c, d, rx, ry, n=16):
    """anello ellittico perpendicolare a d (rx di lato, ry in alto)."""
    dd, u, w = basis(d)
    return [bm.verts.new(c + w * (rx * math.cos(2 * math.pi * k / n)) + u * (ry * math.sin(2 * math.pi * k / n)))
            for k in range(n)]


def basis(d, up=UP):
    d = d.normalized()
    u = up - d * up.dot(d)
    if u.length < 1e-6:
        u = Vector((0, 1, 0)) - d * d.y
    u.normalize()
    return d, u, d.cross(u)


def bridge(bm, r0, r1, mi):
    n = len(r0)
    for i in range(n):
        f = bm.faces.new((r0[i], r0[(i + 1) % n], r1[(i + 1) % n], r1[i]))
        f.material_index = mi


def cap(bm, ring, mi, flip=False):
    f = bm.faces.new(list(reversed(ring)) if flip else ring)
    f.material_index = mi
    return f


def finish(bm):
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def band_bm(c, rx, ry, h, t, a0, a1, n=28, mat=0, z_back=0.0):
    """striscia (elastico) su un arco d'ellisse orizzontale attorno a c: angolo 0 davanti (-Y), 90° a sinistra (+X);
    z_back alza la striscia dietro (segue la nuca o il casco)."""
    bm = bmesh.new()
    rows = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        s, co = math.sin(a), math.cos(a)
        z = c.z + z_back * (1 - co) / 2
        pin = Vector((c.x + s * rx, c.y - co * ry, z))
        pout = Vector((c.x + s * (rx + t), c.y - co * (ry + t), z))
        dz = Vector((0, 0, h / 2))
        rows.append([bm.verts.new(pin - dz), bm.verts.new(pout - dz), bm.verts.new(pout + dz), bm.verts.new(pin + dz)])
    for i in range(n):
        bridge_quad(bm, rows[i], rows[i + 1], mat)
    cap(bm, rows[0], mat, flip=True)
    cap(bm, rows[-1], mat)
    return finish(bm)


def bridge_quad(bm, r0, r1, mi):
    for k in range(4):
        f = bm.faces.new((r0[k], r0[(k + 1) % 4], r1[(k + 1) % 4], r1[k]))
        f.material_index = mi


def torus_bm(c, R, r, segs=20, tsegs=8, mat=0, sy=1.0):
    """anello (ciambella) orizzontale attorno a c; sy schiaccia lungo y (collo non tondo)."""
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        th = 2 * math.pi * i / segs
        dirv = Vector((math.sin(th), -math.cos(th) * sy, 0.0))
        cc = c + dirv * R
        rings.append([bm.verts.new(cc + dirv.normalized() * math.cos(2 * math.pi * k / tsegs) * r
                                   + UP * math.sin(2 * math.pi * k / tsegs) * r) for k in range(tsegs)])
    for i in range(segs):
        bridge(bm, rings[i], rings[(i + 1) % segs], mat)
    return finish(bm)


def ribbon_bm(points, normals, width, thick, mat=0):
    """nastro piatto (cinghia, cordino) lungo una spezzata, appoggiato sulle normali date."""
    bm = bmesh.new()
    rows = []
    n = len(points)
    for i, (p, nv) in enumerate(zip(points, normals)):
        d = (points[min(i + 1, n - 1)] - points[max(i - 1, 0)]).normalized()
        s = d.cross(nv).normalized()
        nn = s.cross(d).normalized()
        if nn.dot(nv) < 0:
            nn = -nn
        rows.append([bm.verts.new(p + s * (sw * width / 2) + nn * (hh * thick))
                     for sw, hh in ((-1, 0), (1, 0), (1, 1), (-1, 1))])
    for i in range(n - 1):
        bridge_quad(bm, rows[i], rows[i + 1], mat)
    cap(bm, rows[0], mat, flip=True)
    cap(bm, rows[-1], mat)
    return finish(bm)


def mat_rows(*cols):
    return Matrix([c for c in cols]).transposed()


def smooth_boundary(bm, iters=6, lam=0.5):
    """liscia i bordi aperti di un guscio (scollo, giromanica, orlo): le facce scelte una per una lasciano un bordo a
    dente di sega, che nello sprite diventa una scaletta di pixel. Laplaciano lungo il bordo: i denti spariscono, le
    curve grandi restano."""
    nb = {}
    for v in bm.verts:
        if v.is_boundary:
            ns = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(ns) == 2:
                nb[v] = ns
    for _ in range(iters):
        new = {v: v.co.lerp((ns[0].co + ns[1].co) / 2, lam) for v, ns in nb.items()}
        for v, co in new.items():
            v.co = co


def keep_clear(B, bm, body, gap):
    """tiene il guscio ad almeno `gap` dal corpo: lo smussamento della stoffa lo tira dentro dove il corpo è convesso
    (fianchi e petto del bruto), e il corpo bucava la pettorina con un trattino scuro."""
    if gap <= 0:
        return
    bmB = bmesh.new()
    bmB.from_mesh(body.data)
    bmB.normal_update()
    tree = BVHTree.FromBMesh(bmB)
    moved = 0
    for v in bm.verts:
        loc, nrm, _, _ = tree.find_nearest(v.co)
        if loc is None:
            continue
        s = (v.co - loc).dot(nrm)
        if s < gap:
            v.co += nrm * (gap - s)
            moved += 1
    bmB.free()
    bm.normal_update()
    B.log("guscio: %d vertici scostati dal corpo (almeno %.3f)" % (moved, gap))


def cut_z(bm, z):
    """taglia il guscio col piano orizzontale z: le strisce catarifrangenti hanno i bordi dritti."""
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-5,
                           plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1.0))


# ============================================================== pose di riferimento per gli oggetti in mano
def posed_bone(B, arm, keyset, key, bone):
    """matrice nel mondo dell'osso nella posa `key` della traccia `keyset` di char_anim (poi torna a riposo)."""
    import char_anim as A7
    import char_poses as CP
    B.use_action(arm, None)
    rig = CP.Rig(arm, {})
    D, pos = rig.deltas(A7.KEYSETS[keyset]()[key])
    A7.apply_local(arm, A7.local_pose(rig, D, pos))
    bpy.context.view_layer.update()
    M = arm.matrix_world @ arm.pose.bones[bone].matrix
    chest = D["spine_03"].copy()                       # rotazione del petto rispetto al riposo (assi del corpo)
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()
    return M, chest


def to_rest(bm, arm, bone, M_pose, scale=1.0):
    """porta un bmesh scritto nella posa (matrice dell'osso M_pose) alle coordinate di riposo dell'osso; `scale` è la
    scala delle proporzioni che la posa darà all'osso (mano 1,3: l'oggetto si costruisce più piccolo)."""
    bn = arm.data.bones[bone]
    M_rest = arm.matrix_world @ bn.matrix_local
    T = M_rest @ M_pose.inverted()
    bmesh.ops.transform(bm, matrix=T, verts=bm.verts)
    if abs(scale - 1.0) > 1e-6:
        h = arm.matrix_world @ bn.head_local
        S = Matrix.Translation(h) @ Matrix.Scale(1.0 / scale, 4) @ Matrix.Translation(-h)
        bmesh.ops.transform(bm, matrix=S, verts=bm.verts)
    bm.normal_update()
    return bm


# ============================================================== accessori
def make_goggles(B, arm, mats, L, pts, cfg, lens):
    """occhiali da polvere: due coppe ellittiche davanti agli occhi (montatura scura, lente), ponte sul naso ed
    elastico attorno alla testa (o al casco). Legati alla testa."""
    ez = L["eye_l"].z + cfg.get("dz", 0.003)
    hc, rx, ry = head_section(pts, ez)
    out = cfg.get("strap_out", 0.004)
    lrx, lry = cfg.get("lens_r", (0.024, 0.019))
    l_in, l_out = cfg.get("lens_in", 0.004), cfg.get("lens_out", 0.026)
    parts = []
    for sd, sx in SIDES:
        e = L["eye_" + sd] + Vector((0, 0, cfg.get("dz", 0.003)))
        d = Vector((sx * cfg.get("wrap", 0.30), -1.0, 0.0)).normalized()
        bm = bmesh.new()
        r0 = ring_verts(bm, e + d * l_in, d, lrx * 0.92, lry * 0.92)
        r1 = ring_verts(bm, e + d * l_out, d, lrx, lry)
        r2 = ring_verts(bm, e + d * (l_out + 0.0015), d, lrx * 0.74, lry * 0.70)
        bridge(bm, r0, r1, 0)
        bridge(bm, r1, r2, 0)
        cap(bm, r2, 1)
        cap(bm, r0, 0, flip=True)
        parts.append(finish(bm))
    gap = abs(L["eye_l"].x - L["eye_r"].x) - 2 * lrx * 0.85
    mid = (L["eye_l"] + L["eye_r"]) / 2 + Vector((0.0, -l_out + 0.006, cfg.get("dz", 0.003) + 0.004))
    parts.append(B.box_bm(mid, (max(gap, 0.004) + 0.010, 0.010, 0.010), mat=0))
    # l'elastico parte dal bordo esterno della lente (angolo 0 davanti, 90° a sinistra) e gira dietro la testa
    sc = hc + Vector((0, cfg.get("strap_dy", 0.0), 0))
    d_l = Vector((cfg.get("wrap", 0.30), -1.0, 0.0)).normalized()
    pe = L["eye_l"] + d_l * (l_out * 0.5) + basis(d_l)[2] * (-lrx)
    pe = pe if pe.x > 0 else L["eye_l"] + Vector((lrx, 0, 0))
    a0 = math.atan2(pe.x / (rx + out), -(pe.y - sc.y) / (ry + out)) - math.radians(cfg.get("strap_overlap_deg", 4))
    parts.append(band_bm(sc, rx + out, ry + out, cfg.get("strap_h", 0.014), 0.005, a0, 2 * math.pi - a0, n=30, mat=0,
                         z_back=cfg.get("strap_z_back", 0.0)))
    return B.rigid_object("Goggles", B.join_bms(parts), "Head", arm, ["GOGGLE", lens], mats, part="head")


def make_helmet(B, arm, mats, L, pts, cfg):
    """casco jet: calotta aperta davanti, che scende sulle orecchie e sulla nuca, bordo scuro, adesivi scoloriti."""
    ez = L["eye_l"].z
    hc, rx, ry = head_section(pts, ez + 0.012)
    off = cfg.get("off", 0.016)
    cz = ez + cfg.get("cz", 0.0)
    R = (rx + off, ry + off, L["crown_z"] - cz + off)
    center = Vector((0.0, hc.y + cfg.get("dy", 0.006), cz))
    fz, sz, bz = cfg.get("front_z", 0.42), cfg.get("side_z", -0.42), cfg.get("back_z", -0.55)
    a0, a1 = cfg.get("az", (34.0, 80.0))

    def keep(co):
        az = math.degrees(math.atan2(abs(co.x), -co.y))           # 0 davanti, 180 dietro
        zc = fz + (sz - fz) * smoothstep(a0, a1, az)
        zc += (bz - sz) * smoothstep(110.0, 170.0, az)
        return co.z > zc
    bm = B.sphere_bm(center, R, mat=0, keep=keep, segs=36, rings=22)
    stick = [(Vector(s[0]).normalized(), math.cos(math.radians(s[1])), s[2]) for s in cfg.get("stickers", [
        ((-0.62, -0.30, 0.72), 15, 1), ((-0.86, 0.30, 0.20), 14, 2), ((0.05, 0.55, 0.83), 15, 1),
        ((-0.30, 0.82, 0.20), 13, 2), ((0.66, -0.20, 0.70), 15, 2)])]
    for f in bm.faces:
        fc = f.calc_center_median() - center
        u = Vector((fc.x / R[0], fc.y / R[1], fc.z / R[2])).normalized()
        if any(e.is_boundary for e in f.edges):
            f.material_index = 3
            continue
        for sv, cmin, mi in stick:
            if u.dot(sv) > cmin:
                f.material_index = mi
    ob = B.rigid_object("Helmet", bm, "Head", arm, ["HELMET", "PATCH", "BRASS", "HELMET_DARK", "HELMET_DARK",
                                                     "HELMET_DARK", "HELMET_DARK"], mats, part="head")
    sol = ob.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = cfg.get("thick", 0.010)
    sol.offset = -1.0
    sol.use_even_offset = False
    sol.use_quality_normals = True
    sol.material_offset = 3
    sol.material_offset_rim = 3
    return ob


def make_gaiter(B, arm, mats, L, pts, cfg, mat="HOOD"):
    """scaldacollo abbassato sotto il mento: ciambella attorno al collo, sopra il collo alto della giacca
    (per Mimmo, il filtro della tuta abbassato sotto il mento)."""
    z = L["chin"].z + cfg.get("dz", -0.022)
    a, b = L["neck_01"], L["Head"]
    r_neck = limb_radius(pts, "neck_01", a, b, max(0.0, min(1.0, (z - a.z) / max(b.z - a.z, 1e-3))), dt=0.3)
    c = Vector((0.0, (a.y + b.y) / 2 + cfg.get("dy", 0.006), z))
    bm = torus_bm(c, r_neck + cfg.get("gap", 0.020), cfg.get("r", 0.016), mat=0, sy=cfg.get("sy", 1.0))
    if cfg.get("filtro"):
        # la cartuccia del filtro, tonda, sul davanti
        fc = cfg["filtro"]
        cc = c + Vector((0.0, -(r_neck + cfg.get("gap", 0.020) + cfg.get("r", 0.016) * 0.6), fc.get("dz", 0.004)))
        bm = B.join_bms([bm, B.sphere_bm(cc, (fc.get("r", 0.024), fc.get("t", 0.014), fc.get("r", 0.024)), mat=1,
                                         segs=14, rings=8)])
    return B.rigid_object("Gaiter", bm, "neck_01", arm, [mat, "METAL_DARK"], mats, part="head")


def make_backpack(B, arm, mats, L, pts, cfg):
    """zaino termico squadrato con la striscia rossa, cinghie sulle spalle, coperchio socchiuso (cerniera vicino
    alla schiena) e un braccio cibernetico pignorato che esce dall'apertura, col gomito alto e la mano che pende
    dietro. Legato al petto (spine_03)."""
    sh_z = L["clavicle_l"].z
    back_y = max(p.y for p, b in pts if b in ("spine_02", "spine_03") and abs(p.x) < 0.08)
    W, D, H = cfg.get("size", (0.34, 0.26, 0.38))
    top = sh_z + cfg.get("top_dz", 0.03)
    y0 = back_y + cfg.get("gap", 0.030)
    c = Vector((0.0, y0 + D / 2, top - H / 2))
    box = B.box_bm(c, (W, D, H), bevel=cfg.get("bevel", 0.022), mat=0, segs=2)
    zs = top - H * cfg.get("stripe_t", 0.60)
    hs = cfg.get("stripe_h", 0.026) / 2
    for z in (zs - hs, zs + hs):
        geom = list(box.verts) + list(box.edges) + list(box.faces)
        bmesh.ops.bisect_plane(box, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1))
    for f in box.faces:
        fc = f.calc_center_median()
        if abs(fc.z - zs) < hs and abs(f.normal.z) < 0.5:
            f.material_index = 1
    finish(box)
    parts = [box]
    # coperchio: cerniera sul bordo vicino alla schiena, il bordo di dietro si alza
    lt = cfg.get("lid_t", 0.032)
    lid = B.box_bm(Vector((0.0, D / 2, lt / 2)), (W + 0.012, D + 0.012, lt), bevel=0.012, mat=0, segs=1)
    bmesh.ops.transform(lid, matrix=Matrix.Translation((0.0, y0 - 0.006, top - 0.004))
                        @ Matrix.Rotation(math.radians(cfg.get("lid_deg", 38.0)), 4, "X"), verts=lid.verts)
    parts.append(finish(lid))
    # braccio pignorato: dall'interno sale fuori dall'apertura dietro, gomito alto, avambraccio e mano che pendono
    ac = cfg.get("arm", {})
    xa = ac.get("x", -0.05)
    yb = y0 + D
    p_sh = Vector((xa, y0 + D * 0.55, top - 0.08))
    p_el = Vector((xa - 0.010, yb + ac.get("el_dy", 0.01), top + ac.get("el_dz", 0.17)))
    p_wr = Vector((xa - 0.020, yb + ac.get("wr_dy", 0.13), top + ac.get("wr_dz", 0.07)))
    ra, rf = ac.get("r", (0.042, 0.035))

    def rings(ts, w=0.045):
        return lambda t, a: 1 if a != 999 and any(abs(t - r) < w for r in ts) else 2

    parts.append(B.tube_bm(p_sh, p_el, [(0, ra), (1, ra * 0.92)], rings((0.62,)), segs=12, extra_ts=(0.575, 0.665)))
    parts.append(B.sphere_bm(p_el, (ra * 1.08,) * 3, mat=3, segs=12, rings=8))
    parts.append(B.tube_bm(p_el, p_wr, [(0, rf), (1, rf * 0.86)], rings((0.30, 0.78)), segs=12,
                           extra_ts=(0.255, 0.345, 0.735, 0.825)))
    parts.append(B.sphere_bm(p_wr, (rf * 0.95,) * 3, mat=3, segs=10, rings=6))
    hd = Vector(ac.get("hand_dir", (0.0, 0.45, -1.0))).normalized()
    dF, uF, wF = basis(hd, Vector((0, 1, 0)))
    Rh = mat_rows(wF, uF, dF)
    hc = p_wr + hd * 0.045
    parts.append(B.box_bm(hc, (0.082, 0.032, 0.074), R=Rh, bevel=0.010, mat=2, segs=1))
    for i in range(4):
        base = hc + hd * 0.034 + wF * (i - 1.5) * 0.019
        tip = base + hd * 0.052 + uF * 0.024
        parts.append(B.tube_bm(base, tip, [(0, 0.0095), (1, 0.008)], lambda t, a: 2, segs=6))
    tb = hc - wF * 0.043 + hd * 0.004
    parts.append(B.tube_bm(tb, tb + hd * 0.040 - wF * 0.014 + uF * 0.012, [(0, 0.010), (1, 0.009)],
                           lambda t, a: 2, segs=6))
    parts += strap_bms(pts, L, y0, top, H, W, cfg.get("straps", {}))
    bm = B.join_bms(parts)
    return B.rigid_object("Backpack", bm, "spine_03", arm, ["BAG", "RED", "METAL", "METAL_DARK"], mats, part="torso")


def strap_bms(pts, L, y0, top, H, W, sc):
    """cinghie dello zaino: dal davanti dello zaino sopra le spalle, giù sul petto e sotto l'ascella fino al fondo."""
    sh_z = L["clavicle_l"].z
    lift = sc.get("lift", 0.034)
    parts = []
    for sd, sx in SIDES:
        x0 = sx * sc.get("x", 0.085)
        ztop = surface_top(pts, x0, 0.0) or (sh_z + 0.05)
        z1, z2 = sh_z - 0.10, sh_z - 0.21
        yf1 = surface_y(pts, x0 * 1.15, z1) or -0.10
        yf2 = surface_y(pts, x0 * 1.45, z2) or -0.10
        side_x = max((abs(p.x) for p, b in pts if b in TORSO and abs(p.z - z2) < 0.03), default=0.16)
        P = [Vector((x0, y0 + 0.004, top - 0.05)),
             Vector((x0, 0.05, ztop + lift * 0.8)),
             Vector((x0 * 1.05, -0.03, ztop + lift * 0.6)),
             Vector((x0 * 1.15, yf1 - lift, z1)),
             Vector((x0 * 1.45, yf2 - lift * 0.9, z2)),
             Vector((sx * (side_x + lift * 0.7), 0.0, z2 - 0.03)),
             Vector((sx * min(side_x, W / 2 - 0.03), y0 + 0.004, top - H + 0.05))]
        N = []
        for p in P:
            cc = Vector((0.0, 0.0, min(p.z, sh_z - 0.06)))
            N.append((p - cc).normalized())
        parts.append(ribbon_bm(P, N, sc.get("w", 0.040), sc.get("t", 0.010), mat=0))
    return parts


# ============================================================== Totò adulto (2107)
def make_hood_up(B, arm, mats, L, pts, cfg):
    """cappuccio della felpa tirato su: guscio largo attorno alla testa, aperto davanti sul viso (dalla fronte
    alle guance), che scende sulla nuca e ai lati fino al collo; il bordo del viso è a costine (TOP_LINING)."""
    ez = L["eye_l"].z
    hc, rx, ry = head_section(pts, ez + 0.012)
    off = cfg.get("off", 0.030)
    cz = ez + cfg.get("cz", -0.004)
    R = (rx + off, ry + off + cfg.get("back", 0.012), L["crown_z"] - cz + off + cfg.get("peak", 0.008))
    center = Vector((0.0, hc.y + cfg.get("dy", 0.012), cz))
    fz, sz = cfg.get("front_z", 0.40), cfg.get("side_z", -1.2)
    a0, a1 = cfg.get("az", (36.0, 72.0))

    def keep(co):
        az = math.degrees(math.atan2(abs(co.x), -co.y))           # 0 davanti, 180 dietro
        return co.z > fz + (sz - fz) * smoothstep(a0, a1, az)
    bm = B.sphere_bm(center, R, mat=0, keep=keep, segs=48, rings=32)
    # da uovo a cappuccio: sotto le orecchie si allarga e scende sulle spalle e sulla nuca, dietro in alto
    # fa la punta della cucitura (dove le due metà si uniscono)
    flare, drop, point = cfg.get("flare", 0.45), cfg.get("drop", 0.05), cfg.get("point", 0.022)
    for v in bm.verts:
        r = v.co - center
        t = max(0.0, min(1.0, -r.z / R[2])) ** 1.5
        v.co.x = center.x + r.x * (1.0 + flare * t)
        if r.y > 0:
            v.co.y += r.y / R[1] * (flare * 0.5 * t * R[1] + point * max(0.0, r.z / R[2]))
        v.co.z -= drop * t
    for f in bm.faces:
        fc = f.calc_center_median() - center
        if abs(fc.x) < cfg.get("seam_w", 0.007) and fc.y > 0 and fc.z > -R[2] * 0.5:
            f.material_index = 2                                 # la cucitura al centro, dalla fronte alla nuca
    for f in bm.faces:
        if any(e.is_boundary for e in f.edges):
            fc = f.calc_center_median() - center
            if fc.y < 0 and fc.z > -R[2] * 0.55:                 # solo il bordo del viso, non il fondo dentro il collo
                f.material_index = 1
    ob = B.rigid_object("HoodUp", bm, "Head", arm, ["HOOD", "TOP_LINING", "HOOD_DARK", "HOOD_DARK", "HOOD_DARK"], mats,
                        part="head")
    sol = ob.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = cfg.get("thick", 0.012)
    sol.offset = -1.0
    sol.use_even_offset = False
    sol.use_quality_normals = True
    sol.material_offset = 2
    sol.material_offset_rim = 1
    return ob


def make_hoodie_front(B, arm, mats, L, pts, cfg, top_off):
    """la tasca a marsupio sulla pancia e i due cordini del cappuccio che pendono sul petto."""
    pz, sh_z = L["pelvis"].z, L["clavicle_l"].z
    parts = []
    pc = cfg.get("pocket", {})
    zc = pz + pc.get("dz", 0.10)
    ys = surface_y(pts, 0.0, zc) or -0.10
    w, h = pc.get("w", 0.21), pc.get("h", 0.12)
    parts.append(B.box_bm(Vector((0.0, ys - top_off - 0.004, zc)), (w, 0.010, h), bevel=0.004, mat=0, segs=1))
    for sx in (1.0, -1.0):                                       # le aperture ai lati, scure
        parts.append(B.box_bm(Vector((sx * (w / 2 - 0.012), ys - top_off - 0.010, zc + 0.01)),
                              (0.016, 0.004, h * 0.7), mat=1, segs=1))
    cc = cfg.get("cords", {})
    z0 = L["chin"].z + cc.get("dz", -0.035)
    for sx in (1.0, -1.0):
        x = sx * cc.get("x", 0.032)
        y0 = (surface_y(pts, x, z0) or -0.08) - top_off - 0.006
        z1 = z0 - cc.get("len", 0.15)
        y1 = (surface_y(pts, x, z1) or -0.10) - top_off - 0.006
        parts.append(B.tube_bm(Vector((x, y0, z0)), Vector((x * 1.1, y1, z1)), [(0, 0.0045), (1, 0.0045)],
                               lambda t, a: 2, segs=6))
        parts.append(B.tube_bm(Vector((x * 1.1, y1, z1)), Vector((x * 1.1, y1, z1 - 0.018)),
                               [(0, 0.006), (1, 0.006)], lambda t, a: 3, segs=6))
    bm = B.join_bms(parts)
    return B.rigid_object("HoodieFront", bm, "spine_02", arm, ["TOP", "TOP_DARK", "TOP_LINING", "METAL_DARK"],
                          mats, part="torso")


def make_zainetto(B, arm, mats, L, pts, cfg):
    """zainetto piccolo e morbido, macchiato di vernice (PATCH), con due bombolette che spuntano dalla patta."""
    import random
    rnd = random.Random(cfg.get("seed", 7))
    sh_z = L["clavicle_l"].z
    back_y = max(p.y for p, b in pts if b in ("spine_02", "spine_03") and abs(p.x) < 0.08)
    W, D, H = cfg.get("size", (0.27, 0.13, 0.33))
    top = sh_z + cfg.get("top_dz", -0.02)
    y0 = back_y + cfg.get("gap", 0.026)
    c = Vector((0.0, y0 + D / 2, top - H / 2))
    box = B.box_bm(c, (W, D, H), bevel=cfg.get("bevel", 0.045), mat=0, segs=3)
    stains = [Vector((rnd.uniform(-W / 2, W / 2), y0 + D, top - rnd.uniform(0.05, H - 0.04))) for _ in range(5)]
    for f in box.faces:
        fc = f.calc_center_median()
        if any((fc - s).length < rnd.uniform(0.022, 0.034) for s in stains):
            f.material_index = 1
    parts = [finish(box)]
    flap = B.box_bm(Vector((0.0, y0 + D / 2 + 0.004, top - 0.045)), (W * 0.9, D + 0.014, 0.10), bevel=0.03,
                    mat=0, segs=2)
    parts.append(finish(flap))
    for i, (x, tilt, mi) in enumerate(cfg.get("cans", [(-0.06, -0.12, 4), (0.035, 0.10, 1)])):
        a = Vector((x, y0 + D * 0.55, top - 0.07))
        b = a + Vector((tilt * 0.4, 0.01, 0.13))
        parts.append(B.tube_bm(a, b, [(0, 0.024), (1, 0.024)], lambda t, aa, mi=mi: mi, segs=12))
        d = (b - a).normalized()
        parts.append(B.tube_bm(b, b + d * 0.02, [(0, 0.016), (1, 0.010)], lambda t, aa: 2, segs=10))
        parts.append(B.tube_bm(b + d * 0.02, b + d * 0.032, [(0, 0.006), (1, 0.006)], lambda t, aa: 3, segs=6))
    parts += strap_bms(pts, L, y0, top, H, W, dict({"x": 0.075, "w": 0.032, "lift": 0.030}, **cfg.get("straps", {})))
    bm = B.join_bms(parts)
    return B.rigid_object("Zainetto", bm, "spine_03", arm, ["BAG", "PATCH", "METAL", "METAL_DARK", "RED"], mats,
                          part="torso")


def paint_flecks(shell, mats, cfg, L):
    """schizzi di vernice sulle maniche e sul davanti della felpa: facce a caso col materiale PATCH."""
    import random
    rnd = random.Random(cfg.get("seed", 11))
    me = shell.data
    me.materials.append(mats["PATCH"])
    mi = len(me.materials) - 1
    hz = L["hand_l"].z + 0.25
    for p in me.polygons:
        c = p.center
        near_hand = c.z < hz and abs(c.x) > 0.16
        if (near_hand and rnd.random() < cfg.get("sleeves", 0.07)) or (c.y < -0.05 and rnd.random() < cfg.get("front", 0.012)):
            p.material_index = mi


def make_kneepads(B, arm, mats, L, pts, cfg):
    """ginocchiere: piastra arrotondata davanti al ginocchio, legata allo stinco. Si appoggia sul punto più avanti
    della gamba sotto la piastra (rotula e stinco, pantaloni compresi): il raggio medio dell'arto la staccava,
    perché davanti lo stinco è più vicino all'asse del polpaccio dietro."""
    out = {}
    w, t, h = cfg.get("size", (0.12, 0.036, 0.14))
    down = cfg.get("down", 0.03)
    for sd, sx in SIDES:
        k, f = L["calf_" + sd], L["foot_" + sd]
        dshin = (f - k).normalized()
        fr = Vector((0, -1, 0))
        fr = (fr - dshin * fr.dot(dshin)).normalized()
        side = dshin.cross(fr).normalized()
        front = None
        for p, bn in pts:
            if not (bn and bn.startswith(("calf", "thigh")) and bn.endswith("_" + sd)):
                continue
            rel = p - k
            if abs(rel.dot(dshin) - down) < h / 2 and abs(rel.dot(side)) < w / 2:
                v = rel.dot(fr)
                front = v if front is None else max(front, v)
        if front is None:
            front = limb_radius(pts, "calf_" + sd, k, f, 0.06)
        c = k + dshin * down + fr * (front + cfg.get("gap", 0.002) + t / 2)
        R = mat_rows(side, fr, -dshin)
        pad = B.box_bm(c, (w, t, h), R=R, bevel=cfg.get("bevel", 0.016), mat=0, segs=2)
        out["pad_" + sd] = B.rigid_object("KneePad_" + sd, pad, "calf_" + sd, arm, ["PAD"], mats)
    return out


def make_rolled_sleeves(B, arm, mats, L, pts, cfg):
    """maniche arrotolate al gomito (esattore): rotolo di stoffa attorno al gomito, legato al braccio."""
    out = {}
    for sd, sx in SIDES:
        a, b = L["lowerarm_" + sd], L["hand_" + sd]
        r = limb_radius(pts, "lowerarm_" + sd, a, b, 0.08) + cfg.get("push", 0.006)
        d = (b - a)
        pa, pb = a + d * cfg.get("t0", -0.04), a + d * cfg.get("t1", 0.14)
        bm = B.tube_bm(pa, pb, [(0, r + 0.010), (0.5, r + 0.016), (1, r + 0.006)],
                       lambda t, an: 1 if (an == 999 or t > 0.8) else 0, segs=16, extra_ts=(0.8,))
        out["roll_" + sd] = B.rigid_object("SleeveRoll_" + sd, bm, "lowerarm_" + sd, arm, ["TOP_DARK", "TOP_LINING"],
                                           mats)
    return out


def make_moustache(B, arm, mats, L, cfg):
    nz = L["nose"]
    c = Vector((0.0, nz.y + cfg.get("dy", 0.010), nz.z - cfg.get("dz", 0.016)))
    bm = B.sphere_bm(c, tuple(cfg.get("r", (0.026, 0.009, 0.0075))), mat=0, segs=12, rings=6)
    return B.rigid_object("Moustache", bm, "Head", arm, ["BEARD"], mats, part="head")


def make_lanyard(B, arm, mats, L, pts, cfg, top_off):
    """cordino rosso dietro il collo, a V sul petto, col tesserino bianco in fondo."""
    sh_z = L["clavicle_l"].z
    nz = L["chin"].z + cfg.get("neck_dz", -0.045)
    zb = sh_z + cfg.get("badge_dz", -0.16)
    yb = (surface_y(pts, 0.0, zb) or -0.12) - top_off
    nk = L["neck_01"]
    back = surface_y(pts, 0.0, nz, front=False, bones=("neck_01", "spine_03")) or (nk.y + 0.05)
    parts = []
    for sd, sx in SIDES:
        zs = sh_z + 0.02
        ys = (surface_y(pts, sx * 0.075, zs) or -0.07) - top_off
        P = [Vector((0.0, back + top_off * 0.8, nz)),
             Vector((sx * 0.060, nk.y + 0.02, nz - 0.005)),
             Vector((sx * 0.075, ys, zs)),
             Vector((sx * 0.012, yb - 0.004, zb + 0.035))]
        N = [Vector((0, 1, 0.4)).normalized(), Vector((sx, 0.2, 0.6)).normalized(), Vector((sx * 0.4, -1, 0.3)).normalized(),
             Vector((0, -1, 0))]
        parts.append(ribbon_bm(P, N, cfg.get("w", 0.013), 0.004, mat=0))
    parts.append(B.box_bm(Vector((0.0, yb - 0.008, zb)), (0.046, 0.007, 0.062), bevel=0.003, mat=1, segs=1))
    return B.rigid_object("Lanyard", B.join_bms(parts), "spine_03", arm, ["RED", "PATCH"], mats, part="torso")


def make_tablet(B, arm, mats, L, cfg, hand_scale):
    """tablet robusto nella mano sinistra, stretto al petto nella posa ferma del messo (messo_idle/base): scritto nel
    riferimento del petto di quella posa e riportato a riposo sull'osso della mano."""
    M, chest = posed_bone(B, arm, cfg.get("keyset", "messo_idle"), cfg.get("key", "base"), "hand_l")
    hp = M.translation
    # assi del petto in posa: x a sinistra, y verso la schiena, z in alto (riferimento del corpo)
    cx, cy, cz = chest @ Vector((1, 0, 0)), chest @ Vector((0, 1, 0)), chest @ Vector((0, 0, 1))
    w, h, t = cfg.get("size", (0.19, 0.25, 0.018))
    tilt = math.radians(cfg.get("tilt_deg", 12.0))
    yaw = math.radians(cfg.get("yaw_deg", 10.0))
    R = Matrix.Rotation(yaw, 3, cz) @ Matrix.Rotation(tilt, 3, cx)
    ax, ay, az = R @ cx, R @ cy, R @ cz
    o = cfg.get("off", (-0.05, -0.02, 0.07))
    c = hp + ax * o[0] + ay * o[1] + az * o[2]
    bm = B.box_bm(c, (w, t, h), R=mat_rows(ax, ay, az), bevel=0.012, mat=0, segs=2)
    for f in bm.faces:
        if f.normal.dot(ay) > 0.9:                          # schermo, verso il petto (e verso il viso quando legge)
            f.material_index = 1
    finish(bm)
    to_rest(bm, arm, "hand_l", M, hand_scale)
    return B.rigid_object("Tablet", bm, "hand_l", arm, ["PAD", "SCREEN"], mats)


def make_laser_pen(B, arm, mats, L, cfg, hand_scale):
    """penna laser nella mano destra: nella posa del puntamento (messo_laser/point) prosegue l'avambraccio teso, con
    la punta rossa (GLOW_LINE: luce senza linee né ombre)."""
    M, chest = posed_bone(B, arm, cfg.get("keyset", "messo_laser"), cfg.get("key", "point"), "hand_r")
    lo, _ = posed_bone(B, arm, cfg.get("keyset", "messo_laser"), cfg.get("key", "point"), "lowerarm_r")
    d = (M.translation - lo.translation).normalized()
    _, u, wv = basis(d)
    start = M.translation + d * cfg.get("from", 0.030) + u * cfg.get("up", 0.010)
    ln, r = cfg.get("len", 0.15), cfg.get("r", 0.012)
    tip = cfg.get("tip", 0.022)
    bm = B.tube_bm(start, start + d * ln, [(0, r), (0.8, r), (1, r * 0.75)],
                   lambda t, a: 1 if t > 1 - tip / ln else 0, segs=10, extra_ts=(1 - tip / ln,))
    to_rest(bm, arm, "hand_r", M, hand_scale)
    return B.rigid_object("LaserPen", bm, "hand_r", arm, ["PAD", "GLOW_LINE"], mats)


# ============================================================== Vito (2064): i baffi
def solo_baffi(beard, L, cfg):
    """della barba restano solo i baffi: le facce sopra la bocca e sotto il naso, davanti, con le punte che
    scendono appena ai lati della bocca."""
    mo = L["mouth"]
    up, down, hw = cfg.get("up", 0.024), cfg.get("down", 0.004), cfg.get("half_w", 0.046)
    droop = cfg.get("droop", 0.014)
    bm = bmesh.new()
    bm.from_mesh(beard.data)
    via = []
    for f in bm.faces:
        c = f.calc_center_median()
        lo = mo.z - down - droop * max(0.0, min(1.0, (abs(c.x) - 0.018) / 0.02))
        if not (abs(c.x) < hw and lo < c.z < mo.z + up and c.y < mo.y + 0.02):
            via.append(f)
    bmesh.ops.delete(bm, geom=via, context="FACES")
    bm.to_mesh(beard.data)
    bm.free()


# ============================================================== Addolorata in casa (2087)
def make_skirt(B, arm, mats, L, pts, cfg):
    """la gonna dell'abito: anelli dalla vita all'orlo sotto il ginocchio, larghi quanto il bacino e le cosce più un
    margine, che si allargano appena verso il fondo. Pesata sul bacino in alto e sulle cosce in basso, così segue il
    passo senza staccarsi dalla vita."""
    pz = L["pelvis"].z
    knee = (L["calf_l"].z + L["calf_r"].z) / 2
    z0 = pz + cfg.get("top_dz", 0.04)
    z1 = knee + cfg.get("hem_dz", -0.09)
    gap, flare = cfg.get("gap", 0.014), cfg.get("flare", 0.05)
    n, segs = cfg.get("rings", 14), cfg.get("segs", 32)
    legs = ("pelvis", "thigh_l", "thigh_r", "calf_l", "calf_r")
    prof = []
    run = None
    for i in range(n):
        z = z0 + (z1 - z0) * i / (n - 1)
        sl = [p for p, b in pts if b in legs and abs(p.z - z) < 0.025] or [p for p, b in pts if b in legs]
        x = max(abs(p.x) for p in sl)
        y0, y1 = min(p.y for p in sl), max(p.y for p in sl)
        run = (x, y0, y1) if run is None else (max(run[0], x), min(run[1], y0), max(run[2], y1))
        prof.append((z, run))
    bm = bmesh.new()
    rings = []
    for i, (z, (x, y0, y1)) in enumerate(prof):
        t = i / (n - 1)
        rx = x + gap + flare * t * t
        ry = (y1 - y0) / 2 + gap + flare * 0.8 * t * t
        rings.append(ring_verts(bm, Vector((0.0, (y0 + y1) / 2, z)), Vector((0, 0, -1)), rx, ry, n=segs))
    for i in range(n - 1):
        bridge(bm, rings[i], rings[i + 1], 0)
    finish(bm)
    sx_l = 1.0 if L["thigh_l"].x > 0 else -1.0

    def weights(co):
        t = max(0.0, min(1.0, (z0 - co.z) / max(z0 - z1, 1e-3)))
        leg = min(0.85, 1.2 * t)
        a = max(0.0, min(1.0, 0.5 + co.x * sx_l / 0.10))   # 1 tutto sinistra, 0 tutto destra
        return {"pelvis": 1.0 - leg, "thigh_l": leg * a, "thigh_r": leg * (1.0 - a)}
    ob = B.skinned_object("Skirt", bm, weights, arm, ["PANTS"], mats, lambda c: "torso")
    sol = ob.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = cfg.get("thick", 0.008)
    sol.offset = 1.0
    sol.use_even_offset = False
    return ob


def make_sarta(B, arm, mats, L, pts, cfg, top_off):
    """il metro da sarta giallo dietro il collo, che pende sui due lati del petto; gli occhiali da vista chiusi,
    appesi al cordino scuro a metà petto; i bottoni del cardigan sotto la V."""
    sh_z = L["clavicle_l"].z
    nz = L["chin"].z + cfg.get("neck_dz", -0.040)
    nk = L["neck_01"]
    back = surface_y(pts, 0.0, nz, front=False, bones=("neck_01", "spine_03")) or (nk.y + 0.05)
    parts = []
    # metro: dietro il collo, sopra le spalle, giù dritto sul petto
    mc = cfg.get("metro", {})
    mx, mlen, mw = mc.get("x", 0.062), mc.get("len", 0.25), mc.get("w", 0.018)
    for sd, sx in SIDES:
        zs = sh_z + 0.03
        ys = (surface_y(pts, sx * mx, zs) or -0.07) - top_off - 0.004
        P = [Vector((0.0, back + top_off, nz + 0.005)), Vector((sx * 0.055, nk.y + 0.025, nz)),
             Vector((sx * mx, ys, zs))]
        for k in (1, 2, 3):
            z = zs - mlen * k / 3
            P.append(Vector((sx * (mx + 0.004 * k), (surface_y(pts, sx * mx, z) or -0.10) - top_off - 0.004, z)))
        N = [Vector((0, 1, 0.4)).normalized(), Vector((sx, 0.2, 0.6)).normalized()] + [Vector((0, -1, 0))] * 4
        parts.append(ribbon_bm(P, N, mw, 0.0025, mat=0))
    # cordino e occhiali
    oc = cfg.get("occhiali", {})
    zg = sh_z + oc.get("dz", -0.13)
    yg = (surface_y(pts, 0.0, zg) or -0.11) - top_off - oc.get("gap", 0.010)
    for sd, sx in SIDES:
        zs = sh_z + 0.015
        ys = (surface_y(pts, sx * 0.050, zs) or -0.07) - top_off - 0.008
        P = [Vector((0.0, back + top_off * 0.9, nz - 0.004)), Vector((sx * 0.050, nk.y + 0.02, nz - 0.008)),
             Vector((sx * 0.050, ys, zs)), Vector((sx * 0.030, yg, zg + 0.012))]
        N = [Vector((0, 1, 0.4)).normalized(), Vector((sx, 0.2, 0.6)).normalized(),
             Vector((sx * 0.3, -1, 0.3)).normalized(), Vector((0, -1, 0))]
        parts.append(ribbon_bm(P, N, 0.004, 0.003, mat=1))
    lr, lw = oc.get("r", 0.019), oc.get("filo", 0.0028)
    tilt = math.radians(oc.get("tilt_deg", 12.0))
    for sx in (1.0, -1.0):
        c = Vector((sx * oc.get("x", 0.024), yg, zg))
        lens = torus_bm(c, lr, lw, segs=18, tsegs=6, mat=2)
        bmesh.ops.rotate(lens, verts=lens.verts, cent=c, matrix=Matrix.Rotation(math.radians(90) - tilt, 3, "X"))
        bmesh.ops.scale(lens, verts=lens.verts, vec=(1.0, 1.0, 0.8), space=Matrix.Translation(-c))
        parts.append(lens)
        parts.append(B.sphere_bm(c, (lr * 0.95, 0.002, lr * 0.76), mat=3, segs=14, rings=6))
    parts.append(B.tube_bm(Vector((0.006, yg, zg + 0.004)), Vector((-0.006, yg, zg + 0.004)), [(0, lw), (1, lw)],
                           lambda t, a: 2, segs=6))
    # bottoni del cardigan
    bc = cfg.get("bottoni", {})
    for k in range(bc.get("n", 4)):
        z = sh_z + bc.get("z0", -0.28) - k * bc.get("passo", 0.075)
        y = (surface_y(pts, 0.0, z) or -0.10) - top_off - bc.get("fuori", 0.010)
        parts.append(B.sphere_bm(Vector((0.0, y, z)), (0.009, 0.005, 0.009), mat=4, segs=8, rings=4))
    bm = B.join_bms(parts)
    return B.rigid_object("Sarta", bm, "spine_03", arm, ["PATCH", "METAL_DARK", "METAL", "LENS", "BELT"], mats,
                          part="torso")


# ============================================================== giacca e pettorina (guscio dal corpo)
def make_top(B, body, fb, L, pts, mats, cfg, kind):
    """giacca a maniche lunghe (rider, messo) o pettorina senza maniche (esattore), copiata dalle facce del busto e
    delle braccia, con polsini e orlo a costine (TOP_LINING), profili e strisce catarifrangenti (REFLECT),
    l'emblema di SIDERA (RED), e l'interno scuro (TOP_DARK) dato dallo spessore."""
    sleeves = kind != "esattore"
    hem_z = cfg["hem_z"]
    cuff_t = cfg.get("cuff_t", 0.84)
    sh_z = L["clavicle_l"].z
    sw = L["upperarm_l"].x
    collar_z = L["chin"].z + cfg.get("collar_dz", -0.014)
    vn = cfg.get("vneck")

    def in_v(c):
        if not vn or c.y > -0.015:
            return False
        z0, z1 = sh_z + vn["z0"], collar_z + 0.02
        if c.z < z0:
            return False
        u = min(1.0, (c.z - z0) / max(z1 - z0, 1e-3))
        return abs(c.x) < 0.004 + vn["w"] * u

    def keep(p, bone):
        c = p.center
        part = B.bone_part(bone)
        if bone in TORSO:
            k = True
            if not sleeves and abs(c.x) / sw > cfg.get("armhole", 0.66) and c.z > sh_z - cfg.get("armhole_depth", 0.16):
                k = False
        elif bone == "pelvis":
            k = c.z > hem_z and not (abs(c.x) < 0.075 and c.z < 1.0 and p.normal.z < -0.25)
        elif bone == "neck_01":
            k = c.z < collar_z
        elif part.startswith("upperarm"):
            k = sleeves
        elif part.startswith("lowerarm"):
            sd = part[-1]
            k = sleeves and B.arm_t(c, L["lowerarm_" + sd], L["hand_" + sd]) < cuff_t
        else:
            k = False
        return k and not in_v(c)

    base = cfg.get("offset", 0.020)

    def off(v, dom):
        o = base
        if dom == "neck_01":
            o += cfg.get("neck_off", 0.008)
        if dom and dom.startswith(("upperarm", "lowerarm")):
            o += cfg.get("sleeve_gap", -0.004)
        return o
    shell, bm, dl, names = B.shell_from_body(body, fb, keep, "Shirt", off, smooth_iters=cfg.get("smooth_iters", 12))
    keep_clear(B, bm, body, cfg.get("min_gap", 0.012))
    if cfg.get("edge_smooth", 6):
        smooth_boundary(bm, cfg.get("edge_smooth", 6))
    bnd = [e for e in bm.edges if e.is_boundary]
    hem = [e for e in bnd if all(v.co.z < hem_z + 0.03 for v in e.verts)]
    for v in {v for e in hem for v in e.verts}:
        v.co.z = hem_z - 0.004
    lining = []
    if cfg.get("hem_band", 0.0) > 0 and hem:
        nv = B.extrude_weighted(bm, hem, dl)
        for v in nv:
            radial = Vector((v.co.x, v.co.y - 0.01, 0.0))
            radial = radial.normalized() if radial.length > 1e-6 else Vector()
            v.co += Vector((0, 0, -cfg["hem_band"])) - radial * cfg.get("hem_in", 0.006)
        lining += nv
    if sleeves:
        for sd in "lr":
            a, b = L["lowerarm_" + sd], L["hand_" + sd]
            axis = (b - a)
            ln = axis.length
            axis = axis.normalized()
            ends = set()
            for e in bm.edges:
                if not e.is_boundary:
                    continue
                for v in e.verts:
                    if (B.bm_dom(v, dl, names) or "").endswith("arm_" + sd) and abs(B.arm_t(v.co, a, b) - cuff_t) < 0.25:
                        ends.add(v)
            for v in ends:
                v.co += axis * (cuff_t * ln - (v.co - a).dot(axis))
            ed = [e for e in bm.edges if e.is_boundary and all(v in ends for v in e.verts)]
            if not ed:
                B.log("!! polsino non trovato", sd)
                continue
            nv = B.extrude_weighted(bm, ed, dl)
            for v in nv:
                ctr = a + axis * (v.co - a).dot(axis)
                rad = (v.co - ctr)
                rad = rad.normalized() if rad.length > 1e-6 else UP
                v.co += axis * cfg.get("cuff_w", 0.036) - rad * cfg.get("cuff_in", 0.004)
            lining += nv
    lin_co = {tuple(round(x, 5) for x in v.co) for v in lining}
    stripes = cfg.get("stripes", {})
    pz = L["pelvis"].z
    for fz, hb in stripes.get("bands", []):
        zz = pz + fz * (sh_z - pz)
        cut_z(bm, zz - hb)
        cut_z(bm, zz + hb)
    bm.normal_update()
    bm.to_mesh(shell.data)
    bm.free()
    B.shade_smooth(shell)
    me = shell.data
    sb = B.face_bones(shell)
    em = cfg.get("emblem")
    reg, parts = [], []
    for p, bone in zip(me.polygons, sb):
        c, n = p.center, p.normal
        part = B.bone_part(bone)
        r = "TOP"
        if sum(1 for vi in p.vertices if tuple(round(x, 5) for x in me.vertices[vi].co) in lin_co) >= 2:
            r = "TOP_LINING"
        elif part.startswith(("upperarm", "lowerarm")):
            if stripes.get("sleeve_cos"):                     # le bande del busto non passano sulle maniche
                sd = part[-1]
                sx = 1.0 if sd == "l" else -1.0
                a, b = (L["upperarm_" + sd], L["lowerarm_" + sd]) if part.startswith("upper") \
                    else (L["lowerarm_" + sd], L["hand_" + sd])
                d = (b - a).normalized()
                outer = UP + Vector((sx, 0, 0))
                outer = (outer - d * outer.dot(d)).normalized()
                rv = c - (a + d * (c - a).dot(d))
                if rv.length > 1e-6 and rv.normalized().dot(outer) > stripes["sleeve_cos"]:
                    r = "REFLECT"
        else:
            for fz, hb in stripes.get("bands", []):
                zz = pz + fz * (sh_z - pz)                    # frazione del busto: 0 bacino, 1 spalle
                if abs(c.z - zz) < hb and c.y < stripes.get("band_max_y", 1.0):
                    r = "REFLECT"
            if em and c.y < 0 and (Vector((c.x, c.z)) - Vector((em["x"], sh_z + em["dz"]))).length < em["r"]:
                r = "RED"
        reg.append(r)
        parts.append(part)
    order = ["TOP", "TOP_LINING", "REFLECT", "RED", "TOP_DARK", "TOP_DARK", "TOP_DARK", "TOP_DARK"]
    me.materials.clear()
    for r in order:
        me.materials.append(mats[r])
    for p, r in zip(me.polygons, reg):
        p.material_index = order.index(r)
    B.set_part_attr(shell, parts)
    sol = shell.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = cfg.get("thick", 0.010)
    sol.offset = -1.0
    sol.use_even_offset = False
    sol.use_quality_normals = True
    sol.material_offset = 4
    sol.material_offset_rim = 4
    return shell


# ============================================================== principale
def build(ns, ctx, kind):
    B = types.SimpleNamespace(**ns)
    arm, body, eyes, brows, hairs, mats, cfg = ctx["arm"], ctx["body"], ctx["eyes"], ctx["brows"], ctx["hair"], \
        ctx["mats"], ctx["outfit"]
    props = ctx.get("proportions", {})
    L = B.landmarks(arm, body, eyes)
    for ob in [body, eyes, brows] + list(hairs.values()):
        B.to_world(ob)
    B.merge_doubles(body)
    B.shade_smooth(body)
    fb = B.face_bones(body)
    pz = L["pelvis"].z
    sh_z = L["clavicle_l"].z
    ey = L["eye_l"]
    tcfg = cfg.get("top", {})
    hem_z = pz + tcfg.get("hem_dz", 0.05)
    tcfg = dict(tcfg, hem_z=hem_z)
    collar_z = L["chin"].z + tcfg.get("collar_dz", -0.014)
    pstripe = cfg.get("pants_stripe_cos", 0.0)
    vn = tcfg.get("vneck")

    def rule(p, bone, part):
        c, n = p.center, p.normal
        if part == "head":
            if bone == "Head":
                f = B.face_features(c, n, L)
                if f:
                    return f
                if kind in ("rider", "toto") and (c.z > ey.z + 0.022 or (c.z > ey.z - 0.04 and c.y > ey.y + 0.035)):
                    return "HAIR"                              # sotto il casco (o il cappuccio), basette e nuca
                return "SKIN"
            if kind == "messo" and c.z < collar_z + 0.006:
                return "COLLAR"                                # colletto della camicia
            if kind == "addolorata" and c.z < collar_z + 0.006:
                return "PANTS"                                 # scollo dell'abito
            return "SKIN"
        if part in ("hand_l", "hand_r"):
            return None
        if kind == "mimmo" and part == "lowerarm_r" and cfg.get("cyber") is not False:
            return "METAL_DARK"                                # sotto la corazza del MANODOPERA
        if part in ("foot_l", "foot_r"):
            return None                                        # dentro le scarpe
        if part.startswith("upperarm"):
            return "TOP_DARK" if kind == "esattore" else "TOP"
        if part.startswith("lowerarm"):
            return "SKIN" if kind == "esattore" else "TOP"
        if bone in TORSO:
            if kind in ("messo", "addolorata") and vn and c.y < -0.015 and c.z > sh_z + vn["z0"] - 0.01:
                u = min(1.0, (c.z - (sh_z + vn["z0"])) / max(collar_z + 0.02 - (sh_z + vn["z0"]), 1e-3))
                if abs(c.x) < 0.016 + vn["w"] * max(u, 0.0):   # solo nella V della giacca, con un margine
                    if kind == "addolorata":
                        return "PANTS"                         # l'abito nella V del cardigan
                    if abs(c.x) < vn.get("tie_w", 0.009) and c.z < collar_z - 0.004:
                        return "BELT"                          # cravatta
                    return "COLLAR"                            # camicia bianca nella V
            return "TOP_DARK" if kind == "esattore" else "TOP"
        if bone == "pelvis":
            if c.z > hem_z + 0.02:
                return "TOP_DARK" if kind == "esattore" else "TOP"
            if c.z > pz + 0.020:
                return "BELT"
            return "PANTS"
        if part.startswith(("thigh", "calf")):
            sx = 1.0 if bone.endswith("_l") else -1.0
            if pstripe and n.x * sx > pstripe:
                return "REFLECT"                               # striscia della tuta
            if kind == "addolorata" and part.startswith("calf"):
                return "PANTS_FOLD"                            # calze velate sotto l'orlo
            if kind == "esattore" and part.startswith("thigh") and abs(c.x) > 0.10 \
                    and abs(c.z - (pz - 0.30)) < 0.06 and c.y > -0.03:
                return "PANTS_FOLD"                            # tasconi laterali
            return "PANTS"
        return "PANTS"
    regions, parts, drop = B.body_regions(body, L, fb, rule)

    pcfg = cfg.get("push_body", {})
    belly = pcfg.get("belly", 0.0)
    bz0, bz1 = pcfg.get("belly_z", (0.98, 1.22))
    belly_hw = pcfg.get("belly_hw", 0.15)

    def push(b, co):
        o = 0.0
        if b and b.startswith(("thigh", "calf")):
            o = cfg.get("pants_push", 0.010)
        elif b == "pelvis" and co.z < pz + 0.02:
            o = cfg.get("pants_push", 0.010) * 0.8
        elif b in ("spine_01", "spine_02", "spine_03") or (b == "pelvis" and co.z >= pz + 0.02):
            o = cfg.get("top_push", 0.006)
        if belly and b in ("pelvis", "spine_01", "spine_02") and co.y < -0.03 and bz0 < co.z < bz1:
            u = (co.z - bz0) / (bz1 - bz0)
            o += belly * math.sin(math.pi * u) * max(0.0, 1.0 - abs(co.x) / belly_hw)
        return o
    B.push_body(body, push)
    pts = body_points(B, body)

    objs = dict(body=body, brows=brows, eyes=eyes)
    objs["shirt"] = make_top(B, body, fb, L, pts, mats, tcfg, kind)
    bcfg = dict(cfg.get("boots", {}))
    bcfg.pop("style", None)
    import char_boots
    boots = char_boots.make_boots_v7(body, arm, mats, L, bcfg, B.rigid_object, B.skinned_object, B.set_part_attr, B.link)
    if len(boots) == 2:
        objs["boots_l"], objs["boots_r"] = boots
    else:
        for i, o in enumerate(boots):
            objs["boot%d" % i] = o
    B.make_brows(brows, mats, L, bushy=cfg.get("brow_bushy", 1.5), lift=cfg.get("brow_lift", 0.0))
    B.make_eyes(eyes, arm, mats, L, glow_side=None)
    top_off = tcfg.get("offset", 0.020) + tcfg.get("thick", 0.010) * 0.2
    fist_bare = ["SKIN", "KNUCKLE", "SKIN", "SKIN", "SKIN_DARK", "SKIN", "TOP_LINING"]
    hs_l = props.get("hand_l", {}).get("scale", [1.0])[0]
    hs_r = props.get("hand_r", {}).get("scale", [1.0])[0]
    if kind == "rider":
        objs["helmet"] = make_helmet(B, arm, mats, L, pts, cfg.get("helmet", {}))
        gcfg = dict(cfg.get("goggles", {}))
        gcfg.setdefault("strap_out", cfg.get("helmet", {}).get("off", 0.016) + 0.004)
        gcfg.setdefault("strap_z_back", 0.022)
        objs["goggles"] = make_goggles(B, arm, mats, L, pts, gcfg, "LENS_TINT")
        objs["gaiter"] = make_gaiter(B, arm, mats, L, pts, cfg.get("gaiter", {}))
        objs["backpack"] = make_backpack(B, arm, mats, L, pts, cfg.get("backpack", {}))
        objs["fist_l"] = B.make_fist("l", arm, mats, L, fist_bare)
        objs["fist_r"] = B.make_fist("r", arm, mats, L, fist_bare)
    elif kind == "esattore":
        objs["goggles"] = make_goggles(B, arm, mats, L, pts, cfg.get("goggles", {}), "LENS")
        if "Hair_Beard" in hairs:
            objs["beard"] = B.make_beard(hairs["Hair_Beard"], mats, L, length=cfg.get("beard_len", 0.55), thick=0.007)
        glove = ["WRAP", "KNUCKLE", "SKIN", "WRAP", "SKIN_DARK", "SKIN", "WRAP"]
        objs["fist_l"] = B.make_fist("l", arm, mats, L, glove)
        objs["fist_r"] = B.make_fist("r", arm, mats, L, glove)
        objs.update(make_kneepads(B, arm, mats, L, pts, cfg.get("kneepads", {})))
        objs.update(make_rolled_sleeves(B, arm, mats, L, pts, cfg.get("rolled", {})))
    elif kind == "addolorata":
        objs["skirt"] = make_skirt(B, arm, mats, L, pts, cfg.get("skirt", {}))
        objs["sarta"] = make_sarta(B, arm, mats, L, pts, cfg.get("sarta", {}), top_off)
        hn = cfg.get("hair_mesh", "Hair_SimpleParted")
        if hn in hairs:
            objs["hair"] = B.make_hair_cap(hairs[hn], mats, L, push=cfg.get("hair_push", 0.003))
        objs["bun"] = B.make_topknot(arm, mats, L, cfg.get("bun", {}))
        objs["fist_l"] = B.make_fist("l", arm, mats, L, fist_bare)
        objs["fist_r"] = B.make_fist("r", arm, mats, L, fist_bare)
    elif kind == "mimmo":
        if cfg.get("cappuccio_su"):                            # i sonnambuli: cappuccio su
            objs["hood"] = make_hood_up(B, arm, mats, L, pts, cfg.get("hood", {}))
        else:
            objs["hood"] = B.make_hood_roll(arm, mats, L, cfg.get("hood", {}))
        if cfg.get("filtro") is not False:                     # Vito (2064) non ha il filtro
            objs["filtro"] = make_gaiter(B, arm, mats, L, pts, cfg.get("filtro", {}), mat="PAD")
        if "Hair_Buzzed" in hairs:
            objs["hair"] = B.make_hair_cap(hairs["Hair_Buzzed"], mats, L, push=0.004)
        if "Hair_Beard" in hairs:
            objs["beard"] = B.make_beard(hairs["Hair_Beard"], mats, L, length=cfg.get("beard_len", 0.2),
                                         thick=cfg.get("beard_thick", 0.004))
            if cfg.get("baffi"):
                solo_baffi(hairs["Hair_Beard"], L, cfg["baffi"])
        if cfg.get("cyber") is False:                          # Vito: niente MANODOPERA, due mani vere
            objs["fist_r"] = B.make_fist("r", arm, mats, L, fist_bare)
        else:
            for i, o in enumerate(B.make_cyber_arm(arm, mats, L, cfg.get("cyber", {"upper": False}), side="r")):
                objs["cyber%d" % i] = o
            objs["fist_r"] = B.make_fist("r", arm, mats, L, ["METAL_LIGHT", "METAL_SEAM", "METAL", "METAL_LIGHT",
                                                             "METAL_SEAM", "METAL", "METAL_DARK"])
        objs["fist_l"] = B.make_fist("l", arm, mats, L, fist_bare)
        if cfg.get("toppa"):                                   # Vito: la toppa del nome, vuota, a sinistra sul petto
            tc = cfg["toppa"]
            sx_l = 1.0 if L["thigh_l"].x > 0 else -1.0
            tx, tz = sx_l * tc.get("x", 0.075), L["clavicle_l"].z + tc.get("dz", -0.10)
            ty = (surface_y(pts, tx, tz) or -0.11) - top_off - 0.004
            objs["toppa"] = B.rigid_object("Toppa", B.sphere_bm(Vector((tx, ty, tz)), (tc.get("w", 0.036), 0.003,
                                                                                    tc.get("h", 0.016)),
                                                                mat=0, segs=8, rings=4),
                                           "spine_03", arm, ["PATCH"], mats, part="torso")
    elif kind == "toto":
        objs["hood"] = make_hood_up(B, arm, mats, L, pts, cfg.get("hood", {}))
        objs["hoodie_front"] = make_hoodie_front(B, arm, mats, L, pts, cfg.get("hoodie", {}), top_off)
        objs["zainetto"] = make_zainetto(B, arm, mats, L, pts, cfg.get("zainetto", {}))
        paint_flecks(objs["shirt"], mats, cfg.get("flecks", {}), L)
        if "Hair_Buzzed" in hairs:
            hc = cfg.get("hair", {})
            cy, ez = hc.get("cut_y", -0.02), ey.z + hc.get("cut_above_eye", 0.03)
            objs["hair"] = B.make_hair_cap(hairs["Hair_Buzzed"], mats, L, push=0.004,
                                           front_cut=lambda c: c.y < cy and c.z > ez)
        if "Hair_Beard" in hairs:
            objs["beard"] = B.make_beard(hairs["Hair_Beard"], mats, L, length=cfg.get("beard_len", 0.35),
                                         thick=cfg.get("beard_thick", 0.005))
        paint = ["SKIN", "PATCH", "SKIN", "SKIN", "SKIN_DARK", "SKIN", "TOP_LINING"]   # nocche sporche di vernice
        objs["fist_l"] = B.make_fist("l", arm, mats, L, paint)
        objs["fist_r"] = B.make_fist("r", arm, mats, L, paint)
    else:
        objs["goggles"] = make_goggles(B, arm, mats, L, pts, cfg.get("goggles", {}), "LENS")
        if "Hair_Buzzed" in hairs:
            hc = cfg.get("hair", {})
            cy, ez = hc.get("cut_y", -0.02), ey.z + hc.get("cut_above_eye", 0.03)
            objs["hair"] = B.make_hair_cap(hairs["Hair_Buzzed"], mats, L, push=0.004,
                                           front_cut=lambda c: c.y < cy and c.z > ez)
        objs["moustache"] = make_moustache(B, arm, mats, L, cfg.get("moustache", {}))
        objs["fist_l"] = B.make_fist("l", arm, mats, L, fist_bare)
        objs["fist_r"] = B.make_fist("r", arm, mats, L, fist_bare)
        objs["lanyard"] = make_lanyard(B, arm, mats, L, pts, cfg.get("lanyard", {}), top_off)
        objs["tablet"] = make_tablet(B, arm, mats, L, cfg.get("tablet", {}), hs_l)
        objs["pen"] = make_laser_pen(B, arm, mats, L, cfg.get("pen", {}), hs_r)
    regions, parts = B.drop_faces(body, regions, parts, drop)
    B.assign_mats(body, regions, mats)
    B.set_part_attr(body, parts)
    return objs, L
