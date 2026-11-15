# -*- coding: utf-8 -*-
"""Genera i file da pubblicare di un contenuto in docs/social/<id>/.

- carosello e immagine: le tavole 1080x1350 (01.jpg, 02.jpg, ...);
- per tutti: storia.jpg, 1080x1920, la tavola verticale per la storia;
- reel: reel.mp4 (1080x1920, H.264 + AAC, moov in testa) e copertina.jpg.

Le tavole sono HTML (sito/tavola.html) fotografato da Chrome senza finestra:
sul runner di GitHub Chrome c'è già, sul PC anche. Niente Playwright.

Uso:
  python strumenti/genera_media.py <id>                 # contenuti/<id>.yml
  python strumenti/genera_media.py --file prove/x.yml --uscita <cartella>
"""
import argparse
import functools
import http.server
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import coda  # noqa: E402
from comune import RADICE  # noqa: E402

MODELLO = RADICE / "sito" / "tavola.html"
PORTA = 8766
MAX_MB_VIDEO = 50


def trova_chrome():
    for c in (os.environ.get("CHROME"), r"C:/Program Files/Google/Chrome/Application/chrome.exe",
              shutil.which("google-chrome"), shutil.which("google-chrome-stable"), shutil.which("chromium")):
        if c and pathlib.Path(c).exists():
            return c
    sys.exit("[errore] Chrome non trovato (variabile CHROME)")


class Server:
    """Un server locale sulla radice del repository: i caratteri si caricano
    solo via http, non da file://."""
    def __enter__(self):
        class Q(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORTA), functools.partial(Q, directory=str(RADICE)))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *a):
        self.srv.shutdown()


def fotografa(chrome, html, w, h, png, tmp):
    # un nome nuovo a ogni scatto: con lo stesso indirizzo Chrome può servire
    # dalla cache la tavola precedente (la storia usciva con la pagina del post)
    pagina = RADICE / f"_tavola_{os.getpid()}_{uuid.uuid4().hex[:8]}.html"
    pagina.write_text(html, encoding="utf-8")
    try:
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
                        f"--user-data-dir={tmp / 'profilo'}", f"--window-size={w},{h}",
                        "--force-device-scale-factor=1", "--virtual-time-budget=5000",
                        f"--screenshot={png}", f"http://127.0.0.1:{PORTA}/{pagina.name}"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    finally:
        pagina.unlink(missing_ok=True)
    im = Image.open(png).convert("RGB")
    if im.size != (w, h):
        im = im.crop((0, 0, w, h))
    return im


def compila(valori):
    html = MODELLO.read_text(encoding="utf-8")
    for k, v in valori.items():
        html = html.replace("{{" + k + "}}", str(v))
    return html


def proporzione(percorso):
    with Image.open(percorso) as im:
        return im.height / im.width


def tavola(chrome, tmp, immagine_url, rapporto, scritta, formato, prima=False, inquadra="50% 50%"):
    import html as h
    if formato == "post":
        w, hh = 1080, 1350
        quadro_w, top = 980, (250 if prima else 220)
        # 4:5 è più alto di 16:9: si riempie il quadro e si ritaglia ai lati
        img_h = 700
        v = dict(tasto_px=46 if prima else 34, spray_px=80 if prima else 58, strati_h=110, scritta_px=36)
    else:
        w, hh = 1080, 1920
        quadro_w, top = 940, 340
        img_h = 1000
        v = dict(tasto_px=58, spray_px=104, strati_h=150, scritta_px=40)
    v.update(larghezza=w, altezza=hh, quadro_top=top, quadro_w=quadro_w, img_h=img_h,
             scritta_top=top + img_h + 36 + 70, rotazione=-1.2 if prima else 0.8,
             immagine=immagine_url or "", scritta=h.escape(scritta or ""), inquadra=inquadra,
             classe="vuoto" if immagine_url is None else "")
    if immagine_url is None:  # fondo del reel: la scritta va in basso, il video in mezzo
        v["scritta_top"] = 1480
    return fotografa(chrome, compila(v), w, hh, tmp / "t.png", tmp)


