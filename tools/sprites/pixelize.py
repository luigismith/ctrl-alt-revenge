# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Post-processo dei G-buffer di tools/blender/char_build.py: da render a pixel art (porting di pix6.py, v6/v6.1).

Cosa fa, per ogni fotogramma (blocchi ss x ss -> 1 pixel):
  * etichetta del materiale per maggioranza, con priorità ai dettagli (occhio luminoso, anelli cyan,
    sopracciglia, bocca...) e almeno 1 pixel per dettaglio presente nel render;
  * ombre in forme: fino a 4 bande per materiale (n·L meno occlusione ambientale dalla profondità),
    rampe con spostamento di tinta, gruppi di colore piccoli fusi coi vicini, 1-2 pixel di riflesso
    su capelli, cuoio e metallo;
  * linee interne dove la profondità salta, riflesso magenta solo a tratti continui, contorno esterno
    di 1 px, pulizia dei pixel orfani;
  * isteresi compensata dal movimento delle ossa (sagoma, etichette e bande restano ferme se il
    cambiamento è minimo): niente pixel che "friggono" da un fotogramma all'altro.
La tavolozza di ogni personaggio sta nel suo JSON (tools/sprites/chars/<id>.json); reduce_palette()
la porta a non più di max_colors (40) colori su tutti i fotogrammi insieme.

