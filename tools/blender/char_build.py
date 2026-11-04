# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: GPL-3.0-or-later
"""CTRL+ALT REVENGE - costruzione e render dei personaggi (pipeline 3D -> pixel, versione v7).

Deriva dalla prova v6/v6.1 (render_v6.py) e dalla prova spike-anim (render_anim.py, author.py).
Costruisce GIG, il punk o il bruto sopra il personaggio CC0 Quaternius Universal Base Character
(Superhero_Male), con geometria procedurale (bmesh, nessun ritocco a mano), e per ogni fotogramma
scrive un G-buffer che il post-processo Python (tools/sprites/pixelize.py) trasforma in pixel art:
  lab : R = id materiale / 64, G/B = 0.5 + 0.5 * normale x/y nello spazio telecamera (EXR float)
  aux : R = profondità (m), G = id parte del corpo / 64, B = 0.5 + 0.5 * normale vera z
salvati in .npz compressi, più un JSON con le ossa proiettate, l'ancora a terra e gli angoli di vista.

Tutto è guidato da un file di lavoro JSON scritto da tools/sprites/build_chars.py:
  blender -b --factory-startup --disable-autoexec --python-exit-code 1 --python char_build.py -- JOB.json

Modalità (campo "mode" del lavoro): frames (G-buffer delle animazioni), explore (miniature Workbench di
tutti i fotogrammi delle clip, per scegliere le pose), preview (render "beauty" per controllare il
modello), portrait (G-buffer del volto a densità più alta, per i ritratti dell'interfaccia).

Note tecniche ereditate dalla v6:
  * ViewLayer.material_override non ha effetto nei render EEVEE in background: per il passo aux si
    sostituiscono i materiali degli slot.
  * le normali lisciate arrivano da un proxy nascosto (Decimate -> Subsurf -> Smooth) via Data Transfer.
  * la telecamera è ortografica, di tre quarti (yaw 30, pitch 12), personaggio rivolto a destra.
  * l'allineamento al pixel del bacino (pelvis snap della v6) qui si fa UNA volta per personaggio,
    sulla guardia: la telecamera resta poi ferma, così l'ancora a terra non deriva mai.
"""
import json
import math
import os
import sys
import time

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, kdtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import char_poses  # noqa: E402

IDS = dict(SKIN=1, HAIR=2, TOP=3, TOP_DARK=4, PANTS=5, BOOTS=6, METAL=7, EYE_GLOW=8, EYE_DARK=9,
           METAL_DARK=10, GLOW_LINE=11, BELT=12, TOP_FOLD=13, TOP_SEAM=14, TOP_LINING=15,
           BOOT_SOLE=16, BOOT_CUFF=17, BEARD=18, METAL_SEAM=19, METAL_LIGHT=20, WRAP=21,
           HOOD=22, HOOD_DARK=23, BROW=24, EYE_SOCKET=25, NOSE_SHADOW=26, MOUTH=27, BEARD_EDGE=28,
           KNUCKLE=29, HAIR_TIE=30, PANTS_FOLD=31, SKIN_DARK=32, CREST=33, CREST_DARK=34, STUD=35,
           WRAP_EDGE=36, LACE=37, PANTS_RIP=38, BRASS=39, SKIN_CREASE=40)
PARTS = dict(none=0, torso=1, head=2, upperarm_l=3, lowerarm_l=4, hand_l=5, upperarm_r=6, lowerarm_r=7,
             hand_r=8, thigh_l=9, calf_l=10, foot_l=11, thigh_r=12, calf_r=13, foot_r=14)
FINGERS = ("index", "middle", "pinky", "ring", "thumb")
EXPORT_BONES = ("root", "pelvis", "spine_01", "spine_02", "spine_03", "neck_01", "Head", "clavicle_l", "clavicle_r",
                "upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r", "hand_r",
                "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r")
UP = Vector((0, 0, 1))


# ============================================================== utilità
def log(*a):
    print("[char]", *a, flush=True)


def new_objects(before):
    return [o for o in bpy.data.objects if o not in before]


def delete_objects(objs):
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)


def iter_fcurve_owners(act):
    owners = []
    for L in getattr(act, "layers", []):
        for st in L.strips:
            for cb in getattr(st, "channelbags", []):
                owners.append(cb)
    if not owners:
        owners.append(act)
    return owners


def strip_channels(act, bones, kinds):
    paths = {f'pose.bones["{b}"].{k}' for b in bones for k in kinds}
    for owner in iter_fcurve_owners(act):
        for fc in [fc for fc in owner.fcurves if fc.data_path in paths]:
            owner.fcurves.remove(fc)


def strip_object_channels(act):
    for owner in iter_fcurve_owners(act):
        for fc in [fc for fc in owner.fcurves if not fc.data_path.startswith("pose.")]:
            owner.fcurves.remove(fc)


def use_action(arm, act):
    ad = arm.animation_data or arm.animation_data_create()
    ad.action = act
    if act is not None and hasattr(ad, "action_slot") and ad.action_slot is None and len(getattr(act, "slots", [])):
        ad.action_slot = act.slots[0]


def bone_part(bn):
    if bn in ("Head", "neck_01"):
        return "head"
    if bn in ("pelvis", "spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r", "root") or bn is None:
        return "torso"
    side = bn[-1] if bn[-2:] in ("_l", "_r") else "l"
    base = bn.split("_")[0]
    if base in FINGERS or bn.startswith("hand"):
        return "hand_" + side
    if bn.startswith("upperarm"):
        return "upperarm_" + side
    if bn.startswith("lowerarm"):
        return "lowerarm_" + side
    if bn.startswith("thigh"):
        return "thigh_" + side
    if bn.startswith("calf"):
        return "calf_" + side
    if bn.startswith(("foot", "ball")):
        return "foot_" + side
    return "torso"


def bm_dom(v, dl, names):
    d = v[dl]
    if not len(d):
        return None
    k = max(d.keys(), key=lambda g: d[g])
    return names.get(k)


def extrude_weighted(bm, edges, dl):
    """estrude dei lati e copia i pesi delle ossa dai vertici d'origine (bmesh non lo fa)."""
    src = {}
    for e in edges:
        for v in e.verts:
            src[tuple(round(c, 6) for c in v.co)] = v
    ret = bmesh.ops.extrude_edge_only(bm, edges=edges)
    nv = [g for g in ret["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in nv:
        o = src.get(tuple(round(c, 6) for c in v.co))
        if o is not None and dl is not None:
            for k, w in o[dl].items():
                v[dl][k] = w
    return nv


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def merge_doubles(ob, dist=1e-4):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bm.to_mesh(ob.data)
    bm.free()


def shade_smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True
    try:
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass


def face_bones(ob):
    """osso dominante per poligono (somma dei pesi sui vertici)."""
    names = {vg.index: vg.name for vg in ob.vertex_groups}
    me = ob.data
    vdom = []
    for v in me.vertices:
        d = {}
        for g in v.groups:
            d[names[g.group]] = g.weight
        vdom.append(d)
    out = []
    for p in me.polygons:
        acc = {}
        for vi in p.vertices:
            for n, w in vdom[vi].items():
                acc[n] = acc.get(n, 0.0) + w
        out.append(max(acc, key=acc.get) if acc else None)
    return out


def vert_bones(ob):
    names = {vg.index: vg.name for vg in ob.vertex_groups}
    out = []
    for v in ob.data.vertices:
        if v.groups:
            g = max(v.groups, key=lambda g: g.weight)
            out.append(names[g.group])
        else:
            out.append(None)
    return out


def set_part_attr(ob, parts_per_face):
    me = ob.data
    if "part" in me.attributes:
        me.attributes.remove(me.attributes["part"])
    at = me.attributes.new("part", "FLOAT", "CORNER")
    vals = np.zeros(len(me.loops), np.float32)
    for p, pt in zip(me.polygons, parts_per_face):
        vals[p.loop_start:p.loop_start + p.loop_total] = PARTS[pt] / 64.0
    at.data.foreach_set("value", vals)


def assign_mats(ob, region_per_face, mats):
    order = []
    for r in region_per_face:
        if r not in order:
            order.append(r)
    ob.data.materials.clear()
    for r in order:
        ob.data.materials.append(mats[r])
    idx = {r: i for i, r in enumerate(order)}
    for p, r in zip(ob.data.polygons, region_per_face):
        p.material_index = idx[r]
    return order


def rigid_object(name, bm, bone, arm, regions, mats, part=None, smooth=True):
    """bmesh costruito in coordinate di riposo del mondo -> oggetto legato al 100% a `bone`."""
    me = bpy.data.meshes.new(name)
    fmat = [f.material_index for f in bm.faces]
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(me.vertices))), 1.0, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    ob.data.materials.clear()
    for r in regions:
        ob.data.materials.append(mats[r])
    for p, mi in zip(me.polygons, fmat):
        p.material_index = min(mi, len(regions) - 1)
    for p in me.polygons:
        p.use_smooth = smooth
    set_part_attr(ob, [part or bone_part(bone)] * len(me.polygons))
    return ob


