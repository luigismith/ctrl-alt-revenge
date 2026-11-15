# -*- coding: utf-8 -*-
"""La coda: i contenuti in contenuti/*.yml, i loro controlli e il veto.

Formato di un contenuto: vedi docs/progetto.md, §3.

Il veto: quando un contenuto è «pronto» gli si apre una issue «In coda: <id>».
Chiuderla (anche dall'app GitHub sul telefono) lo ferma; riaprirla lo fa
ripartire. Dopo l'uscita la issue la chiude il bot, con il permalink.
"""
import datetime as dt
import os
import pathlib
import re
import subprocess

import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from comune import RADICE, apri_issue, gh_disponibile, leggi_issue, oggi_roma

CARTELLA = RADICE / "contenuti"
TIPI = {"carosello", "immagine", "reel"}
STATI = {"bozza", "pronto"}
MAX_DIDASCALIA = 2200          # Instagram, in unità UTF-16
MAX_HASHTAG = 5
MAX_TAVOLE = 10                # ne bastano 10: l'API ne accetterebbe 20
MAX_TITOLO_YT = 100
MAX_DESCR_YT = 5000
REEL_SECONDI = (3, 90)         # sotto i 90 s vale anche come Short
VETO_ORE = 48
BOT = "github-actions[bot]"

# La lista nera degli spoiler NON sta nel repository (è pubblico: sarebbe
# un indice della trama). Sul runner arriva dal secret, in locale da un file
# fuori dal repository. Se manca, i controlli falliscono.
SPOILER_SECRET = "CARU_PAROLE_VIETATE"
SPOILER_LOCALE = pathlib.Path(r"C:\Users\Admin\ctrlaltrevenge-lab\social-privato\spoiler.txt")


def leggi(percorso):
    dati = yaml.safe_load(pathlib.Path(percorso).read_text(encoding="utf-8")) or {}
    dati["_file"] = pathlib.Path(percorso)
    return dati


def tutti():
    return [leggi(p) for p in sorted(CARTELLA.glob("*.yml"))]


def salva_campo(contenuto, campo, valore):
    """Cambia un campo nel file YAML senza riscriverlo tutto (i commenti restano)."""
    f = contenuto["_file"]
    testo = f.read_text(encoding="utf-8")
    riga = f"{campo}: {valore}"
    if re.search(rf"^{campo}:.*$", testo, flags=re.M):
        testo = re.sub(rf"^{campo}:.*$", riga, testo, count=1, flags=re.M)
    else:
        testo = testo.rstrip("\n") + "\n" + riga + "\n"
    f.write_text(testo, encoding="utf-8")
    contenuto[campo] = valore


def data_uscita(c):
    u = c.get("uscita")
    return u if isinstance(u, dt.date) else dt.date.fromisoformat(str(u))


def fonte(c):
    return RADICE / str(c.get("fonte", ""))


def parole_vietate():
    testo = os.environ.get(SPOILER_SECRET)
    if testo is None and SPOILER_LOCALE.exists():
        testo = SPOILER_LOCALE.read_text(encoding="utf-8")
    if testo is None:
        return None
    # Formato (della regia): una voce per riga, # per i commenti, maiuscole
    # indifferenti. [voce] = parola intera («[Riva]» non scatta su «arriva»);
    # le altre si cercano anche come pezzo di parola.
    regole = []
    for riga in testo.splitlines():
        v = riga.strip()
        if not v or v.startswith("#"):
            continue
        if v.startswith("[") and v.endswith("]") and len(v) > 2:
            regole.append(re.compile(rf"(?<!\w){re.escape(v[1:-1].strip())}(?!\w)", re.I))
        else:
            regole.append(re.compile(re.escape(v), re.I))
    return regole


def unita_utf16(s):
    return len(s.encode("utf-16-le")) // 2


def info_video(percorso):
    """(durata in secondi, ha_audio). Usa ffprobe se c'è; sul runner di GitHub
    ffmpeg arriva da pip (imageio-ffmpeg) senza ffprobe, quindi si legge
    l'intestazione di `ffmpeg -i`."""
    import shutil
    if shutil.which("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                            "-of", "default=nw=1", str(percorso)], capture_output=True, text=True)
        if r.returncode != 0:
            return None, False
        durata = re.search(r"duration=([\d.]+)", r.stdout)
        return (float(durata.group(1)) if durata else None), "codec_type=audio" in r.stdout
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(percorso)], capture_output=True, text=True)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    durata = int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else None
    return durata, bool(re.search(r"Stream #.*: Audio:", r.stderr))


