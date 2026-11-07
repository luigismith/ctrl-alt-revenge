# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Percorsi, configurazioni e lancio di Blender per la pipeline dei personaggi."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
LAB = os.environ.get("CAR_LAB") or os.path.join(os.path.expanduser("~"), "ctrlaltrevenge-lab")
# Blender 4.5.15 del laboratorio: la cartella portatile su Windows, l'app sul Mac.
BLENDER = (os.path.join(LAB, "tools", "blender-4.5.15", "Blender.app", "Contents", "MacOS", "Blender")
           if sys.platform == "darwin" else os.path.join(LAB, "tools", "blender-4.5.15", "blender.exe"))
OUT = os.path.join(HERE, "out")
CHARS = os.path.join(HERE, "chars")
BLENDER_SCRIPTS = os.path.join(REPO, "tools", "blender")
ASSETS = os.path.join(REPO, "game", "assets")

SOURCES = dict(
    body=os.path.join(LAB, "sources", "chars", "ubc-body", "Superhero_Male_FullBody.gltf"),
    body_f=os.path.join(LAB, "sources", "chars", "ubc-body", "Superhero_Female_FullBody.gltf"),
    hair_dir=os.path.join(LAB, "sources", "chars", "ubc-hair"),
    ual1=os.path.join(LAB, "sources", "chars", "ual1-standard", "extracted", "Animation Library[Standard]",
                      "Unreal Engine", "AL_Standard.fbx"),
    ual2=os.path.join(LAB, "sources", "chars", "ual2-standard", "extracted", "Universal Animation Library 2 [Standard]",
                      "Unreal-Godot", "UAL2_Standard.glb"),
    m2m_json=os.path.join(LAB, "sources", "anim", "spike-out", "m2m_json"),
)


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path, data, indent=1):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=indent, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def camera():
    return load_json(os.path.join(HERE, "camera.json"))


def _merge(base, over):
    """unione ricorsiva: i dizionari si fondono, il resto (liste comprese) si sostituisce."""
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def char_cfg(cid):
    """configurazione del personaggio. Una variante ha "base" (il personaggio di partenza) e cambia solo
    quello che scrive; "anims_keep" dice quali animazioni della base tenere, nell'ordine della base, e
    "anims" le aggiunge o ne cambia i campi (un'animazione della base si fonde con quella della variante)."""
    cfg = load_json(os.path.join(CHARS, cid + ".json"))
    if "base" not in cfg:
        return cfg
    base = char_cfg(cfg["base"])
    keep = cfg.get("anims_keep")
    anims = {n: a for n, a in base["anims"].items() if keep is None or n in keep}
    for n, a in cfg.get("anims", {}).items():
        anims[n] = _merge(base["anims"].get(n, {}), a)
    over = {k: v for k, v in cfg.items() if k not in ("base", "anims_keep", "anims")}
    out = _merge(base, over)
    out["anims"] = anims
    return out


def run_blender(script, job, timeout=1800, tag="blender"):
    """lancia Blender in background con un file di lavoro; log in out/logs; errore se fallisce."""
    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    jpath = os.path.join(OUT, "jobs", f"{tag}-{stamp}.json")
    save_json(jpath, job)
    logp = os.path.join(OUT, "logs", f"{tag}-{stamp}.log")
    cmd = [BLENDER, "-b", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1",
           "--python", os.path.join(BLENDER_SCRIPTS, script), "--", jpath]
    t0 = time.time()
    with open(logp, "w", encoding="utf-8", errors="replace") as lf:
        try:
            r = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, timeout=timeout)
            code = r.returncode
        except subprocess.TimeoutExpired:
            code = 124
    txt = open(logp, encoding="utf-8", errors="replace").read()
    keep = [l for l in txt.splitlines() if l.startswith(("[char]", "[poses]", "[retarget]", "Traceback", "  File", "Error"))
            or "Error" in l]
    keep = [l for l in keep if "Cannot read" not in l and "_png.png" not in l]
    for l in keep[-40:]:
        print("   ", l[:220])
    print(f"   blender {script} {tag}: codice {code} in {time.time() - t0:.0f}s (log {logp})")
    if code != 0 or "Traceback" in txt:
        raise SystemExit(f"Blender fallito ({tag}), vedi {logp}")
    return logp


def run_blender_args(script, args, timeout=600, tag="blender"):
    """come run_blender, ma con argomenti dopo "--" (char_retarget.py)."""
    os.makedirs(os.path.join(OUT, "logs"), exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    logp = os.path.join(OUT, "logs", f"{tag}-{stamp}.log")
    cmd = [BLENDER, "-b", "--factory-startup", "--disable-autoexec", "--python-exit-code", "1",
           "--python", os.path.join(BLENDER_SCRIPTS, script), "--"] + list(args)
    t0 = time.time()
    with open(logp, "w", encoding="utf-8", errors="replace") as lf:
        try:
            code = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 124
    txt = open(logp, encoding="utf-8", errors="replace").read()
    for l in [l for l in txt.splitlines() if l.startswith(("[retarget]", "[scale]", "[footlock] max", "Traceback"))][-8:]:
        print("   ", l[:200])
    print(f"   blender {script} {tag}: codice {code} in {time.time() - t0:.0f}s")
    if code != 0 or "Traceback" in txt:
        raise SystemExit(f"Blender fallito ({tag}), vedi {logp}")


def base_job(cid, cfg, mode, out):
    cam = camera()
    job = dict(id=cid, mode=mode, out=out, body=SOURCES["body_f" if cfg.get("corpo") == "f" else "body"], hair_dir=SOURCES["hair_dir"],
               ual1=SOURCES["ual1"], ual2=SOURCES["ual2"], camera=cam, outfit=cfg["outfit"],
               outfit_cfg=cfg.get("outfit_cfg", {}), hair_meshes=cfg.get("hair_meshes", []),
               reshape=cfg.get("reshape"), proportions=cfg.get("proportions", {}),
               normals=cfg.get("normals", "proxy"), frame_px=cfg.get("frame_px", 208),
               beauty_cols=cfg.get("beauty_cols", {}), authored=cfg.get("authored", []),
               pose_params=cfg.get("pose_params", {}),
               action_libs=[os.path.join(OUT, p) if not os.path.isabs(p) else p for p in cfg.get("action_libs", [])])
    return job


def say(*a):
    print(*a, flush=True)
    sys.stdout.flush()