def skinned_object(name, bm, weights_fn, arm, regions, mats, parts_fn, smooth=True):
    """bmesh in coordinate di riposo -> oggetto con pesi per vertice: weights_fn(co) -> {osso: peso}."""
    me = bpy.data.meshes.new(name)
    fmat = [f.material_index for f in bm.faces]
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    groups = {}
    for v in me.vertices:
        for bn, w in weights_fn(v.co).items():
            if bn not in groups:
                groups[bn] = ob.vertex_groups.new(name=bn)
            groups[bn].add([v.index], w, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    ob.data.materials.clear()
    for r in regions:
        ob.data.materials.append(mats[r])
    for p, mi in zip(me.polygons, fmat):
        p.material_index = min(mi, len(regions) - 1)
        p.use_smooth = smooth
    set_part_attr(ob, [parts_fn(p.center) for p in me.polygons])
    return ob


def basis_from_dir(d, up_hint=Vector((0, 0, 1))):
    d = d.normalized()
    u = up_hint - d * up_hint.dot(d)
    if u.length < 1e-6:
        u = Vector((0, 1, 0)) - d * d.y
    u.normalize()
    w = d.cross(u)
    return d, u, w


def tube_bm(a, b, radii, mat_fn, segs=16, up_hint=Vector((0, 0, 1)), extra_ts=(), cap=True):
    """tubo da a a b; radii: [(t, r)]; mat_fn(t, ang_gradi) -> slot (ang 0 = lato up_hint, 999 = tappi)."""
    d, u, w = basis_from_dir(b - a, up_hint)
    ts = sorted(set([round(t, 4) for t in list(np.linspace(0, 1, 9)) + list(extra_ts)]))

    def rad(t):
        tt = [x[0] for x in radii]
        rr = [x[1] for x in radii]
        return float(np.interp(t, tt, rr))

    bm = bmesh.new()
    rings = []
    for t in ts:
        c = a + (b - a) * t
        r = rad(t)
        ring = []
        for k in range(segs):
            ang = 2 * math.pi * k / segs
            ring.append(bm.verts.new(c + (u * math.cos(ang) + w * math.sin(ang)) * r))
        rings.append(ring)
    for i in range(len(ts) - 1):
        for k in range(segs):
            k2 = (k + 1) % segs
            f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
            tm = (ts[i] + ts[i + 1]) / 2
            am = math.degrees(2 * math.pi * (k + 0.5) / segs)
            am = (am + 180) % 360 - 180
            f.material_index = mat_fn(tm, am)
    if cap:
        for ring, t in ((rings[0], 0.0), (rings[-1], 1.0)):
            f = bm.faces.new(ring if t > 0.5 else list(reversed(ring)))
            f.material_index = mat_fn(t, 999)
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sphere_bm(center, radii_xyz, R=Matrix.Identity(3), mat=0, keep=None, segs=16, rings=10):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    if keep is not None:
        dele = [v for v in bm.verts if not keep(v.co)]
        bmesh.ops.delete(bm, geom=dele, context="VERTS")
    S = Matrix.Diagonal(Vector(radii_xyz)).to_4x4()
    M = Matrix.Translation(center) @ R.to_4x4() @ S
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    for f in bm.faces:
        f.material_index = mat
    bm.normal_update()
    if keep is None:
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def box_bm(center, size, R=Matrix.Identity(3), bevel=0.0, mat=0, segs=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    S = Matrix.Diagonal(Vector(size)).to_4x4()
    bmesh.ops.transform(bm, matrix=S, verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=bevel, segments=segs,
                        profile=0.5, affect="EDGES", clamp_overlap=True)
    M = Matrix.Translation(center) @ R.to_4x4()
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    for f in bm.faces:
        f.material_index = mat
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def cone_bm(base, tip, r_base, mat=0, segs=8, flat=1.0, side=None):
    """cono (punta di cresta, borchia): base circolare verso tip; `flat` schiaccia la base lungo `side`."""
    d = tip - base
    dd, u, w = basis_from_dir(d, side if side is not None else UP)
    bm = bmesh.new()
    ring = []
    for k in range(segs):
        ang = 2 * math.pi * k / segs
        ring.append(bm.verts.new(base + (u * math.cos(ang) * flat + w * math.sin(ang)) * r_base))
    t = bm.verts.new(tip)
    for k in range(segs):
        f = bm.faces.new((ring[k], ring[(k + 1) % segs], t))
        f.material_index = mat
    f = bm.faces.new(list(reversed(ring)))
    f.material_index = mat
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def join_bms(bms):
    me = bpy.data.meshes.new("tmpjoin")
    out = bmesh.new()
    for b in bms:
        b.to_mesh(me)
        out.from_mesh(me)
        b.free()
    bpy.data.meshes.remove(me)
    return out


# ============================================================== materiali
def make_label_mat(name, id_val):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nodes, links = nt.nodes, nt.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0
    geo = nodes.new("ShaderNodeNewGeometry")
    vt = nodes.new("ShaderNodeVectorTransform")
    vt.vector_type = "NORMAL"
    vt.convert_from = "WORLD"
    vt.convert_to = "CAMERA"
    links.new(geo.outputs["Normal"], vt.inputs["Vector"])
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(vt.outputs["Vector"], sep.inputs["Vector"])

    def remap(sock):
        mth = nodes.new("ShaderNodeMath")
        mth.operation = "MULTIPLY_ADD"
        mth.inputs[1].default_value = 0.5
        mth.inputs[2].default_value = 0.5
        links.new(sock, mth.inputs[0])
        return mth.outputs[0]

    comb = nodes.new("ShaderNodeCombineColor")
    comb.inputs[0].default_value = id_val / 64.0
    links.new(remap(sep.outputs["X"]), comb.inputs[1])
    links.new(remap(sep.outputs["Y"]), comb.inputs[2])
    links.new(comb.outputs[0], em.inputs["Color"])
    links.new(em.outputs[0], out.inputs["Surface"])
    m["label"] = name[2:]
    return m


def make_aux_mat():
    """R = profondità (m), G = parte/64 (attributo per angolo), B = 0.5+0.5*normale vera z (telecamera)."""
    m = bpy.data.materials.new("AUX")
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    em = nodes.new("ShaderNodeEmission")
    geo = nodes.new("ShaderNodeNewGeometry")
    neg = nodes.new("ShaderNodeMath")
    neg.operation = "MULTIPLY"
    camd = nodes.new("ShaderNodeCameraData")
    links.new(camd.outputs["View Z Depth"], neg.inputs[0])
    neg.inputs[1].default_value = 1.0
    att = nodes.new("ShaderNodeAttribute")
    att.attribute_type = "GEOMETRY"
    att.attribute_name = "part"
    vt2 = nodes.new("ShaderNodeVectorTransform")
    vt2.vector_type = "NORMAL"
    vt2.convert_from = "WORLD"
    vt2.convert_to = "CAMERA"
    links.new(geo.outputs["True Normal"], vt2.inputs["Vector"])
    sep2 = nodes.new("ShaderNodeSeparateXYZ")
    links.new(vt2.outputs["Vector"], sep2.inputs["Vector"])
    mz = nodes.new("ShaderNodeMath")
    mz.operation = "MULTIPLY_ADD"
    mz.inputs[1].default_value = 0.5
    mz.inputs[2].default_value = 0.5
    links.new(sep2.outputs["Z"], mz.inputs[0])
    comb = nodes.new("ShaderNodeCombineColor")
    links.new(neg.outputs[0], comb.inputs[0])
    links.new(att.outputs["Fac"], comb.inputs[1])
    links.new(mz.outputs[0], comb.inputs[2])
    links.new(comb.outputs[0], em.inputs["Color"])
    links.new(em.outputs[0], out.inputs["Surface"])
    return m


def make_beauty_mats(cols):
    """materiali "beauty" per anteprime ed esplorazione: colori dal JSON del personaggio."""
    out = {}
    for k in IDS:
        c = cols.get(k, "#ff00ff")
        rgb = tuple(int(c[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
        lin = tuple(x ** 2.2 for x in rgb)
        m = bpy.data.materials.new("B_" + k)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*lin, 1)
        bsdf.inputs["Roughness"].default_value = 0.6
        if k.startswith(("METAL", "BRASS", "STUD")):
            bsdf.inputs["Metallic"].default_value = 0.7
            bsdf.inputs["Roughness"].default_value = 0.35
        if k in ("EYE_GLOW", "GLOW_LINE"):
            bsdf.inputs["Emission Color"].default_value = (*lin, 1)
            bsdf.inputs["Emission Strength"].default_value = 4.0
        m.diffuse_color = (*lin, 1.0)
        out[k] = m
    return out


# ============================================================== import e rimodellamento
def import_character(job):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=job["body"])
    objs = new_objects(before)
    arm = [o for o in objs if o.type == "ARMATURE"][0]
    body = [o for o in objs if o.type == "MESH" and o.name.lower().startswith("superhero")][0]
    eyes = [o for o in objs if o.type == "MESH" and o.name.lower().startswith("eyes")][0]
    brows = [o for o in objs if o.type == "MESH" and o.name.lower().startswith("eyebrows")][0]
    delete_objects([o for o in objs if o.name.startswith("Icosphere")])
    hair = {}
    for hn in job.get("hair_meshes", []):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(job["hair_dir"], hn + ".gltf"))
        objs = new_objects(before)
        for o in objs:
            if o.type == "MESH" and not o.name.startswith("Icosphere"):
                for m in o.modifiers:
                    if m.type == "ARMATURE":
                        m.object = arm
                mw = o.matrix_world.copy()
                o.parent = arm
                o.matrix_world = mw
                hair[hn] = o
        delete_objects([o for o in objs if o.type == "ARMATURE" or o.name.startswith("Icosphere")])
    return arm, body, eyes, brows, hair


def reshape_body(arm, meshes, spec):
    """scala delle singole ossa (assi dell'osso: Y = lunghezza, X/Z = spessore), senza eredità ai figli;
    la deformazione si cuoce nelle mesh e la posa diventa il nuovo riposo (dalla prova spike-anim)."""
    saved = {b.name: b.inherit_scale for b in arm.data.bones}
    for b in arm.data.bones:
        b.inherit_scale = "NONE"
    for bn, v in spec.items():
        arm.pose.bones[bn].scale = v
    bpy.context.view_layer.update()
    for ob in meshes:
        mods = [m for m in ob.modifiers if m.type == "ARMATURE"]
        if not mods:
            continue
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob],
                                       selected_editable_objects=[ob]):
            bpy.ops.object.modifier_apply(modifier=mods[0].name)
    bpy.context.view_layer.objects.active = arm
    with bpy.context.temp_override(object=arm, active_object=arm, selected_objects=[arm]):
        bpy.ops.object.mode_set(mode="POSE")
        bpy.ops.pose.armature_apply(selected=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    for b in arm.data.bones:
        b.inherit_scale = saved[b.name]
    for pb in arm.pose.bones:
        pb.scale = (1, 1, 1)
    body = meshes[0]
    co = np.empty(len(body.data.vertices) * 3, np.float32)
    body.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    zmin = float((np.c_[co, np.ones(len(co))] @ np.array(body.matrix_world).T)[:, 2].min())
    # la suola del riposo torna a z = -0.010 come nel corpo originale: si spostano mesh e ossa
    # (non l'oggetto armatura, così le coordinate del rig restano quelle del mondo)
    dz = -(zmin + 0.010)
    T = Matrix.Translation((0.0, 0.0, dz))
    for ob in meshes:
        ob.data.transform(ob.matrix_world.inverted() @ T @ ob.matrix_world)
    bpy.context.view_layer.objects.active = arm
    with bpy.context.temp_override(object=arm, active_object=arm, selected_objects=[arm]):
        bpy.ops.object.mode_set(mode="EDIT")
        Ti = arm.matrix_world.inverted() @ T @ arm.matrix_world
        for eb in arm.data.edit_bones:
            eb.transform(Ti, scale=False, roll=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    for ob in meshes:
        m = ob.modifiers.new("Armature", "ARMATURE")
        m.object = arm
    bpy.context.view_layer.update()
    log("reshape", {k: tuple(v) for k, v in spec.items()}, "correzione suolo dz=%.3f m" % dz)


def to_world(ob):
    mw = ob.matrix_world.copy()
    if mw == Matrix.Identity(4):
        return
    par = ob.parent
    ob.data.transform(mw)
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    if par is not None:
        ob.parent = par
        ob.matrix_parent_inverse = par.matrix_world.inverted()


def landmarks(arm, body, eyes):
    B = {b.name: b for b in arm.data.bones}

    def bh(n):
        return arm.matrix_world @ B[n].head_local

    def bt(n):
        return arm.matrix_world @ B[n].tail_local

    ew = [eyes.matrix_world @ v.co for v in eyes.data.vertices]
    eye_l = sum((p for p in ew if p.x > 0), Vector()) / max(1, sum(1 for p in ew if p.x > 0))
    eye_r = sum((p for p in ew if p.x < 0), Vector()) / max(1, sum(1 for p in ew if p.x < 0))
    vb = vert_bones(body)
    head_pts = [body.matrix_world @ v.co for v, b in zip(body.data.vertices, vb) if b == "Head"]
    nose = min((p for p in head_pts if abs(p.x) < 0.012 and eye_l.z - 0.07 < p.z < eye_l.z - 0.005), key=lambda p: p.y)
    chin = min((p for p in head_pts if abs(p.x) < 0.015 and p.y < nose.y + 0.06), key=lambda p: p.z)
    crown = max(head_pts, key=lambda p: p.z)
    back = max((p for p in head_pts if abs(p.x) < 0.02 and p.z > eye_l.z), key=lambda p: p.y)
    L = dict(eye_l=eye_l, eye_r=eye_r, nose=nose, chin=chin, crown_z=crown.z, crown=crown, back=back,
             mouth=Vector((0.0, nose.y + 0.012, nose.z - 0.40 * (nose.z - chin.z))))
    # cavallo: il punto più basso del bacino al centro (per la misura "niente camicia fra le gambe")
    crotch = [body.matrix_world @ v.co for v, b in zip(body.data.vertices, vb) if b == "pelvis" and abs(v.co.x) < 0.02]
    if crotch:
        L["crotch"] = min(crotch, key=lambda p: p.z)
        L["crotch_obj"] = body                 # per il cavallo deformato (frame_data)
    for k in ("upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r", "hand_r", "Head", "pelvis",
              "foot_l", "foot_r", "calf_l", "calf_r", "thigh_l", "thigh_r", "spine_01", "spine_02", "spine_03",
              "neck_01", "clavicle_l", "clavicle_r", "ball_l", "ball_r"):
        L[k] = bh(k)
        L[k + "_t"] = bt(k)
    log("landmarks", {k: tuple(round(x, 3) for x in v) if isinstance(v, Vector) else round(v, 3) for k, v in L.items()
                      if k in ("eye_l", "eye_r", "nose", "chin", "crown", "back", "mouth", "pelvis", "neck_01")})
    return L


def arm_t(c, a, b):
    """parametro t della proiezione di c sul segmento a->b (0 = a, 1 = b)."""
    d = b - a
    return (c - a).dot(d) / max(d.length_squared, 1e-9)


# ============================================================== pezzi comuni dei costumi
def body_regions(body, L, fb, rule):
    """regione per poligono del corpo (rule(poligono, osso, parte) -> nome o None = da togliere)."""
    regions, parts, drop = [], [], []
    for p, bone in zip(body.data.polygons, fb):
        part = bone_part(bone)
        r = rule(p, bone, part)
        if r is None:
            drop.append(p.index)
            r = "SKIN"
        regions.append(r)
        parts.append(part)
    return regions, parts, drop


def face_features(c, n, L):
    """incavi degli occhi, ombra del naso, bocca sulle facce della testa."""
    for e in (L["eye_l"], L["eye_r"]):
        if (c - e).length < 0.026 and c.y < e.y + 0.012 and c.z > e.z - 0.02:
            return "EYE_SOCKET"
    nz = L["nose"]
    if abs(c.x) < 0.022 and nz.z - 0.022 < c.z < nz.z + 0.004 and c.y < nz.y + 0.03 and n.z < -0.25:
        return "NOSE_SHADOW"
    mo = L["mouth"]
    if abs(c.x) < 0.026 and abs(c.z - mo.z) < 0.006 and c.y < mo.y + 0.02:
        return "MOUTH"
    return None


def push_body(body, rules):
    """spinge i vertici lungo la normale: rules(osso, co) -> offset in metri; poi liscia gambe e busto."""
    me = body.data
    vb = vert_bones(body)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    legs = [v for v, b in zip(bm.verts, vb) if b and b.startswith(("thigh", "calf"))]
    for _ in range(8):
        bmesh.ops.smooth_vert(bm, verts=legs, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    for v, b in zip(bm.verts, vb):
        off = rules(b, v.co)
        if off:
            v.co += v.normal * off
    bm.to_mesh(me)
    bm.free()


def drop_faces(body, regions, parts, drop):
    me = body.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    dset = set(drop)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index in dset], context="FACES")
    bm.to_mesh(me)
    bm.free()
    regions = [r for i, r in enumerate(regions) if i not in dset]
    parts = [pt for i, pt in enumerate(parts) if i not in dset]
    return regions, parts


def shell_from_body(body, fb, keep_fn, name, offset_fn, smooth_iters=12):
    """guscio (camicia, canottiera) copiato dalle facce del corpo, rilassato e spinto in fuori."""
    sh = body.copy()
    sh.data = body.data.copy()
    sh.name = name
    link(sh)
    for m in list(sh.modifiers):
        if m.type != "ARMATURE":
            sh.modifiers.remove(m)
    keep = [keep_fn(p, bone) for p, bone in zip(sh.data.polygons, fb)]
    bm = bmesh.new()
    bm.from_mesh(sh.data)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f, k in zip(bm.faces, keep) if not k], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    dl = bm.verts.layers.deform.active
    names = {vg.index: vg.name for vg in sh.vertex_groups}
    inner = [v for v in bm.verts if not v.is_boundary]
    for _ in range(smooth_iters):           # stoffa, non pelle: via il rilievo muscolare del manichino
        bmesh.ops.smooth_vert(bm, verts=inner, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset_fn(v, bm_dom(v, dl, names))
    bm.normal_update()
    return sh, bm, dl, names


def boundary_loops(edges):
    loops, seen = [], set()
    for e in edges:
        if e.index in seen:
            continue
        stack, comp = [e], []
        seen.add(e.index)
        while stack:
            x = stack.pop()
            comp.append(x)
            for v in x.verts:
                for e2 in v.link_edges:
                    if e2.is_boundary and e2.index not in seen:
                        seen.add(e2.index)
                        stack.append(e2)
        loops.append(comp)
    return loops


def make_boots(body, arm, mats, L, top_z=0.262, toe=0.012, scale_x=1.12, push=0.016, cuff_z=0.225,
               lace=False, sole_z=-0.024):
    """stivali: inviluppo convesso di ogni piede, suddiviso, suola piatta, gambale (dalla v6)."""
    vbn = vert_bones(body)
    names_b = {vg.index: vg.name for vg in body.vertex_groups}
    out = []
    for side in ("l", "r"):
        pts, wts = [], []
        for v, bnm in zip(body.data.vertices, vbn):
            if bnm and bnm.endswith("_" + side) and (bnm.startswith(("foot", "ball")) or
                                                    (bnm.startswith("calf") and v.co.z < top_z + 0.01)):
                pts.append(v.co.copy())
                wts.append({names_b[g.group]: g.weight for g in v.groups})
        kd = kdtree.KDTree(len(pts))
        for i, p in enumerate(pts):
            kd.insert(p, i)
        kd.balance()
        bmB = bmesh.new()
        for p in pts:
            bmB.verts.new(p)
        bmesh.ops.convex_hull(bmB, input=bmB.verts)
        bmesh.ops.delete(bmB, geom=[v for v in bmB.verts if not v.link_faces], context="VERTS")
        bmesh.ops.subdivide_edges(bmB, edges=bmB.edges, cuts=2, use_grid_fill=True)
        bmesh.ops.triangulate(bmB, faces=bmB.faces)
        for _ in range(4):
            bmesh.ops.smooth_vert(bmB, verts=bmB.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bmB.normal_update()
        fx = L["foot_" + side].x
        for v in bmB.verts:
            v.co += v.normal * push
            v.co.x = fx + (v.co.x - fx) * scale_x
            if v.co.z < 0.03:
                v.co.z = sole_z
            if v.co.y < L["ball_" + side].y - 0.065:
                v.co.y -= toe
        dele = [f for f in bmB.faces if f.calc_center_median().z > top_z and abs(f.normal.z) > 0.5]
        bmesh.ops.delete(bmB, geom=dele, context="FACES")
        bmB.normal_update()
        me_b = bpy.data.meshes.new("Boot_" + side)
        bmB.to_mesh(me_b)
        bmB.free()
        ob_b = link(bpy.data.objects.new("Boot_" + side, me_b))
        groups = {}
        for i, v in enumerate(me_b.vertices):
            _, j, _ = kd.find(v.co)
            for gn, w in wts[j].items():
                if gn not in groups:
                    groups[gn] = ob_b.vertex_groups.new(name=gn)
                groups[gn].add([i], w, "REPLACE")
        mod = ob_b.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        reg, prt = [], []
        fbb = face_bones(ob_b)
        for p, bone in zip(me_b.polygons, fbb):
            c = p.center
            if c.z < sole_z + 0.016:
                r = "BOOT_SOLE"
            elif c.z > cuff_z:
                r = "BOOT_CUFF"
            elif lace and c.y < L["foot_" + side].y - 0.02 and abs(c.x - fx) < 0.022 and 0.06 < c.z < cuff_z \
                    and int(c.z / 0.022) % 2 == 0:
                r = "LACE"
            else:
                r = "BOOTS"
            reg.append(r)
            prt.append(bone_part(bone))
        for p in me_b.polygons:
            p.use_smooth = True
        assign_mats(ob_b, reg, mats)
        set_part_attr(ob_b, prt)
        out.append(ob_b)
    return out


def make_beard(beard, mats, L, length=1.0, thick=0.010, mat="BEARD"):
    """barba con volume (Solidify + mento più lungo), riga della bocca, bordo (dalla v6)."""
    merge_doubles(beard)
    bm = bmesh.new()
    bm.from_mesh(beard.data)
    bm.normal_update()
    for v in bm.verts:
        off = 0.006 * length
        if v.co.z < L["mouth"].z:
            k = min(1.0, (L["mouth"].z - v.co.z) / 0.05)
            off += 0.010 * k * length
            v.co.z -= 0.020 * k * k * length
            v.co.y -= 0.008 * k * length
        v.co += v.normal * off
    bm.to_mesh(beard.data)
    bm.free()
    shade_smooth(beard)
    bm = bmesh.new()
    bm.from_mesh(beard.data)
    bm.edges.ensure_lookup_table()
    loops = boundary_loops([e for e in bm.edges if e.is_boundary])
    mouth_loop = None
    for lp in loops:
        cen = sum((v.co for e in lp for v in e.verts), Vector()) / (2 * len(lp))
        per = sum(e.calc_length() for e in lp)
        if per < 0.16 and abs(cen.x) < 0.02 and cen.y < -0.05:
            mouth_loop = lp
    mouth_faces, edge_faces = set(), set()
    for lp in loops:
        tgt = mouth_faces if lp is mouth_loop else edge_faces
        for e in lp:
            for f in e.link_faces:
                tgt.add(f.index)
    reg = []
    mo = L["mouth"]
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(c.z - mo.z) < 0.0065 and abs(c.x) < 0.030 and c.y < mo.y + 0.012 and f.normal.y < -0.3:
            reg.append("MOUTH")
        elif f.index in mouth_faces:
            reg.append("MOUTH")
        elif f.index in edge_faces:
            reg.append("BEARD_EDGE")
        else:
            reg.append(mat)
    bm.free()
    assign_mats(beard, reg, mats)
    set_part_attr(beard, ["head"] * len(beard.data.polygons))
    sb = beard.modifiers.new("Vol", "SOLIDIFY")
    sb.thickness = thick
    sb.offset = -1.0
    sb.use_rim = True
    return beard


def make_brows(brows, mats, L, bushy=1.6, lift=0.0):
    """sopracciglia ingrandite (bushy = spessore) e, con lift, alzate: a 1x restano una riga sopra l'occhio."""
    merge_doubles(brows)
    bm = bmesh.new()
    bm.from_mesh(brows.data)
    zc = L["eye_l"].z + 0.014
    for v in bm.verts:
        cx = 0.032 if v.co.x > 0 else -0.032
        v.co.x = cx + (v.co.x - cx) * 1.15
        v.co.z = zc + (v.co.z - zc) * bushy + lift
        v.co.y -= 0.004
    bm.to_mesh(brows.data)
    bm.free()
    assign_mats(brows, ["BROW"] * len(brows.data.polygons), mats)
    set_part_attr(brows, ["head"] * len(brows.data.polygons))
    so = brows.modifiers.new("Thick", "SOLIDIFY")
    so.thickness = 0.006
    return brows


def make_eyes(eyes, arm, mats, L, glow_side=None):
    """occhi: uno può brillare (cyan) con un disco emissivo davanti."""
    ereg = []
    sgn = {"left": 1.0, "right": -1.0}.get(glow_side, 0.0)
    for p in eyes.data.polygons:
        ereg.append("EYE_GLOW" if sgn and p.center.x * sgn > 0 else "EYE_DARK")
    assign_mats(eyes, ereg, mats)
    set_part_attr(eyes, ["head"] * len(eyes.data.polygons))
    if not sgn:
        return None
    e = L["eye_l"] if glow_side == "left" else L["eye_r"]
    return rigid_object("EyeGlow", sphere_bm(e + Vector((0, -0.006, 0)), (0.015, 0.008, 0.012), mat=0),
                        "Head", arm, ["EYE_GLOW"], mats, part="head")


def make_fist(side, arm, mats, L, regions, name=None, size=(0.085, 0.098, 0.074), grooves=None, wrist=None):
    """pugno: blocco arrotondato delle nocche + pollice; slot: 0 blocco, 1 cresta delle nocche,
    2 dita piegate (fronte), 3 dorso, 4 solchi delle dita, 5 pollice, 6 polso (dalla v6).
    grooves (v7, mano nuda): {"at": [...], "w": mezza larghezza, "cuts": n, "fold": {"x", "w", "z1"}} solchi
    delle dita sulla faccia davanti e piega delle dita sui fianchi (il blocco si suddivide perché restino
    stretti); wrist: {"a", "b", "r0", "r1", "band": [t0, t1]} polso, con la fascia (slot 6) solo fra t0 e t1."""
    h = L["hand_" + side]
    ht = L["hand_" + side + "_t"]
    d = (ht - h).normalized()
    dF, uF, wF = basis_from_dir(d, UP)
    Rf = Matrix((dF, wF, uF)).transposed()
    cen = h + dF * 0.058 - uF * 0.006
    bmF = box_bm(cen, size, R=Rf, bevel=0.018, mat=0, segs=2)
    g_at, g_w, fold = (-0.024, 0.0, 0.024), 0.006, None
    if grooves:
        # v7, mano nuda: tutto il blocco si suddivide, così i solchi delle dita (davanti) e la piega delle dita
        # (sui fianchi) restano stretti; con un materiale "dettaglio" sopravvivono a 1x
        g_at, g_w, fold = tuple(grooves.get("at", g_at)), grooves.get("w", g_w), grooves.get("fold")
        bmesh.ops.subdivide_edges(bmF, edges=list(bmF.edges), cuts=grooves.get("cuts", 3), use_grid_fill=True)
    for f in bmF.faces:
        lc = Rf.transposed() @ (f.calc_center_median() - cen)
        if lc.x > 0.030 and lc.z > -0.005:
            f.material_index = 1
        elif lc.x > 0.034 and lc.z <= -0.005:
            f.material_index = 2
        elif lc.z > 0.02 and lc.x < 0.02:
            f.material_index = 3
        if lc.x > 0.038 and any(abs(lc.y - s) < g_w for s in g_at):
            f.material_index = 4
        if fold and abs(lc.y) > size[1] / 2 - 0.006 and abs(lc.x - fold.get("x", 0.012)) < fold.get("w", 0.005) \
                and lc.z < fold.get("z1", 0.015):
            f.material_index = 4                                 # piega delle dita vista di fianco
    thumb_c = h + dF * 0.055 - uF * 0.030 - Vector((0, 1, 0)) * 0.035
    tb = box_bm(thumb_c, (0.060, 0.030, 0.028), R=Rf, bevel=0.010, mat=5, segs=1)
    bmJ = join_bms([bmF, tb])
    wc = wrist or {}
    b0, b1 = wc.get("band", (0.0, 1.0))           # tratto del polso con lo slot 6 (fascia); il resto è slot 0
    wrist = tube_bm(h - dF * wc.get("a", 0.020), h + dF * wc.get("b", 0.025),
                    [(0, wc.get("r0", 0.047)), (1, wc.get("r1", 0.050))],
                    lambda t, a: 6 if b0 <= t <= b1 else 0, segs=14, extra_ts=(b0, b1))
    bmJ = join_bms([bmJ, wrist])
    return rigid_object(name or ("Fist_" + side), bmJ, "hand_" + side, arm, regions, mats)


def make_knuckle_duster(side, arm, mats, L):
    """tirapugni: barra sulle nocche con quattro anelli."""
    h = L["hand_" + side]
    ht = L["hand_" + side + "_t"]
    d = (ht - h).normalized()
    dF, uF, wF = basis_from_dir(d, UP)
    Rf = Matrix((dF, wF, uF)).transposed()
    cen = h + dF * 0.103 + uF * 0.004
    bar = box_bm(cen, (0.030, 0.112, 0.050), R=Rf, bevel=0.008, mat=0, segs=1)
    rings = []
    for s in (-0.036, -0.012, 0.012, 0.036):
        c = cen + wF * s + dF * 0.010
        rings.append(sphere_bm(c, (0.020, 0.012, 0.030), R=Rf, mat=1, segs=8, rings=5))
    bmJ = join_bms([bar] + rings)
    return rigid_object("Duster_" + side, bmJ, "hand_" + side, arm, ["BRASS", "BRASS"], mats)


def make_wrap_tube(side, arm, mats, L, t0=0.62, t1=1.0, r0=0.050, r1=0.046, mat="WRAP", edge="WRAP_EDGE",
                   name=None, bands=0):
    """fasce/polsino sull'avambraccio: tubo da t0 a t1 dell'avambraccio, con bordi."""
    a = L["lowerarm_" + side]
    b = L["hand_" + side]
    d = b - a
    pa, pb = a + d * t0, a + d * t1 + d.normalized() * 0.012

    def mfn(t, ang):
        if ang == 999:
            return 1
        if t < 0.08 or t > 0.92:
            return 1
        if bands and int(t * bands * 2) % 2 == 1:
            return 1
        return 0
    bm = tube_bm(pa, pb, [(0, r0), (1, r1)], mfn, segs=16, extra_ts=(0.08, 0.92))
    return rigid_object(name or ("Wrap_" + side), bm, "lowerarm_" + side, arm, [mat, edge], mats)


def make_hair_cap(hair, mats, L, push=0.005, mat="HAIR", front_cut=None):
    merge_doubles(hair)
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * push
    if front_cut is not None:
        dele = [f for f in bm.faces if front_cut(f.calc_center_median())]
        bmesh.ops.delete(bm, geom=dele, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(hair.data)
    bm.free()
    shade_smooth(hair)
    assign_mats(hair, [mat] * len(hair.data.polygons), mats)
    set_part_attr(hair, ["head"] * len(hair.data.polygons))
    return hair


def make_topknot(arm, mats, L, cfg):
    """codino raccolto (topknot): crocchia sulla nuca alta, legaccio e ciuffo, legati alla testa."""
    crown, back = L["crown"], L["back"]
    hc = Vector((0.0, (crown.y + back.y) / 2, (crown.z + back.z) / 2))
    hc = Vector((0.0, -0.01, L["eye_l"].z + 0.02))
    ang = math.radians(cfg.get("angle_deg", 38.0))     # dalla verticale verso la nuca
    dirv = Vector((0.0, math.sin(ang), math.cos(ang)))
    # punto del cranio in quella direzione
    r_head = cfg.get("head_r", 0.105)
    base = hc + dirv * r_head
    rb = cfg.get("bun_r", (0.046, 0.052, 0.044))
    cen = base + dirv * (rb[2] * 0.95)
    R = Matrix((Vector((1, 0, 0)), dirv.cross(Vector((1, 0, 0))).normalized(), dirv)).transposed()
    bun = sphere_bm(cen, rb, R=R, mat=0, segs=14, rings=9)
    tie = tube_bm(base + dirv * 0.004, base + dirv * 0.020, [(0, 0.030), (1, 0.030)], lambda t, a: 1, segs=12)
    parts = [bun, tie]
    tuft = cfg.get("tuft", 0.0)
    if tuft > 0:
        tip = cen + dirv * (rb[2] + tuft) + Vector((0, 0.025, 0))
        parts.append(cone_bm(cen + dirv * rb[2] * 0.5, tip, 0.026, mat=0, segs=8, flat=0.7))
    bm = join_bms(parts)
    ob = rigid_object("TopKnot", bm, "Head", arm, ["HAIR", "HAIR_TIE"], mats, part="head")
    return ob


def make_mohawk(arm, mats, L, cfg):
    """cresta: punte schiacciate lungo la linea mediana del cranio, dalla fronte alla nuca."""
    hc = Vector((0.0, -0.005, L["eye_l"].z + 0.015))
    r_head = cfg.get("head_r", 0.100)
    n = cfg.get("spikes", 7)
    a0, a1 = math.radians(cfg.get("from_deg", -28)), math.radians(cfg.get("to_deg", 118))
    hmax = cfg.get("height", 0.10)
    parts = []
    for i in range(n):
        t = i / (n - 1)
        a = a0 + (a1 - a0) * t
        dirv = Vector((0.0, math.sin(a), math.cos(a)))
        base = hc + dirv * (r_head - 0.012)
        h = hmax * (0.62 + 0.38 * math.sin(math.pi * min(1.0, t * 1.15)))
        tip = base + dirv * h + Vector((0, 0.030, 0.0)) * (0.5 + t)
        parts.append(cone_bm(base, tip, cfg.get("base_r", 0.034), mat=0, segs=10, flat=0.38,
                             side=Vector((1, 0, 0))))
    # striscia alla base (capelli rasati in mezzo)
    strip_pts = []
    for i in range(9):
        a = a0 + (a1 - a0) * i / 8
        strip_pts.append(hc + Vector((0.0, math.sin(a), math.cos(a))) * (r_head + 0.002))
    for i in range(8):
        parts.append(tube_bm(strip_pts[i], strip_pts[i + 1], [(0, 0.020), (1, 0.020)], lambda t, a: 1, segs=8))
    bm = join_bms(parts)
    return rigid_object("Mohawk", bm, "Head", arm, ["CREST", "CREST_DARK"], mats, part="head")


def make_cyber_arm(arm, mats, L, cfg):
    """braccio sinistro cibernetico (metallo scuro, anelli cyan): gomito, avambraccio corazzato, polso,
    parte bassa del braccio sotto la manica arrotolata (dalla v6, rivisto)."""
    objs = []
    ua_l, la_l, ha_l = L["upperarm_l"], L["lowerarm_l"], L["hand_l"]
    d_ua = (la_l - ua_l).normalized()
    up_from = cfg.get("upper_from", 0.55)

    def m_upper(t, ang):
        if ang == 999:
            return 2
        if abs(t - 0.78) < 0.06:
            return 3                                  # anello luminoso sopra il gomito
        if abs(t - 0.45) < 0.04:
            return 1
        return 0
    a = ua_l + (la_l - ua_l) * up_from
    b = la_l - d_ua * 0.030
    objs.append(rigid_object("UpperArmor", tube_bm(a, b, [(0, 0.050), (1, 0.047)], m_upper, segs=18,
                                                    extra_ts=(0.41, 0.49, 0.72, 0.84)),
                             "upperarm_l", arm, ["METAL", "METAL_SEAM", "METAL_DARK", "GLOW_LINE"], mats))
    objs.append(rigid_object("Elbow", sphere_bm(la_l, (0.048, 0.048, 0.048), mat=0), "lowerarm_l", arm,
                             ["METAL_DARK"], mats))
    d_la = (ha_l - la_l).normalized()
    rings = cfg.get("rings", (0.30, 0.62))

    def m_fore(t, ang):
        if ang == 999:
            return 2
        for rt in rings:
            if abs(t - rt) < 0.035:
                return 3                              # anelli cyan tutto intorno
        if abs(t - 0.88) < 0.02 or abs(t - 0.12) < 0.02:
            return 1
        if abs(ang) < 16 and 0.40 < t < 0.56:
            return 3                                  # striscia cyan sul dorso
        if abs(abs(ang) - 95) < 7:
            return 1
        if ang > 120 or ang < -120:
            return 4                                  # lato inferiore più chiaro (luce di ritorno)
        return 0
    a = la_l + d_la * 0.03
    b = ha_l - d_la * 0.008
    objs.append(rigid_object("Gauntlet", tube_bm(a, b, [(0, 0.056), (0.35, 0.064), (1, 0.068)], m_fore, segs=20,
                                                  extra_ts=(0.265, 0.335, 0.585, 0.655, 0.10, 0.14, 0.86, 0.90,
                                                            0.40, 0.56)),
                             "lowerarm_l", arm, ["METAL", "METAL_SEAM", "METAL_DARK", "GLOW_LINE", "METAL_LIGHT"], mats))
    objs.append(rigid_object("Wrist", tube_bm(ha_l - d_la * 0.012, ha_l + d_la * 0.022, [(0, 0.050), (1, 0.046)],
                                              lambda t, a: 0, segs=14), "hand_l", arm, ["METAL_DARK"], mats))
    return objs


def make_hood_roll(arm, mats, L, cfg):
    """cappuccio grigio raccolto sul collo: anello spesso attorno alla base del collo, più gonfio dietro,
    con la stoffa del cappuccio appoggiata tra le scapole e due cordini davanti."""
    nk = L["neck_01"]
    c = Vector((0.0, nk.y + cfg.get("dy", 0.004), nk.z + cfg.get("dz", 0.010)))
    R0, r0 = cfg.get("ring_r", 0.092), cfg.get("tube_r", 0.030)
    segs, tsegs = 24, 10
    bm = bmesh.new()
    rings = []
    for i in range(segs):
        th = 2 * math.pi * i / segs                  # 0 = davanti (-Y), pi = dietro
        dirv = Vector((math.sin(th), -math.cos(th), 0.0))
        back = max(0.0, -math.cos(th))               # 1 dietro
        R = R0 + cfg.get("back_r", 0.012) * back
        r = r0 * (0.75 + 0.75 * back)
        cc = c + dirv * R + Vector((0, 0, -0.010 * back))
        ring = []
        for k in range(tsegs):
            ph = 2 * math.pi * k / tsegs
            off = dirv * math.cos(ph) * r + Vector((0, 0, 1)) * math.sin(ph) * r * (1.0 + 0.25 * back)
            ring.append(bm.verts.new(cc + off))
        rings.append(ring)
    for i in range(segs):
        for k in range(tsegs):
            a, b2 = rings[i][k], rings[i][(k + 1) % tsegs]
            cc2, d2 = rings[(i + 1) % segs][(k + 1) % tsegs], rings[(i + 1) % segs][k]
            f = bm.faces.new((a, b2, cc2, d2))
            ph = 2 * math.pi * (k + 0.5) / tsegs
            f.material_index = 1 if (math.cos(ph) < -0.45) else 0     # lato interno più scuro
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    parts = [bm]
    # stoffa del cappuccio tra le scapole
    pk = cfg.get("pad_k", 1.0)                       # scala della stoffa fra le scapole (1 = com'era nella v7)
    hb = c + Vector((0.0, R0 + 0.028 * pk, -0.055))
    parts.append(sphere_bm(hb, (0.088 * pk, 0.034 * pk, 0.075 * pk), mat=0, segs=14, rings=8))
    parts.append(sphere_bm(hb + Vector((0, 0.010, 0.020)), (0.050 * pk, 0.020 * pk, 0.040 * pk), mat=1, segs=10, rings=6))
    # cordini
    for sx in (-1, 1):
        p0 = c + Vector((sx * 0.030, -R0 + 0.006, -0.010))
        p1 = p0 + Vector((sx * 0.006, -0.018, -cfg.get("string_len", 0.11)))
        parts.append(tube_bm(p0, p1, [(0, 0.0065), (1, 0.0065)], lambda t, a: 2, segs=6))
    bmJ = join_bms(parts)

    def wfn(co):
        return {"spine_03": 0.75, "neck_01": 0.25} if co.z > nk.z - 0.01 else {"spine_03": 1.0}
    return skinned_object("HoodRoll", bmJ, wfn, arm, ["HOOD", "HOOD_DARK", "HOOD"], mats, lambda c: "torso")


def make_proportions_list(spec):
    out = {}
    for bn, v in spec.items():
        out[bn] = (tuple(v["scale"]), v.get("inherit"))
    return out


# ============================================================== costumi
def build_gig(ctx):
    """GIG: come la locandina. Codino e barba grigi, camicia da lavoro ocra con maniche arrotolate sopra un
    cappuccio grigio raccolto sul collo, fasce blu sulla mano destra, pantaloni oliva, stivali marroni;
    braccio sinistro cibernetico (metallo scuro, anelli cyan, pugno di metallo), occhio destro cyan."""
    arm, body, eyes, brows, hairs, mats, cfg = ctx["arm"], ctx["body"], ctx["eyes"], ctx["brows"], ctx["hair"], \
        ctx["mats"], ctx["outfit"]
    hair, beard = hairs["Hair_Buzzed"], hairs["Hair_Beard"]
    L = landmarks(arm, body, eyes)
    for ob in (body, eyes, brows, hair, beard):
        to_world(ob)
    merge_doubles(body)
    shade_smooth(body)
    fb = face_bones(body)
    ua_r, la_r, ha_r = L["upperarm_r"], L["lowerarm_r"], L["hand_r"]
    ua_l, la_l = L["upperarm_l"], L["lowerarm_l"]
    sleeve_l = cfg.get("sleeve_l_t", 0.80)       # manica sinistra: arrotolata sopra il gomito
    sleeve_r = cfg.get("sleeve_r_t", 0.20)       # manica destra: arrotolata appena sotto il gomito
    hem_z = cfg.get("hem_z", 0.865)
    scfg = cfg.get("shirt", {})                    # v7: camicia aperta, niente cavallo, lembi separati

    def open_w(z):
        """mezza larghezza dell'apertura davanti della camicia alla quota z (stretta sotto il colletto, larga
        all'orlo)."""
        w0, w1 = scfg.get("open_front", (0.012, 0.05))
        u = max(0.0, min(1.0, (1.34 - z) / max(1.34 - hem_z, 1e-3)))
        return w0 + (w1 - w0) * u

    def rule(p, bone, part):
        # sotto la camicia il corpo prende il colore della camicia: se la attraversa non si vede
        c, n = p.center, p.normal
        if part == "head":
            if bone == "Head":
                return face_features(c, n, L) or "SKIN"
            return "SKIN" if c.z > 1.545 else "HOOD"
        if part in ("hand_l", "hand_r"):
            return None
        if part in ("foot_l", "foot_r") and cfg.get("boots", {}).get("style") == "v7":
            return None                                         # dentro gli stivali nuovi
        if part == "upperarm_l":
            return "TOP" if arm_t(c, ua_l, la_l) < sleeve_l - 0.04 else "METAL_DARK"
        if part == "lowerarm_l":
            return "METAL_DARK"
        if part == "upperarm_r":
            return "TOP"
        if part == "lowerarm_r":
            return "TOP" if arm_t(c, la_r, ha_r) < sleeve_r - 0.04 else "SKIN"
        if bone in ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r"):
            if c.y < -0.02 and abs(c.x) < 0.080 and c.z > 1.30:
                return "HOOD"                                  # felpa nella V del colletto
            if scfg.get("open_front") and c.y < -0.02 and abs(c.x) < open_w(c.z) + 0.02:
                return "HOOD"                                  # felpa sotto la camicia aperta
            return "TOP"
        if bone == "pelvis":
            if scfg.get("open_front") and c.z > 1.0:
                return "HOOD" if c.y < 0.0 else "TOP"          # felpa davanti, sotto la camicia aperta
            return "TOP" if c.z > 1.0 else ("BELT" if c.z > 0.935 else "PANTS")
        return "PANTS"
    regions, parts, drop = body_regions(body, L, fb, rule)

    pcfg = cfg.get("push_body", {})            # spinte lungo la normale, prima della camicia (default = valori v7)
    push_legs, push_pelvis = pcfg.get("legs", 0.016), pcfg.get("pelvis", 0.012)
    belly = pcfg.get("belly", 0.0)              # un filo di pancia: spinta davanti (y < 0) fra belly_z[0] e [1]
    bz0, bz1 = pcfg.get("belly_z", (1.00, 1.18))
    belly_hw = pcfg.get("belly_hw", 0.14)       # mezza larghezza della pancia: ai fianchi la spinta si spegne
    push_neck = pcfg.get("neck", 0.0)           # collo da pugile nella mesh: la scala di neck_01 passerebbe alla testa

    def legs(b, co):
        if b and b.startswith(("thigh", "calf")):
            return push_legs
        if b == "pelvis" and co.z < 0.95:
            return push_pelvis
        if belly and b in ("pelvis", "spine_01", "spine_02") and co.y < -0.03 and bz0 < co.z < bz1:
            u = (co.z - bz0) / (bz1 - bz0)
            return belly * math.sin(math.pi * u) * max(0.0, 1.0 - abs(co.x) / belly_hw)
        if push_neck and b == "neck_01":
            return push_neck
        return 0.0
    push_body(body, legs)

    # ---------------- camicia (guscio dal busto e dalle braccia)
    def keep(p, bone):
        c = p.center
        part = bone_part(bone)
        k = False
        if bone in ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r"):
            k = True
        elif bone == "pelvis" and c.z > hem_z:
            k = True
            # v7: niente camicia fra le gambe: via le facce del cavallo (al centro e rivolte in basso); il dietro
            # resta intero fino all'orlo
            if scfg.get("crotch_cut") and abs(c.x) < scfg.get("crotch_w", 0.075) \
                    and c.z < scfg.get("crotch_z", 1.0) and p.normal.z < scfg.get("crotch_nz", -0.25):
                k = False
        elif scfg.get("hips") and part in ("thigh_l", "thigh_r") and c.z > hem_z:
            # v7: la camicia scende sui fianchi fino all'orlo: fuori, davanti e dietro la coscia, mai all'interno
            sx = 1.0 if part.endswith("_l") else -1.0
            n = p.normal
            k = not (sx * n.x < -0.3 or (n.z < -0.5 and sx * c.x < 0.10))
        elif bone == "neck_01" and c.z < 1.548:
            k = True
        elif part == "upperarm_r":
            k = True
        elif part == "lowerarm_r":
            k = arm_t(c, la_r, ha_r) < sleeve_r
        elif part == "upperarm_l":
            k = arm_t(c, ua_l, la_l) < sleeve_l
        # colletto aperto a V (si vede il cappuccio)
        if k and c.y < -0.03 and 1.33 < c.z < 1.56:
            half = 0.012 + 0.060 * max(0.0, min(1.0, (c.z - 1.34) / 0.16))
            if abs(c.x) < half:
                k = False
        # v7: camicia aperta davanti fino all'orlo (due lembi separati, mai uniti al centro)
        if k and scfg.get("open_front") and c.y < -0.02 and c.z < 1.34 and abs(c.x) < open_w(c.z):
            k = False
        return k

    flare, flare_z, flare_h = scfg.get("flare", 0.020), scfg.get("flare_z", 1.08), scfg.get("flare_h", 0.18)
    sleeve_gap = scfg.get("sleeve_gap", -0.004)   # distanza della manica dal braccio, oltre a shirt_offset

    def off(v, dom):
        z = v.co.z
        o = cfg.get("shirt_offset", 0.024)
        if flare and z < flare_z:
            o += flare * max(0.0, min(1.0, (flare_z - z) / flare_h))   # orlo largo, camicia fuori dai pantaloni
        if dom == "neck_01":
            o += 0.010
        if dom and dom.startswith(("upperarm", "lowerarm")):
            o += sleeve_gap
        return o
    shirt, bm, dl, names = shell_from_body(body, fb, keep, "Shirt", off, smooth_iters=scfg.get("smooth_iters", 12))
    bnd = [e for e in bm.edges if e.is_boundary]
    if scfg:
        # v7: l'orlo è tutto il bordo basso, anche sui fianchi (non i lati dell'apertura davanti)
        hem_top = hem_z + 0.03
        hem = [e for e in bnd if all(v.co.z < hem_top for v in e.verts)]
    else:
        hem = [e for e in bnd if all(v.co.z < 1.0 and bm_dom(v, dl, names) == "pelvis" for v in e.verts)]
    log("camicia: orlo", len(hem))
    # bordi dritti: l'orlo a quota costante, le maniche tagliate su un piano perpendicolare al braccio
    front_dz = scfg.get("front_dz", 0.0)            # v7: lembi davanti appena più corti (orlo appena irregolare)
    for v in {v for e in hem for v in e.verts}:
        v.co.z = hem_z - 0.004 + front_dz * max(0.0, min(1.0, -v.co.y / 0.08))
    for side, a, b, t_end in (("r", la_r, ha_r, sleeve_r), ("l", ua_l, la_l, sleeve_l)):
        axis = (b - a)
        ln = axis.length
        axis = axis.normalized()
        for e in bm.edges:
            if not e.is_boundary:
                continue
            for v in e.verts:
                if (bm_dom(v, dl, names) or "").endswith("arm_" + side) and abs(arm_t(v.co, a, b) - t_end) < 0.25:
                    v.co += axis * (t_end * ln - (v.co - a).dot(axis))
    for edges, dz, dout in ((hem, -scfg.get("hem_drop", 0.036), scfg.get("hem_out", 0.016)),):
        if not edges:
            continue
        nv = extrude_weighted(bm, edges, dl)
        for v in nv:
            radial = Vector((v.co.x, v.co.y - 0.02, 0.0))
            if radial.length > 1e-6:
                radial.normalize()
            v.co += Vector((0, 0, dz)) + radial * dout
    # risvolti delle maniche: anello più largo all'estremità, rimboccato verso la spalla
    cuffs = []
    for side, a, b, t_end in (("r", la_r, ha_r, sleeve_r), ("l", ua_l, la_l, sleeve_l)):
        ed = [e for e in bm.edges if e.is_boundary and all(
            (bm_dom(v, dl, names) or "").endswith("arm_" + side) and abs(arm_t(v.co, a, b) - t_end) < 0.25
            for v in e.verts)]
        if not ed:
            log("!! risvolto non trovato", side)
            continue
        axis = (b - a).normalized()
        nv = extrude_weighted(bm, ed, dl)
        for v in nv:
            ctr = a + axis * (v.co - a).dot(axis)
            rad = (v.co - ctr)
            rad = rad.normalized() if rad.length > 1e-6 else Vector((0, 0, 1))
            v.co += rad * scfg.get("cuff_roll", 0.013) - axis * 0.004
        nvs = set(nv)
        nv2 = extrude_weighted(bm, [e for e in bm.edges if e.is_boundary and all(v in nvs for v in e.verts)], dl)
        for v in nv2:
            ctr = a + axis * (v.co - a).dot(axis)
            rad = (v.co - ctr)
            rad = rad.normalized() if rad.length > 1e-6 else Vector((0, 0, 1))
            v.co += -axis * cfg.get("cuff_w", 0.040) + rad * 0.002
        cuffs += nv + nv2
    cuff_co = {tuple(round(x, 5) for x in v.co) for v in cuffs}
    if scfg.get("pelvis_only_below"):
        # v7: sotto questa quota la camicia segue il bacino; le cosce la spingono appena (thigh_k), così i lembi
        # non si stirano fra le gambe nel calcio, nella guardia e nel passo
        zlim, tk = scfg["pelvis_only_below"], scfg.get("thigh_k", 0.0)
        pel = [k for k, n in names.items() if n == "pelvis"]
        for v in bm.verts:
            if v.co.z >= zlim:
                continue
            d = v[dl]
            moved = 0.0                              # peso tolto alle gambe: passa al bacino
            for k in [k for k in d.keys() if names.get(k, "").startswith(("thigh", "calf"))]:
                w = d[k]
                kept = w * tk if names[k].startswith("thigh") else 0.0
                moved += w - kept
                if kept > 0.0:
                    d[k] = kept
                else:
                    del d[k]
            if pel:
                d[pel[0]] = d.get(pel[0], 0.0) + moved
            tot = sum(d.values())
            if tot <= 1e-6 and pel:
                d[pel[0]] = 1.0
            else:
                for k in list(d.keys()):
                    d[k] = d[k] / tot
    bm.normal_update()
    bm.to_mesh(shirt.data)
    bm.free()
    shade_smooth(shirt)
    sb_ = face_bones(shirt)
    sreg, sparts = [], []
    me_s = shirt.data
    cuff_idx = set()
    for p in me_s.polygons:
        if sum(1 for vi in p.vertices if tuple(round(x, 5) for x in me_s.vertices[vi].co) in cuff_co) >= 2:
            cuff_idx.add(p.index)
    for p, bone in zip(me_s.polygons, sb_):
        c, n = p.center, p.normal
        part = bone_part(bone)
        r = "TOP"
        if p.index in cuff_idx:
            r = "TOP_LINING"
        elif part in ("upperarm_r", "lowerarm_r", "upperarm_l"):
            ua, la = (ua_r, la_r) if part.endswith("_r") else (ua_l, la_l)
            t = arm_t(c, ua, la)
            if 0.06 < t < 0.13:
                r = "TOP_SEAM"                                       # cucitura della spalla
            if (c - la).length < 0.075 and n.y < -0.30:
                r = "TOP_FOLD"                                       # pieghe all'interno del gomito
        else:
            # pochi dettagli e larghi: a 1x le cuciture sottili diventano rumore
            if c.y > 0.06 and (abs(c.z - 1.08) < 0.010 or abs(c.z - 1.17) < 0.009):
                r = "TOP_FOLD"                                       # pieghe in vita, dietro
            if abs(abs(c.x) - 0.165) < 0.007 and c.z < 1.3 and abs(c.y) < 0.06:
                r = "TOP_FOLD"                                       # cuciture laterali
        sreg.append(r)
        sparts.append(part)
    sorder = ["TOP", "TOP_FOLD", "TOP_SEAM", "TOP_LINING", "TOP_LINING", "TOP_LINING"]
    me_s.materials.clear()
    for r in sorder:
        me_s.materials.append(mats[r])
    for p, r in zip(me_s.polygons, sreg):
        p.material_index = sorder.index(r)
    set_part_attr(shirt, sparts)
    sol = shirt.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = 0.010
    sol.offset = -1.0
    sol.use_even_offset = False
    sol.use_quality_normals = True
    sol.material_offset = 3
    sol.material_offset_rim = 3

    bcfg = dict(cfg.get("boots", {}))
    if bcfg.pop("style", None) == "v7":
        import char_boots
        boots = char_boots.make_boots_v7(body, arm, mats, L, bcfg, rigid_object, skinned_object, set_part_attr, link)
    else:
        boots = make_boots(body, arm, mats, L, **bcfg)
    make_beard(beard, mats, L, length=cfg.get("beard_len", 1.15), thick=0.011)
    # attaccatura dei capelli più alta, come nella locandina (capelli tirati indietro nel codino): la fronte
    # resta scoperta e il viso non sembra un elmo
    hl = cfg.get("hairline")
    cut = None
    if hl and hl.get("mode") == "band":
        # v7: solo una fascia di fronte sopra le sopracciglia; tempie e cima della testa restano coperte
        ez = L["eye_l"].z
        z0, z1, hw, cy = hl.get("z0", 0.014), hl.get("z1", 0.05), hl.get("half_w", 0.05), hl.get("cut_y", -0.03)
        cut = lambda c: (c.y < cy and ez + z0 < c.z < ez + z1 - 0.5 * max(0.0, abs(c.x) - 0.02)  # noqa: E731
                         and abs(c.x) < hw)
    elif hl:
        cut_y, eye_z = hl.get("cut_y", -0.045), L["eye_l"].z + hl.get("above_eye", 0.03)
        cut = lambda c: c.y < cut_y and c.z > eye_z  # noqa: E731
    make_hair_cap(hair, mats, L, push=0.006, front_cut=cut)
    topknot = make_topknot(arm, mats, L, cfg.get("topknot", {}))
    make_brows(brows, mats, L, bushy=cfg.get("brow_bushy", 1.7), lift=cfg.get("brow_lift", 0.0))
    glow = make_eyes(eyes, arm, mats, L, glow_side=cfg.get("eye_side", "right"))
    cyber = make_cyber_arm(arm, mats, L, cfg.get("cyber", {}))
    hood = make_hood_roll(arm, mats, L, cfg.get("hood", {}))
    fist_l = make_fist("l", arm, mats, L, ["METAL_LIGHT", "KNUCKLE", "METAL", "METAL_LIGHT", "METAL_SEAM", "METAL",
                                           "METAL_DARK"])
    hcfg = cfg.get("hand_r", {})
    if hcfg.get("bare"):
        # v7: mano destra nuda (pelle, nocche e solchi delle dita); delle fasce da boxe resta solo una fascia
        # sottile al polso, che non copre la mano
        fist_r = make_fist("r", arm, mats, L, ["SKIN", "SKIN", "SKIN", "SKIN", "SKIN_CREASE", "SKIN",
                                               "WRAP" if hcfg.get("wrist_band", True) else "SKIN"],
                           grooves=hcfg.get("grooves"), wrist=hcfg.get("wrist"))
        wrap_r = None
    else:
        fist_r = make_fist("r", arm, mats, L, ["WRAP", "WRAP_EDGE", "SKIN", "WRAP", "SKIN_DARK", "WRAP", "WRAP"])
        wrap_r = make_wrap_tube("r", arm, mats, L, t0=cfg.get("wrap_t0", 0.66), bands=3)
    regions, parts = drop_faces(body, regions, parts, drop)
    assign_mats(body, regions, mats)
    set_part_attr(body, parts)
    objs = dict(body=body, shirt=shirt, beard=beard, hair=hair, topknot=topknot,
                brows=brows, eyes=eyes, hood=hood, fist_l=fist_l, fist_r=fist_r)
    if wrap_r is not None:
        objs["wrap_r"] = wrap_r
    if len(boots) == 2:
        objs["boots_l"], objs["boots_r"] = boots
    else:
        for i, o in enumerate(boots):
            objs["boot%d" % i] = o
    if glow is not None:
        objs["glow"] = glow
    for i, o in enumerate(cyber):
        objs["cyber%d" % i] = o
    return objs, L


def build_thug(ctx, kind):
    """punk (snello, cresta, canotta, jeans scuri strappati, anfibi) o bruto (massiccio, testa rasata,
    canotta grigia, pantaloni da lavoro arancioni, tirapugni)."""
    arm, body, eyes, brows, hairs, mats, cfg = ctx["arm"], ctx["body"], ctx["eyes"], ctx["brows"], ctx["hair"], \
        ctx["mats"], ctx["outfit"]
    L = landmarks(arm, body, eyes)
    for ob in [body, eyes, brows] + list(hairs.values()):
        to_world(ob)
    merge_doubles(body)
    shade_smooth(body)
    fb = face_bones(body)
    pz = L["pelvis"].z
    sh_z = L["clavicle_l"].z
    sw = L["upperarm_l"].x                     # mezza larghezza delle spalle (cambia col rimodellamento)
    ey = L["eye_l"]

    def rule(p, bone, part):
        c, n = p.center, p.normal
        if part == "head":
            if bone == "Head":
                f = face_features(c, n, L)
                if f:
                    return f
                if kind == "punk" and c.z > ey.z + 0.035 and abs(c.x) > 0.020 \
                        and not (c.y < ey.y + 0.006 and c.z < ey.z + 0.075):
                    return "SKIN_DARK"                       # lati rasati
                return "SKIN"
            return "SKIN"
        if part in ("hand_l", "hand_r"):
            return None
        if part in ("foot_l", "foot_r") and cfg.get("boots", {}).get("style") == "v7":
            return None                                         # dentro gli stivali nuovi
        if part.startswith(("upperarm", "lowerarm")):
            sd = part[-1]
            if part.startswith("lowerarm") and arm_t(c, L["lowerarm_" + sd], L["hand_" + sd]) > 0.72:
                return "STUD" if kind == "punk" else "SKIN"  # polsino borchiato
            return "SKIN"
        if bone in ("spine_01", "spine_02", "spine_03", "clavicle_l", "clavicle_r"):
            ax = abs(c.x) / sw
            if c.y < -0.02 and ax < cfg.get("neckline", 0.26) and c.z > sh_z - cfg.get("neck_depth", 0.10):
                return "SKIN"                                # scollo davanti
            if c.y > 0.02 and ax < 0.26 and c.z > sh_z - 0.035:
                return "SKIN"                                # scollo dietro
            if ax > cfg.get("armhole", 0.62) and c.z > sh_z - cfg.get("armhole_depth", 0.17):
                return "SKIN"                                # giromanica
            s_in, s_out = cfg.get("strap", (0.28, 0.52))
            if c.z > sh_z - 0.03 and not (s_in < ax < s_out):
                return "SKIN"                                # spalle scoperte, restano le spalline
            return "TOP"
        if bone == "pelvis":
            if c.z > pz + 0.065:
                return "TOP"
            if c.z > pz + 0.020:
                return "BELT"
            return "PANTS"
        if part.startswith("thigh"):
            if kind == "bruiser" and abs(c.x) > 0.10 and abs(c.z - (pz - 0.30)) < 0.05 and c.y > -0.02:
                return "PANTS_FOLD"                          # tasconi laterali
            return "PANTS"
        if part.startswith("calf"):
            kn = L["calf_" + bone[-1]] if bone[-2:] in ("_l", "_r") else L["calf_l"]
            if kind == "punk" and (c - kn).length < 0.055 and c.y < kn.y - 0.01:
                return "PANTS_RIP"                           # strappo sul ginocchio
            if kind == "bruiser" and (c - kn).length < 0.06 and c.y < kn.y:
                return "PANTS_FOLD"                          # ginocchiera
            return "PANTS"
        return "PANTS"
    regions, parts, drop = body_regions(body, L, fb, rule)

    def push(b, co):
        if b and b.startswith(("thigh", "calf")):
            return cfg.get("pants_push", 0.010)
        if b == "pelvis" and co.z < pz + 0.02:
            return cfg.get("pants_push", 0.010) * 0.8
        if b in ("spine_01", "spine_02", "spine_03") or (b == "pelvis" and co.z >= pz + 0.02):
            return cfg.get("top_push", 0.006)
        return 0.0
    push_body(body, push)
    bcfg = dict(cfg.get("boots", {}))
    if bcfg.pop("style", None) == "v7":
        import char_boots
        boots = char_boots.make_boots_v7(body, arm, mats, L, bcfg, rigid_object, skinned_object, set_part_attr, link)
    else:
        boots = make_boots(body, arm, mats, L, **bcfg)
    make_brows(brows, mats, L, bushy=cfg.get("brow_bushy", 1.5))
    make_eyes(eyes, arm, mats, L, glow_side=None)
    objs = dict(body=body, brows=brows, eyes=eyes)
    if len(boots) == 2:
        objs["boots_l"], objs["boots_r"] = boots
    else:
        for i, o in enumerate(boots):
            objs["boot%d" % i] = o
    if kind == "punk":
        objs["mohawk"] = make_mohawk(arm, mats, L, cfg.get("mohawk", {}))
        objs["fist_l"] = make_fist("l", arm, mats, L, ["SKIN", "KNUCKLE", "SKIN", "SKIN", "SKIN_DARK", "SKIN", "STUD"])
        objs["fist_r"] = make_fist("r", arm, mats, L, ["SKIN", "KNUCKLE", "SKIN", "SKIN", "SKIN_DARK", "SKIN", "STUD"])
        for sd in "lr":
            objs["band_" + sd] = make_wrap_tube(sd, arm, mats, L, t0=0.70, r0=0.044, r1=0.042, mat="BELT",
                                                edge="STUD", name="Band_" + sd, bands=3)
    else:
        if "Hair_Beard" in hairs:
            objs["beard"] = make_beard(hairs["Hair_Beard"], mats, L, length=cfg.get("beard_len", 0.6), thick=0.007)
        objs["fist_l"] = make_fist("l", arm, mats, L, ["SKIN", "KNUCKLE", "SKIN", "SKIN", "SKIN_DARK", "SKIN", "SKIN"])
        objs["fist_r"] = make_fist("r", arm, mats, L, ["SKIN", "KNUCKLE", "SKIN", "SKIN", "SKIN_DARK", "SKIN", "SKIN"])
        objs["duster_l"] = make_knuckle_duster("l", arm, mats, L)
        objs["duster_r"] = make_knuckle_duster("r", arm, mats, L)
    regions, parts = drop_faces(body, regions, parts, drop)
    assign_mats(body, regions, mats)
    set_part_attr(body, parts)
    return objs, L


def apply_proportions(arm, actions, exag):
    """scala delle ossa in posa (prima si tolgono le chiavi di scala delle azioni su quelle ossa)."""
    for a in actions:
        strip_channels(a, list(exag.keys()), ("scale",))
        strip_object_channels(a)
    for bn, (sv, inherit) in exag.items():
        arm.pose.bones[bn].scale = sv
        if inherit:
            arm.data.bones[bn].inherit_scale = inherit


def add_proxy_normals(ob, arm, ratio=0.08, smooth=6):
    px = ob.copy()
    px.data = ob.data.copy()
    px.name = ob.name + "_proxy"
    link(px)
    for m in list(px.modifiers):
        px.modifiers.remove(m)
    dec = px.modifiers.new("Dec", "DECIMATE")
    dec.ratio = ratio
    sub = px.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    sm = px.modifiers.new("Smooth", "SMOOTH")
    sm.factor = 0.6
    sm.iterations = smooth
    am = px.modifiers.new("Arm", "ARMATURE")
    am.object = arm
    px.hide_render = True
    px.hide_viewport = False
    dt = ob.modifiers.new("DT", "DATA_TRANSFER")
    dt.object = px
    dt.use_object_transform = True
    dt.use_loop_data = True
    dt.data_types_loops = {"CUSTOM_NORMAL"}
    dt.loop_mapping = "POLYINTERP_NEAREST"
    dt.mix_mode = "REPLACE"
    dt.mix_factor = 1.0
    return px


# ============================================================== azioni
def import_actions(job, arm):
    actions = []
    for key, imp in (("ual1", "fbx"), ("ual2", "gltf")):
        path = job.get(key)
        if not path:
            continue
        before = set(bpy.data.objects)
        acts_before = set(bpy.data.actions)
        if imp == "fbx":
            bpy.ops.import_scene.fbx(filepath=path)
        else:
            bpy.ops.import_scene.gltf(filepath=path)
        objs = new_objects(before)
        new = [a for a in bpy.data.actions if a not in acts_before]
        for a in new:
            a.use_fake_user = True
        actions += new
        delete_objects(objs)
    for lib in job.get("action_libs", []):
        with bpy.data.libraries.load(lib) as (df, dt):
            dt.actions = list(df.actions)
        for a in dt.actions:
            if a:
                a.use_fake_user = True
                actions.append(a)
    # via tutte le chiavi di scala (valgono 1): le scale di proporzione e di "smear" si mettono a mano
    allb = [b.name for b in arm.data.bones]
    for a in actions:
        strip_channels(a, allb, ("scale",))
        strip_object_channels(a)
    log("azioni importate:", len(actions))
    return actions


def find_action(actions, name):
    for a in actions:
        if a.name == name or a.name.endswith("|" + name):
            return a
    raise KeyError("azione mancante: " + name)


def fist_pose(arm, actions):
    jab = find_action(actions, "Punch_Jab")
    use_action(arm, jab)
    bpy.context.scene.frame_set(int(jab.frame_range[0]))
    out = {}
    for pb in arm.pose.bones:
        if pb.name.split("_")[0] in FINGERS:
            q = pb.rotation_quaternion.copy() if pb.rotation_mode == "QUATERNION" else pb.rotation_euler.to_quaternion()
            out[pb.name] = q
    use_action(arm, None)
    return out


# ============================================================== telecamera e proiezione
class Cam:
    def __init__(self, scene, cam_cfg):
        D = 10.0
        self.D = D
        cd = bpy.data.cameras.new("Cam")
        cd.type = "ORTHO"
        cd.clip_start = 0.1
        cd.clip_end = 100.0
        self.ob = link(bpy.data.objects.new("Cam", cd))
        scene.camera = self.ob
        self.set_view(cam_cfg["yaw_deg"], cam_cfg["pitch_deg"], Vector((0.0, 0.0, cam_cfg["target_z_m"])))

    def set_view(self, yaw_deg, pitch_deg, target):
        yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
        # personaggio rivolto a destra: la telecamera sta a -X e vede il suo lato destro
        self.dirv = Vector((-math.cos(yaw) * math.cos(pitch), -math.sin(yaw) * math.cos(pitch), math.sin(pitch)))
        self.target = target.copy()
        self.base_loc = self.target + self.dirv * self.D
        self.ob.location = self.base_loc
        self.ob.rotation_euler = (self.target - self.base_loc).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        R = self.ob.matrix_world.to_3x3()
        self.right, self.up, self.back = R.col[0].copy(), R.col[1].copy(), R.col[2].copy()
        self.shift = (0.0, 0.0)

    def set_frame(self, W1, p1, ss):
        self.W1, self.p1, self.ss = W1, p1, ss
        self.ortho = W1 * p1
        self.ob.data.ortho_scale = self.ortho

    def place(self, du_px=0.0, dv_px=0.0):
        """sposta la telecamera: il contenuto si muove di (-du, -dv) px a 1x."""
        self.shift = (du_px, dv_px)
        self.ob.location = self.base_loc + self.right * (du_px * self.p1) - self.up * (dv_px * self.p1)
        bpy.context.view_layer.update()

    def project(self, P):
        Pc = self.ob.matrix_world.inverted() @ P
        u = (Pc.x / self.ortho + 0.5) * self.W1
        v = (0.5 - Pc.y / self.ortho) * self.W1
        return u, v, -Pc.z


def bone_world(arm, bn):
    pb = arm.pose.bones[bn]
    return arm.matrix_world @ pb.head, arm.matrix_world @ pb.tail


def bone_rot(arm, bn):
    pb = arm.pose.bones[bn]
    Mp = (arm.matrix_world @ pb.matrix).to_3x3().normalized()
    Mr = (arm.matrix_world @ arm.data.bones[bn].matrix_local).to_3x3().normalized()
    return Mp @ Mr.inverted()


def view_angles(cam, F, U):
    F = F.normalized()
    U = (U - F * U.dot(F)).normalized()
    Rr = F.cross(U)
    c = cam.back.normalized()
    yaw = math.degrees(math.atan2(c.dot(Rr), c.dot(F)))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, c.dot(U)))))
    ux, uy = U.dot(cam.right), U.dot(cam.up)
    roll = 0.0 if ux * ux + uy * uy < 1e-8 else math.degrees(math.atan2(ux, uy))
    return yaw, pitch, roll