def durata_video(percorso):
    return info_video(percorso)[0]


def testi_pubblici(c):
    """Tutto il testo che finisce online: è qui che si cercano gli spoiler."""
    righe = [("didascalia", str(c.get("didascalia", "")))]
    for n, t in enumerate(c.get("tavole") or [], start=1):
        righe += [(f"tavola {n}, testo", str(t.get("testo", ""))), (f"tavola {n}, alt", str(t.get("alt", "")))]
    yt = c.get("youtube") or {}
    righe += [("titolo YouTube", str(yt.get("titolo", ""))), ("descrizione YouTube", str(yt.get("descrizione", "")))]
    righe += [("hashtag", " ".join(c.get("hashtag") or []))]
    return righe


def valida(c, vietate):
    """Restituisce la lista degli errori (vuota se va bene).
    Una parola vietata si segnala con il campo e la riga, MAI con la parola:
    i log del repository sono pubblici."""
    e = []
    nome = c["_file"].name
    for campo in ("id", "tipo", "uscita", "stato", "fonte", "didascalia"):
        if not c.get(campo):
            e.append(f"{nome}: manca «{campo}»")
    if e:
        return e
    if c["_file"].stem != str(c["id"]):
        e.append(f"{nome}: l'id deve essere uguale al nome del file")
    if c["tipo"] not in TIPI:
        e.append(f"{nome}: tipo «{c['tipo']}» sconosciuto ({', '.join(sorted(TIPI))})")
    if c["stato"] not in STATI:
        e.append(f"{nome}: stato «{c['stato']}» sconosciuto")
    try:
        data_uscita(c)
    except ValueError:
        e.append(f"{nome}: data di uscita non valida")
    if not fonte(c).is_dir():
        e.append(f"{nome}: la cartella della fonte non esiste")
    if unita_utf16(str(c["didascalia"])) > MAX_DIDASCALIA:
        e.append(f"{nome}: didascalia oltre {MAX_DIDASCALIA} caratteri")
    hashtag = c.get("hashtag") or []
    if len(hashtag) > MAX_HASHTAG:
        e.append(f"{nome}: {len(hashtag)} hashtag, il massimo è {MAX_HASHTAG}")
    if any(not re.fullmatch(r"[\wàèéìòù]+", h) for h in hashtag):
        e.append(f"{nome}: gli hashtag vanno scritti senza # e senza spazi")
    if "#" in str(c["didascalia"]):
        e.append(f"{nome}: gli hashtag vanno nel campo «hashtag», non nella didascalia")
    if not isinstance(c.get("ai", False), bool):
        e.append(f"{nome}: «ai» deve essere true o false")

    if c["tipo"] in ("carosello", "immagine"):
        tavole = c.get("tavole") or []
        if c["tipo"] == "immagine" and len(tavole) != 1:
            e.append(f"{nome}: un'immagine ha una tavola sola")
        if c["tipo"] == "carosello" and not 2 <= len(tavole) <= MAX_TAVOLE:
            e.append(f"{nome}: un carosello ha da 2 a {MAX_TAVOLE} tavole")
        for n, t in enumerate(tavole, start=1):
            if not (fonte(c) / str(t.get("media", ""))).is_file():
                e.append(f"{nome}: tavola {n}, il file del media non c'è")
            if not t.get("alt"):
                e.append(f"{nome}: tavola {n}, manca il testo alternativo (alt)")
            elif len(str(t["alt"])) > 1000:
                e.append(f"{nome}: tavola {n}, alt oltre 1000 caratteri")
    if c["tipo"] == "reel":
        video = fonte(c) / str(c.get("video", ""))
        if not c.get("video") or not video.is_file():
            e.append(f"{nome}: il video non c'è")
        else:
            d = durata_video(video)
            if d is None:
                e.append(f"{nome}: il video non si legge (ffprobe)")
            elif not REEL_SECONDI[0] <= d <= REEL_SECONDI[1]:
                e.append(f"{nome}: il video dura {d:.1f} s, va da {REEL_SECONDI[0]} a {REEL_SECONDI[1]} s")
        yt = c.get("youtube") or {}
        if not yt.get("titolo"):
            e.append(f"{nome}: un reel diventa anche Short: manca youtube.titolo")
        elif len(str(yt["titolo"])) > MAX_TITOLO_YT or re.search(r"[<>]", str(yt["titolo"])):
            e.append(f"{nome}: titolo YouTube oltre {MAX_TITOLO_YT} caratteri o con < >")
        if len(str(yt.get("descrizione", ""))) > MAX_DESCR_YT or re.search(r"[<>]", str(yt.get("descrizione", ""))):
            e.append(f"{nome}: descrizione YouTube troppo lunga o con < >")

    if vietate is None:
        e.append(f"{nome}: lista degli spoiler assente (secret {SPOILER_SECRET} o file locale): non si pubblica alla cieca")
    else:
        for campo, testo in testi_pubblici(c):
            for n_riga, riga in enumerate(testo.splitlines() or [""], start=1):
                if any(r.search(riga) for r in vietate):
                    e.append(f"{nome}: parola della lista nera in «{campo}», riga {n_riga}")
    return e


