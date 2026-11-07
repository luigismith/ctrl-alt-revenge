#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Le voci delle battute con Qwen3-TTS in locale: «progetta e clona» (decisione 92 della storia).

Fasi, da lanciare in ordine (ognuna riprende da dove trova i file):
  riferimenti  VoiceDesign 1.7B fa il riferimento di ogni voce progettata (il messo usa la ripresa dei campioni)
  prese        Base 0.6B clona il riferimento, una presa per seme, per ogni battuta che ha la voce
  scegli       Whisper trascrive ogni presa; vince quella con meno lettere sbagliate (CER)
  finali       trattamento ffmpeg, tempi delle parole, inviluppo per la bocca, .ogg e manifest.json
  tv           solo l'ultimo passo: rifà gli .ogg da _finali con il filtro TV (livello di voci.json, o --tv)
  demo         le scene montate, in .wav e in .mp4 con i sottotitoli

Uso (Python isolato, con il Python di <laboratorio>\\tts\\venv-qwen3; vedi LEGGIMI.md):
  python -I -X utf8 tools/voci/voci.py <fase> [--capitolo prologo] [--voce <voce>=<proposta>] [--solo <voce>]
        [--tv <livello>|senza] [--uscita <cartella>] [--battute <file>] [--voci <file>] [--lab <cartella>]

Di default le battute sono docs/lore/battute/<capitolo>.json, la regia delle voci docs/lore/voci/voci.json
(tutte e due private, fuori da git) e il laboratorio è %CAR_LAB%\\tts, altrimenti %USERPROFILE%\\ctrlaltrevenge-lab\\tts.
Niente download: i modelli stanno in <lab>\\modelli. L'audio contiene le battute: resta nel laboratorio.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import soundfile as sf

TICK = 60  # tick al secondo del gioco
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAB = os.environ.get("CAR_LAB") or os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"), "ctrlaltrevenge-lab")
TTS = os.path.join(LAB, "tts")


# ---------------------------------------------------------------- comuni

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def tts_text(text, pron):
    """Il testo per il TTS: pronunce del dizionario, a parole intere."""
    out = text
    for k, v in pron.items():
        if k == "nota":
            continue
        out = re.sub(r"(?<![\w+])" + re.escape(k) + r"(?![\w+])", v, out)
    return out


def tidy(wav, sr, pad_s=0.06):
    wav = np.asarray(wav, dtype=np.float32).flatten()
    if wav.size == 0:
        return wav
    thr = 10 ** (-45 / 20) * max(1e-9, float(np.max(np.abs(wav))))
    idx = np.where(np.abs(wav) > thr)[0]
    if idx.size:
        pad = int(pad_s * sr)
        wav = wav[max(0, idx[0] - pad): min(wav.size, idx[-1] + pad)]
    peak = float(np.max(np.abs(wav))) or 1.0
    return wav * (10 ** (-1 / 20) / peak)


def trim(wav, sr, pad_s=0.04):
    """Toglie il silenzio ai bordi (sotto -45 dB dal picco) senza cambiare il volume."""
    wav = np.asarray(wav, dtype=np.float32).flatten()
    thr = 10 ** (-45 / 20) * max(1e-9, float(np.max(np.abs(wav))))
    idx = np.where(np.abs(wav) > thr)[0]
    if idx.size:
        pad = int(pad_s * sr)
        wav = wav[max(0, idx[0] - pad): min(wav.size, idx[-1] + pad)]
    return wav


def seed_all(s):
    import torch
    torch.manual_seed(int(s))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(s))
    np.random.seed(int(s) % (2 ** 32))


def device():
    import torch
    return "cuda:0" if torch.cuda.is_available() else "cpu"


def voiced_lines(a, cfg, lines):
    """[(scena, id, chiave voce, testo)] nell'ordine del file delle battute."""
    who = cfg["chi_ha_la_voce"][a.capitolo]
    out = []
    for scena, battute in lines["scene"].items():
        for lid, text in battute.items():
            v = who.get(scena, {}).get(lid)
            if v:
                out.append((scena, lid, v, text))
    return out


def resolve(cfg, vkey):
    """Chiave voce (per esempio messo_porta) -> (voce base, configurazione della voce base, configurazione propria)."""
    own = cfg["voci"][vkey]
    base = own.get("come", vkey)
    return base, cfg["voci"][base], own