Cel shading (blocco pixel_cfg.cel del JSON, dal 4 novembre 2026): al posto delle 4 bande ogni materiale ha toni
fissi, cioè soglie su n·L e l'indice della rampa per ogni tono (cel.thr e cel.idx, per materiale cel.mat_thr e
cel.mat_idx: due toni quasi ovunque, un terzo solo dove serve ai volumi). L'occlusione resta solo nei contatti
(ascelle, fra le gambe, sotto il mento), le normali si lisciano dentro ogni parte del corpo, le pieghe stampate
tornano nel loro materiale e linee, contorno colorato e isole troppo piccoli si tolgono.
"""
import colorsys
import math
import os

import numpy as np
from scipy import ndimage

import pix_v7 as V7

NID = 64
PART_BONE = {1: "spine_02", 2: "Head", 3: "upperarm_l", 4: "lowerarm_l", 5: "hand_l", 6: "upperarm_r",
             7: "lowerarm_r", 8: "hand_r", 9: "thigh_l", 10: "calf_l", 11: "foot_l", 12: "thigh_r",
             13: "calf_r", 14: "foot_r"}
FEATURES = ("EYE_GLOW", "EYE_DARK", "BROW", "MOUTH", "EYE_SOCKET", "NOSE_SHADOW", "KNUCKLE", "BEARD_EDGE",
            "HAIR_TIE", "STUD", "LACE", "SKIN_CREASE", "PATCH")
N4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def tohex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(max(0, min(255, c)))) for c in rgb)


def hue_toward(h, target, amt):
    d = ((target - h + 180) % 360) - 180
    return (h + max(-abs(d), min(abs(d), amt * np.sign(d) if d else 0))) % 360


def hs_ramp(mid, dark_target=255.0, light_target=50.0, dh_dark=14.0, dh_light=9.0, vd=0.70, vl=1.22,
            sd=1.06, sl=0.90, vh=1.13, sh=0.82, **_):
    """rampa di 6 colori da un colore medio: [linea, ombra, medio, luce, luce piena, riflesso], con la tinta
    che scivola verso il blu-viola nelle ombre e verso il giallo nelle luci (dalla v6). La "luce piena" è la
    quarta banda delle ombre in forme (spalle, braccia, pieghe rivolte alla luce chiave), più chiara e calda
    della luce ma ancora satura; il riflesso resta per i punti di 1-2 px su capelli, cuoio e metallo."""
    r, g, b = [c / 255.0 for c in hx(mid)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h *= 360

    def mk(hh, ss, vv):
        rr, gg, bb = colorsys.hsv_to_rgb((hh % 360) / 360.0, max(0, min(1, ss)), max(0, min(1, vv)))
        return tohex((rr * 255, gg * 255, bb * 255))
    shadow = mk(hue_toward(h, dark_target, dh_dark), s * sd, v * vd)
    line = mk(hue_toward(h, dark_target, dh_dark * 1.8), min(1, s * 1.12 + 0.05), v * 0.42)
    light = mk(hue_toward(h, light_target, dh_light), s * sl, min(1.0, v * vl + 0.03))
    high = mk(hue_toward(h, light_target, dh_light * 1.5), s * sl * sh, min(1.0, v * vl * vh + 0.06))
    hi = mk(hue_toward(h, light_target, dh_light * 1.6), s * 0.5, min(1.0, v * 1.45 + 0.12))
    return [line, shadow, mid, light, high, hi]


def build_palette(pcfg):
    P = {}
    for name, r in pcfg["ramps"].items():
        P[name] = list(r["list"]) if "list" in r else hs_ramp(**r)
        if "override" in r:
            for k, c in r["override"].items():
                P[name][int(k)] = c
    P["OUT"] = [pcfg.get("outline", "#140e1e")] * 5
    P["RIM"] = [pcfg.get("rim", "#e0559b")] * 5
    return P


# ============================================================== caricamento e campionamento
def load_frame(path):
    z = np.load(path)
    a = z["alpha"].astype(bool)
    ids = z["ids"].astype(np.int32)
    n2 = z["n"].astype(np.float32)
    nx, ny = n2[..., 0], n2[..., 1]
    nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0, 1))
    n = np.stack([nx, ny, nz], -1)
    d = z["depth"].astype(np.float32)
    part = z["part"].astype(np.int32)
    ids[~a] = 0
    part[~a] = 0
    return dict(a=a, ids=ids, n=n, d=d, part=part)


def blocks(x, s):
    H, W = x.shape[:2]
    h, w = H // s, W // s
    x = x[:h * s, :w * s]
    x = x.reshape(h, s, w, s, *x.shape[2:])
    x = np.moveaxis(x, 2, 1)
    return x.reshape(h, w, s * s, *x.shape[4:])


def shifted(arr, dy, dx, fill):
    H, W = arr.shape[:2]
    out = np.full_like(arr, fill)
    ys = slice(max(dy, 0), H + min(dy, 0))
    yd = slice(max(-dy, 0), H + min(-dy, 0))
    xs = slice(max(dx, 0), W + min(dx, 0))
    xd = slice(max(-dx, 0), W + min(-dx, 0))
    out[yd, xd] = arr[ys, xs]
    return out


def ao_hi(F, ss, r_px=(1.5, 3.0), eps=0.03):
    """occlusione in spazio schermo dalla profondità (quota di campioni vicini davanti al pixel)."""
    a, d = F["a"], F["d"]
    dd = np.where(a, d, 1e9)
    occ = np.zeros(a.shape, np.float32)
    nsamp = 0
    for r in r_px:
        R = int(round(r * ss))
        for k in range(8):
            ang = 2 * math.pi * k / 8 + (0.39 if R > ss * 2 else 0)
            dy, dx = int(round(R * math.sin(ang))), int(round(R * math.cos(ang)))
            sh = shifted(dd, dy, dx, 1e9)
            occ += (sh < dd - eps).astype(np.float32)
            nsamp += 1
    occ /= nsamp
    occ[~a] = 0
    return occ


def contact_ao(F, ss, pairs, r_px=(1.0, 2.0), eps=0.03):
    """occlusione solo fra coppie di parti del corpo scelte: quota dei campioni vicini che stanno davanti al pixel
    E appartengono a una parte "di contatto" della sua (ascelle: busto-braccio; fra le gambe: coscia-coscia; sotto
    il mento: busto sotto la testa). pairs = [[parte del pixel, parte davanti], ...]."""
    a, d, part = F["a"], F["d"], F["part"]
    T = np.zeros((16, 16), bool)
    for p, q in pairs:
        T[int(p), int(q)] = True
    dd = np.where(a, d, 1e9)
    occ = np.zeros(a.shape, np.float32)
    nsamp = 0
    for r in r_px:
        R = int(round(r * ss))
        for k in range(8):
            ang = 2 * math.pi * k / 8 + (0.39 if R > ss * 2 else 0)
            dy, dx = int(round(R * math.sin(ang))), int(round(R * math.cos(ang)))
            sh = shifted(dd, dy, dx, 1e9)
            sp = shifted(part, dy, dx, 0)
            occ += ((sh < dd - eps) & T[part, sp]).astype(np.float32)
            nsamp += 1
    occ /= nsamp
    occ[~a] = 0
    return occ


def smooth_normals(lo, sigma, by="part"):
    """normali lisciate a 1x dentro ogni parte del corpo (o materiale): le ombre seguono i volumi grandi e non le
    sfaccettature del modello."""
    n, a = lo["n"], lo["alpha"]
    grp = lo["part"] if by == "part" else lo["ids"]
    out = n.copy()
    for g in np.unique(grp[a]):
        m = (grp == g) & a
        w = ndimage.gaussian_filter(m.astype(np.float32), sigma, mode="constant")
        for c in range(3):
            s = ndimage.gaussian_filter(np.where(m, n[..., c], 0).astype(np.float32), sigma, mode="constant")
            out[..., c] = np.where(m, s / np.maximum(w, 1e-6), out[..., c])
    out /= np.maximum(np.linalg.norm(out, axis=-1, keepdims=True), 1e-6)
    return out


def clean_islands(ids, alpha, mats, min_px):
    """isole di un materiale dell'elenco più piccole di min_px (4-connesse) prendono il materiale più comune
    intorno: niente puntini di fodera o di cappuccio sulla camicia."""
    ids = ids.copy()
    h, w = ids.shape
    for mid in mats:
        lab, nlab = ndimage.label(ids == mid)
        if not nlab:
            continue
        sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, nlab + 1))
        for ci in np.nonzero(sizes < min_px)[0] + 1:
            ys, xs = np.nonzero(lab == ci)
            votes = {}
            for y, x in zip(ys, xs):
                for dy, dx in N4:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and alpha[yy, xx] and ids[yy, xx] not in (0, mid):
                        votes[int(ids[yy, xx])] = votes.get(int(ids[yy, xx]), 0) + 1
            if votes:
                ids[ys, xs] = max(votes, key=votes.get)
    return ids


def downsample(F, ss, cfg, ID, prev=None, mv=None, occ_hi=None, occ_c_hi=None):
    ab, ib, nb, db, pb = (blocks(F[k], ss) for k in ("a", "ids", "n", "d", "part"))
    nsub = ss * ss
    cov = ab.mean(-1)
    cnt = np.zeros(ab.shape[:2] + (NID,), np.int32)
    for k in np.unique(F["ids"]):
        if k:
            cnt[..., k] = ((ib == k) & ab).sum(-1)
    idm = cnt.argmax(-1)
    feat_ids = [ID[k] for k in FEATURES if k in ID]
    glow = ID["GLOW_LINE"]
    eye = ID["EYE_GLOW"]
    idm = np.where(cnt[..., glow] >= cfg.get("glow_min", 3), glow, idm)
    thr = max(1, int(round(cfg["feat_frac"] * nsub)))
    for k in reversed(feat_ids):
        if k == eye:
            continue
        idm = np.where(cnt[..., k] >= thr, k, idm)
    idm = np.where(cnt[..., eye] >= 1, eye, idm)
    alpha = cov >= cfg["cov_thr"]
    alpha |= idm == eye
    if prev is not None and cfg["hyst"]:
        h, w = alpha.shape
        yy, xx = np.mgrid[0:h, 0:w]
        qy = np.clip(yy - mv[..., 1], 0, h - 1)
        qx = np.clip(xx - mv[..., 0], 0, w - 1)
        pa = prev["alpha"][qy, qx]
        pid = prev["ids"][qy, qx]
        alpha = np.where(pa, cov >= cfg["cov_keep"], cov >= cfg["cov_add"]) | (idm == eye)
        pc = np.take_along_axis(cnt, pid[..., None], -1)[..., 0]
        keep = (pid > 0) & (pc >= cfg["lab_keep"] * nsub) & alpha
        prot = feat_ids + [glow]
        feat = np.isin(idm, prot)
        keep &= ~(feat & ~np.isin(pid, prot))
        idm = np.where(keep, pid, idm)
    idm[~alpha] = 0
    sel = (ib == idm[..., None]) & ab
    wsum = np.maximum(sel.sum(-1), 1)
    nn = (nb * sel[..., None]).sum(-2) / wsum[..., None]
    nn = nn / np.maximum(np.linalg.norm(nn, axis=-1, keepdims=True), 1e-6)
    dd = (db * sel).sum(-1) / wsum
    pcnt = np.stack([((pb == k) & sel).sum(-1) for k in range(15)], -1)
    part = pcnt.argmax(-1)
    part[~alpha] = 0
    out = dict(alpha=alpha, ids=idm, n=nn, d=dd, part=part, cnt=cnt, cov=cov)
    if occ_hi is not None:
        ob = blocks(occ_hi, ss)
        out["occ"] = (ob * sel).sum(-1) / wsum
    else:
        out["occ"] = np.zeros_like(dd)
    if occ_c_hi is not None:
        ob = blocks(occ_c_hi, ss)
        out["occ_c"] = (ob * sel).sum(-1) / wsum
    # almeno 1 px per ogni dettaglio presente nel render
    for k in feat_ids:
        tot = int((F["ids"] == k).sum())
        if tot >= cfg["feat_min_hi"] and not (out["ids"] == k).any():
            c = np.where(out["alpha"] | (cnt[..., k] > 0), cnt[..., k], -1)
            y, x = np.unravel_index(int(c.argmax()), c.shape)
            if cnt[y, x, k] > 0:
                out["ids"][y, x] = k
                out["alpha"][y, x] = True
                if out["part"][y, x] == 0:
                    out["part"][y, x] = 2
    return out


# ============================================================== ombre
class Shader:
    def __init__(self, cfg, pcfg, ID):
        self.cfg = cfg
        self.ID = ID
        self.NAME = {v: k for k, v in ID.items()}
        self.pal = build_palette(pcfg)
        self.spec = {}
        for mname, sp in pcfg["spec"].items():
            if mname in ID:
                self.spec[ID[mname]] = (sp[0], sp[1], sp[2] if len(sp) > 2 else None)
        self.spec_mats = {ID[k]: v for k, v in pcfg.get("spec_mats", {}).items() if k in ID}
        self.big = {ID[k] for k in pcfg.get("big_mats", []) if k in ID}
        self.L = np.array(cfg["key"], np.float32)
        self.L /= np.linalg.norm(self.L)
        # cel shading: toni fissi per materiale (soglie su n·L e indici della rampa per ogni tono)
        self.cel = cfg.get("cel") or None
        self.idxmap = {}
        if self.cel and self.cel.get("shadow_mix"):
            # ombra più chiara: l'indice 1 della rampa si sposta verso il medio (0 = com'è, 1 = il medio); un numero
            # vale per tutte le rampe, un dizionario per rampa ("*" = le altre)
            sm = self.cel["shadow_mix"]
            for name, r in pcfg["ramps"].items():
                if "list" in r:
                    continue
                t = float(sm.get(name, sm.get("*", 0.0)) if isinstance(sm, dict) else sm)
                if t > 0:
                    c1, c2 = hx(self.pal[name][1]), hx(self.pal[name][2])
                    self.pal[name][1] = tohex(tuple((1 - t) * a + t * b for a, b in zip(c1, c2)))

    def cel_bands(self, mid):
        """(soglie, indici della rampa per tono) del materiale nel cel shading."""
        name = self.NAME.get(int(mid), "")
        c = self.cel
        thr = (c.get("mat_thr") or {}).get(name, c["thr"])
        idx = (c.get("mat_idx") or {}).get(name, c["idx"])
        if len(idx) != len(thr) + 1:
            raise ValueError(f"cel: {name} ha {len(thr)} soglie ma {len(idx)} indici")
        return thr, idx

    def color(self, rname, idx):
        r = self.pal[rname]
        return hx(r[min(idx, len(r) - 1)])

    def bands(self, lo, prev=None, mv=None):
        ids, n = lo["ids"], lo["n"]
        h, w = ids.shape
        lam = (n * self.L).sum(-1)
        lam_eff = lam - self.cfg["ao_k"] * lo["occ"]
        V = np.array([0, 0, 1], np.float32)
        Hv = self.L + V
        Hv /= np.linalg.norm(Hv)
        specv = np.clip((n * Hv).sum(-1), 0, 1)
        ramp = np.full((h, w), "", dtype=object)
        idx = np.zeros((h, w), np.int32)
        band = np.full((h, w), -1, np.int32)
        if prev is not None and self.cfg["hyst"]:
            yy, xx = np.mgrid[0:h, 0:w]
            qy = np.clip(yy - mv[..., 1], 0, h - 1)
            qx = np.clip(xx - mv[..., 0], 0, w - 1)
            pb_all = prev["band"][qy, qx]
            pid_all = prev["ids"][qy, qx]
        for mid in np.unique(ids):
            if mid == 0:
                continue
            sp = self.spec.get(int(mid))
            if sp is None:
                raise KeyError("manca la voce di tavolozza per il materiale " + self.NAME.get(int(mid), str(mid)))
            m = ids == mid
            if sp[1] is None:
                ramp[m] = sp[0]
                idx[m] = sp[2]
                continue
            thr = sp[1]
            if self.cel:
                thr, imap = self.cel_bands(mid)
                self.idxmap[int(mid)] = np.asarray(imap, np.int32)
            b = np.zeros((h, w), np.int32)
            for t in thr:
                b += (lam_eff > t).astype(np.int32)
            if prev is not None and self.cfg["hyst"]:
                same = (pid_all == mid) & (pb_all >= 0)
                near = np.zeros((h, w), bool)
                for t in thr:
                    near |= np.abs(lam_eff - t) < self.cfg["band_hyst"]
                b = np.where(same & near & (np.abs(pb_all - b) == 1), pb_all, b)
            if self.cel and "contact_m" in lo:
                # nei contatti (ascelle, fra le gambe, sotto il mento) il tono più scuro del materiale
                skip = {self.ID[k] for k in self.cel.get("contact_skip", []) if k in self.ID}
                if int(mid) not in skip:
                    b = np.where(lo["contact_m"], 0, b)
            ramp[m] = sp[0]
            idx[m] = self.idxmap[int(mid)][b[m]] if self.cel else 1 + b[m]
            band[m] = b[m]
        return ramp, idx, band, lam_eff, specv

    def merge_small(self, ids, band, alpha, min_px):
        """gruppi di una banda più piccoli di min_px prendono la banda vicina più comune (stesso materiale)."""
        h, w = ids.shape
        for _ in range(3):
            changed = 0
            for mid in np.unique(ids[alpha & (band >= 0)]):
                if mid not in self.big:
                    continue
                mm = (ids == mid) & (band >= 0)
                for b in np.unique(band[mm]):
                    lab, nlab = ndimage.label(mm & (band == b))
                    if nlab == 0:
                        continue
                    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, nlab + 1))
                    for ci in np.nonzero(sizes < min_px)[0] + 1:
                        ys, xs = np.nonzero(lab == ci)
                        votes = {}
                        for y, x in zip(ys, xs):
                            for dy, dx in N4:
                                yy, xx = y + dy, x + dx
                                if 0 <= yy < h and 0 <= xx < w and ids[yy, xx] == mid and band[yy, xx] >= 0 \
                                        and band[yy, xx] != b:
                                    votes[band[yy, xx]] = votes.get(band[yy, xx], 0) + 1
                        if votes:
                            band[ys, xs] = max(votes, key=votes.get)
                            changed += 1
            if not changed:
                break
        return band


def compose(lo, sh, cfg, prev=None, mv=None):
    ID = sh.ID
    alpha, ids, n, d = lo["alpha"], lo["ids"], lo["n"], lo["d"]
    h, w = alpha.shape
    ramp, idx, band, lam, specv = sh.bands(lo, prev, mv)
    band = sh.merge_small(ids, band, alpha, cfg["min_cluster"])
    if cfg.get("band_mode"):
        band = V7.band_mode(ids, band, alpha, int(cfg["band_mode"]))
    for mid in np.unique(ids):
        sp = sh.spec.get(int(mid))
        if sp is not None and sp[1] is not None:
            m = (ids == mid) & (band >= 0)
            idx[m] = sh.idxmap[int(mid)][band[m]] if sh.cel else 1 + band[m]
    rgba = np.zeros((h, w, 4), np.uint8)
    for rn in set(ramp[alpha].tolist()):
        m = alpha & (ramp == rn)
        for k in np.unique(idx[m]):
            rgba[m & (idx == k)] = (*sh.color(rn, int(k)), 255)
    # riflessi di 1-2 px (nel cel, con spec_top, solo sul tono più chiaro del materiale)
    if cfg["spec"]:
        for mid, thr in sh.spec_mats.items():
            top = 1
            if sh.cel and sh.cel.get("spec_top") and int(mid) in sh.idxmap:
                top = len(sh.idxmap[int(mid)]) - 1
            mm = alpha & (ids == mid) & (band >= top)
            if not mm.any():
                continue
            lab, nlab = ndimage.label(mm)
            for ci in range(1, nlab + 1):
                ys, xs = np.nonzero(lab == ci)
                if len(ys) < 10:
                    continue
                sv = specv[ys, xs] ** cfg["spec_pow"]
                j = int(sv.argmax())
                if sv[j] < thr:
                    continue
                pts = [(ys[j], xs[j])]
                if len(ys) >= 30:
                    best, bp = -1, None
                    for dy, dx in N4:
                        yy, xx = ys[j] + dy, xs[j] + dx
                        if 0 <= yy < h and 0 <= xx < w and lab[yy, xx] == ci:
                            v_ = specv[yy, xx] ** cfg["spec_pow"]
                            if v_ > best:
                                best, bp = v_, (yy, xx)
                    if bp is not None and best > thr * 0.92:
                        pts.append(bp)
                rn = sh.spec[mid][0]
                for (y, x) in pts:
                    rgba[y, x, :3] = sh.color(rn, 5)
    pad = 2
    H, W = h + 2 * pad, w + 2 * pad
    big = np.zeros((H, W, 4), np.uint8)
    big[pad:pad + h, pad:pad + w] = rgba
    A = np.zeros((H, W), bool)
    A[pad:pad + h, pad:pad + w] = alpha
    Dp = np.full((H, W), 1e9, np.float32)
    Dp[pad:pad + h, pad:pad + w] = np.where(alpha, d, 1e9)
    Ip = np.zeros((H, W), np.int32)
    Ip[pad:pad + h, pad:pad + w] = ids
    Rp = np.full((H, W), "", dtype=object)
    Rp[pad:pad + h, pad:pad + w] = ramp
    noline = np.isin(Ip, [ID["EYE_GLOW"], ID["GLOW_LINE"]])
    # linee interne dove la profondità salta (il pixel più lontano prende il colore "linea" della sua rampa)
    line = np.zeros((H, W), bool)
    for dy, dx in N4:
        Dn = shifted(Dp, dy, dx, 1e9)
        An = shifted(A, dy, dx, False)
        line |= A & An & (Dp - Dn > cfg["depth_thr"])
    line &= ~noline
    # linee interne fra materiali scelti (cfg "mat_lines": coppie [A, B]): il pixel del materiale A che tocca
    # il materiale B prende il colore "linea" della sua rampa. Servono dove la profondità non salta ma a 1x ci
    # vuole un segno: bordo delle fasce sul polso, ombra sotto l'orlo della camicia e sotto i risvolti.
    for a_name, b_name in cfg.get("mat_lines", []):
        if a_name not in ID or b_name not in ID:
            continue
        ma = Ip == ID[a_name]
        mb = Ip == ID[b_name]
        touch = np.zeros((H, W), bool)
        for dy, dx in N4:
            touch |= ma & shifted(mb, dy, dx, False)
        line |= touch & ~noline
    if cfg.get("pp_lines"):
        line = V7.pixel_perfect(line)
    if sh.cel and sh.cel.get("line_min", 0) > 1:
        # niente frammenti di linea interna più corti di line_min px (8-connessi): a 1x sono macchie
        lab, nlab = ndimage.label(line, structure=np.ones((3, 3)))
        if nlab:
            sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, nlab + 1))
            line = np.isin(lab, np.nonzero(sizes >= sh.cel["line_min"])[0] + 1)
    for y, x in zip(*np.nonzero(line)):
        rn = Rp[y, x]
        big[y, x, :3] = sh.color(rn, 0) if rn else hx(sh.pal["OUT"][0])
    # luce di contorno magenta (bordo sinistro), solo a tratti continui
    if cfg["rim"]:
        Lr = np.array(cfg["rim_dir"], np.float32)
        Lr /= np.linalg.norm(Lr)
        npad = np.zeros((H, W, 3), np.float32)
        npad[pad:pad + h, pad:pad + w] = lo.get("n_rim", n)
        rimv = (npad * Lr).sum(-1)
        edge = np.zeros((H, W), bool)
        for dy, dx in [(0, -1), (-1, 0), (-1, -1)]:
            edge |= A & ~shifted(A, dy, dx, False)
        rim = edge & (rimv > cfg["rim_thr"]) & ~noline
        rim &= np.isin(Ip, [ID[k] for k in cfg["rim_mats"] if k in ID])
        lab, nlab = ndimage.label(rim, structure=np.ones((3, 3)))
        if nlab:
            sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, nlab + 1))
            keep = np.isin(lab, np.nonzero(sizes >= cfg["rim_min_run"])[0] + 1)
            big[keep, :3] = hx(sh.pal["RIM"][0])
    # contorno esterno
    out = np.zeros((H, W), bool)
    for dy, dx in N4:
        out |= ~A & shifted(A, dy, dx, False)
    big[out] = (*hx(sh.pal["OUT"][0]), 255)
    if cfg.get("selout"):
        V7.selout_colors(big, A, Rp, out, sh.pal, hx(sh.pal["OUT"][0]))
        if sh.cel and sh.cel.get("selout_min", 0) > 1:
            # tratti di contorno colorato più corti di selout_min px tornano al contorno scuro
            oc = np.array(hx(sh.pal["OUT"][0]), np.uint8)
            col = out & (big[..., :3] != oc).any(-1)
            kk = (big[..., 0].astype(np.int64) << 16) | (big[..., 1].astype(np.int64) << 8) | big[..., 2]
            for v in np.unique(kk[col]):
                lab, nlab = ndimage.label(col & (kk == v), structure=np.ones((3, 3)))
                sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, nlab + 1))
                short = np.isin(lab, np.nonzero(sizes < sh.cel["selout_min"])[0] + 1)
                big[short, :3] = oc
    prot = np.isin(Ip, [ID[k] for k in FEATURES if k in ID] + [ID["GLOW_LINE"]])
    big = fix_orphans(big, prot)
    return big[pad:pad + h, pad:pad + w], band


def fix_orphans(big, protect):
    """pixel isolati di un colore non di dettaglio prendono il colore dei vicini più frequente. Si copia solo il
    colore, dal vicino che ce l'ha: l'alfa non cambia, quindi la sagoma resta quella del G-buffer. (Fino alla v7 si
    copiava il pixel opposto a quel vicino, a volte di un altro colore e a volte vuoto: da lì le tacche di 1 px sul
    contorno.)"""
    H, W = big.shape[:2]
    key = (big[..., 0].astype(np.int64) << 16) | (big[..., 1].astype(np.int64) << 8) | big[..., 2]
    key[big[..., 3] == 0] = -1
    nb = np.stack([shifted(key, dy, dx, -1) for dy, dx in N4], 0)
    lonely = (key >= 0) & ~protect & ~(nb == key[None]).any(0) & ((nb >= 0).sum(0) >= 3)
    out = big.copy()
    for y, x in zip(*np.nonzero(lonely)):
        vals = [int(v) for v in nb[:, y, x] if v >= 0]
        best = max(set(vals), key=vals.count)
        if vals.count(best) >= 2:
            k = [i for i in range(4) if nb[i, y, x] == best][0]
            dy, dx = N4[k]
            out[y, x, :3] = big[y + dy, x + dx, :3]
    return out


# ============================================================== movimento dalle ossa
def part_motion(fd_prev, fd_cur):
    mv = {}
    for k, bn in PART_BONE.items():
        a = fd_prev["bones"][bn]
        b = fd_cur["bones"][bn]
        ua, va = (a[0] + a[3]) / 2, (a[1] + a[4]) / 2
        ub, vb = (b[0] + b[3]) / 2, (b[1] + b[4]) / 2
        mv[k] = (int(round(ub - ua)), int(round(vb - va)))
    return mv


def part_map_lo(part_hi, ss):
    pb = blocks(part_hi, ss)
    h, w = pb.shape[:2]
    cnt = np.stack([(pb == k).sum(-1) for k in range(15)], -1)
    cnt[..., 0] = 0
    pm = np.where(cnt.max(-1) > 0, cnt.argmax(-1), 0)
    for _ in range(2):
        z = pm == 0
        if not z.any():
            break
        best = np.zeros((h, w), np.int32)
        bestc = np.zeros((h, w), np.int32)
        for k in range(1, 15):
            m = (pm == k).astype(np.int32)
            c = ndimage.uniform_filter(m.astype(np.float32), size=3, mode="constant") * 9
            c = np.rint(c).astype(np.int32)
            upd = c > bestc
            best = np.where(upd, k, best)
            bestc = np.where(upd, c, bestc)
        pm = np.where(z & (bestc > 0), best, pm)
    return pm


def mv_field(part_map, mvd):
    h, w = part_map.shape
    f = np.zeros((h, w, 2), np.int32)
    for k, (du, dv) in mvd.items():
        m = part_map == k
        f[m, 0] = du
        f[m, 1] = dv
    return f


# ============================================================== un'animazione
DEFAULT_CFG = dict(feat_frac=0.12, feat_min_hi=3, hyst=True, cov_thr=0.45, cov_keep=0.30, cov_add=0.58,
                   lab_keep=0.30, band_hyst=0.07, depth_thr=0.08, rim=True, rim_thr=0.30,
                   rim_dir=[-0.85, 0.35, -0.4], rim_min_run=5, key=[0.38, 0.70, 0.60], spec_pow=16,
                   min_cluster=5, ao_k=0.55, spec=True, glow_min=3)


def pixelize_sequence(raw_anim_dir, fdata, ss, shader, cfg, loop=False, faces=None):
    """elabora i fotogrammi nell'ordine (due giri per i cicli, così l'isteresi si chiude) -> RGBA 1x."""
    order = list(range(len(fdata)))
    passes = order + order if (loop and cfg["hyst"] and len(order) > 1) else order
    prev, prev_fd = None, None
    results = {}
    labels = {}
    normals = {}
    cel = cfg.get("cel") or {}
    relabel = None
    if cel.get("relabel"):
        # pieghe stampate (TOP_FOLD, PANTS_FOLD) rimesse nel loro materiale: nel cel non fanno macchie
        relabel = np.arange(256, dtype=np.int32)
        for src, dst in cel["relabel"].items():
            if src in shader.ID and dst in shader.ID:
                relabel[shader.ID[src]] = shader.ID[dst]
    contact = cel.get("contact")
    W1 = None
    for step, i in enumerate(passes):
        fd = fdata[i]
        F = load_frame(os.path.join(raw_anim_dir, fd["file"]))
        W1 = F["a"].shape[1] // ss
        if relabel is not None:
            F["ids"] = relabel[F["ids"]]
        occ = ao_hi(F, ss) if cfg["ao_k"] > 0 else None
        occ_c = None
        if contact:
            occ_c = contact_ao(F, ss, contact["pairs"], tuple(contact.get("r_px", (1.0, 2.0))),
                               contact.get("eps", 0.03))
        mv = None
        if prev is not None and cfg["hyst"]:
            mvd = part_motion(prev_fd, fd)
            mv = mv_field(part_map_lo(F["part"], ss), mvd)
        lo = downsample(F, ss, cfg, shader.ID, prev if cfg["hyst"] else None, mv, occ, occ_c)
        if cel.get("islands"):
            isl = cel["islands"]
            lo["ids"] = clean_islands(lo["ids"], lo["alpha"], [shader.ID[k] for k in isl["mats"] if k in shader.ID],
                                      isl.get("min_px", 4))
        if cel.get("rim_capsule") is not None:
            # riflesso magenta calcolato con le normali di prima (render + capsule leggere): le normali lisciate del
            # cel lo spegnerebbero sui bordi
            lo["n_rim"] = V7.capsule_normals(dict(lo), fd, cfg["p1"], W1, cel["rim_capsule"])
        if cfg.get("capsule_n", 0) > 0:
            lo["n"] = V7.capsule_normals(lo, fd, cfg["p1"], W1, cfg["capsule_n"])
        if cel.get("head_n", 0) > 0:
            hm = [shader.ID[k] for k in cel["head_mats"] if k in shader.ID] if cel.get("head_mats") else None
            lo["n"] = V7.head_normals(lo, fd, cfg["p1"], W1, cel["head_n"], cel.get("head_c_dz", 0.0), hm)
        if cel.get("n_smooth", 0) > 0:
            lo["n"] = smooth_normals(lo, cel["n_smooth"], cel.get("n_smooth_by", "part"))
        if contact:
            # maschera dei contatti, con isteresi compensata dal moto delle ossa: un pixel che era in contatto ci
            # resta finché l'occlusione supera contact.keep
            cm = lo["occ_c"] > contact.get("thr", 0.2)
            keep_thr = contact.get("keep")
            if prev is not None and cfg["hyst"] and "contact_m" in prev and keep_thr is not None:
                h_, w_ = cm.shape
                yy, xx = np.mgrid[0:h_, 0:w_]
                qy = np.clip(yy - mv[..., 1], 0, h_ - 1)
                qx = np.clip(xx - mv[..., 0], 0, w_ - 1)
                pcm = prev["contact_m"][qy, qx]
                cm = np.where(pcm, lo["occ_c"] > keep_thr, cm)
            lo["contact_m"] = cm & lo["alpha"]
        sprite, band = compose(lo, shader, cfg, prev if cfg["hyst"] else None, mv)
        lo["band"] = band
        prev, prev_fd = lo, fd
        ids_out = lo["ids"].copy()
        st = cfg.get("stamps") or {}
        if st.get("face") and "eye_r" in fd.get("points", {}):
            expr = (faces[i] if faces else None) or "neutral"
            sprite, ids_out = V7.face_stamp(sprite, ids_out, lo["part"], lo["d"], fd, shader.ID, shader.pal, expr,
                                            st.get("eye", "cyan"))
        if fd.get("trail") and cfg.get("smear_draw", True):
            names = sorted({k for s_ in fd["trail"] for k in s_} - set(cfg.get("smear_skip", [])))
            sprite = V7.draw_smear(sprite, fd["trail"], shader.pal, names, ramps=cfg.get("smear_ramps"))
        results[i] = sprite
        labels[i] = np.stack([ids_out, lo["part"]], 0).astype(np.uint8)
        normals[i] = V7.normal_image(sprite, lo)
    pixelize_sequence.normals = [normals[i] for i in order]
    return [results[i] for i in order], [labels[i] for i in order]


# ============================================================== riduzione della tavolozza
def _lab(rgb):
    c = np.asarray(rgb, np.float64) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def reduce_palette(images, max_colors, protect=()):
    """porta l'insieme dei colori di tutte le immagini a <= max_colors fondendo le coppie più vicine (CIELAB),
    il colore meno usato va nel più usato; i colori protetti non si toccano. Restituisce (mappa, tavolozza)."""
    counts = {}
    for im in images:
        a = im[..., 3] > 0
        px = im[a][:, :3]
        if not len(px):
            continue
        keys, cnt = np.unique(px.astype(np.int64) @ np.array([65536, 256, 1]), return_counts=True)
        for k, c in zip(keys.tolist(), cnt.tolist()):
            counts[k] = counts.get(k, 0) + c
    prot = {int(hx(c)[0]) * 65536 + int(hx(c)[1]) * 256 + int(hx(c)[2]) for c in protect}
    remap = {k: k for k in counts}

    def rgb(k):
        return ((k >> 16) & 255, (k >> 8) & 255, k & 255)
    live = dict(counts)
    while len(live) > max_colors:
        keys = list(live.keys())
        labs = _lab(np.array([rgb(k) for k in keys], np.float64))
        dist = np.sqrt(((labs[:, None, :] - labs[None, :, :]) ** 2).sum(-1))
        np.fill_diagonal(dist, 1e9)
        for i, k in enumerate(keys):
            if k in prot:
                pass
        # coppia più vicina in cui almeno uno non è protetto
        order = np.argsort(dist, axis=None)
        done = False
        for flat in order[:2000]:
            i, j = divmod(int(flat), len(keys))
            a, b = keys[i], keys[j]
            if a in prot and b in prot:
                continue
            if a in prot or (b not in prot and live[a] >= live[b]):
                keep, drop = a, b
            else:
                keep, drop = b, a
            live[keep] += live.pop(drop)
            for k, v in remap.items():
                if v == drop:
                    remap[k] = keep
            done = True
            break
        if not done:
            break
    return remap, sorted(live.keys(), key=lambda k: -live[k])


def apply_remap(im, remap):
    out = im.copy()
    a = out[..., 3] > 0
    keys = out[..., :3].astype(np.int64) @ np.array([65536, 256, 1])
    for src, dst in remap.items():
        if src != dst:
            m = a & (keys == src)
            out[m, 0] = (dst >> 16) & 255
            out[m, 1] = (dst >> 8) & 255
            out[m, 2] = dst & 255
    return out
