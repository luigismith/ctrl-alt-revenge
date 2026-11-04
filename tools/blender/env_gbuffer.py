# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - sfondi e oggetti di scena: costruzione di una scena da un JSON e render del G-buffer.

Deriva dalla prova spike-env (env_build.py). La scena è descritta per intero da un file di lavoro JSON
scritto da tools/env/layout.py (codice Python MIT): qui non c'è nessuna scelta artistica, solo geometria.

  blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python env_gbuffer.py -- JOB.json

Sistema di riferimento (metri): X lungo la strada (verso destra sullo schermo), Y profondità (lontano
dalla telecamera), Z in alto. Telecamera ortografica di tre quarti, la stessa dei personaggi
(tools/sprites/camera.json: yaw 30, pitch 12, 48 px/m), con supersampling ss. L'immagine viene poi
inclinata in verticale (shear k = tan(yaw)·sin(pitch)) nel post-processo, così la strada è orizzontale.

Passate (PNG RGBA 8 bit, vista "Raw", nessun anti-aliasing, alfa = copertura):
  alb  colore base (sRGB 0..1 scritto così com'è)
  nrm  R,G = 0.5 + 0.5 * normale x,y nello spazio telecamera; B = classe / 255
  oid  R,G = indice dell'oggetto (16 bit); B = id del materiale / 255
  emi  colore emissivo (neon, finestre accese, lampade), nero altrove
  pxy  R,G = X quantizzata (16 bit); B = byte alto di Y
  pyz  R = byte basso di Y; G,B = Z quantizzata (16 bit)
La posizione è quantizzata in [P0, P0 + SPAN] su 65535 passi.

Tipi di oggetto nel JSON: box, mesh, cyl, tube, kit, fence (rete metallica a maglie romboidali).
Ogni oggetto ha cls (classe numerica), mat (id materiale), alb ([r,g,b] 0..1), emi (opzionale).
"""
import json
import math
import os
import sys
import zlib

import bmesh
import bpy
from mathutils import Matrix, Vector

PASSES = ["alb", "nrm", "oid", "emi", "pxy", "pyz"]


# ------------------------------------------------------------------ utilità
def argv_job():
    argv = sys.argv[sys.argv.index("--") + 1:]
    with open(argv[0], encoding="utf-8") as fh:
        return json.load(fh)


def link(ob, coll):
    coll.objects.link(ob)
    return ob


# ------------------------------------------------------------------ materiale G-buffer
class GBuf:
    """Un solo node group condiviso: il valore PASS sceglie quale passata esce dall'emissione."""

    def __init__(self, p0, span):
        self.group = self._build(p0, span)
        self.cache = {}

    def _build(self, p0, span):
        g = bpy.data.node_groups.new("GBUF", "ShaderNodeTree")
        io = g.interface
        for nm, tp in (("CLS", "NodeSocketFloat"), ("MAT", "NodeSocketFloat"), ("ALB", "NodeSocketColor"),
                       ("EMI", "NodeSocketColor")):
            io.new_socket(nm, in_out="INPUT", socket_type=tp)
        io.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
        N, L = g.nodes, g.links
        gi = N.new("NodeGroupInput")
        go = N.new("NodeGroupOutput")

        def value(name, v):
            n = N.new("ShaderNodeValue")
            n.name = n.label = name
            n.outputs[0].default_value = v
            return n.outputs[0]

        def m(op, a, b=None, c=None):
            n = N.new("ShaderNodeMath")
            n.operation = op
            for i, x in enumerate((a, b, c)):
                if x is None:
                    continue
                if isinstance(x, (int, float)):
                    n.inputs[i].default_value = float(x)
                else:
                    L.new(x, n.inputs[i])
            return n.outputs[0]

        def sep_rgb(sock):
            n = N.new("ShaderNodeSeparateColor")
            L.new(sock, n.inputs[0])
            return n.outputs[0], n.outputs[1], n.outputs[2]

        def sep_xyz(sock):
            n = N.new("ShaderNodeSeparateXYZ")
            L.new(sock, n.inputs[0])
            return n.outputs[0], n.outputs[1], n.outputs[2]

        PASS = value("PASS", 0.0)
        oi = N.new("ShaderNodeObjectInfo")
        geo = N.new("ShaderNodeNewGeometry")
        vt = N.new("ShaderNodeVectorTransform")
        vt.vector_type = "NORMAL"
        vt.convert_from = "WORLD"
        vt.convert_to = "CAMERA"
        L.new(geo.outputs["Normal"], vt.inputs[0])
        nx, ny, _nz = sep_xyz(vt.outputs[0])
        px, py, pz = sep_xyz(geo.outputs["Position"])
        ar, ag, ab = sep_rgb(gi.outputs["ALB"])
        er, eg, eb = sep_rgb(gi.outputs["EMI"])
        idx = oi.outputs["Object Index"]
        idx_hi = m("FLOOR", m("DIVIDE", idx, 256.0))
        idx_lo = m("SUBTRACT", idx, m("MULTIPLY", idx_hi, 256.0))

        def quant(p, p0_, sp):
            t = m("MINIMUM", m("MAXIMUM", m("DIVIDE", m("SUBTRACT", p, p0_), sp), 0.0), 1.0)
            q = m("FLOOR", m("ADD", m("MULTIPLY", t, 65535.0), 0.5))
            hi = m("FLOOR", m("DIVIDE", q, 256.0))
            lo = m("SUBTRACT", q, m("MULTIPLY", hi, 256.0))
            return m("DIVIDE", hi, 255.0), m("DIVIDE", lo, 255.0)

        xh, xl = quant(px, p0[0], span)
        yh, yl = quant(py, p0[1], span)
        zh, zl = quant(pz, p0[2], span)
        half = lambda s: m("MULTIPLY_ADD", s, 0.5, 0.5)
        chans = {
            0: (ar, ag, ab),
            1: (half(nx), half(ny), m("DIVIDE", gi.outputs["CLS"], 255.0)),
            2: (m("DIVIDE", idx_hi, 255.0), m("DIVIDE", idx_lo, 255.0), m("DIVIDE", gi.outputs["MAT"], 255.0)),
            3: (er, eg, eb),
            4: (xh, xl, yh),
            5: (yl, zh, zl),
        }
        outs = []
        for c in range(3):
            acc = None
            for p, vals in chans.items():
                sel = m("COMPARE", PASS, float(p), 0.25)
                term = m("MULTIPLY", sel, vals[c])
                acc = term if acc is None else m("ADD", acc, term)
            outs.append(acc)
        cc = N.new("ShaderNodeCombineColor")
        for c in range(3):
            L.new(outs[c], cc.inputs[c])
        em = N.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 1.0
        L.new(cc.outputs[0], em.inputs["Color"])
        L.new(em.outputs[0], go.inputs["Shader"])
        return g

    def material(self, cls, mat, alb, emi):
        key = (int(cls), int(mat), tuple(round(float(c), 4) for c in alb), tuple(round(float(c), 4) for c in emi))
        if key in self.cache:
            return self.cache[key]
        mt = bpy.data.materials.new("GB_%d" % len(self.cache))
        mt.use_nodes = True
        nt = mt.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        gn = nt.nodes.new("ShaderNodeGroup")
        gn.node_tree = self.group
        gn.inputs["CLS"].default_value = float(cls)
        gn.inputs["MAT"].default_value = float(mat)
        gn.inputs["ALB"].default_value = (*key[2], 1.0)
        gn.inputs["EMI"].default_value = (*key[3], 1.0)
        nt.links.new(gn.outputs["Shader"], out.inputs["Surface"])
        self.cache[key] = mt
        return mt

    def set_pass(self, p):
        self.group.nodes["PASS"].outputs[0].default_value = float(p)


# ------------------------------------------------------------------ geometria procedurale
def mesh_from_bm(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def box_bm(size, at, rz=0.0, bevel=0.0):
    """Parallelepipedo: 'at' = angolo minimo (x, y, z) prima della rotazione attorno a Z (sull'angolo)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = size
    for v in bm.verts:
        v.co.x = (v.co.x + 0.5) * sx
        v.co.y = (v.co.y + 0.5) * sy
        v.co.z = (v.co.z + 0.5) * sz
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=1, affect="EDGES")
    M = Matrix.Translation(Vector(at)) @ Matrix.Rotation(math.radians(rz), 4, "Z")
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    return bm


def cyl_bm(c, r, h, n=12, axis="z", r2=None, caps=True):
    """Cilindro (o tronco di cono se r2) con base centrata in c, lungo l'asse dato."""
    bm = bmesh.new()
    r2 = r if r2 is None else r2
    ring0, ring1 = [], []
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        ring0.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0.0)))
        ring1.append(bm.verts.new((r2 * math.cos(a), r2 * math.sin(a), h)))
    for k in range(n):
        bm.faces.new((ring0[k], ring0[(k + 1) % n], ring1[(k + 1) % n], ring1[k]))
    if caps:
        bm.faces.new(list(reversed(ring0)))
        bm.faces.new(ring1)
    R = Matrix.Identity(4)
    if axis == "x":
        R = Matrix.Rotation(math.radians(90), 4, "Y")
    elif axis == "y":
        R = Matrix.Rotation(math.radians(-90), 4, "X")
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(c)) @ R, verts=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def tube_bm(pts, radius, segs=6):
    bm = bmesh.new()
    rings = []
    pts = [Vector(p) for p in pts]
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized()
        b = t.cross(a).normalized()
        rings.append([bm.verts.new(p + radius * (math.cos(2 * math.pi * k / segs) * a +
                                                 math.sin(2 * math.pi * k / segs) * b)) for k in range(segs)])
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for k in range(segs):
            bm.faces.new((r0[k], r0[(k + 1) % segs], r1[(k + 1) % segs], r1[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def raw_mesh_bm(verts, faces):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for f in faces:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def fence_bm(o):
    """Rete metallica a maglie romboidali in un piano verticale.
    o: x0,x1 (o y0,y1 se along='y'), y (o x), z0, h, pitch (m), bar (m), along ('x'|'y'), slant (fattore su z)."""
    bm = bmesh.new()
    along = o.get("along", "x")
    a0, a1 = (o["x0"], o["x1"]) if along == "x" else (o["y0"], o["y1"])
    length = a1 - a0
    h, z0 = o["h"], o["z0"]
    pitch, bar = o["pitch"], o["bar"]
    zs = o.get("slant", 1.0)

    def pt(a, z):
        if along == "x":
            return Vector((a0 + a, o["y"], z0 + z))
        return Vector((o["x"], a0 + a, z0 + z))

    nrm_dir = Vector((0, -1, 0)) if along == "x" else Vector((-1, 0, 0))

    def bar_q(a_, za, b_, zb, w):
        p0, p1 = pt(a_, za), pt(b_, zb)
        d = p1 - p0
        side = d.cross(nrm_dir).normalized() * (w / 2)
        vs = [bm.verts.new(p0 - side), bm.verts.new(p1 - side), bm.verts.new(p1 + side), bm.verts.new(p0 + side)]
        f = bm.faces.new(vs)
        if f.normal.dot(nrm_dir) < 0:
            f.normal_flip()

    n = int((length + h / zs) / pitch) + 2
    for i in range(-n, n + 1):
        s0 = i * pitch
        for sgn in (1, -1):
            xa, za, xb, zb = s0, 0.0, s0 + sgn * h / zs, h
            if xa > xb:
                xa, za, xb, zb = xb, zb, xa, za
            if xb < 0 or xa > length:
                continue
            if xa < 0:
                za = za + (zb - za) * (0 - xa) / (xb - xa)
                xa = 0.0
            if xb > length:
                zb = za + (zb - za) * (length - xa) / (xb - xa)
                xb = length
            if abs(xb - xa) > 1e-4:
                bar_q(xa, za, xb, zb, bar)
    for z in o.get("rails", [0.02, h - 0.03]):
        bar_q(0.0, z, length, z, o.get("rail_w", bar * 2.0))
    return bm


# ------------------------------------------------------------------ kit
class Kits:
    def __init__(self, dirs):
        self.dirs = dirs
        self.protos = {}
        self.coll = bpy.data.collections.new("PROTO")
        bpy.context.scene.collection.children.link(self.coll)
        self.coll.hide_render = True

    def path(self, key):
        kit, name = key.split(":", 1)
        d = self.dirs[kit]
        for ext in (".glb", ".gltf"):
            p = os.path.join(d, name + ext)
            if os.path.exists(p):
                return p
        raise FileNotFoundError(key)

    def get(self, key):
        """Importa una volta, unisce in una sola mesh (trasformazioni applicate); ritorna (oggetto, min, max)."""
        if key in self.protos:
            return self.protos[key]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=self.path(key))
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == "MESH"]
        for o in meshes:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
        for o in new:
            if o.type != "MESH":
                bpy.data.objects.remove(o, do_unlink=True)
        if len(meshes) > 1:
            with bpy.context.temp_override(active_object=meshes[0], selected_editable_objects=meshes,
                                           selected_objects=meshes, object=meshes[0]):
                bpy.ops.object.join()
        ob = meshes[0]
        ob.data = ob.data.copy()
        ob.data.transform(ob.matrix_world)
        ob.matrix_world = Matrix.Identity(4)
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        self.coll.objects.link(ob)
        ob.name = "P_" + key
        co = [v.co for v in ob.data.vertices]
        mn = Vector([min(v[i] for v in co) for i in range(3)])
        mx = Vector([max(v[i] for v in co) for i in range(3)])
        self.protos[key] = (ob, mn, mx)
        return self.protos[key]


# ------------------------------------------------------------------ costruzione
def build(job, gb, coll):
    kits = Kits(job.get("kit_dirs", {}))
    objs = []
    for i, o in enumerate(job["objects"]):
        t = o["type"]
        oid = i + 1
        alb = o.get("alb", [0.5, 0.5, 0.5])
        emi = o.get("emi") or [0.0, 0.0, 0.0]
        cls, mat = o.get("cls", 1), o.get("mat", 0)
        if t == "kit":
            src, mn, mx = kits.get(o["key"])
            me = src.data.copy()
            s = o.get("s", 1.0)
            sv = Vector(s) if isinstance(s, (list, tuple)) else Vector((s, s, s))
            R = Matrix.Rotation(math.radians(o.get("rz", 0.0)), 4, "Z")
            S = Matrix.Diagonal((*sv, 1.0))
            corners = [R @ S @ Vector((cx, cy, cz)) for cx in (mn.x, mx.x) for cy in (mn.y, mx.y) for cz in (mn.z, mx.z)]
            bmn = Vector([min(c[k] for c in corners) for k in range(3)])
            at = Vector(o["at"])
            M = Matrix.Translation(at - bmn) @ R @ S
            me.transform(M)
            # materiali del kit: tutti sostituiti da costanti (mappa per nome, altrimenti quelli dell'oggetto)
            mm = o.get("matmap", {})
            slots = [mt.name.split(".")[0] if mt else "" for mt in me.materials]
            me.materials.clear()
            for nm in slots:
                spec = mm.get(nm, {})
                me.materials.append(gb.material(spec.get("cls", cls), spec.get("mat", mat), spec.get("alb", alb),
                                                spec.get("emi", emi) or [0, 0, 0]))
            if not slots:
                me.materials.append(gb.material(cls, mat, alb, emi))
        else:
            if t == "box":
                bm = box_bm(o["size"], o["at"], o.get("rz", 0.0), o.get("bevel", 0.0))
            elif t == "cyl":
                bm = cyl_bm(o["c"], o["r"], o["h"], o.get("n", 12), o.get("axis", "z"), o.get("r2"), o.get("caps", True))
            elif t == "tube":
                bm = tube_bm(o["pts"], o["r"], o.get("n", 6))
            elif t == "mesh":
                bm = raw_mesh_bm(o["verts"], o["faces"])
            elif t == "fence":
                bm = fence_bm(o)
            else:
                raise ValueError("tipo sconosciuto: " + t)
            me = mesh_from_bm(bm, "%s_%d" % (t, i))
            me.materials.append(gb.material(cls, mat, alb, emi))
            for p in me.polygons:
                p.use_smooth = bool(o.get("smooth", False))
        ob = link(bpy.data.objects.new("O%d" % oid, me), coll)
        ob.pass_index = oid
        objs.append(ob)
    return objs


def setup_render(scene, W, H):
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            break
        except TypeError:
            continue
    scene.eevee.taa_render_samples = 1
    if hasattr(scene.eevee, "use_shadows"):
        scene.eevee.use_shadows = False
    if hasattr(scene.eevee, "use_raytracing"):
        scene.eevee.use_raytracing = False
    scene.render.filter_size = 0.0
    scene.render.film_transparent = True
    scene.render.dither_intensity = 0.0
    scene.view_settings.view_transform = "Raw"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    scene.render.resolution_x = W
    scene.render.resolution_y = H
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    world = bpy.data.worlds.new("W")
    world.color = (0, 0, 0)
    scene.world = world


def main():
    job = argv_job()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    v = job["view"]
    psi, th = math.radians(v["yaw"]), math.radians(v["pitch"])
    ppm, ss = float(v["ppm"]), int(v["ss"])
    k = math.tan(psi) * math.sin(th)
    x0, x1, y0, y1, oy = v["x0"], v["x1"], v["y0"], v["y1"], v["oy"]
    r = Vector((math.cos(psi), math.sin(psi), 0.0))
    f = Vector((-math.sin(psi) * math.cos(th), math.cos(psi) * math.cos(th), -math.sin(th)))
    u = r.cross(f).normalized()
    # intervallo verticale non inclinato necessario (metri sul piano immagine)
    sy_max = (oy - y0) / ppm - min(k * x0, k * x1) / ppm
    sy_min = (oy - y1) / ppm - max(k * x0, k * x1) / ppm
    W = int(round((x1 - x0) * ss))
    H = int(math.ceil((sy_max - sy_min) * ppm * ss)) + 2
    p0, span = job.get("p0", [-40.0, -40.0, -20.0]), float(job.get("span", 200.0))
    gb = GBuf(p0, span)
    coll = bpy.data.collections.new("SCENE")
    scene.collection.children.link(coll)
    objs = build(job, gb, coll)
    bpy.context.view_layer.update()
    # distanza: tutta la scena davanti alla telecamera
    dmin, dmax = 1e9, -1e9
    for ob in objs:
        for vv in ob.data.vertices:
            d = vv.co.dot(f)
            dmin, dmax = min(dmin, d), max(dmax, d)
    cam_d = bpy.data.cameras.new("Cam")
    cam_d.type = "ORTHO"
    cam_d.sensor_fit = "HORIZONTAL"
    cam_d.ortho_scale = W / (ppm * ss)
    cam = bpy.data.objects.new("Cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sx_c = (x0 + W / (2.0 * ss)) / ppm
    sy_c = sy_max - H / (2.0 * ppm * ss)
    dist0 = dmin - 5.0
    cam.location = sx_c * r + sy_c * u + dist0 * f
    cam.rotation_euler = (math.radians(90.0 - v["pitch"]), 0.0, psi)
    cam_d.clip_start = 0.5
    cam_d.clip_end = (dmax - dist0) + 5.0
    setup_render(scene, W, H)
    os.makedirs(job["out_dir"], exist_ok=True)
    tag = job["tag"]
    for pi, name in enumerate(PASSES):
        gb.set_pass(pi)
        scene.render.filepath = os.path.join(job["out_dir"], "%s_%s.png" % (tag, name))
        bpy.ops.render.render(write_still=True)
    meta = dict(tag=tag, view=v, k=k, ss=ss, W=W, H=H, sy_max=sy_max, sy_min=sy_min, p0=p0, span=span,
                r=list(r), u=list(u), f=list(f), cam_location=list(cam.location), objects=len(objs),
                passes=PASSES, materials=len(gb.cache))
    with open(os.path.join(job["out_dir"], "%s_meta.json" % tag), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    print("[env_gbuffer] fatto", tag, W, H, "oggetti", len(objs), "materiali", len(gb.cache))


if __name__ == "__main__":
    main()