def overrides(a):
    out = {}
    for o in a.voce or []:
        k, v = o.split("=", 1)
        out[k] = v
    return out


def voice_name(cfg, base, ov):
    return ov.get(base) or cfg["voci"][base]["voce"]


def ref_paths(a, base, name):
    d = os.path.join(a.lab, "voci", "riferimenti")
    return os.path.join(d, "%s_%s.wav" % (base, name)), os.path.join(d, "%s_%s.txt" % (base, name))


def out_root(a):
    return a.uscita or os.path.join(a.lab, "voci", a.capitolo)


# ---------------------------------------------------------------- fasi

def fase_riferimenti(a, cfg, lines):
    import torch
    from qwen_tts import Qwen3TTSModel
    ov = overrides(a)
    model = None
    for base, v in cfg["voci"].items():
        if "come" in v:
            continue
        names = list(v.get("proposte", {}).keys()) or [v["voce"]]
        for name in names:
            wav_p, txt_p = ref_paths(a, base, name)
            if os.path.exists(wav_p):
                continue
            os.makedirs(os.path.dirname(wav_p), exist_ok=True)
            r = v.get("riferimento")
            if r and "file_campione" in r:  # ripresa già fatta: si copia
                cap, scena, ids = r["testo_da"]
                text = r["unione"].join(lines["scene"][scena][i] for i in ids)
                shutil.copyfile(os.path.join(a.lab, r["file_campione"]), wav_p)
                open(txt_p, "w", encoding="utf-8").write(text)
                print("riferimento %s_%s: copiato dai campioni" % (base, name), flush=True)
                continue
            p = v["proposte"][name]
            if model is None:
                model = Qwen3TTSModel.from_pretrained(os.path.join(a.lab, "modelli", cfg["modelli"]["progetto"]["cartella"]),
                                                      device_map=device(), dtype=torch.bfloat16, attn_implementation="sdpa")
            text = v["riferimento_testo"]
            seed_all(p["seed"])
            t0 = time.perf_counter()
            wavs, sr = model.generate_voice_design(text=text, instruct=p["instruct"], language="Italian")
            w = tidy(wavs[0], sr)
            sf.write(wav_p, w, sr, subtype="PCM_16")
            open(txt_p, "w", encoding="utf-8").write(text)
            print("riferimento %s_%s: %.1f s in %.1f s" % (base, name, w.size / sr, time.perf_counter() - t0), flush=True)
    _ = ov


def fase_prese(a, cfg, lines):
    import torch
    from qwen_tts import Qwen3TTSModel
    ov = overrides(a)
    model = Qwen3TTSModel.from_pretrained(os.path.join(a.lab, "modelli", cfg["modelli"]["clone"]["cartella"]),
                                          device_map=device(), dtype=torch.bfloat16, attn_implementation="sdpa")
    prompts = {}
    root = out_root(a)
    log_p = os.path.join(root, "_prese.json")
    log = load(log_p) if os.path.exists(log_p) else {}
    for scena, lid, vkey, text in voiced_lines(a, cfg, lines):
        base, bcfg, own = resolve(cfg, vkey)
        if a.solo and base not in a.solo:
            continue
        name = voice_name(cfg, base, ov)
        if (base, name) not in prompts:
            wav_p, txt_p = ref_paths(a, base, name)
            prompts[(base, name)] = model.create_voice_clone_prompt(ref_audio=wav_p, ref_text=open(txt_p, encoding="utf-8").read())
        say = tts_text(text, cfg["pronunce"])
        for s in own.get("semi") or bcfg["semi"]:
            fn = os.path.join(root, "_prese", scena, "%s__%s__%d.wav" % (lid, name, s))
            if os.path.exists(fn):
                continue
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            seed_all(s)
            t0 = time.perf_counter()
            wavs, sr = model.generate_voice_clone(text=say, language="Italian", voice_clone_prompt=prompts[(base, name)])
            w = tidy(wavs[0], sr)
            sf.write(fn, w, sr, subtype="PCM_16")
            dt = time.perf_counter() - t0
            log[os.path.relpath(fn, root)] = {"scena": scena, "id": lid, "voce": vkey, "proposta": name, "seme": s,
                                              "testo_tts": say, "durata_s": round(w.size / sr, 2), "calcolo_s": round(dt, 1)}
            save(log, log_p)
            print("%-40s %5.2f s in %5.1f s" % (os.path.relpath(fn, root), w.size / sr, dt), flush=True)


