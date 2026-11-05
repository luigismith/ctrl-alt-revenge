# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - pipeline dei personaggi con un comando.

Uso (sempre con il Python del laboratorio e -I, dalla radice del repo):
  python -I tools/sprites/build_chars.py all [gig thug_punk thug_bruiser]
      render (Blender) -> pixel -> atlante + JSON -> validazione -> tavole di controllo -> ritratti -> scena
  python -I tools/sprites/build_chars.py publish [id ...]
      copia in game/assets i file già validati (nome temporaneo + rinomina, così il gioco non li legge a metà)
Passi singoli: retarget, render, bones, pixel, assemble, validate, review, portrait, scene, explore, preview.
Il lavoro intermedio va in tools/sprites/out/ (ignorata da git). Configurazione: tools/sprites/chars/<id>.json,
telecamera e luci comuni: tools/sprites/camera.json.
"""
import argparse
import glob
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import charlib as C  # noqa: E402
import pixelize as PX  # noqa: E402
import review as RV  # noqa: E402

IDS_ALL = ["gig", "thug_punk", "thug_bruiser"]
ENEMIES = ["thug_punk", "thug_bruiser"]
PAIRS = ("grab_hold", "knee", "throw")
# punti del fotogramma nel JSON (§4): nome nel JSON, nome nei dati del render
POINTS = (("fist_l", "fist_l"), ("fist_r", "fist_r"), ("foot_l", "toe_l"), ("foot_r", "toe_r"), ("head", "head_c"))
RETARGETS = [
    # (nome azione, file JSON Mesh2Motion in sources/anim/spike-out/m2m_json)
    ("M2M_KickRoundhouse", "kick-roundhouse.json"),
    ("M2M_KickFront", "kick-front.json"),
]


def raw_dir(cid):
    return os.path.join(C.OUT, "raw", cid)


def pix_dir(cid):
    return os.path.join(C.OUT, "pix", cid)


def final_dir(cid):
    return os.path.join(C.OUT, "final", cid)


def review_dir(cid):
    return os.path.join(C.OUT, "review", cid)


# ============================================================== Blender
def step_retarget(force=False):
    """calci Mesh2Motion (CC0) sul rig UBC -> out/anim/actions_m2m.blend (rifatto solo se manca)."""
    blend = os.path.join(C.OUT, "anim", "actions_m2m.blend")
    js = os.path.join(C.OUT, "anim", "actions_m2m.json")
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    if os.path.exists(blend) and not force:
        have = C.load_json(js) if os.path.exists(js) else {}
        if all(n in have for n, _ in RETARGETS):
            return blend
    if force:
        for p in (blend, js):
            if os.path.exists(p):
                os.remove(p)
    for name, src in RETARGETS:
        C.run_blender_args("char_retarget.py", [
            "--body", C.SOURCES["body"], "--src_json", os.path.join(C.SOURCES["m2m_json"], src),
            "--fist_fbx", C.SOURCES["ual1"], "--name", name, "--out_blend", blend, "--out_json", js],
            timeout=600, tag="retarget-" + name)
    return blend


def anim_jobs(cfg, only=None):
    out = []
    for name, an in cfg["anims"].items():
        if only and name not in only:
            continue
        picks = [dict(f=fr.get("f"), at=fr.get("at"), t=fr.get("t"), scale=fr.get("scale"), src=fr.get("src"),
                      smear=fr.get("smear"), smear_from=fr.get("smear_from")) for fr in an["frames"]]
        out.append(dict(name=name, src=an["src"], picks=picks, bob_px=an.get("bob_px", 2), upper=an.get("upper"),
                        stride=an.get("stride"), period=an.get("period"), loop=an.get("loop", False),
                        spring=an.get("spring", True), twist_deg=an.get("twist_deg", 0.0),
                        twist_phase=an.get("twist_phase", 0.0)))
    return out


def step_render(cid, only=None, bones_only=False):
    cfg = C.char_cfg(cid)
    if cfg.get("action_libs"):
        step_retarget()
    out = raw_dir(cid) if not bones_only else os.path.join(C.OUT, "bones", cid)
    job = C.base_job(cid, cfg, "frames", out)
    job["anims"] = anim_jobs(cfg, only)
    job["bones_only"] = bones_only
    job["topknot_spring"] = cfg.get("topknot_spring", False)
    job["spring_cfg"] = cfg.get("spring_cfg", {})
    if not only and not bones_only and os.path.isdir(out):
        shutil.rmtree(out)
    C.run_blender("char_build.py", job, timeout=3600, tag=("bones-" if bones_only else "render-") + cid)
    if only and not bones_only:
        # unisce i meta dei render parziali
        pass


def step_preview(cid, specs):
    cfg = C.char_cfg(cid)
    out = os.path.join(C.OUT, "preview", cid)
    job = C.base_job(cid, cfg, "preview", out)
    job["preview"] = specs
    job["preview_res"] = 900
    C.run_blender("char_build.py", job, timeout=900, tag=f"preview-{cid}")


def step_explore(cid, clips, step=1):
    cfg = C.char_cfg(cid)
    if cfg.get("action_libs"):
        step_retarget()
    out = os.path.join(C.OUT, "explore", cid)
    job = C.base_job(cid, cfg, "explore", out)
    job["explore"] = clips
    job["explore_step"] = step
    job["explore_scale"] = 2
    C.run_blender("char_build.py", job, timeout=1800, tag=f"explore-{cid}")
    RV.explore_sheets(os.path.join(out, "explore"), os.path.join(review_dir(cid), "explore"))


def step_portrait_render(cid):
    cfg = C.char_cfg(cid)
    out = os.path.join(C.OUT, "raw_portrait", cid)
    job = C.base_job(cid, cfg, "portrait", out)
    job["portrait"] = cfg["portrait"]
    C.run_blender("char_build.py", job, timeout=900, tag=f"portrait-{cid}")


# ============================================================== pixel
def shader_for(cfg, meta):
    pcfg = cfg["palette"]
    pcfg_cfg = dict(PX.DEFAULT_CFG)
    pcfg_cfg.update(cfg.get("pixel_cfg", {}))
    cam = C.camera()
    pcfg_cfg["key"] = cam["luce_chiave"]["camera"]
    pcfg_cfg["rim_dir"] = cam["luce_di_contorno"]["camera"]
    pcfg_cfg["rim_thr"] = cam["luce_di_contorno"]["soglia"]
    pcfg_cfg["rim_mats"] = pcfg.get("rim_mats", [])
    pcfg_cfg["p1"] = meta.get("p1", 1.0 / cam["pixels_per_meter"])
    sh = PX.Shader(pcfg_cfg, pcfg, meta["ids"])
    return sh, pcfg_cfg


def step_pixel(cid, only=None):
    cfg = C.char_cfg(cid)
    meta = C.load_json(os.path.join(raw_dir(cid), "meta.json"))
    sh, pcfg = shader_for(cfg, meta)
    ss = meta["ss"]
    out = pix_dir(cid)
    os.makedirs(out, exist_ok=True)
    for name, an in cfg["anims"].items():
        if only and name not in only:
            continue
        d = os.path.join(raw_dir(cid), name)
        fdata = C.load_json(os.path.join(d, "frames.json"))
        faces = [fr.get("face") or ("pain" if name.startswith("hurt") else "neutral") for fr in an["frames"]]
        sprites, labels = PX.pixelize_sequence(d, fdata, ss, sh, pcfg, loop=an.get("loop", False), faces=faces)
        od = os.path.join(out, name)
        os.makedirs(od, exist_ok=True)
        for f in glob.glob(os.path.join(od, "*.png")) + glob.glob(os.path.join(od, "*.npz")):
            os.remove(f)
        nrm = getattr(PX.pixelize_sequence, "normals", None)
        for i, sp in enumerate(sprites):
            Image.fromarray(sp, "RGBA").save(os.path.join(od, f"{i:02d}.png"))
            np.savez_compressed(os.path.join(od, f"{i:02d}_lab.npz"), ids=labels[i][0], part=labels[i][1])
            if nrm is not None:
                Image.fromarray(nrm[i], "RGBA").save(os.path.join(od, f"{i:02d}_n.png"))
        C.say(f"  pixel {cid}/{name}: {len(sprites)} fotogrammi")


def load_pix(cid, name):
    od = os.path.join(pix_dir(cid), name)
    files = sorted(glob.glob(os.path.join(od, "[0-9][0-9].png")))
    return [np.asarray(Image.open(f).convert("RGBA")).copy() for f in files]


def load_pix_normals(cid, name):
    od = os.path.join(pix_dir(cid), name)
    files = sorted(glob.glob(os.path.join(od, "[0-9][0-9]_n.png")))
    return [np.asarray(Image.open(f).convert("RGBA")).copy() for f in files]


# ============================================================== box dalle ossa
def P(fd, bn, tail=False):
    b = fd["bones"][bn]
    return (b[3], b[4]) if tail else (b[0], b[1])


def mid(a, b, t=0.5):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def aabb(pts, pad, anchor):
    ax, ay = anchor
    x0 = int(math.floor(min(p[0] for p in pts) - pad - ax))
    y0 = int(math.floor(min(p[1] for p in pts) - pad - ay))
    x1 = int(math.ceil(max(p[0] for p in pts) + pad - ax))
    y1 = int(math.ceil(max(p[1] for p in pts) + pad - ay))
    return [x0, y0, max(1, x1 - x0), max(1, y1 - y0)]


def hurt_boxes(fd, mode, anchor, hcfg):
    head_r = hcfg.get("head_r", [7, 8])
    torso = aabb([P(fd, "pelvis"), P(fd, "spine_03", True), P(fd, "clavicle_l", True), P(fd, "clavicle_r", True),
                  P(fd, "spine_02")], hcfg.get("torso_pad", 4), anchor)
    hc = fd["points"]["head_c"]
    head = [int(math.floor(hc[0] - head_r[0] - anchor[0])), int(math.floor(hc[1] - head_r[1] - anchor[1])),
            2 * head_r[0], 2 * head_r[1]]
    if mode == "lying":
        pts = [P(fd, b) for b in ("pelvis", "spine_03", "Head", "thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l",
                                   "foot_r")] + [P(fd, "Head", True)]
        return [aabb(pts, 3, anchor)]
    out = [torso, head]
    if mode == "low":
        legs = aabb([P(fd, b) for b in ("thigh_l", "thigh_r", "calf_l", "calf_r", "foot_l", "foot_r")], 3, anchor)
        out.append(legs)
    return out


def hit_box(fd, kind, anchor):
    pts = fd["points"]
    if kind in ("fist_l", "fist_r"):
        s = kind[-1]
        w = P(fd, "hand_" + s)
        el = P(fd, "lowerarm_" + s)
        return aabb([w, (pts["fist_" + s][0], pts["fist_" + s][1]), mid(el, w, 0.5)], 2, anchor)
    if kind in ("foot_l", "foot_r"):
        s = kind[-1]
        return aabb([P(fd, "foot_" + s), (pts["toe_" + s][0], pts["toe_" + s][1]),
                     mid(P(fd, "calf_" + s), P(fd, "foot_" + s), 0.4)], 2, anchor)
    if kind in ("knee_l", "knee_r"):
        s = kind[-1]
        k = P(fd, "calf_" + s)
        return aabb([k, mid(P(fd, "thigh_" + s), k, 0.6)], 4, anchor)
    raise KeyError(kind)


# ============================================================== atlante
def crop(sp):
    ys, xs = np.nonzero(sp[..., 3])
    if not len(xs):
        return sp[:1, :1], (0, 0)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return sp[y0:y1, x0:x1], (int(x0), int(y0))


def pack(sizes, margin=1):
    """impacchettamento a scaffali (altezze decrescenti), margine di 1 px; prova più larghezze e tiene
    l'area minore. sizes: [(w, h)] -> (W, H, [(x, y)])."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    best = None
    wmin = max(w for w, h in sizes) + 2 * margin
    for W in sorted({max(wmin, w) for w in (256, 384, 512, 640, 768, 896, 1024, 1280, 1536, 2048)}):
        pos = [None] * len(sizes)
        x, y, shelf = margin, margin, 0
        for i in order:
            w, h = sizes[i]
            if x + w + margin > W:
                x, y = margin, y + shelf + margin
                shelf = 0
            pos[i] = (x, y)
            x += w + margin
            shelf = max(shelf, h)
        H = y + shelf + margin
        area = W * H
        score = area * (1.0 + 0.15 * abs(math.log(W / max(H, 1))))
        if best is None or score < best[0]:
            best = (score, W, H, pos)
    return best[1], best[2], best[3]


