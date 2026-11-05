#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Costruisce il sito statico di CTRL+ALT REVENGE in una cartella pronta per GitHub Pages.

Uso, dalla radice del repository (solo la libreria standard di Python, dal 3.10 in su):

    python -I tools/site/build.py                    # in _site/
    python -I tools/site/build.py --out /tmp/sito    # altrove
    python -I tools/site/build.py --url http://127.0.0.1:8620/ctrl-alt-revenge/   # prova in locale

Che cosa fa:
1. legge i testi di site/content/it.json e en.json (stessa struttura, lo controlla), i dati comuni di
   site/content/dati.json e il manifesto dei media, site/media/media.json (lo scrive
   tools/site/media.py: misure, testi alternativi, tipi dei video, dati della cattura);
2. riempie il modello unico site/modello/pagina.html due volte: l'italiano nella radice,
   l'inglese in en/. La pagina 404, in tutte e due le lingue, viene da site/modello/404.html;
3. copia css/, js/ e media/ e aggiunge robots.txt, sitemap.xml e .nojekyll; site/js/scala.js (le scale
   intere e il movimento, prima del primo disegno) va anche dentro il <head> di ogni pagina, e la
   Content-Security-Policy della pagina ne porta l'impronta: fuori dal sito non parte niente;
4. controlla il risultato e si ferma se trova qualcosa che non va: parole vietate (spoiler,
   nomi veri, il genere sbagliato), risorse esterne (CDN, font, script), file citati che
   mancano (anche negli indirizzi assoluti del sito, come og:image e canonical), ancore senza
   destinazione, script in linea che la CSP non ammette, lettere che il font CAR Pixel non ha.

La demo web non la fa questo script: la esporta tools/site/export_web.sh e il workflow
.github/workflows/sito.yml la mette in gioca/, che qui resta libera.