class Asr:
    def __init__(self, wdir):
        import torch
        from transformers import pipeline
        self.p = pipeline("automatic-speech-recognition", model=wdir, device=0 if torch.cuda.is_available() else -1)

    def run(self, path, words=False):
        import librosa
        y, _ = librosa.load(path, sr=16000, mono=True)
        kw = {"generate_kwargs": {"language": "it", "task": "transcribe", "num_beams": 5}}
        if words:
            kw["return_timestamps"] = "word"
        r = self.p({"raw": y, "sampling_rate": 16000}, **kw)
        return r


NUM = {"1": "uno", "2": "due", "3": "tre"}


def norm_words(s):
    s = s.lower().replace("’", "'")
    s = re.sub(r"[^\w\sàèéìíòóùú']", " ", s).replace("'", " ")
    return [NUM.get(w, w) for w in s.split()]


def letters(s):
    import unicodedata
    t = "".join(norm_words(s)).replace("h", "")
    return [c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn"]


def edit_rate(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
            prev, d[j] = d[j], cur
    return d[len(hyp)] / max(1, len(ref))


def fase_scegli(a, cfg, lines):
    root = out_root(a)
    log = load(os.path.join(root, "_prese.json"))
    asr = Asr(os.path.join(a.lab, "modelli", cfg["modelli"]["controllo"]["cartella"]))
    ov = overrides(a)
    sc_p = os.path.join(root, "_scelte.json")
    scelte = load(sc_p) if os.path.exists(sc_p) else {}
    for scena, lid, vkey, text in voiced_lines(a, cfg, lines):
        base, _, _ = resolve(cfg, vkey)
        if a.solo and base not in a.solo:
            continue
        name = voice_name(cfg, base, ov)
        cands = [(k, r) for k, r in log.items() if r["scena"] == scena and r["id"] == lid and r["proposta"] == name]
        res = []
        for k, r in cands:
            hyp = asr.run(os.path.join(root, k))["text"].strip()
            c = edit_rate(letters(text), letters(hyp))
            res.append({"presa": k, "seme": r["seme"], "durata_s": r["durata_s"], "sentito": hyp, "cer": round(c, 3)})
        durs = sorted(x["durata_s"] for x in res)
        med = durs[len(durs) // 2]
        # Vince il CER più basso; a pari merito (entro 0,01) la durata più vicina alla mediana.
        # Il punto, il punto interrogativo e l'esclamativo finali che sente Whisper devono tornare con il testo.
        end = lambda s: (s.strip() or ".")[-1] if (s.strip() or ".")[-1] in ".?!" else "."
        res.sort(key=lambda x: (round(x["cer"] / 0.01), end(x["sentito"]) != end(text), abs(x["durata_s"] - med)))
        forced = cfg.get("scelte_a_mano", {}).get(a.capitolo, {}).get("%s/%s" % (scena, lid))
        if forced is not None and not ov:
            res.sort(key=lambda x: x["seme"] != forced)
        scelte["%s/%s" % (scena, lid)] = {"scelta": res[0], "candidate": res, "a_mano": forced is not None and not ov}
        b = res[0]
        print("%-22s seme %d CER %.3f %.2f s | %s" % (scena + "/" + lid, b["seme"], b["cer"], b["durata_s"], b["sentito"]), flush=True)
    save(scelte, os.path.join(root, "_scelte.json"))


def ffmpeg(args):
    """L'ffmpeg del laboratorio se c'è, altrimenti quello nel PATH."""
    exe = os.path.join(LAB, "tools", "ffmpeg", "bin", "ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    subprocess.run([exe if os.path.exists(exe) else "ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args, check=True)


def envelope(wav, sr):
    """Un valore 0-100 per tick: RMS in dB fra -48 e -12, attacco svelto e rilascio più lento."""
    hop = sr / TICK
    n = int(np.ceil(wav.size / hop))
    vals, last = [], 0.0
    for i in range(n):
        seg = wav[int(i * hop): int((i + 1) * hop)]
        rms = float(np.sqrt(np.mean(seg ** 2))) if seg.size else 0.0
        db = 20 * np.log10(max(rms, 1e-6))
        x = min(1.0, max(0.0, (db + 48) / 36))
        last = x if x > last else last * 0.55 + x * 0.45
        vals.append(int(round(last * 100)))
    return vals


def align_words(text, chunks, dur):
    """Tempi (inizio, fine) per ogni parola del testo del gioco (split sugli spazi), dai tempi delle parole di Whisper."""
    toks = text.split()
    wl = [(c["text"].strip(), c["timestamp"][0], c["timestamp"][1]) for c in chunks if c["text"].strip()]
    if wl and len(norm_words(" ".join(t for t, _, _ in wl))) == len(norm_words(text)) and len(wl) == len(toks):
        return [[round(s, 3), round(e if e is not None else s, 3)] for _, s, e in wl], "whisper"
    # Proporzionale alle lettere, fra l'inizio e la fine del parlato sentiti da Whisper.
    t0 = wl[0][1] if wl else 0.06
    t1 = (wl[-1][2] or wl[-1][1]) if wl else dur - 0.06
    tot = sum(max(1, len(letters(t))) for t in toks)
    out, acc = [], 0
    for t in toks:
        n = max(1, len(letters(t)))
        out.append([round(t0 + (t1 - t0) * acc / tot, 3), round(t0 + (t1 - t0) * (acc + n) / tot, 3)])
        acc += n
    return out, "proporzionale"


def tv_livello(a, cfg):
    tv = cfg.get("tv") or {}
    return (getattr(a, "tv", None) or tv.get("livello") or "senza"), tv


def codifica(a, cfg, tr, wav_in, ogg, livello=None):
    """L'ultimo passo, comune a tutte le voci: il filtro TV a tubo catodico sopra il trattamento, poi Ogg Vorbis.
    Il .wav di _finali resta com'è (senza filtro), così il passo si rifà quando cambia il livello."""
    liv, tv = tv_livello(a, cfg)
    liv = livello or liv
    sr = int(tv.get("campionamento_hz", 24000))
    if liv == "senza" or liv not in tv.get("livelli", {}):
        ffmpeg(["-i", wav_in, "-af", "aresample=%d" % sr, "-ac", "1", "-c:a", "libvorbis", "-q:a", "6", ogg])
        return "senza"
    p = tv["livelli"][liv]
    target = re.findall(r"loudnorm=I=(-?\d+(?:\.\d+)?)", cfg["trattamenti"][tr])
    dur = sf.info(wav_in).duration
    f = 0.03
    voce = ("highpass=f={passa_alto_hz}:poles=2,lowpass=f={passa_basso_hz}:poles=2,"
            "equalizer=f={presenza_hz}:t=q:w=1.4:g={presenza_db},"
            "volume={saturazione_db}dB,asoftclip=type=tanh,volume=-{saturazione_db}dB,"
            "acompressor=threshold=-22dB:ratio={compressione}:attack=4:release=70,"
            "aecho=0.9:0.9:{stanza_ms}:{stanza},").format(**p)
    voce += "loudnorm=I=%s:TP=-1.5:LRA=6,aresample=%d" % (target[-1] if target else "-18", sr)
    ronzio = ("sine=f=%s:sample_rate=%d:duration=%.3f,afade=t=in:d=%.2f,afade=t=out:st=%.3f:d=%.2f,volume=%sdB"
              % (tv.get("ronzio_hz", 15625), sr, dur, f, max(0.0, dur - f), f, p["ronzio_db"]))
    fc = "[0:a]%s[v];%s[r];[v][r]amix=inputs=2:duration=first:normalize=0[o]" % (voce, ronzio)
    ffmpeg(["-i", wav_in, "-filter_complex", fc, "-map", "[o]", "-ac", "1", "-c:a", "libvorbis", "-q:a", "6", ogg])
    return liv


def fase_tv(a, cfg, lines):
    root = out_root(a)
    man_p = os.path.join(root, "manifest.json")
    man = load(man_p)
    for key, b in man["battute"].items():
        scena, lid = key.split("/")
        b["tv"] = codifica(a, cfg, b["trattamento"], os.path.join(root, "_finali", scena, lid + ".wav"), os.path.join(root, b["file"]))
    liv, tv = tv_livello(a, cfg)
    man["tv"] = liv
    man["campionamento_hz"] = int(tv.get("campionamento_hz", 24000))
    save(man, man_p)
    print("filtro TV:", liv, "su", len(man["battute"]), "battute")


def fase_finali(a, cfg, lines):
    root = out_root(a)
    scelte = load(os.path.join(root, "_scelte.json"))
    log = load(os.path.join(root, "_prese.json"))
    asr = Asr(os.path.join(a.lab, "modelli", cfg["modelli"]["controllo"]["cartella"]))
    ov = overrides(a)
    man_p = os.path.join(root, "manifest.json")
    man = load(man_p) if os.path.exists(man_p) else {"formato": 1, "battute": {}}
    for scena, lid, vkey, text in voiced_lines(a, cfg, lines):
        base, bcfg, own = resolve(cfg, vkey)
        if a.solo and base not in a.solo:
            continue
        key = "%s/%s" % (scena, lid)
        sc = scelte[key]["scelta"]
        src = os.path.join(root, sc["presa"])
        tr = own.get("trattamento") or bcfg["trattamento"]
        wav_out = os.path.join(root, "_finali", scena, lid + ".wav")
        os.makedirs(os.path.dirname(wav_out), exist_ok=True)
        ffmpeg(["-i", src, "-af", cfg["trattamenti"][tr] + ",aresample=24000", "-ac", "1", "-c:a", "pcm_s16le", wav_out])
        w, sr = sf.read(wav_out, dtype="float32")
        w = trim(w, sr)  # solo i bordi: il volume resta quello del loudnorm
        sf.write(wav_out, w, sr, subtype="PCM_16")
        r = asr.run(wav_out, words=True)
        dur = w.size / sr
        parole, metodo = align_words(text, r.get("chunks", []), dur)
        ogg_rel = "%s/%s.ogg" % (scena, lid)
        ogg = os.path.join(root, scena, lid + ".ogg")
        os.makedirs(os.path.dirname(ogg), exist_ok=True)
        liv = codifica(a, cfg, tr, wav_out, ogg)
        name = voice_name(cfg, base, ov)
        man["battute"][key] = {
            "file": ogg_rel,
            "chi": base,
            "voce": name,
            "trattamento": tr,
            "tv": liv,
            "durata_s": round(dur, 3),
            "testo_sha1": hashlib.sha1(text.encode("utf-8")).hexdigest(),
            "parole": parole,
            "parole_da": metodo,
            "inviluppo": envelope(w, sr),
            "seme": sc["seme"],
            "cer": sc["cer"],
            "licenza": "Qwen3-TTS-12Hz-0.6B-Base (Apache-2.0), voce progettata con Qwen3-TTS-12Hz-1.7B-VoiceDesign (Apache-2.0) da una descrizione, nessuna persona reale",
        }
        print("%-22s %.2f s, parole: %s, CER %.3f" % (key, dur, metodo, sc["cer"]), flush=True)
    man["nota"] = ("Voci delle battute (decisione 92). Una voce per id di battuta, scena/id come in battute/%s.json. "
                   "file: relativo a questo manifest. parole: [inizio, fine] in secondi per ogni parola del testo diviso sugli spazi. "
                   "inviluppo: un valore 0-100 per tick (60 al secondo) per la bocca e le luci di Tere. testo_sha1: se non torna con il testo "
                   "della battuta, la voce è vecchia e va rifatta." % a.capitolo)
    man["inviluppo_tick_al_s"] = TICK
    liv, tv = tv_livello(a, cfg)
    man["tv"] = liv
    man["campionamento_hz"] = int(tv.get("campionamento_hz", 24000))
    man["generato"] = time.strftime("%Y-%m-%d %H:%M")
    save(man, man_p)


def ass_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return "%d:%02d:%05.2f" % (h, m, s)


def fase_demo(a, cfg, lines):
    """Le scene in ordine di copione: voce dove c'è, silenzio col testo per chi non ha voce. Sottotitoli col nome."""
    root = out_root(a)
    man = load(os.path.join(root, "manifest.json"))
    pd = cfg["pause_demo"]
    sr_man = int(man.get("campionamento_hz", 24000))
    who_names = cfg.get("nomi_demo", {})  # prefisso dell'id della battuta -> nome nei sottotitoli
    sr = sr_man
    seq, subs, t = [], [], 0.0
    scenes = [s for s in lines["scene"] if any(k.startswith(s + "/") for k in man["battute"])]
    for scena in scenes:
        title = scena.upper().replace("_", " ")
        subs.append((t, t + 1.6, "", "— %s —" % title))
        seq.append(np.zeros(int(sr * 2.0), dtype=np.float32)); t += 2.0
        for lid, text in lines["scene"][scena].items():
            key = "%s/%s" % (scena, lid)
            spk = who_names.get(re.sub(r"_\d+$", "", lid), lid.split("_")[0].upper())
            if key in man["battute"]:
                w, _ = sf.read(os.path.join(root, man["battute"][key]["file"]), dtype="float32")
                d = w.size / sr
            else:
                d = max(pd["gig_minimo_s"], len(text) / pd["gig_caratteri_al_s"])
                w = np.zeros(int(sr * d), dtype=np.float32)
                spk += " (testo)"
            subs.append((t, t + d + pd["dopo_voce_s"] * 0.9, spk, text))
            seq += [w, np.zeros(int(sr * pd["dopo_voce_s"]), dtype=np.float32)]
            t += d + pd["dopo_voce_s"]
        seq.append(np.zeros(int(sr * 1.0), dtype=np.float32)); t += 1.0
    ddir = os.path.join(a.lab, "voci", "demo")
    os.makedirs(ddir, exist_ok=True)
    base = "demo_voci_%s%s" % (a.capitolo, ("_" + "_".join(o.replace("=", "-") for o in a.voce)) if a.voce else "")
    sf.write(os.path.join(ddir, base + ".wav"), np.concatenate(seq), sr, subtype="PCM_16")
    ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 960", "PlayResY: 540", "",
           "[V4+ Styles]",
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
           "Style: T,Consolas,30,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,60,60,80,1",
           "Style: N,Consolas,24,&H00FFF000,&H00FFF000,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,2,0,2,60,60,130,1",
           "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for s, e, spk, text in subs:
        if spk:
            ass.append("Dialogue: 0,%s,%s,N,,0,0,0,,%s" % (ass_time(s), ass_time(e), spk))
        ass.append("Dialogue: 0,%s,%s,T,,0,0,0,,%s" % (ass_time(s), ass_time(e), text))
    open(os.path.join(ddir, base + ".ass"), "w", encoding="utf-8").write("\n".join(ass) + "\n")
    cwd = os.getcwd()
    os.chdir(ddir)
    try:
        ffmpeg(["-f", "lavfi", "-i", "color=c=0x101418:s=960x540:r=30", "-i", base + ".wav",
                "-vf", "drawbox=x=0:y=0:w=960:h=64:color=black:t=fill,drawbox=x=0:y=476:w=960:h=64:color=black:t=fill,ass=" + base + ".ass",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", base + ".mp4"])
    finally:
        os.chdir(cwd)
    print(os.path.join(ddir, base + ".mp4"), "%.1f s" % t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fase", choices=["riferimenti", "prese", "scegli", "finali", "tv", "demo"])
    ap.add_argument("--capitolo", default="prologo")
    ap.add_argument("--battute", help="di default docs/lore/battute/<capitolo>.json")
    ap.add_argument("--voci", default=os.path.join(REPO, "docs", "lore", "voci", "voci.json"))
    ap.add_argument("--lab", default=TTS, help="la cartella tts del laboratorio")
    ap.add_argument("--voce", action="append", help="voce=proposta, per provare un'altra proposta")
    ap.add_argument("--solo", action="append", help="solo questa voce base (messo, tere)")
    ap.add_argument("--tv", help="livello del filtro TV al posto di quello di voci.json (o senza)")
    ap.add_argument("--uscita", help="cartella di uscita al posto di <lab>\\voci\\<capitolo>")
    a = ap.parse_args()
    a.battute = a.battute or os.path.join(REPO, "docs", "lore", "battute", a.capitolo + ".json")
    cfg, lines = load(a.voci), load(a.battute)
    {"riferimenti": fase_riferimenti, "prese": fase_prese, "scegli": fase_scegli,
     "finali": fase_finali, "tv": fase_tv, "demo": fase_demo}[a.fase](a, cfg, lines)


if __name__ == "__main__":
    sys.exit(main())