def deformed_vertex(L, key):
    """posizione deformata (posa corrente) del vertice del corpo più vicino al punto a riposo L[key]; None se il
    corpo valutato non ha gli stessi vertici di quello a riposo."""
    ob = L.get(key + "_obj")
    if ob is None:
        return None
    if key + "_vi" not in L:
        P0, mw = L[key], ob.matrix_world
        L[key + "_vi"] = min(range(len(ob.data.vertices)), key=lambda i: ((mw @ ob.data.vertices[i].co) - P0).length)
    bpy.context.view_layer.update()
    oe = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = oe.to_mesh()
    P = None
    if len(me.vertices) == len(ob.data.vertices):
        P = oe.matrix_world @ me.vertices[L[key + "_vi"]].co
    oe.to_mesh_clear()
    return P


def frame_data(arm, cam, L, ground_z):
    fd = {"bones": {}, "shift_px": list(cam.shift)}
    for bn in EXPORT_BONES:
        h, t = bone_world(arm, bn)
        uh = cam.project(h)
        ut = cam.project(t)
        fd["bones"][bn] = [round(uh[0], 3), round(uh[1], 3), round(uh[2], 4), round(ut[0], 3), round(ut[1], 3),
                           round(ut[2], 4)]
    Rh = bone_rot(arm, "Head")
    F, U = Rh @ Vector((0, -1, 0)), Rh @ Vector((0, 0, 1))
    hc_rest = Vector((0.0, -0.01, (L["chin"].z + L["crown_z"]) / 2))
    pbH = arm.pose.bones["Head"]
    Mh = arm.matrix_world @ pbH.matrix @ arm.data.bones["Head"].matrix_local.inverted() @ arm.matrix_world.inverted()
    hc = Mh @ hc_rest
    yaw, pitch, roll = view_angles(cam, F, U)
    u, v, dpt = cam.project(hc)
    fd["head"] = dict(yaw=round(yaw, 2), pitch=round(pitch, 2), roll=round(roll, 2), u=round(u, 3), v=round(v, 3),
                      depth=round(dpt, 4))
    # punti utili: centro della testa, collo (presa), ginocchia, punte dei piedi e dei pugni
    for name, P in (("neck", (bone_world(arm, "neck_01")[0] + bone_world(arm, "Head")[0]) / 2),
                    ("head_c", hc)):
        u, v, dpt = cam.project(P)
        fd.setdefault("points", {})[name] = [round(u, 3), round(v, 3), round(dpt, 4)]
    for side in ("l", "r"):
        h, t = bone_world(arm, "hand_" + side)
        tip = h + (t - h).normalized() * 0.11
        u, v, dpt = cam.project(tip)
        fd["points"]["fist_" + side] = [round(u, 3), round(v, 3), round(dpt, 4)]
        fh, ft = bone_world(arm, "ball_" + side)
        u, v, dpt = cam.project(ft)
        fd["points"]["toe_" + side] = [round(u, 3), round(v, 3), round(dpt, 4)]
    if "crotch" in L:
        # cavallo, per la misura della camicia (pixel ocra fra le gambe): "crotch_pelvis" è solidale col bacino
        # (dà l'asse del bacino), "crotch" è il vertice del corpo deformato, cioè il cavallo dei pantaloni che si vede
        pbP = arm.pose.bones["pelvis"]
        Mp = arm.matrix_world @ pbP.matrix @ arm.data.bones["pelvis"].matrix_local.inverted() @ \
            arm.matrix_world.inverted()
        Pp = Mp @ L["crotch"]
        u, v, dpt = cam.project(Pp)
        fd["points"]["crotch_pelvis"] = [round(u, 3), round(v, 3), round(dpt, 4)]
        P = deformed_vertex(L, "crotch") or Pp
        u, v, dpt = cam.project(P)
        fd["points"]["crotch"] = [round(u, 3), round(v, 3), round(dpt, 4)]
    root_h, _ = bone_world(arm, "root")
    g = Vector((root_h.x, root_h.y, ground_z))
    u, v, _ = cam.project(g)
    fd["ground"] = [round(u, 3), round(v, 3)]
    pel, _ = bone_world(arm, "pelvis")
    u, v, _ = cam.project(Vector((pel.x, pel.y, ground_z)))
    fd["ground_pelvis"] = [round(u, 3), round(v, 3)]
    fl = bone_world(arm, "foot_l")[0]
    fr = bone_world(arm, "foot_r")[0]
    mid = (fl + fr) / 2
    u, v, _ = cam.project(Vector((mid.x, mid.y, ground_z)))
    fd["ground_feet"] = [round(u, 3), round(v, 3)]
    fd["pelvis_height_m"] = round(pel.z, 4)
    return fd