def guard_pelvis_h(cid, fdata):
    """altezza del bacino sopra l'ancora nella guardia (px): serve all'ancora 'pelvis_h' dei salti."""
    fd = fdata["idle"][0] if "idle" in fdata else next(iter(fdata.values()))[0]
    return fd["ground"][1] - fd["bones"]["pelvis"][1]


def anchor_of(fd, mode, pel_h):
    """root = punto a terra del rig (fermo nelle animazioni sul posto); pelvis = a terra sotto il bacino
    (cadute, rialzo, vittime in volo); pelvis_h = sotto il bacino ma all'altezza di guardia (salti: le gambe
    raccolte salgono, il corpo non cade)."""
    if mode == "root":
        g = fd["ground"]
    elif mode == "pelvis":
        g = fd["ground_pelvis"]
    elif mode == "pelvis_h":
        g = (fd["ground"][0], fd["bones"]["pelvis"][1] + pel_h)
    else:
        raise KeyError(mode)
    return int(math.floor(g[0] + 0.5)), int(math.floor(g[1] + 0.5))


# ============================================================== coppie (prese)
def victim_offsets(gig_cfg, gig_fdata, gig_anchor, enemy_fdata):
    """per ogni fotogramma di GIG in grab_hold/knee/throw e ogni nemico: (dx, dy) tali che il punto di presa
    della vittima (specchiata, perché guarda GIG) cada sulle mani di GIG. Le coordinate sono in px dello sprite
    con GIG rivolto a destra. Restituisce {anim: [ {nemico: [dx, dy, anim, fotogramma]} ]} e gli scarti verticali."""
    res, errs = {}, []
    for name in PAIRS:
        if name not in gig_cfg["anims"]:
            continue
        an = gig_cfg["anims"][name]
        rows = []
        for i, fr in enumerate(an["frames"]):
            v = fr["victim"]
            fd = gig_fdata[name][i]
            ax, ay = gig_anchor[name][i]
            hands = mid(P(fd, "hand_l", True), P(fd, "hand_r", True))
            if v.get("gig") == "knee_r":
                hands = P(fd, "calf_r")
            row = {}
            for en in ENEMIES:
                efd_all = enemy_fdata.get(en)
                if not efd_all:
                    row[en] = [v.get("dx", 24), v.get("dy", 0), v["anim"], v["frame"]]
                    continue
                efd = efd_all[v["anim"]][v["frame"]]
                emode = C.char_cfg(en)["anims"][v["anim"]].get("anchor", "root")
                gx, gy = anchor_of(efd, emode, efd_all["_pel_h"])
                grip = v.get("grip", "neck")
                if grip == "neck":
                    gp = efd["points"]["neck"]
                elif grip == "chest":
                    gp = mid(P(efd, "spine_02"), P(efd, "spine_03", True))
                else:
                    gp = P(efd, "pelvis")
                # vittima specchiata attorno alla sua ancora
                rel_x = -(gp[0] - gx)
                rel_y = gp[1] - gy
                dx = (hands[0] - ax) - rel_x + v.get("dx_adj", 0)
                dy_ideal = (hands[1] - ay) - rel_y
                dy = v.get("dy", 0)
                errs.append((name, i, en, round(dy_ideal - dy, 1)))
                row[en] = [int(round(dx)), int(dy), v["anim"], v["frame"]]
            row["behind"] = bool(v.get("behind", False))
            rows.append(row)
        res[name] = rows
    return res, errs


