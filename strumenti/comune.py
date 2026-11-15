# -*- coding: utf-8 -*-
"""Pezzi comuni ai pubblicatori, alla sentinella e ai controlli.

Solo libreria standard (più PyYAML), così gli script girano uguali sul
runner di GitHub e sul PC, senza installare niente.

Le regole che vengono da Elettrofoni, e perché:
- l'idempotenza vive in stato.json, non nell'API: l'API a volte non mostra
  un contenuto pubblicato trenta secondi prima;
- lo stato si salva (commit e push) SUBITO dopo una pubblicazione, prima di
  ogni altro passo: se la run muore dopo, la successiva non ripubblica;
- su un errore dell'API ci si ferma e si apre una issue: niente retry in loop;
- i log sono pubblici: un token non si stampa mai.
"""
import datetime as dt
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import zoneinfo

RADICE = pathlib.Path(__file__).resolve().parent.parent
FILE_STATO = RADICE / "stato.json"
ROMA = zoneinfo.ZoneInfo("Europe/Rome")

REPO = os.environ.get("GITHUB_REPOSITORY", "luigismith/ctrl-alt-revenge")
PROPRIETARIO, NOME_REPO = REPO.split("/")
URL_SITO = f"https://{PROPRIETARIO}.github.io/{NOME_REPO}/"
UA = "ctrl-alt-revenge-bot/1.0 (+https://github.com/%s)" % REPO


def adesso():
    return dt.datetime.now(dt.timezone.utc)


def oggi_roma():
    return dt.datetime.now(ROMA).date()


# ------------------------------------------------------------------ HTTP ---

class ErroreHTTP(RuntimeError):
    def __init__(self, metodo, url, codice, corpo):
        # L'URL si stampa senza parametri: lì dentro può esserci un token.
        pulito = url.split("?")[0]
        super().__init__(f"{metodo} {pulito} → HTTP {codice}: {corpo[:400]}")
        self.codice, self.corpo = codice, corpo


def http(metodo, url, params=None, dati=None, intestazioni=None, timeout=60):
    """Una chiamata HTTP. Restituisce (codice, testo, url_finale). Solleva
    ErroreHTTP sui codici >= 400. Nessun retry: chi chiama decide."""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    corpo = None
    intest = {"User-Agent": UA}
    intest.update(intestazioni or {})
    if dati is not None:
        if isinstance(dati, (dict, list)) and intest.get("Content-Type") == "application/json":
            corpo = json.dumps(dati).encode("utf-8")
        elif isinstance(dati, dict):
            corpo = urllib.parse.urlencode(dati).encode("utf-8")
            intest.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            corpo = dati
    rich = urllib.request.Request(url, data=corpo, method=metodo, headers=intest)
    try:
        with urllib.request.urlopen(rich, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), r.geturl()
    except urllib.error.HTTPError as e:
        raise ErroreHTTP(metodo, url, e.code, e.read().decode("utf-8", "replace")) from None


def online(url, tipi=("image/", "video/", "text/html"), attesa_max=240):
    """Il file è servito davvero? Pages impiega un minuto a distribuire:
    è un'attesa di cortesia, non un retry su errore."""
    fine = time.time() + attesa_max
    while True:
        try:
            rich = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
            with urllib.request.urlopen(rich, timeout=20) as r:
                if r.status == 200 and r.headers.get("content-type", "").startswith(tipi):
                    return True
        except Exception:
            pass
        if time.time() > fine:
            return False
        time.sleep(10)


# ---------------------------------------------------------------- GitHub ---

def _gh(metodo, percorso, dati=None):
    tok = os.environ.get("GITHUB_TOKEN")
    if not tok:
        raise RuntimeError("GITHUB_TOKEN assente")
    _, testo, _ = http(metodo, f"https://api.github.com/repos/{REPO}/{percorso}", dati=dati,
                       intestazioni={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                                     "Content-Type": "application/json"})
    return json.loads(testo) if testo else {}


def gh_disponibile():
    return bool(os.environ.get("GITHUB_TOKEN"))


def issue_aperta_con_titolo(titolo):
    for i in _gh("GET", "issues?state=open&per_page=100"):
        if i.get("title") == titolo and "pull_request" not in i:
            return i
    return None


def apri_issue(titolo, corpo, etichette=("pubblicazione",)):
    """Una issue per problema: se ce n'è già una aperta con lo stesso
    titolo, non se ne apre un'altra (la notifica è già arrivata)."""
    if not gh_disponibile():
        print(f"[issue, solo log] {titolo}\n{corpo}")
        return None
    gia = issue_aperta_con_titolo(titolo)
    if gia:
        print(f"[issue] già aperta: #{gia['number']} {titolo}")
        return gia["number"]
    i = _gh("POST", "issues", {"title": titolo, "body": corpo, "labels": list(etichette)})
    print(f"[issue] aperta #{i['number']}: {titolo}")
    return i["number"]


def leggi_issue(numero):
    return _gh("GET", f"issues/{numero}")


def commenta_issue(numero, testo):
    return _gh("POST", f"issues/{numero}/comments", {"body": testo})


def chiudi_issue(numero, testo=None):
    if testo:
        commenta_issue(numero, testo)
    return _gh("PATCH", f"issues/{numero}", {"state": "closed", "state_reason": "completed"})


# ----------------------------------------------------------------- stato ---

def leggi_stato():
    if FILE_STATO.exists():
        return json.loads(FILE_STATO.read_text(encoding="utf-8"))
    return {"uscite": [], "ultimo_errore": None}


def scrivi_stato(stato, messaggio, altri_file=(), spingi=True):
    """Scrive stato.json e, sul runner, lo committa e lo spinge subito.
    Un salvataggio che può perdere la corsa con un altro commit non è un
    salvataggio: ci si riallinea e si riprova (Elettrofoni, 07/10/2026)."""
    FILE_STATO.write_text(json.dumps(stato, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if not spingi or not os.environ.get("GITHUB_ACTIONS"):
        print(f"[stato] scritto in locale: {messaggio}")
        return
    file = [str(FILE_STATO)] + [str(f) for f in altri_file if pathlib.Path(f).exists()]
    subprocess.run(["git", "add", *file], check=True, cwd=RADICE)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=RADICE).returncode == 0:
        return
    subprocess.run(["git", "commit", "-m", messaggio], check=True, cwd=RADICE)
    for tentativo in range(1, 9):
        if subprocess.run(["git", "push"], cwd=RADICE).returncode == 0:
            return
        print(f"[warn] push dello stato respinto, mi riallineo ({tentativo}/8)")
        subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=RADICE)
        time.sleep(3 * tentativo)
    raise RuntimeError("push dello stato fallito dopo 8 tentativi")


def uscite_di(stato, rete):
    return [u for u in stato.get("uscite", []) if u.get("rete") == rete]


def gia_uscito(stato, rete, id_contenuto):
    return any(u["id"] == id_contenuto for u in uscite_di(stato, rete))
