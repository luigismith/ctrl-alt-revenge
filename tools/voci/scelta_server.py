#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Il server locale della pagina delle voci: la pagina viene dal repo (tools/voci/scelta/index.html), l'audio e i dati
da <laboratorio>\\tts\\voci; le scelte finiscono in <laboratorio>\\tts\\voci\\scelta\\scelte_luigi.json.

Uso:  python -I tools/voci/scelta_server.py [porta]      poi si apre http://127.0.0.1:8765/
Il laboratorio è %CAR_LAB%, altrimenti %USERPROFILE%\\ctrlaltrevenge-lab.
Ascolta solo su 127.0.0.1: le voci non escono dal PC. Si ferma con Ctrl+C.
"""
import json
import os
import shutil
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

LAB = os.path.join(os.environ.get("CAR_LAB") or os.path.join(os.environ.get("USERPROFILE") or os.path.expanduser("~"),
                                                             "ctrlaltrevenge-lab"), "tts")
RADICE = os.path.join(LAB, "voci")
PAGINA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scelta", "index.html")
SCELTE = os.path.join(RADICE, "scelta", "scelte_luigi.json")
MAX = 256 * 1024


class Gestore(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".ogg": "audio/ogg", ".mp4": "video/mp4",
                      ".json": "application/json", ".js": "text/javascript", ".html": "text/html; charset=utf-8",
                      ".css": "text/css", ".ass": "text/plain; charset=utf-8"}

    def __init__(self, *args, **kw):
        super().__init__(*args, directory=RADICE, **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "/scelta/")
            self.end_headers()
            return
        if self.path.split("?")[0] in ("/scelta/", "/scelta/index.html"):
            body = open(PAGINA, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if rng and rng.startswith("bytes=") and os.path.isfile(path):
            return self.parziale(path, rng)
        super().do_GET()

    def parziale(self, path, rng):
        size = os.path.getsize(path)
        a, _, b = rng[6:].split(",")[0].partition("-")
        try:
            start = int(a) if a else max(0, size - int(b))
            end = int(b) if (a and b) else size - 1
        except ValueError:
            self.send_error(416)
            return
        if start >= size:
            self.send_response(416)
            self.send_header("Content-Range", "bytes */%d" % size)
            self.end_headers()
            return
        end = min(end, size - 1)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            self.wfile.write(f.read(end - start + 1))

    def do_POST(self):
        if self.path != "/salva":
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX:
            self.send_error(413)
            return
        try:
            dati = json.loads(self.rfile.read(n).decode("utf-8"))
            assert isinstance(dati, dict)
        except Exception:
            self.send_error(400, "JSON non valido")
            return
        dati["salvato"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if os.path.exists(SCELTE):
            shutil.copyfile(SCELTE, SCELTE + ".prima")
        tmp = SCELTE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(dati, f, ensure_ascii=False, indent=1)
        os.replace(tmp, SCELTE)
        body = json.dumps({"ok": True, "salvato": dati["salvato"]}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    srv = ThreadingHTTPServer(("127.0.0.1", porta), Gestore)
    print("Pagina delle voci: http://127.0.0.1:%d/  (Ctrl+C per fermare)" % porta, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