# ============================================================== assemblaggio
def palette_remap(cfg, meta, allim):
    """riduzione della tavolozza su un insieme di fotogrammi -> (mappa, colori). pixel_cfg.pal_mode: "material"
    fonde solo toni vicini della stessa rampa (v7), "cel" fonde con i ruoli dei colori (pix_v7.reduce_cel),
    altrimenti riduzione globale in CIELAB."""
    pal = cfg["palette"]
    pm = cfg.get("pixel_cfg", {}).get("pal_mode")
    if pm == "material":
        import pix_v7
        sh_, _ = shader_for(cfg, meta)
        return pix_v7.reduce_by_ramp(allim, pal.get("max_colors", 32), sh_.pal, pal.get("protect", []))
    if pm == "cel":
        import pix_v7
        sh_, _ = shader_for(cfg, meta)
        cel = cfg.get("pixel_cfg", {}).get("cel") or {}
        pc = dict(cel.get("pal") or {})
        if "band_idx" not in pc:
            # i toni dei materiali sono gli indici della rampa usati dal cel
            bi = set(cel.get("idx", [1, 3]))
            for v in (cel.get("mat_idx") or {}).values():
                bi |= set(v)
            pc["band_idx"] = sorted(bi)
        return pix_v7.reduce_cel(allim, pal.get("max_colors", 32), sh_.pal, pal.get("protect", []), **pc)
    return PX.reduce_palette(allim, pal.get("max_colors", 32), pal.get("protect", []))