# ------------------------------------------------------------------ veto ---

def titolo_veto(c):
    return f"In coda: {c['id']}"


def apri_veto(c, anteprima_url=None):
    """Apre la issue di veto (se manca) e ne scrive il numero nel contenuto."""
    if c.get("issue"):
        return c["issue"]
    corpo = (f"**Esce il {data_uscita(c):%d/%m/%Y}** su Instagram"
             + (" e YouTube Shorts" if c["tipo"] == "reel" else "") + ".\n\n"
             "> Per **fermarlo**, chiudi questa issue (anche dall'app GitHub sul telefono).\n"
             "> Per farlo ripartire, riaprila.\n\n"
             f"**Didascalia:**\n\n{c['didascalia']}\n\n"
             + (f"**Anteprima:** {anteprima_url}\n" if anteprima_url else ""))
    numero = apri_issue(titolo_veto(c), corpo, etichette=("in coda",))
    if numero:
        salva_campo(c, "issue", numero)
    return numero


def veto(c):
    """(via_libera, motivo). Senza issue non si pubblica: la si apre e si
    aspetta la finestra di 48 ore."""
    if not gh_disponibile():
        return True, "GitHub non raggiungibile da qui (prova locale): veto non controllato"
    if not c.get("issue"):
        apri_veto(c)
        return False, f"issue di veto appena aperta: si aspettano {VETO_ORE} ore"
    i = leggi_issue(c["issue"])
    if i.get("state") == "closed":
        chi = (i.get("closed_by") or {}).get("login", "?")
        return False, f"issue #{c['issue']} chiusa da {chi}: contenuto fermato"
    aperta = dt.datetime.fromisoformat(i["created_at"].replace("Z", "+00:00"))
    if dt.datetime.now(dt.timezone.utc) - aperta < dt.timedelta(hours=VETO_ORE):
        return False, f"issue #{c['issue']} aperta da meno di {VETO_ORE} ore"
    return True, f"issue #{c['issue']} aperta, nessun veto"


def prossimo(contenuti, gia_usciti, tipi):
    """Il contenuto più vecchio pronto, di questi tipi, con la data arrivata."""
    candidati = [c for c in contenuti
                 if c.get("stato") == "pronto" and c.get("tipo") in tipi
                 and c["id"] not in gia_usciti and data_uscita(c) <= oggi_roma()]
    return sorted(candidati, key=lambda c: (data_uscita(c), c["id"]))[0] if candidati else None


if __name__ == "__main__":
    # python strumenti/coda.py prossimo  → l'id del prossimo contenuto da preparare (o niente)
    import sys
    from comune import leggi_stato, uscite_di
    if sys.argv[1:] == ["prossimo"]:
        c = prossimo(tutti(), {u["id"] for u in uscite_di(leggi_stato(), "instagram")}, TIPI)
        print(c["id"] if c else "")
