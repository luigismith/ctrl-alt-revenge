# -*- coding: utf-8 -*-
"""Una volta sola, sul PC di Luigi: il consenso di Google per il canale
YouTube del gioco, e i tre secret di GitHub.

  python -I strumenti/ottieni_token_youtube.py

Cosa fa:
1. chiede l'ID client e il segreto client del client OAuth «App desktop»
   (si incollano, non si vedono mentre si scrivono);
2. apre il browser sul consenso di Google: lì si sceglie il CANALE del gioco
   (l'account brand Ctrl-Alt-Revenge), non quello personale;
3. riceve la risposta su 127.0.0.1, scambia il codice (con PKCE) e controlla
   quale canale ha dato il consenso;
4. se il canale è giusto, carica YT_CLIENT_ID, YT_CLIENT_SECRET e
   YT_REFRESH_TOKEN nei secret del repository con `gh secret set`, leggendoli
   da stdin: niente finisce sullo schermo, in un file o nella cronologia.

Prima: la schermata di consenso del progetto Google va messa «In production».
In «Testing» il refresh token scade dopo 7 giorni.
Il refresh token non serve copiarlo in Vaultwarden: se si perde, si rilancia
questo script. In Vaultwarden vanno l'ID client e il segreto client.
"""
import base64
import getpass
import hashlib
import http.server
import json
import secrets
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

AMBITI = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
REPO_PREDEFINITO = "luigismith/ctrl-alt-revenge"


def chiedi(testo):
    v = getpass.getpass(testo + " (non si vede mentre lo incolli): ").strip()
    if not v:
        sys.exit("vuoto: interrotto")
    return v


def main():
    if not shutil.which("gh"):
        sys.exit("serve gh (GitHub CLI) con il login fatto: gh auth login")
    repo = (input(f"Repository [{REPO_PREDEFINITO}]: ").strip() or REPO_PREDEFINITO)
    client_id = chiedi("ID client OAuth")
    client_secret = chiedi("Segreto client OAuth")

    verificatore = secrets.token_urlsafe(64)
    sfida = base64.urlsafe_b64encode(hashlib.sha256(verificatore.encode()).digest()).rstrip(b"=").decode()
    controllo = secrets.token_urlsafe(16)
    ricevuto = {}

    class Gestore(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            ricevuto.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>Fatto: puoi chiudere questa scheda e tornare al terminale.</p>".encode("utf-8"))

        def log_message(self, *a):
            pass   # niente log: l'URL contiene il codice di autorizzazione

    server = http.server.HTTPServer(("127.0.0.1", 0), Gestore)
    redirect = f"http://127.0.0.1:{server.server_port}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code", "scope": AMBITI,
        "access_type": "offline", "prompt": "consent select_account", "state": controllo,
        "code_challenge": sfida, "code_challenge_method": "S256"})
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()
    print("\nSi apre il browser. Scegli il canale Ctrl-Alt-Revenge (account brand), poi «Consenti».")
    print("Se Google avvisa «app non verificata»: Avanzate → vai al progetto (è il tuo).")
    webbrowser.open(url)
    t.join(timeout=600)
    server.server_close()

    if ricevuto.get("state") != controllo or "code" not in ricevuto:
        sys.exit(f"consenso non riuscito: {ricevuto.get('error', 'nessuna risposta entro 10 minuti')}")
    corpo = urllib.parse.urlencode({
        "code": ricevuto["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect, "grant_type": "authorization_code", "code_verifier": verificatore}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=corpo), timeout=30) as r:
            risposta = json.loads(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"scambio del codice fallito: HTTP {e.code} {e.read()[:200]!r}")
    refresh = risposta.get("refresh_token")
    if not refresh:
        sys.exit("Google non ha dato il refresh token: togli l'accesso all'app da myaccount.google.com/permissions e rilancia")

    rich = urllib.request.Request("https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
                                  headers={"Authorization": f"Bearer {risposta['access_token']}"})
    with urllib.request.urlopen(rich, timeout=30) as r:
        canali = json.loads(r.read()).get("items", [])
    if not canali:
        sys.exit("questo account non ha un canale YouTube: crea prima il canale del gioco e rilancia")
    nome = canali[0]["snippet"]["title"]
    if input(f"\nIl consenso viene dal canale «{nome}». È quello del gioco? [s/N] ").strip().lower() != "s":
        sys.exit("interrotto: nessun secret caricato. Rilancia e scegli il canale giusto.")

    for nome_secret, valore in (("YT_CLIENT_ID", client_id), ("YT_CLIENT_SECRET", client_secret),
                                ("YT_REFRESH_TOKEN", refresh)):
        r = subprocess.run(["gh", "secret", "set", nome_secret, "--repo", repo], input=valore, text=True,
                           capture_output=True)
        if r.returncode != 0:
            sys.exit(f"{nome_secret} non caricato: {r.stderr.strip()[:200]}")
        print(f"[ok] {nome_secret} caricato in {repo}")
    print("\nFatto. Ricorda: ID client e segreto client vanno anche in Vaultwarden (cartella «Claude - infrastruttura»).")


if __name__ == "__main__":
    main()