def step_assemble(cid):
    cfg = C.char_cfg(cid)
    meta = C.load_json(os.path.join(raw_dir(cid), "meta.json"))
    hcfg = cfg.get("boxes", {})
    names = list(cfg["anims"].keys())
    sprites = {n: load_pix(cid, n) for n in names}
    fdata = {n: C.load_json(os.path.join(raw_dir(cid), n, "frames.json")) for n in names}
    # riduzione della tavolozza su tutti i fotogrammi insieme
    allim = [s for n in names for s in sprites[n]]
    remap, colors = palette_remap(cfg, meta, allim)
    for n in names:
        sprites[n] = [PX.apply_remap(s, remap) for s in sprites[n]]
    C.say(f"  tavolozza {cid}: {len(colors)} colori")
    # ancore (nel fotogramma intero) e box
    anchors, frames_out, origins, inplace = {}, {}, {}, []
    for n in names:
        an = cfg["anims"][n]
        mode = an.get("anchor", "root")
        if mode == "root":
            inplace.append(n)
        if mode == "first":
            a0 = anchor_of(fdata[n][0], "root", guard_pelvis_h(cid, fdata))
            anchors[n] = [a0 for _ in fdata[n]]
        else:
            anchors[n] = [anchor_of(fd, mode, guard_pelvis_h(cid, fdata)) for fd in fdata[n]]
    # offset delle vittime (solo GIG)
    victims, vlog = {}, []
    if cid == "gig":
        enemy_fd = {}
        for en in ENEMIES:
            ed = {}
            for an_name in ("grabbed", "kneed", "thrown", "idle"):
                for base in (raw_dir(en), os.path.join(C.OUT, "bones", en)):
                    p = os.path.join(base, an_name, "frames.json")
                    if os.path.exists(p):
                        ed[an_name] = C.load_json(p)
                        break
            if len(ed) == 4:
                ed["_pel_h"] = guard_pelvis_h(en, ed)
                enemy_fd[en] = ed
        victims, vlog = victim_offsets(cfg, fdata, anchors, enemy_fd)
        if len(enemy_fd) < 2:
            C.say("  ATTENZIONE: offset delle vittime provvisori (mancano i dati dei nemici)")
    # ritaglio, deduplica, impacchettamento
    uniq, keys = [], {}
    ref = {}
    first_of = []
    normals_all = {n: load_pix_normals(cid, n) for n in names}
    for n in names:
        ref[n] = []
        origins[n] = []
        for fi, sp in enumerate(sprites[n]):
            c, o = crop(sp)
            h = hashlib.sha1(c.tobytes() + str(c.shape).encode()).hexdigest()
            if h not in keys:
                keys[h] = len(uniq)
                uniq.append(c)
                first_of.append((n, fi, o))
            ref[n].append(keys[h])
            origins[n].append(o)
    W, H, pos = pack([(c.shape[1], c.shape[0]) for c in uniq])
    atlas = np.zeros((H, W, 4), np.uint8)
    for c, (x, y) in zip(uniq, pos):
        atlas[y:y + c.shape[0], x:x + c.shape[1]] = c
    natlas = None
    if all(len(normals_all[n]) == len(sprites[n]) for n in names):
        natlas = np.zeros((H, W, 4), np.uint8)
        natlas[..., :3] = (128, 128, 255)
        for c, (x, y), (n, fi, (ox, oy)) in zip(uniq, pos, first_of):
            nm = normals_all[n][fi][oy:oy + c.shape[0], ox:ox + c.shape[1]]
            natlas[y:y + c.shape[0], x:x + c.shape[1]] = nm
    out_anims = {}
    for n in names:
        an = cfg["anims"][n]
        frs = []
        for i, fr in enumerate(an["frames"]):
            u = ref[n][i]
            x, y = pos[u]
            c = uniq[u]
            ox, oy = origins[n][i]
            ax, ay = anchors[n][i]
            fd = fdata[n][i]
            hurt = hurt_boxes(fd, fr.get("hurt", an.get("hurt", "std")), (ax, ay), hcfg)
            hit = [hit_box(fd, fr["hit"], (ax, ay))] if fr.get("hit") else []
            tags = list(fr.get("tags", []))
            if fr.get("hit") and "active" not in tags:
                tags.insert(0, "active")
            rec = {"rect": [int(x), int(y), int(c.shape[1]), int(c.shape[0])], "anchor": [ax - ox, ay - oy],
                   "ticks": int(fr["t"]), "hurt": hurt, "hit": hit, "events": list(fr.get("ev", [])), "tags": tags,
                   "dx": int(fr.get("dx", 0))}
            pts = fd.get("points", {})
            rp = {}
            for key, src_name in POINTS:
                if src_name in pts:
                    rp[key] = [int(round(pts[src_name][0] - ax)), int(round(pts[src_name][1] - ay))]
            if "fist_l" in rp and "fist_r" in rp:
                rp["grip"] = [(rp["fist_l"][0] + rp["fist_r"][0]) // 2, (rp["fist_l"][1] + rp["fist_r"][1]) // 2]
            if rp:
                rec["points"] = rp
            if cid == "gig" and n in PAIRS:
                rec["victim"] = victims[n][i]
            frs.append(rec)
        out_anims[n] = {"loop": bool(an.get("loop", False)), "frames": frs}
        frames_out[n] = sprites[n]
    data = {"id": cid, "format": 1, "image": cid + ".png", "pixels_per_meter": C.camera()["pixels_per_meter"], "animations": out_anims}
    fdir = final_dir(cid)
    os.makedirs(fdir, exist_ok=True)
    Image.fromarray(atlas, "RGBA").save(os.path.join(fdir, cid + ".png"), optimize=True)
    if natlas is not None:
        Image.fromarray(natlas, "RGBA").save(os.path.join(fdir, cid + "_n.png"), optimize=True)
        data["normal_image"] = cid + "_n.png"
    write_sprite_json(os.path.join(fdir, cid + ".json"), data)
    # piedi rispetto all'ancora (controllo della deriva: un piede che resta a terra non deve scivolare)
    feet = {}
    for n in names:
        feet[n] = []
        for fd, (ax, ay) in zip(fdata[n], anchors[n]):
            row = {}
            for s in "lr":
                fu, fv = fd["bones"]["foot_" + s][0], fd["bones"]["foot_" + s][1]
                row[s] = [round(fu - ax, 2), round(fv - ay, 2)]
            feet[n].append(row)
    C.save_json(os.path.join(fdir, cid + ".debug.json"),
                dict(inplace=inplace, origins=origins, feet=feet, palette=["#%06x" % k for k in colors],
                     guard_height_px=meta.get("guard_height_px"), victim_dy_error=vlog))
    C.say(f"  atlante {cid}: {W}x{H}, {len(uniq)} fotogrammi unici su {sum(len(v) for v in ref.values())}")
    if vlog:
        worst = max(abs(e[3]) for e in vlog)
        C.say(f"  prese: scarto verticale massimo {worst} px")
    return data


def write_sprite_json(path, data):
    """JSON compatto e leggibile: un fotogramma per riga."""
    lines = ["{", f'  "id": "{data["id"]}",', '  "format": 1,', f'  "image": "{data["image"]}",']
    if data.get("normal_image"):
        lines.append(f'  "normal_image": "{data["normal_image"]}",')
    lines += ['  "pixels_per_meter": %d,' % C.camera()["pixels_per_meter"], '  "animations": {']
    names = list(data["animations"].keys())
    for k, n in enumerate(names):
        an = data["animations"][n]
        lines.append(f'    "{n}": {{')
        lines.append(f'      "loop": {"true" if an["loop"] else "false"},')
        lines.append('      "frames": [')
        for j, f in enumerate(an["frames"]):
            s = json.dumps(f, ensure_ascii=False, separators=(", ", ": "))
            lines.append("        " + s + ("," if j < len(an["frames"]) - 1 else ""))
        lines.append("      ]")
        lines.append("    }" + ("," if k < len(names) - 1 else ""))
    lines += ["  }", "}", ""]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))
    json.load(open(tmp, encoding="utf-8"))
    os.replace(tmp, path)