def ha_audio(video):
    return coda.info_video(video)[1]


def componi_reel(fondo_png, video, uscita):
    """Il video al centro del fondo verticale. Specifiche di Instagram:
    MP4 con moov in testa, H.264 progressivo a GOP chiusi, 4:2:0, AAC 48 kHz."""
    filtro = ("[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,setsar=1[v];"
              "[0:v][v]overlay=(W-w)/2:(H-h)/2:shortest=1,fps=30,format=yuv420p[out]")
    cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(fondo_png), "-i", str(video)]
    if ha_audio(video):
        mappa_audio = ["-map", "1:a:0"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        mappa_audio = ["-map", "2:a:0", "-shortest"]
    cmd += ["-filter_complex", filtro, "-map", "[out]", *mappa_audio,
            "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "21", "-maxrate", "12M",
            "-bufsize", "24M", "-g", "60", "-keyint_min", "60", "-sc_threshold", "0", "-flags", "+cgop",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(uscita)]
    subprocess.run(cmd, check=True)
    mb = uscita.stat().st_size / 1e6
    if mb > MAX_MB_VIDEO:
        raise RuntimeError(f"reel di {mb:.0f} MB, oltre {MAX_MB_VIDEO} MB: comprimere la fonte")


def genera(c, uscita):
    uscita.mkdir(parents=True, exist_ok=True)
    chrome = trova_chrome()
    base = "/" + str(coda.fonte(c).relative_to(RADICE)).replace("\\", "/")
    prodotti = []
    with Server(), tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        if c["tipo"] in ("carosello", "immagine"):
            for n, tv in enumerate(c["tavole"], start=1):
                media = coda.fonte(c) / tv["media"]
                im = tavola(chrome, tmp, f"{base}/{tv['media']}", proporzione(media), tv.get("testo"), "post",
                            prima=(n == 1), inquadra=tv.get("inquadra", "50% 50%"))
                f = uscita / f"{n:02d}.jpg"
                im.save(f, quality=90, optimize=True, progressive=False)  # JPEG semplice: l'API vuole JPEG
                prodotti.append(f)
            prima = c["tavole"][0]
            st = tavola(chrome, tmp, f"{base}/{prima['media']}", proporzione(coda.fonte(c) / prima["media"]),
                        prima.get("testo"), "verticale", inquadra=prima.get("inquadra", "50% 50%"))
            st.save(uscita / "storia.jpg", quality=88)
            prodotti.append(uscita / "storia.jpg")
        else:
            fondo = tavola(chrome, tmp, None, 0, c.get("scritta"), "verticale")
            fondo_png = tmp / "fondo.png"
            fondo.save(fondo_png)
            reel = uscita / "reel.mp4"
            componi_reel(fondo_png, coda.fonte(c) / c["video"], reel)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i", str(reel), "-frames:v", "1",
                            "-q:v", "3", str(uscita / "copertina.jpg")], check=True)
            prodotti += [reel, uscita / "copertina.jpg"]
    (uscita / "indice.json").write_text(json.dumps([p.name for p in prodotti], indent=1), encoding="utf-8")
    for p in prodotti:
        print(f"[ok] {p.relative_to(RADICE) if p.is_relative_to(RADICE) else p}  {p.stat().st_size // 1024} KB")
    return prodotti


def main():
    a = argparse.ArgumentParser()
    a.add_argument("id", nargs="?")
    a.add_argument("--file")
    a.add_argument("--uscita")
    arg = a.parse_args()
    c = coda.leggi(arg.file) if arg.file else coda.leggi(coda.CARTELLA / f"{arg.id}.yml")
    uscita = pathlib.Path(arg.uscita) if arg.uscita else RADICE / "docs" / "social" / str(c["id"])
    genera(c, uscita)


if __name__ == "__main__":
    main()
