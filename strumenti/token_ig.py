# -*- coding: utf-8 -*-
"""Il token di Instagram, dal modello di Elettrofoni (token_ig.py).

- Luigi lo incolla una volta nel secret IG_ACCESS_TOKEN;
- da lì vive CIFRATO in token.enc (AES-256-GCM, chiave dal secret STATE_KEY)
  e si rinnova da solo dopo 25 giorni (dura 60 giorni, si rinnova da quando
  ne ha uno);
- non si stampa mai: nei log c'è solo redigi().
Un rinnovo va salvato nello stesso commit dello stato, altrimenti si perde
(Elettrofoni, 21/09/2026): per questo scrivi_stato() aggiunge token.enc.
"""
import base64
import datetime as dt
import json
import os

from comune import RADICE, http

FILE_TOKEN = RADICE / "token.enc"
GRAPH = "https://graph.instagram.com/v27.0"
GRAPH_SENZA_VERSIONE = "https://graph.instagram.com"
GIORNI_PRIMA_DEL_RINNOVO = 25


def redigi(token):
    return f"<token redatto, {len(token)} caratteri>"


def _aes():
    # importato qui: serve solo sul runner, il PC non ne ha bisogno
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    return AESGCM, PBKDF2HMAC, hashes


def _chiave(passphrase, salt):
    _, PBKDF2HMAC, hashes = _aes()
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000).derive(passphrase.encode())


def _salva(token, passphrase):
    AESGCM, _, _ = _aes()
    salt, nonce = os.urandom(16), os.urandom(12)
    ora = dt.datetime.now(dt.timezone.utc).isoformat()
    ct = AESGCM(_chiave(passphrase, salt)).encrypt(nonce, json.dumps({"token": token, "emesso_il": ora}).encode(), None)
    FILE_TOKEN.write_text(json.dumps({"v": 1, "salt": base64.b64encode(salt).decode(),
                                      "nonce": base64.b64encode(nonce).decode(),
                                      "ct": base64.b64encode(ct).decode()}, indent=1), encoding="utf-8")


def _leggi(passphrase):
    AESGCM, _, _ = _aes()
    b = json.loads(FILE_TOKEN.read_text(encoding="utf-8"))
    dati = AESGCM(_chiave(passphrase, base64.b64decode(b["salt"]))).decrypt(
        base64.b64decode(b["nonce"]), base64.b64decode(b["ct"]), None)
    return json.loads(dati)


def eta_giorni():
    """Quanti giorni ha il token (per la sentinella). None se non si legge."""
    try:
        dati = _leggi(os.environ["STATE_KEY"])
        return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(dati["emesso_il"])).days
    except Exception:
        return None


def token_corrente():
    """(token, rinnovato). Bootstrap dal secret se token.enc manca."""
    passphrase = os.environ.get("STATE_KEY")
    if not passphrase:
        raise SystemExit("STATE_KEY mancante (secret di GitHub).")
    if not FILE_TOKEN.exists():
        seme = (os.environ.get("IG_ACCESS_TOKEN") or "").strip()
        if not seme:
            raise SystemExit("token.enc assente e IG_ACCESS_TOKEN mancante: serve il primo token.")
        _salva(seme, passphrase)
        print(f"[token] primo avvio da IG_ACCESS_TOKEN: {redigi(seme)} cifrato in token.enc")
    dati = _leggi(passphrase)
    eta = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(dati["emesso_il"])
    if eta < dt.timedelta(days=GIORNI_PRIMA_DEL_RINNOVO):
        return dati["token"], False
    print(f"[token] età {eta.days} giorni: rinnovo…")
    # Su errore ci si ferma: niente retry in loop. Il corpo della risposta
    # non contiene il token; l'URL con il token non si stampa (vedi ErroreHTTP).
    _, testo, _ = http("GET", f"{GRAPH_SENZA_VERSIONE}/refresh_access_token",
                       params={"grant_type": "ig_refresh_token", "access_token": dati["token"]}, timeout=30)
    nuovo = json.loads(testo)["access_token"]
    _salva(nuovo, passphrase)
    print(f"[token] rinnovato: {redigi(nuovo)}")
    return nuovo, True