def frames_from_atlas(cid, root=None):
    """ricostruisce i fotogrammi interi (stessa tela) dall'atlante e dal JSON: per tavole, GIF e scena."""
    d = os.path.join(root, cid) if root else final_dir(cid)
    data = C.load_json(os.path.join(d, cid + ".json"))
    atlas = np.asarray(Image.open(os.path.join(d, cid + ".png")).convert("RGBA"))
    return data, atlas


def sprite_of(atlas, f):
    x, y, w, h = f["rect"]
    return atlas[y:y + h, x:x + w]


def place(canvas, sp, ax, ay, anchor, mirror=False):
    """disegna lo sprite con l'ancora in (ax, ay) sulla tela (alpha 0/255)."""
    h, w = sp.shape[:2]
    if mirror:
        sp = sp[:, ::-1]
        x0 = ax - (w - 1 - anchor[0])
    else:
        x0 = ax - anchor[0]
    y0 = ay - anchor[1]
    H, W = canvas.shape[:2]
    for yy in range(h):
        Y = y0 + yy
        if not 0 <= Y < H:
            continue
        row = sp[yy]
        m = row[:, 3] > 0
        xs = np.nonzero(m)[0]
        for xx in xs:
            X = x0 + xx
            if 0 <= X < W:
                canvas[Y, X] = row[xx]