# ============================================================== render
def setup_render(scene, W):
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            break
        except TypeError:
            continue
    scene.eevee.taa_render_samples = 1
    scene.render.filter_size = 0.0
    scene.render.film_transparent = True
    scene.render.dither_intensity = 0.0
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.resolution_x = W
    scene.render.resolution_y = W
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"
    w = bpy.data.worlds.new("W")
    w.color = (0, 0, 0)
    scene.world = w


def render_exr(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    arr = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(arr)
    bpy.data.images.remove(img)
    os.remove(path)
    return arr.reshape(h, w, 4)[::-1]


def render_gbuffer(scene, aux_mat, path_noext):
    lab = render_exr(scene, path_noext + "_lab.exr")
    saved = []
    for ob in scene.objects:
        if ob.type == "MESH" and not ob.hide_render:
            saved.append((ob, [sl.material for sl in ob.material_slots]))
            for sl in ob.material_slots:
                sl.material = aux_mat
    aux = render_exr(scene, path_noext + "_aux.exr")
    for ob, ms in saved:
        for sl, m in zip(ob.material_slots, ms):
            sl.material = m
    alpha = lab[..., 3] > 0.5
    ids = np.rint(lab[..., 0] * 64).astype(np.uint8)
    ids[~alpha] = 0
    n = np.stack([lab[..., 1] * 2 - 1, lab[..., 2] * 2 - 1], -1).astype(np.float16)
    depth = aux[..., 0].astype(np.float32)
    part = np.rint(aux[..., 1] * 64).astype(np.uint8)
    tnz = (aux[..., 2] * 2 - 1).astype(np.float16)
    np.savez_compressed(path_noext + ".npz", ids=ids, n=n, depth=depth, part=part, alpha=alpha, tnz=tnz)


def eval_bbox_cam(cam, objs):
    dg = bpy.context.evaluated_depsgraph_get()
    us, vs, zs = [], [], []
    for o in objs:
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        mw = oe.matrix_world
        for v in me.vertices:
            P = mw @ v.co
            u, vv, _ = cam.project(P)
            us.append(u)
            vs.append(vv)
            zs.append(P.z)
        oe.to_mesh_clear()
    return min(us), max(us), min(vs), max(vs), min(zs)


# ============================================================== pose procedurali
class GuardIdle:
    """guardia (Punch_Jab fotogramma 1) con respiro: il bacino scende di pixel interi, i piedi restano
    piantati (IK), come negli idle SNES (dalla v6)."""

    def __init__(self, arm, actions, scene):
        self.arm, self.scene = arm, scene
        base = find_action(actions, "Punch_Jab")
        self.src = base.copy()
        self.src.name = "Guard_Idle_src"
        use_action(arm, base)
        self.f0 = int(base.frame_range[0])
        scene.frame_set(self.f0)
        self.pel_loc0 = arm.pose.bones["pelvis"].location.copy()
        strip_channels(self.src, ["pelvis"], ("location",))

    def begin(self):
        arm = self.arm
        use_action(arm, self.src)
        self.scene.frame_set(self.f0)
        bpy.context.view_layer.update()
        self.empties = []
        for side in ("l", "r"):
            foot = arm.pose.bones["foot_" + side]
            mw = arm.matrix_world @ foot.matrix
            e = link(bpy.data.objects.new("IK_" + side, None))
            e.matrix_world = mw
            self.empties.append(e)
            ik = arm.pose.bones["calf_" + side].constraints.new("IK")
            ik.target = e
            ik.chain_count = 2
            ik.use_tail = True
            cr = foot.constraints.new("COPY_ROTATION")
            cr.target = e
        pel_bone = arm.data.bones["pelvis"]
        self.to_local = (arm.matrix_world @ pel_bone.matrix_local).to_3x3().inverted()

    def set(self, dz):
        off = self.to_local @ Vector((0.0, 0.0, -dz))
        self.arm.pose.bones["pelvis"].location = self.pel_loc0 + off
        self.scene.frame_set(self.f0)

    def end(self):
        arm = self.arm
        for side in ("l", "r"):
            for pbn in ("calf_" + side, "foot_" + side):
                pb = arm.pose.bones[pbn]
                for c in list(pb.constraints):
                    pb.constraints.remove(c)
        delete_objects(self.empties)
        arm.pose.bones["pelvis"].location = (0, 0, 0)


# ============================================================== principale
def build(job):
    t0 = time.time()
    arm, body, eyes, brows, hair = import_character(job)
    if job.get("reshape"):
        reshape_body(arm, [body, eyes, brows] + list(hair.values()), {k: tuple(v) for k, v in job["reshape"].items()})
    actions = import_actions(job, arm)
    scene = bpy.context.scene
    scene.render.fps = 30
    mats = {k: make_label_mat("L_" + k, v) for k, v in IDS.items()}
    ctx = dict(arm=arm, body=body, eyes=eyes, brows=brows, hair=hair, mats=mats, outfit=job.get("outfit_cfg", {}))
    kind = job["outfit"]
    if kind == "gig":
        objs, L = build_gig(ctx)
    else:
        objs, L = build_thug(ctx, kind)
    if job.get("normals", "proxy") == "proxy":
        for k in ("body", "shirt", "boots_l", "boots_r", "beard", "hair"):
            if k in objs:
                add_proxy_normals(objs[k], arm, ratio=0.06 if k in ("body", "shirt") else 0.25,
                                  smooth=8 if k in ("body", "shirt") else 4)
    fist = fist_pose(arm, actions)
    # azioni scritte dalle pose (char_poses): si creano sul rig di questo personaggio
    authored = job.get("authored", [])
    if authored:
        rig = char_poses.Rig(arm, fist)
        for spec in authored:
            act = char_poses.make_action(rig, spec["set"], spec["name"], job.get("pose_params", {}))
            act.use_fake_user = True
            actions.append(act)
    exag = make_proportions_list(job.get("proportions", {}))
    apply_proportions(arm, actions, exag)
    log("costruito", {k: len(o.data.polygons) for k, o in objs.items()}, "t=%.1fs" % (time.time() - t0))
    return arm, objs, L, actions, scene, mats


def guard_pose(arm, actions, scene):
    jab = find_action(actions, "Punch_Jab")
    use_action(arm, jab)
    scene.frame_set(int(jab.frame_range[0]))


def main():
    job = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
    os.makedirs(job["out"], exist_ok=True)
    t0 = time.time()
    arm, objs, L, actions, scene, mats = build(job)
    if job.get("topknot_spring") and "topknot" in objs:
        import char_anim
        tk = job.get("outfit_cfg", {}).get("topknot", {})
        hc = Vector((0.0, -0.01, L["eye_l"].z + 0.02))
        ang = math.radians(tk.get("angle_deg", 38.0))
        dirv = Vector((0.0, math.sin(ang), math.cos(ang)))
        base = hc + dirv * (tk.get("head_r", 0.105) - 0.012)
        rb = tk.get("bun_r", (0.046, 0.052, 0.044))
        tip = hc + dirv * (tk.get("head_r", 0.105) + rb[2] * 1.95)
        char_anim.add_topknot_bone(arm, objs["topknot"], base, tip)
        log("codino: osso con molla aggiunto")
    camc = job["camera"]
    cam = Cam(scene, camc)
    p1 = 1.0 / camc["pixels_per_meter"]
    W1 = job.get("frame_px", 208)
    ss = camc.get("supersampling", 4)
    cam.set_frame(W1, p1, ss)
    render_objs = [o for o in objs.values()]
    mode = job.get("mode", "frames")
    ground_z = job.get("ground_z", -0.024)
    # allineamento globale: il bacino della guardia cade al centro di un pixel (pelvis snap una volta sola)
    guard_pose(arm, actions, scene)
    cam.place(0, 0)
    P, _ = bone_world(arm, "pelvis")
    u, v, _ = cam.project(P)
    du, dv = (u - math.floor(u)) - 0.5, (v - math.floor(v)) - 0.5
    cam.place(du, dv)
    bx = eval_bbox_cam(cam, render_objs)
    log("guardia: bbox", [round(x, 1) for x in bx[:4]], "altezza %.1f px" % (bx[3] - bx[2]), "suola z %.3f" % bx[4])
    meta = dict(ids=IDS, parts=PARTS, W1=W1, ss=ss, p1=p1, ortho=cam.ortho, camera=camc, shift=[du, dv],
                guard_bbox_px=[round(x, 2) for x in bx[:4]], guard_height_px=round(bx[3] - bx[2], 2),
                sole_z=round(bx[4], 4), id=job["id"], outfit=kind_of(job), anims={})
    if mode == "preview":
        render_previews(job, scene, arm, actions, objs, cam, L)
        return
    if mode == "explore":
        L_GLOBAL[0] = L
        render_explore(job, scene, arm, actions, objs, cam)
        return
    setup_render(scene, W1 * ss)
    aux_mat = make_aux_mat()
    if mode == "portrait":
        render_portrait(job, scene, arm, actions, objs, cam, L, aux_mat, meta)
        return
    import char_render
    char_render.run(globals(), job, scene, arm, actions, objs, cam, L, aux_mat, meta, camc, p1, ground_z, t0)
    with open(os.path.join(job["out"], "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    log("fatto in %.1fs" % (time.time() - t0))


def kind_of(job):
    return job["outfit"]


SCALED = {}


def apply_frame_scale(arm, spec):
    """"smear" di contatto: scala di un osso in un solo fotogramma (stinco, avambraccio), moltiplicata per
    quella delle proporzioni; s scalare = uniforme, lista = [x, y (lunghezza), z]."""
    for bn, sv in list(SCALED.items()):
        arm.pose.bones[bn].scale = sv
    SCALED.clear()
    if spec:
        for bn, s in spec.items():
            pb = arm.pose.bones[bn]
            SCALED[bn] = tuple(pb.scale)
            m = (s, s, s) if not isinstance(s, list) else tuple(s)
            pb.scale = tuple(a * b for a, b in zip(pb.scale, m))
    bpy.context.view_layer.update()


# ============================================================== anteprime ed esplorazione
def beauty_setup(job, scene, objs, cam):
    bmats = make_beauty_mats(job.get("beauty_cols", {}))
    for o in objs.values():
        for s in o.material_slots:
            k = s.material["label"] if "label" in s.material else s.material.name[2:]
            s.material = bmats.get(k, s.material)
    sun = link(bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")))
    sun.data.energy = 3.0
    key = Vector(job["camera"]["luce_chiave"]["mondo"])
    sun.rotation_euler = key.to_track_quat("Z", "Y").to_euler()
    w = bpy.data.worlds.new("Wb")
    w.color = (0.10, 0.09, 0.14)
    scene.world = w
    return sun


def render_previews(job, scene, arm, actions, objs, cam, L):
    beauty_setup(job, scene, objs, cam)
    for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            scene.render.engine = e
            break
        except TypeError:
            continue
    scene.eevee.taa_render_samples = 16
    scene.render.filter_size = 1.5
    res = job.get("preview_res", 900)
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "AgX"
    scene.render.film_transparent = False
    old = cam.ob.data.ortho_scale
    for spec in job.get("preview", ["Punch_Jab:1"]):
        an, fr = spec.split(":")
        use_action(arm, find_action(actions, an))
        scene.frame_set(int(fr))
        cam.ob.data.ortho_scale = job.get("preview_ortho", 2.6)
        cam.place(*cam.shift)
        scene.render.filepath = os.path.join(job["out"], f"preview_{an}_{fr}.png")
        bpy.ops.render.render(write_still=True)
        loc = cam.ob.location.copy()
        hh, ht = bone_world(arm, "Head")
        cam.ob.location = (hh + ht) / 2 + cam.back * 10.0
        cam.ob.data.ortho_scale = 0.62
        scene.render.filepath = os.path.join(job["out"], f"preview_{an}_{fr}_head.png")
        bpy.ops.render.render(write_still=True)
        cam.ob.location = loc
    cam.ob.data.ortho_scale = old


def render_explore(job, scene, arm, actions, objs, cam):
    """miniature Workbench (colori piatti dei materiali) di tutti i fotogrammi delle clip richieste."""
    bmats = make_beauty_mats(job.get("beauty_cols", {}))
    for o in objs.values():
        for s in o.material_slots:
            k = s.material["label"] if "label" in s.material else s.material.name[2:]
            s.material = bmats.get(k, s.material)
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_object_outline = True
    scene.render.film_transparent = False
    sc = job.get("explore_scale", 2)
    scene.render.resolution_x = cam.W1 * sc
    scene.render.resolution_y = cam.W1 * sc
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    out = {}
    for name in job["explore"]:
        if name == "guard":
            act = find_action(actions, "Punch_Jab")
            frames = [int(act.frame_range[0])]
        else:
            act = find_action(actions, name)
            frames = list(range(int(act.frame_range[0]), int(act.frame_range[1]) + 1, job.get("explore_step", 1)))
        use_action(arm, act)
        d = os.path.join(job["out"], "explore", name.replace("|", "_"))
        os.makedirs(d, exist_ok=True)
        rec = []
        for f in frames:
            scene.frame_set(f)
            scene.render.filepath = os.path.join(d, f"f{f:03d}.png")
            bpy.ops.render.render(write_still=True)
            fd = frame_data(arm, cam, L_GLOBAL[0], job.get("ground_z", -0.024))
            fd["frame"] = f
            rec.append(fd)
        with open(os.path.join(d, "frames.json"), "w") as fh:
            json.dump(rec, fh)
        out[name] = frames
        log("esplorata", name, len(frames))
    with open(os.path.join(job["out"], "explore", "index.json"), "w") as fh:
        json.dump(dict(W1=cam.W1, scale=sc, clips=out), fh, indent=1)


L_GLOBAL = [None]


def render_portrait(job, scene, arm, actions, objs, cam, L, aux_mat, meta):
    """volto di tre quarti a densità più alta, come G-buffer (stessa pipeline di pixel)."""
    pc = job["portrait"]
    act = find_action(actions, pc.get("action", "Idle_Loop"))
    use_action(arm, act)
    scene.frame_set(int(pc.get("frame", act.frame_range[0])))
    ppm = pc.get("pixels_per_meter", 96)
    W = pc.get("frame_px", 48)
    hh, ht = bone_world(arm, "Head")
    c = (hh + ht) / 2 + Vector((0, 0, pc.get("dz", 0.0)))
    cam.set_view(pc.get("yaw_deg", 55.0), pc.get("pitch_deg", 6.0), c)
    cam.set_frame(W, 1.0 / ppm, cam.ss)
    cam.place(0, 0)
    scene.render.resolution_x = W * cam.ss
    scene.render.resolution_y = W * cam.ss
    d = os.path.join(job["out"], "portrait")
    os.makedirs(d, exist_ok=True)
    render_gbuffer(scene, aux_mat, os.path.join(d, "f001"))
    fd = frame_data(arm, cam, L, job.get("ground_z", -0.024))
    fd["frame"] = 1
    fd["file"] = "f001.npz"
    with open(os.path.join(d, "frames.json"), "w") as fh:
        json.dump([fd], fh)
    meta.update(W1=W, p1=1.0 / ppm, portrait=pc)
    meta["anims"]["portrait"] = dict(src="portrait", frames=[1])
    with open(os.path.join(d, "meta.json"), "w") as fh:
        json.dump(meta, fh, indent=1)
    log("ritratto fatto")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