Il modello è HTML con poche regole:
    {{ t.eroe.motto }}            testo, con i caratteri speciali protetti
    {{ t.storia.testo | html }}   testo con i pochi tag ammessi (b, i, em, span con le classi note, a, kbd, br)
    {{ t.gioco.titolo | pixel }}  come il primo, ma controlla che CAR Pixel abbia tutte le lettere
    {{ m.eroe | json }}           dati per gli script della pagina
    {% for p in t.gioco.pilastri %} ... {{ loop.index }} ... {% endfor %}
    {% if p.slice %} ... {% else %} ... {% endif %}      (anche {% if not ... %})
    {# commento #}
Nei testi, [[nome]] diventa il numero o il testo di dati.json, sezione "numeri".
Una voce di un elenco con "mostra": false resta fuori dal sito (righe facoltative, decide Luigi).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import stat
import struct
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"
CONTENT = SITE / "content"
MODELLO = SITE / "modello"
MEDIA = SITE / "media"
FONT_TTF = ROOT / "game" / "assets" / "fonts" / "car_pixel_bold.ttf"
TESTS = ROOT / "game" / "tests"
LINGUE = ("it", "en")
RISERVATA = "gioca"          # cartella della demo web, la riempie il workflow

# ------------------------------------------------------------------ parole vietate
# Spoiler, nomi veri, il genere sbagliato e altre cose che il sito non deve dire (brief del sito,
# regole di rispetto di docs/lore/storia.md e decisioni del 4 novembre 2026). Si cercano nel testo
# e negli attributi delle pagine finite, URL esclusi.
VIETATE_SENSIBILI = [  # maiuscole e minuscole contano: sono nomi
    "Dario", "Altamura", "Caporale", "Cosimo", "Warden", "Custode", "Custodi", "TUTORE", "Teresa", "EFESTO", "Leonida", "Vito",
    "Riva", "Jindal", "Flacks", "Mittal", "ArcelorMittal", "Federacciai", "Iacovone", "Mostro",
    "ARIA VERA",
]
VIETATE = [  # maiuscole e minuscole non contano
    r"picchia\s*duro", "picchiaduro", "brawler", r"beat[\s\-']*'?em[\s\-']*up", r"16[\s\-]?bit",
    "ilva", "acciaierie", "sonnambul", "finta bonifica", "inganno", "cantiere segreto", "fisioterapia",
    r"modalit[àa] turno", r"aggiornamento 3\.0", "delfin", "dolphin", "2107", "2062", "2064", "2065",
    "2067", "riaccension", "altiforni ricostruiti", "agosto 2026", "safety stoat", "chatgpt",
    "sleepwalk", "città dei veleni", "città morta",
]

# Tag e attributi ammessi nei testi (filtro | html).
TAG_AMMESSI = {"b", "strong", "i", "em", "span", "a", "kbd", "br", "small", "q", "abbr", "cite", "sup"}
ATTR_AMMESSI = {"class", "lang", "href", "title"}
CLASSI_AMMESSE = {"sidera", "occhio", "tere", "nota", "parola", "tasto", "data", "nowrap"}


class Errore(Exception):
    pass


# ------------------------------------------------------------------ modelli

_TOKEN = re.compile(r"({%.*?%}|{{.*?}}|{#.*?#})", re.S)


def _parse(src: str, nome: str) -> list:
    pila: list[tuple[str, list, dict]] = [("radice", [], {})]
    for pezzo in _TOKEN.split(src):
        if not pezzo:
            continue
        corpo = pila[-1][1]
        if pezzo.startswith("{#"):
            continue
        if pezzo.startswith("{{"):
            espr = pezzo[2:-2].strip()
            parti = [p.strip() for p in espr.split("|")]
            corpo.append(("var", parti[0], parti[1:]))
        elif pezzo.startswith("{%"):
            cmd = pezzo[2:-2].strip()
            m = re.fullmatch(r"for (\w+) in ([\w.]+)", cmd)
            if m:
                nodo = {"tipo": "for", "var": m.group(1), "espr": m.group(2), "corpo": []}
                corpo.append(nodo)
                pila.append(("for", nodo["corpo"], nodo))
                continue
            m = re.fullmatch(r"if (not )?([\w.]+)", cmd)
            if m:
                nodo = {"tipo": "if", "neg": bool(m.group(1)), "espr": m.group(2), "corpo": [], "altro": []}
                corpo.append(nodo)
                pila.append(("if", nodo["corpo"], nodo))
                continue
            if cmd == "else":
                if pila[-1][0] != "if":
                    raise Errore(f"{nome}: else fuori da un if")
                nodo = pila[-1][2]
                pila[-1] = ("else", nodo["altro"], nodo)
                continue
            if cmd in ("endfor", "endif"):
                atteso = ("for",) if cmd == "endfor" else ("if", "else")
                if pila[-1][0] not in atteso:
                    raise Errore(f"{nome}: {cmd} senza apertura")
                pila.pop()
                continue
            raise Errore(f"{nome}: comando sconosciuto {{% {cmd} %}}")
        else:
            corpo.append(("testo", pezzo))
    if len(pila) != 1:
        raise Errore(f"{nome}: blocco non chiuso ({pila[-1][0]})")
    return pila[0][1]


def _cerca(ctx: list[dict], espr: str):
    parti = espr.split(".")
    for livello in reversed(ctx):
        if parti[0] in livello:
            v = livello[parti[0]]
            break
    else:
        raise Errore(f"variabile sconosciuta: {espr}")
    for p in parti[1:]:
        if isinstance(v, dict) and p in v:
            v = v[p]
        elif isinstance(v, list) and p.isdigit() and int(p) < len(v):
            v = v[int(p)]
        else:
            raise Errore(f"variabile sconosciuta: {espr} (manca «{p}»)")
    return v


class Pagina:
    """Rende un modello con il contesto dato; `controlli` raccoglie i testi da verificare."""

    def __init__(self, nome: str, glifi: set[int]):
        self.nome = nome
        self.glifi = glifi

    def rendi(self, nodi: list, ctx: list[dict]) -> str:
        out = []
        for n in nodi:
            if isinstance(n, tuple) and n[0] == "testo":
                out.append(n[1])
            elif isinstance(n, tuple) and n[0] == "var":
                out.append(self._var(n[1], n[2], ctx))
            elif n["tipo"] == "for":
                elenco = _cerca(ctx, n["espr"])
                if not isinstance(elenco, list):
                    raise Errore(f"{self.nome}: {n['espr']} non è un elenco")
                for i, x in enumerate(elenco):
                    loop = {"index": i + 1, "index0": i, "first": i == 0, "last": i == len(elenco) - 1,
                            "length": len(elenco)}
                    out.append(self.rendi(n["corpo"], ctx + [{n["var"]: x, "loop": loop}]))
            elif n["tipo"] == "if":
                try:
                    v = _cerca(ctx, n["espr"])
                except Errore:
                    v = None          # negli if una chiave che manca vale "falso"
                vero = bool(v) != n["neg"]
                out.append(self.rendi(n["corpo"] if vero else n["altro"], ctx))
        return "".join(out)

    def _var(self, espr: str, filtri: list[str], ctx: list[dict]) -> str:
        v = _cerca(ctx, espr)
        if "json" in filtri:
            return json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        if isinstance(v, bool) or v is None or isinstance(v, (dict, list)):
            raise Errore(f"{self.nome}: {espr} non è un testo")
        s = str(v)
        if "zeri6" in filtri:
            s = s.zfill(6)
        if "pixel" in filtri:
            mancano = sorted({c for c in s if ord(c) not in self.glifi and not c.isspace()})
            if mancano:
                raise Errore(f"{self.nome}: CAR Pixel non ha {''.join(mancano)!r} (in {espr}: {s!r})")
        if "html" in filtri:
            controlla_html(s, espr)
            return s
        if "crudo" in filtri:          # solo per quello che scrive questo script, mai per i testi
            if not espr.startswith("gen."):
                raise Errore(f"{self.nome}: | crudo vale solo per i valori gen.*")
            return s
        return html.escape(s, quote=True)


class _Validatore(HTMLParser):
    def __init__(self, dove: str):
        super().__init__(convert_charrefs=True)
        self.dove = dove
        self.aperti: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in TAG_AMMESSI:
            raise Errore(f"{self.dove}: tag non ammesso <{tag}>")
        for k, v in attrs:
            if k not in ATTR_AMMESSI:
                raise Errore(f"{self.dove}: attributo non ammesso {k} in <{tag}>")
            if k == "class" and not set((v or "").split()) <= CLASSI_AMMESSE:
                raise Errore(f"{self.dove}: classe non ammessa {v!r} (ammesse: {sorted(CLASSI_AMMESSE)})")
            if k == "lang" and v not in LINGUE:
                raise Errore(f"{self.dove}: lingua {v!r}")
            if k == "href" and not (v.startswith("https://") or v.startswith("#")):
                raise Errore(f"{self.dove}: collegamento {v!r} (solo https:// o #)")
        if tag != "br":
            self.aperti.append(tag)

    def handle_endtag(self, tag):
        if not self.aperti or self.aperti[-1] != tag:
            raise Errore(f"{self.dove}: </{tag}> non chiude niente")
        self.aperti.pop()


def controlla_html(s: str, dove: str) -> None:
    if re.search(r"&(?![a-zA-Z]+;|#\d+;)", s):
        raise Errore(f"{dove}: & da scrivere &amp;")
    v = _Validatore(dove)
    v.feed(s)
    v.close()
    if v.aperti:
        raise Errore(f"{dove}: tag non chiusi {v.aperti}")


# ------------------------------------------------------------------ contenuti

def _carica(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise Errore(f"{p.relative_to(ROOT)}: JSON non valido ({e})") from e


def _filtra(v):
    """Toglie le voci con "mostra": false (anche annidate)."""
    if isinstance(v, dict):
        return {k: _filtra(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_filtra(x) for x in v if not (isinstance(x, dict) and x.get("mostra") is False)]
    return v


def _forma(v, dove="") -> object:
    """La struttura di un contenuto senza i testi: serve a confrontare l'italiano con l'inglese."""
    if isinstance(v, dict):
        return {k: _forma(x, f"{dove}.{k}") for k, x in v.items()}
    if isinstance(v, list):
        return [_forma(x, f"{dove}[{i}]") for i, x in enumerate(v)]
    return type(v).__name__


def _differenze(a, b, dove="") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out = [f"{dove}.{k}: c'è solo in italiano" for k in a if k not in b]
        out += [f"{dove}.{k}: c'è solo in inglese" for k in b if k not in a]
        for k in a:
            if k in b:
                out += _differenze(a[k], b[k], f"{dove}.{k}")
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{dove}: {len(a)} voci in italiano e {len(b)} in inglese"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _differenze(x, y, f"{dove}[{i}]")]
    return [] if a == b else [f"{dove}: {a} in italiano, {b} in inglese"]


def _segnaposti(v, numeri: dict, dove=""):
    if isinstance(v, dict):
        return {k: _segnaposti(x, numeri, f"{dove}.{k}") for k, x in v.items()}
    if isinstance(v, list):
        return [_segnaposti(x, numeri, f"{dove}[{i}]") for i, x in enumerate(v)]
    if isinstance(v, str):
        def sost(m):
            if m.group(1) not in numeri:
                raise Errore(f"{dove}: [[{m.group(1)}]] non è in dati.json, sezione numeri")
            return str(numeri[m.group(1)])
        return re.sub(r"\[\[(\w+)\]\]", sost, v)
    return v


def arricchisci(t: dict, manifesto: dict, lingua: str) -> None:
    """Le schermate dei pilastri prendono misure e testo alternativo dal manifesto dei media."""
    schermate = {s["file"]: s for s in manifesto.get("schermate", [])}
    for p in t.get("gioco", {}).get("pilastri", []):
        for s in p.get("schermate", []):
            m = schermate.get(f"schermate/{s['nome']}.png")
            if not m:
                raise Errore(f"la schermata {s['nome']} non è nel manifesto dei media (tools/site/media.py)")
            s.setdefault("w", m["larghezza"])
            s.setdefault("h", m["altezza"])
            s.setdefault("alt", m["alt"][lingua])


def versione_sprite() -> str:
    """Impronta dei file in site/media/sprite: va in coda agli indirizzi (?v=) degli sprite, così il browser non
    mescola mai una striscia nuova con una normal map o un JSON vecchi rimasti nella cache (5 novembre 2026: GIG
    a strisce nella prova della luce, con la normal map 632x306 della cache e lo sprite nuovo 800x384)."""
    h = hashlib.sha256()
    for p in sorted((MEDIA / "sprite").iterdir()):
        if p.is_file():
            h.update(p.name.encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()[:10]


def css_sprite(radice: str) -> str:
    """Le strisce degli sprite in CSS, dai JSON di tools/site/media.py: così si vedono (fermi, al primo
    fotogramma della guardia) anche senza JavaScript. sito.js poi le anima con gli stessi dati.
    Il percorso dev'essere assoluto: un url() dentro una variabile CSS si risolve nel foglio che la usa."""
    regole = []
    ver = versione_sprite()
    for p in sorted((MEDIA / "sprite").glob("*.json")):
        d = _carica(p)
        n = p.stem
        cw, ch = d["cella"]
        iw, ih = d["dimensioni"]
        px0, py0 = d["piedi"]
        regole.append(f'[data-sprite="{n}"]{{--img:url("{radice}media/sprite/{d["immagine"]}?v={ver}");--cw:{cw};--ch:{ch};'
                      f'--iw:{iw};--ih:{ih};--px0:{px0};--py0:{py0}}}')
        for v, f in d.get("varianti", {}).items():
            regole.append(f'[data-sprite="{n}"][data-variante="{v}"]{{--img:url("{radice}media/sprite/{f}?v={ver}")}}')
        regole.append(f'.palco__sprite:has(>[data-sprite="{n}"]),.palchetto:not(.palchetto--due):has(>[data-sprite="{n}"]),'
                      f'.continua__gig:has(>[data-sprite="{n}"]){{--cw:{cw};--ch:{ch}}}')
    return "\n".join(regole)


def conta_test() -> int:
    """Quanti gruppi di test automatici ha il gioco: le funzioni _test_ di game/tests e dei test dell'audio.
    Ogni gruppo fa più controlli: il numero dei controlli lo dice Godot quando li esegue."""
    n = 0
    for p in list(TESTS.rglob("*.gd")) + list((ROOT / "tools" / "audio" / "godot_tests").rglob("*.gd")):
        n += len(re.findall(r"^func _?test_\w*\(", p.read_text(encoding="utf-8", errors="replace"), re.M))
    if n == 0:
        raise Errore("non trovo i test del gioco (func _test_ in game/tests): il testo di «A che punto siamo» li conta")
    return n


def glifi_ttf(p: Path) -> set[int]:
    """I caratteri che il font ha, letti dalla tabella cmap (formati 4 e 12)."""
    dati = p.read_bytes()
    n = struct.unpack(">H", dati[4:6])[0]
    tabelle = {dati[12 + 16 * i:16 + 16 * i].decode("latin-1"): struct.unpack(">II", dati[20 + 16 * i:28 + 16 * i])
               for i in range(n)}
    off = tabelle["cmap"][0]
    _, quante = struct.unpack(">HH", dati[off:off + 4])
    codici: set[int] = set()
    for i in range(quante):
        _, _, sub = struct.unpack(">HHI", dati[off + 4 + 8 * i:off + 12 + 8 * i])
        s = off + sub
        formato = struct.unpack(">H", dati[s:s + 2])[0]
        if formato == 4:
            segx2 = struct.unpack(">H", dati[s + 6:s + 8])[0]
            fine = struct.unpack(f">{segx2 // 2}H", dati[s + 14:s + 14 + segx2])
            inizio = struct.unpack(f">{segx2 // 2}H", dati[s + 16 + segx2:s + 16 + 2 * segx2])
            for a, b in zip(inizio, fine):
                if a != 0xFFFF:
                    codici.update(range(a, b + 1))
        elif formato == 12:
            gruppi = struct.unpack(">I", dati[s + 12:s + 16])[0]
            for g in range(gruppi):
                a, b, _ = struct.unpack(">III", dati[s + 16 + 12 * g:s + 28 + 12 * g])
                codici.update(range(a, b + 1))
    return codici


def csp(script_in_linea: str) -> str:
    """La Content-Security-Policy delle pagine: tutto dal sito stesso, e l'unico script in linea è scala.js.
    Gli stili in linea servono agli sprite (style e <style>); data: alle maschere a scacchi disegnate da sito.js."""
    impronta = base64.b64encode(hashlib.sha256(script_in_linea.encode("utf-8")).digest()).decode("ascii")
    return ("default-src 'self'; script-src 'self' 'sha256-" + impronta + "'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; media-src 'self'; font-src 'self'; connect-src 'self'; object-src 'none'; "
            "base-uri 'self'; form-action 'none'")


def controlla_csp(sorgente: str, nome: str) -> list[str]:
    """Ogni script in linea della pagina finita deve avere la sua impronta nella CSP."""
    m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', sorgente)
    if not m:
        return [f"{nome}: manca la Content-Security-Policy"]
    politica = html.unescape(m.group(1))
    errori = []
    for corpo in re.findall(r"<script>(.*?)</script>", sorgente, re.S):
        impronta = base64.b64encode(hashlib.sha256(corpo.encode("utf-8")).digest()).decode("ascii")
        if f"'sha256-{impronta}'" not in politica:
            errori.append(f"{nome}: uno script in linea non è ammesso dalla CSP")
    return errori


# ------------------------------------------------------------------ controlli sulle pagine finite

class _Raccogli(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rif: list[tuple[str, str, str]] = []      # (tag, attributo, valore)
        self.id: set[str] = set()
        self.testo: list[str] = []
        self.attr_testo: list[str] = []
        self._salta = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            if a["id"] in self.id:
                raise Errore(f"id doppio: {a['id']}")
            self.id.add(a["id"])
        for k, v in attrs:
            if v is None:
                continue
            if k in ("src", "href", "poster", "srcset", "content") or k.startswith("data-src"):
                self.rif.append((tag, k, v))
            if k in ("alt", "title", "aria-label", "content", "placeholder") or k.startswith("data-testo"):
                self.attr_testo.append(v)
        if tag in ("script", "style"):
            self._salta += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._salta -= 1

    def handle_data(self, data):
        if not self._salta:
            self.testo.append(data)


def controlla_pagina(out: Path, file: Path, url_sito: str) -> list[str]:
    errori = []
    sorgente = file.read_text(encoding="utf-8")
    r = _Raccogli()
    r.feed(sorgente)
    nome = file.relative_to(out).as_posix()
    base = urlparse(url_sito)
    for tag, attr, v in r.rif:
        if attr == "content" and not re.match(r"https?://|/", v):
            continue                                  # meta content che non è un indirizzo
        if attr == "srcset":
            valori = [x.strip().split()[0] for x in v.split(",") if x.strip()]
        else:
            valori = [v]
        for u in valori:
            p = urlparse(u)
            if p.scheme in ("http", "https"):
                proprio = p.netloc == base.netloc and p.path.startswith(base.path)
                scaricata = tag in ("script", "img", "video", "source", "audio", "iframe", "track", "embed") or (
                    tag == "link" and attr == "href" and not _link_navigazione(sorgente, u))
                if scaricata and not proprio:
                    errori.append(f"{nome}: risorsa esterna <{tag} {attr}={u}>")
                if proprio:
                    # og:image, canonical, alternate: indirizzi assoluti del sito, il file deve esserci
                    resto = p.path[len(base.path):]
                    dest = out / resto
                    if not (resto == RISERVATA or resto.startswith(RISERVATA + "/")):
                        esiste = (dest / "index.html").exists() if (not resto or resto.endswith("/") or dest.is_dir()) else dest.exists()
                        if not esiste:
                            errori.append(f"{nome}: {u} non esiste nel sito")
                continue
            if p.scheme in ("mailto", "data") or u.startswith("#") or not u:
                if u.startswith("#") and len(u) > 1 and u[1:] not in r.id:
                    errori.append(f"{nome}: ancora senza destinazione {u}")
                continue
            if p.scheme:
                errori.append(f"{nome}: indirizzo strano {u}")
                continue
            if u.startswith("/"):
                if not u.startswith(base.path):
                    errori.append(f"{nome}: percorso assoluto fuori dal sito {u}")
                    continue
                dest = out / p.path[len(base.path):]
            else:
                dest = (file.parent / p.path).resolve()
            rel = dest.resolve().relative_to(out.resolve()).as_posix() if dest.resolve().is_relative_to(out.resolve()) else None
            if rel is None:
                errori.append(f"{nome}: {u} esce dalla cartella del sito")
                continue
            if rel == RISERVATA or rel.startswith(RISERVATA + "/"):
                continue                                  # la demo la mette il workflow
            esiste = (dest / "index.html").exists() if dest.is_dir() else dest.exists()
            if not esiste:
                errori.append(f"{nome}: {u} non esiste")
    testo = " ".join(r.testo + r.attr_testo)
    errori += [f"{nome}: {e}" for e in parole_vietate(testo)]
    errori += controlla_csp(sorgente, nome)
    return errori


def _link_navigazione(sorgente: str, u: str) -> bool:
    """<link rel="canonical|alternate"> verso le pagine: non sono risorse da scaricare."""
    return bool(re.search(r'<link rel="(canonical|alternate)"[^>]*href="' + re.escape(u) + '"', sorgente))


def parole_vietate(testo: str) -> list[str]:
    trovate = []
    for w in VIETATE_SENSIBILI:
        if re.search(r"\b" + re.escape(w) + r"\b", testo):
            trovate.append(f"parola vietata «{w}»")
    for w in VIETATE:
        m = re.search(w, testo, re.I)
        if m:
            trovate.append(f"parola vietata «{m.group(0)}»")
    return trovate


def controlla_css(out: Path) -> list[str]:
    errori = []
    for p in (out / "css").rglob("*.css"):
        for u in re.findall(r"url\(\s*['\"]?([^'\")]+)", p.read_text(encoding="utf-8")):
            if u.startswith("data:"):
                continue
            if re.match(r"[a-z]+:", u) or u.startswith("//"):
                errori.append(f"{p.relative_to(out).as_posix()}: risorsa esterna {u}")
            elif not (p.parent / u).resolve().exists():
                errori.append(f"{p.relative_to(out).as_posix()}: {u} non esiste")
        if "@import" in p.read_text(encoding="utf-8"):
            errori.append(f"{p.relative_to(out).as_posix()}: niente @import")
    for p in (out / "js").rglob("*.js"):
        s = p.read_text(encoding="utf-8")
        for u in re.findall(r"['\"`](https?://[^'\"`]+)", s):
            errori.append(f"{p.relative_to(out).as_posix()}: indirizzo esterno {u}")
        if re.search(r"document\.cookie|navigator\.sendBeacon|\bgtag\(|analytics", s):
            errori.append(f"{p.relative_to(out).as_posix()}: niente cookie né tracciamenti")
    return errori


# ------------------------------------------------------------------ costruzione

def _scrivibile(func, percorso, _info=None) -> None:
    """Per rmtree: su Windows le cartelle copiate da OneDrive hanno l'attributo di sola lettura."""
    os.chmod(percorso, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
    func(percorso)


def _cancella(cartella: Path) -> None:
    """Svuota una cartella fatta da questo script. Su Windows antivirus, indicizzatore e OneDrive tengono
    aperti per un attimo i file appena scritti, e le cartelle possono essere in sola lettura: si riprova."""
    for tentativo in range(20):
        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(cartella, onexc=_scrivibile)
            else:
                shutil.rmtree(cartella, onerror=_scrivibile)
            return
        except FileNotFoundError:
            return
        except OSError:
            if tentativo == 19:
                raise
            time.sleep(0.5)


def _copia(da: Path, a: Path) -> None:
    """copytree senza gli attributi dei file (niente sola lettura ereditata da OneDrive): ai permessi si
    aggiunge solo la scrittura per chi costruisce, il resto resta com'è (0644 e 0755 su Linux)."""
    shutil.copytree(da, a, copy_function=shutil.copyfile, ignore=shutil.ignore_patterns("*.md", "__pycache__", "media.json"),
                    dirs_exist_ok=True)
    for p in [a, *a.rglob("*")]:
        os.chmod(p, os.stat(p).st_mode | stat.S_IWUSR)

def costruisci(out: Path, url: str | None) -> None:
    dati = _carica(CONTENT / "dati.json")
    url_sito = (url or dati["url_sito"]).rstrip("/") + "/"
    numeri = dict(dati.get("link", {}))
    numeri.update(dati.get("numeri", {}))
    numeri["test"] = conta_test()
    manifesto = _carica(MEDIA / "media.json")
    numeri.setdefault("punteggio", manifesto["cattura"]["punteggio"])
    numeri.setdefault("tick", manifesto["cattura"]["tick_fine"])
    numeri.setdefault("hash", manifesto["cattura"]["hash"][:8])
    numeri.setdefault("godot", dati["godot"])

    testi = {l: _segnaposti(_filtra(_carica(CONTENT / f"{l}.json")), numeri, l) for l in LINGUE}
    for l in LINGUE:
        arricchisci(testi[l], manifesto, l)
    diff = _differenze(_forma(_carica(CONTENT / "it.json")), _forma(_carica(CONTENT / "en.json")))
    if diff:
        raise Errore("it.json ed en.json non hanno la stessa struttura:\n  " + "\n  ".join(diff[:30]))

    glifi = glifi_ttf(FONT_TTF)
    modello = _parse((MODELLO / "pagina.html").read_text(encoding="utf-8"), "pagina.html")
    modello404 = _parse((MODELLO / "404.html").read_text(encoding="utf-8"), "404.html")

    if out.exists():
        if not (out / ".sito-costruito").exists() and any(out.iterdir()):
            raise Errore(f"{out} non è vuota e non l'ha fatta questo script: non la cancello")
        _cancella(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / ".sito-costruito").write_text("fatta da tools/site/build.py\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    for cartella in ("css", "js", "media"):
        _copia(SITE / cartella, out / cartella)
    if (out / RISERVATA).exists():
        raise Errore(f"site/ contiene già {RISERVATA}/: è il posto della demo web")

    percorso = urlparse(url_sito).path
    scala_js = (SITE / "js" / "scala.js").read_text(encoding="utf-8")
    gen = {"sprite_css": css_sprite(percorso), "scala_js": scala_js, "csp": csp(scala_js)}
    pagine = {}
    for l in LINGUE:
        altra = "en" if l == "it" else "it"
        radice = "" if l == "it" else "../"
        pagina = {
            "lingua": l, "altra": altra, "radice": radice,
            "url": url_sito + ("" if l == "it" else "en/"),
            "url_it": url_sito, "url_en": url_sito + "en/",
            "url_altra": url_sito + ("en/" if l == "it" else ""),
            "href_altra": ("en/" if l == "it" else "../"),
            "gioca": radice + RISERVATA + "/?lang=" + l,
            "og_immagine": url_sito + "media/" + manifesto["social"]["file"],
            "assoluta": percorso,
            "media_v": versione_sprite(),
        }
        ctx = [{"t": testi[l], "d": dati, "m": manifesto, "n": numeri, "pagina": pagina,
                "altra_t": testi[altra], "gen": gen}]
        html_pagina = Pagina(f"pagina.html ({l})", glifi).rendi(modello, ctx)
        dest = out / ("index.html" if l == "it" else "en/index.html")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_pagina, encoding="utf-8")
        pagine[l] = dest
    ctx = [{"it": testi["it"], "en": testi["en"], "d": dati, "m": manifesto, "n": numeri,
            "pagina": {"assoluta": percorso, "url_it": url_sito, "url_en": url_sito + "en/", "media_v": versione_sprite()},
            "gen": gen}]
    (out / "404.html").write_text(Pagina("404.html", glifi).rendi(modello404, ctx), encoding="utf-8")

    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {url_sito}sitemap.xml\n", encoding="utf-8")
    voci = []
    for l in LINGUE:
        loc = url_sito + ("" if l == "it" else "en/")
        alt = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{x}" href="{url_sito + ("" if x == "it" else "en/")}"/>'
                      for x in LINGUE)
        voci.append(f"  <url>\n    <loc>{loc}</loc>{alt}\n  </url>")
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(voci) + "\n</urlset>\n", encoding="utf-8")

    errori = []
    for f in list(pagine.values()) + [out / "404.html"]:
        errori += controlla_pagina(out, f, url_sito)
    errori += controlla_css(out)
    if errori:
        raise Errore("Il sito non passa i controlli:\n  " + "\n  ".join(errori))
    peso = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"sito: {out} · {len(list(out.rglob('*.html')))} pagine, {peso / 1e6:.1f} MB · "
          f"{numeri['test']} test contati · indirizzo {url_sito}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "_site"), help="cartella di uscita (predefinita: _site)")
    ap.add_argument("--url", default=None, help="indirizzo del sito, se diverso da quello di dati.json")
    a = ap.parse_args()
    try:
        costruisci(Path(a.out).resolve(), a.url)
    except Errore as e:
        print(f"ERRORE: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