# ============================================================== tavole di controllo
def step_review(cid):
    data, atlas = frames_from_atlas(cid)
    rd = review_dir(cid)
    os.makedirs(rd, exist_ok=True)
    for f in glob.glob(os.path.join(rd, "anim_*.gif")) + glob.glob(os.path.join(rd, "sheet_*.png")):
        os.remove(f)
    for n, an in data["animations"].items():
        S = 160
        frames, anchors, boxes, labels, ticks = [], [], [], [], []
        for i, f in enumerate(an["frames"]):
            can = np.zeros((S, S, 4), np.uint8)
            place(can, sprite_of(atlas, f), 64, 128, f["anchor"])
            frames.append(can)
            anchors.append((64, 128))
            boxes.append((f["hurt"], f["hit"]))
            t = ",".join(x[:4] for x in f["tags"])
            ev = ",".join(e.replace("sfx:", "").replace("fx:", "")[:6] for e in f["events"])
            labels.append(f"#{i} {f['ticks']}t {t} {ev}".strip())
            ticks.append(f["ticks"])
        tot = sum(ticks)
        title = f"{cid} {n}: {len(frames)} fotogrammi, {tot} tick ({tot / 60:.2f} s){' ciclo' if an['loop'] else ''}"
        RV.contact_sheet(frames, labels, title, os.path.join(rd, f"sheet_{n}_4x.png"), scale=4, anchors=anchors,
                         boxes=boxes, sub="giallo = ancora, azzurro = hurtbox, rosso = hitbox")
        RV.contact_sheet(frames, [str(i) for i in range(len(frames))], f"{cid} {n} 1x",
                         os.path.join(rd, f"sheet_{n}_1x.png"), scale=1)
        RV.save_gif(frames * (3 if an["loop"] else 1), ticks * (3 if an["loop"] else 1),
                    os.path.join(rd, f"anim_{n}.gif"), scale=3)
    C.say(f"  tavole di controllo in {rd}")


def step_pairs_review(root=None):
    """tavola delle prese: GIG + vittima specchiata con gli offset del JSON, per entrambi i nemici."""
    g, ga = frames_from_atlas("gig", root)
    rows = []
    for en in ENEMIES:
        try:
            e, ea = frames_from_atlas(en, root)
        except FileNotFoundError:
            continue
        for name in PAIRS:
            for i, f in enumerate(g["animations"][name]["frames"]):
                v = f["victim"][en]
                vf = e["animations"][v[2]]["frames"][v[3]]
                can = np.zeros((150, 190, 4), np.uint8)
                ax, ay = 60, 130
                if f["victim"]["behind"]:
                    place(can, sprite_of(ea, vf), ax + v[0], ay + v[1], vf["anchor"], mirror=True)
                    place(can, sprite_of(ga, f), ax, ay, f["anchor"])
                else:
                    place(can, sprite_of(ga, f), ax, ay, f["anchor"])
                    place(can, sprite_of(ea, vf), ax + v[0], ay + v[1], vf["anchor"], mirror=True)
                rows.append((en, name, i, can, f["ticks"]))
    rd = os.path.join(C.OUT, "review", "pairs")
    os.makedirs(rd, exist_ok=True)
    for en in ENEMIES:
        sel = [r for r in rows if r[0] == en]
        if not sel:
            continue
        RV.contact_sheet([r[3] for r in sel], [f"{r[1]}#{r[2]}" for r in sel], f"prese GIG + {en} (vittima specchiata)",
                         os.path.join(rd, f"pairs_{en}_4x.png"), scale=3)
        RV.save_gif([r[3] for r in sel], [max(r[4], 8) for r in sel], os.path.join(rd, f"pairs_{en}.gif"), scale=3)
    C.say(f"  tavole delle prese in {rd}")


def step_scene(root=None):
    """scena di prova 480x270 (la risoluzione del gioco): i tre personaggi rivolti a destra e specchiati, su fondo scuro."""
    W, H = 480, 270
    can = np.zeros((H, W, 4), np.uint8)
    can[..., :3] = (18, 15, 36)
    can[..., 3] = 255
    can[188:261, :, :3] = (34, 26, 52)
    put = []
    for cid, x, y, an, fi, mir in (("thug_punk", 65, 220, "idle", 0, False), ("gig", 165, 238, "idle", 0, False),
                                   ("thug_bruiser", 273, 228, "idle", 0, True), ("thug_punk", 375, 210, "jab", 4, True),
                                   ("gig", 430, 255, "jab1", 1, True), ("gig", 115, 258, "kick", 3, False)):
        try:
            data, atlas = frames_from_atlas(cid, root)
        except FileNotFoundError:
            continue
        if an not in data["animations"]:
            continue
        frs = data["animations"][an]["frames"]
        f = frs[min(fi, len(frs) - 1)]
        put.append((y, cid, x, f, atlas, mir))
    for y, cid, x, f, atlas, mir in sorted(put, key=lambda t: t[0]):
        # ombra
        for dx in range(-12, 13):
            for dy in (-2, -1, 0, 1, 2):
                if (dx / 12.0) ** 2 + (dy / 2.0) ** 2 <= 1 and 0 <= y + dy < H and 0 <= x + dx < W:
                    can[y + dy, x + dx, :3] = (can[y + dy, x + dx, :3] * 0.55).astype(np.uint8)
        place(can, sprite_of(atlas, f), x, y, f["anchor"], mirror=mir)
    rd = os.path.join(C.OUT, "review")
    os.makedirs(rd, exist_ok=True)
    im = Image.fromarray(can, "RGBA").convert("RGB")
    im.save(os.path.join(rd, "scene_1x.png"))
    im.resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(rd, "scene_3x.png"))
    C.say(f"  scena di prova in {rd}")


# ============================================================== ritratti
def step_portrait(cid):
    cfg = C.char_cfg(cid)
    step_portrait_render(cid)
    d = os.path.join(C.OUT, "raw_portrait", cid, "portrait")
    meta = C.load_json(os.path.join(d, "meta.json"))
    sh, pcfg = shader_for(cfg, meta)
    pcfg = dict(pcfg)
    pcfg.update(cfg["portrait"].get("pixel_cfg", {}))
    fdata = C.load_json(os.path.join(d, "frames.json"))
    sprites, _ = PX.pixelize_sequence(d, fdata, meta["ss"], sh, pcfg, loop=False)
    sp = sprites[0]
    # stessa tavolozza dello sprite: ogni colore va al più vicino della tavolozza finale del personaggio
    dbg = os.path.join(final_dir(cid), cid + ".debug.json")
    if os.path.exists(dbg):
        pal = [PX.hx(c) for c in C.load_json(dbg)["palette"]]
        sp = snap_to_palette(sp, pal)
    # ritaglio 32x32 attorno al volto (centro testa)
    hc = fdata[0]["points"]["head_c"]
    pc = cfg["portrait"]
    cx = int(round(hc[0])) + pc.get("shift", [0, 0])[0]
    cy = int(round(hc[1])) + pc.get("shift", [0, 0])[1]
    x0, y0 = cx - 16, cy - 16
    out = np.zeros((32, 32, 4), np.uint8)
    for y in range(32):
        for x in range(32):
            X, Y = x0 + x, y0 + y
            if 0 <= X < sp.shape[1] and 0 <= Y < sp.shape[0]:
                out[y, x] = sp[Y, X]
    pd = os.path.join(C.OUT, "final", "portraits")
    os.makedirs(pd, exist_ok=True)
    Image.fromarray(out, "RGBA").save(os.path.join(pd, cid + ".png"))
    Image.fromarray(out, "RGBA").resize((256, 256), Image.NEAREST).save(os.path.join(review_dir(cid), "portrait_8x.png"))
    C.say(f"  ritratto {cid} pronto")


def snap_to_palette(sp, pal):
    out = sp.copy()
    a = out[..., 3] > 0
    px = out[a][:, :3].astype(np.float64)
    P = np.array(pal, np.float64)
    lp = PX._lab(px)
    lP = PX._lab(P)
    d = ((lp[:, None, :] - lP[None, :, :]) ** 2).sum(-1)
    out[a, :3] = P[d.argmin(1)].astype(np.uint8)
    return out


# ============================================================== validazione e pubblicazione
def step_validate(root=None, portraits=False):
    args = [sys.executable, "-I", os.path.join(C.HERE, "validate_sprites.py"), root or os.path.join(C.OUT, "final")]
    if portraits:
        args.append("--portraits")
    r = subprocess.run(args)
    return r.returncode == 0


def step_publish(ids):
    """copia nel gioco solo dopo la validazione: nome temporaneo e poi rinomina (os.replace)."""
    if not step_validate():
        raise SystemExit("validazione fallita: non pubblico")
    for cid in ids:
        src = final_dir(cid)
        dst = os.path.join(C.ASSETS, "sprites", cid)
        os.makedirs(dst, exist_ok=True)
        names = [cid + ".png", cid + ".json"]
        if os.path.exists(os.path.join(src, cid + "_n.png")):
            names.insert(1, cid + "_n.png")
        for fn in names:
            tmp = os.path.join(dst, "." + fn + ".tmp")
            shutil.copyfile(os.path.join(src, fn), tmp)
            os.replace(tmp, os.path.join(dst, fn))
        pp = os.path.join(C.OUT, "final", "portraits", cid + ".png")
        if os.path.exists(pp):
            pdst = os.path.join(C.ASSETS, "ui", "portraits")
            os.makedirs(pdst, exist_ok=True)
            tmp = os.path.join(pdst, "." + cid + ".png.tmp")
            shutil.copyfile(pp, tmp)
            os.replace(tmp, os.path.join(pdst, cid + ".png"))
        C.say(f"  pubblicato {cid} -> {dst}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step")
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--specs", default="Punch_Jab:1")
    ap.add_argument("--clips", default="")
    ap.add_argument("--step_n", type=int, default=1)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    ids = a.ids or IDS_ALL
    only = [x for x in a.only.split(",") if x] or None
    if a.step == "retarget":
        step_retarget(force=True)
        return
    if a.step == "validate":
        sys.exit(0 if step_validate(portraits=True) else 1)
    if a.step == "publish":
        step_publish(ids)
        return
    if a.step == "scene":
        step_scene()
        return
    if a.step == "pairs":
        step_pairs_review()
        return
    for cid in ids:
        C.say(f"== {cid}: {a.step}")
        if a.step == "preview":
            step_preview(cid, a.specs.split(","))
        elif a.step == "explore":
            step_explore(cid, a.clips.split(","), a.step_n)
        elif a.step == "render":
            step_render(cid, only)
        elif a.step == "bones":
            step_render(cid, only, bones_only=True)
        elif a.step == "pixel":
            step_pixel(cid, only)
        elif a.step == "assemble":
            step_assemble(cid)
        elif a.step == "review":
            step_review(cid)
        elif a.step == "portrait":
            step_portrait(cid)
        elif a.step == "post":
            step_pixel(cid, only)
            step_assemble(cid)
            step_review(cid)
        elif a.step == "all":
            step_render(cid)
            step_pixel(cid)
            step_assemble(cid)
            step_review(cid)
            if C.char_cfg(cid).get("portrait"):
                step_portrait(cid)
        else:
            raise SystemExit("passo sconosciuto: " + a.step)
    if a.step == "all":
        if "gig" in ids:
            # gli offset delle prese di GIG dipendono dai fotogrammi delle vittime: si ricalcolano alla fine
            C.say("== gig: offset delle prese con i nemici appena rifatti")
            step_assemble("gig")
            step_review("gig")
        step_validate(portraits=True)
        step_pairs_review()
        step_scene()


if __name__ == "__main__":
    main()
