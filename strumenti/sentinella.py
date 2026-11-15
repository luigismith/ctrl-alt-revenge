# -*- coding: utf-8 -*-
"""La sentinella: ogni sera controlla che il sistema stia vivendo da solo.

È uno script, non una routine Claude (costa zero token). Apre una issue per
problema, e non la ripete se è già aperta (le issue arrivano per email a
Luigi e la regia le vede con `gh issue list`):

- un'uscita prevista nell'ultima giornata chiusa non c'è;
- un reel è uscito su Instagram ma lo Short no;
- la coda copre meno di 14 giorni (al massimo una issue a settimana);
- il token di Instagram scade entro 10 giorni, non si legge o non risponde;
- il refresh token di YouTube non risponde (usarlo una volta a settimana lo
  tiene vivo: muore dopo sei mesi senza uso);
- il sito non risponde con 200.

Ogni controllo parte solo quando la sua parte è accesa: prima del primo post
(niente in stato.json, niente «pronto»), senza secret o con Pages spento, la
sentinella tace. Così non serve un interruttore in più.

Le issue sul token, su YouTube, sul sito e sulla coda si chiudono da sole
quando il problema sparisce. Quelle sulle uscite mancate no: un post saltato
resta saltato, e la issue la chiude chi l'ha guardato.

Prova con date finte: `python -I prove/prova_sentinella.py`.
"""
import datetime as dt
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from comune import (ROMA, URL_SITO, _gh, apri_issue, chiudi_issue, gh_disponibile, http,
                    leggi_stato, oggi_roma, uscite_di)

GIORNI_IG = (1, 4, 6)          # martedì, venerdì, domenica (come pubblica-ig.yml)
COPERTURA_GIORNI = 14
TOKEN_IG_VITA = 60             # giorni di vita di un token lungo di Instagram
TOKEN_IG_PREAVVISO = 10
ETICHETTA = "sentinella"
GIORNI = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")

# Prefissi dei titoli: servono a ritrovare le issue da chiudere.
T_USCITA = "Sentinella: uscita mancata"
T_SHORT = "Sentinella: Short mancato"
T_CODA = "Sentinella: la coda copre meno di 14 giorni"
T_TOKEN_IG = "Sentinella: il token di Instagram"
T_TOKEN_YT = "Sentinella: il token di YouTube non risponde"
T_SITO = "Sentinella: il sito non risponde"
SI_CHIUDONO_DA_SOLE = (T_CODA, T_TOKEN_IG, T_TOKEN_YT, T_SITO)


def giorno_roma(iso):
    return dt.datetime.fromisoformat(iso).astimezone(ROMA).date()


def acceso(contenuti, stato):
    """La pubblicazione è partita? Prima del primo «pronto» non c'è niente da sorvegliare."""
    return bool(stato.get("uscite")) or any(c.get("stato") == "pronto" for c in contenuti)


# ------------------------------------------------- controlli (senza rete) ---

def controlla_uscite(oggi, contenuti, stato, fermato):
    """Ieri era un giorno di uscita, c'era qualcosa di pronto con la data
    arrivata, e su Instagram non è uscito niente. `fermato(c)` dice se Luigi
    ha messo il veto (issue chiusa da lui): quello non è un'uscita mancata."""
    ieri = oggi - dt.timedelta(days=1)
    if ieri.weekday() not in GIORNI_IG:
        return []
    usciti = {u["id"] for u in uscite_di(stato, "instagram")}
    in_ritardo = [c for c in contenuti
                  if c.get("stato") == "pronto" and c["id"] not in usciti
                  and _data(c) <= ieri and not fermato(c)]
    uscito_ieri = any(giorno_roma(u["quando"]) == ieri for u in uscite_di(stato, "instagram"))
    if not in_ritardo or uscito_ieri:
        return []
    elenco = "\n".join(f"- `{c['id']}` (previsto il {_data(c):%d/%m})" for c in in_ritardo)
    return [(f"{T_USCITA} il {ieri:%d/%m/%Y}",
             f"Ieri ({GIORNI[ieri.weekday()]} {ieri:%d/%m}) era un giorno di uscita su Instagram e non è uscito niente.\n\n"
             f"In coda, con la data arrivata:\n{elenco}\n\n"
             "Da guardare: le run di «Pubblica su Instagram» di ieri (sono partite? cosa dice il log?) "
             "e le issue con l'etichetta «pubblicazione». Questa issue non si chiude da sola.")]


def controlla_short(adesso_utc, contenuti, stato, fermato):
    """Un reel uscito su Instagram da più di un giorno, e su YouTube niente."""
    su_yt = {u["id"] for u in uscite_di(stato, "youtube")}
    problemi = []
    for u in uscite_di(stato, "instagram"):
        if u.get("tipo") != "reel" or u["id"] in su_yt:
            continue
        c = next((x for x in contenuti if x["id"] == u["id"]), None)
        if c is not None and fermato(c):
            continue
        if adesso_utc - dt.datetime.fromisoformat(u["quando"]) > dt.timedelta(hours=26):
            problemi.append((f"{T_SHORT}: {u['id']}",
                             f"Il reel `{u['id']}` è uscito su Instagram il {giorno_roma(u['quando']):%d/%m}, "
                             "ma su YouTube lo Short non c'è.\n\n"
                             "Da guardare: le run di «Pubblica su YouTube» e i secret `YT_*`. "
                             "Questa issue non si chiude da sola."))
    return problemi


def controlla_coda(oggi, contenuti, stato, fermato):
    """La coda deve coprire 14 giorni. Una issue a settimana al massimo: il
    numero della settimana sta nel titolo."""
    usciti = {u["id"] for u in uscite_di(stato, "instagram")}
    futuri = [c for c in contenuti
              if c.get("stato") == "pronto" and c["id"] not in usciti and not fermato(c)]
    ultima = max((_data(c) for c in futuri), default=None)
    if ultima is not None and ultima >= oggi + dt.timedelta(days=COPERTURA_GIORNI):
        return []
    anno, sett, _ = oggi.isocalendar()
    copre = (f"fino al {ultima:%d/%m}" if ultima and ultima >= oggi else "nessun giorno")
    return [(f"{T_CODA} (settimana {sett}/{anno})",
             f"In coda, pronti e non ancora usciti: {len(futuri)} contenuti; la coda copre {copre}.\n\n"
             "Per la regia: servono materiali nuovi in `inbox/`, con la loro `nota.md`. "
             "La routine del lunedì li mette in coda. Questa issue si chiude da sola quando la coda torna a 14 giorni.")]


def controlla_token_ig(eta):
    """`eta`: giorni del token, o None se il token c'è ma non si legge."""
    if eta is None:
        return [(f"{T_TOKEN_IG} non si legge",
                 "`token.enc` c'è, ma con `STATE_KEY` non si decifra. "
                 "Forse il secret è cambiato: va rimesso il token con `IG_ACCESS_TOKEN` (vedi la pagina dell'accensione).")]
    restano = TOKEN_IG_VITA - eta
    if restano > TOKEN_IG_PREAVVISO:
        return []
    return [(f"{T_TOKEN_IG} scade fra {max(restano, 0)} giorni",
             f"Il token ha {eta} giorni; ne vive {TOKEN_IG_VITA}. Il rinnovo automatico (pubblicazione e "
             "«Rinnova token Instagram» della domenica) non ha funzionato.\n\n"
             "Da fare: lanciare a mano «Rinnova token Instagram» e guardarne il log. Se è già scaduto, "
             "Luigi genera un token nuovo dall'app Meta e lo rimette con `gh secret set IG_ACCESS_TOKEN`, "
             "poi si cancella `token.enc`.")]


# ------------------------------------------------- controlli (con la rete) ---

def _data(c):
    u = c.get("uscita")
    return u if isinstance(u, dt.date) else dt.date.fromisoformat(str(u))


def eta_token_ig():
    """(acceso, età). Acceso solo se c'è la chiave e c'è il token cifrato."""
    from token_ig import FILE_TOKEN, eta_giorni
    if not os.environ.get("STATE_KEY") or not FILE_TOKEN.exists():
        return False, None
    return True, eta_giorni()


def prova_token_ig():
    """Il token risponde davvero? Una lettura di /me, senza pubblicare niente
    e senza rinnovare (il rinnovo lo fa chi può salvare token.enc).
    Restituisce (problemi, nome_account)."""
    from token_ig import GRAPH, _leggi
    try:
        token = _leggi(os.environ["STATE_KEY"])["token"]
        # ErroreHTTP stampa l'URL senza parametri: il token non finisce nel log
        _, testo, _ = http("GET", f"{GRAPH}/me", params={"fields": "user_id,username", "access_token": token},
                           timeout=30)
        import json
        return [], json.loads(testo).get("username", "?")
    except Exception as e:
        return [(f"{T_TOKEN_IG} non risponde",
                 f"{str(e)[:300]}\n\nSe il token è stato revocato (password cambiata, app tolta da Instagram), "
                 "Luigi ne genera uno nuovo dall'app Meta, lo rimette con `gh secret set IG_ACCESS_TOKEN` "
                 "e si cancella `token.enc` (vedi ACCENSIONE.md).")], None


def prova_token_yt():
    """[] se il refresh token risponde; i problemi altrimenti. None se spento."""
    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        return None
    from pubblica_yt import access_token
    try:
        access_token()          # il token di accesso non si stampa né si salva
        return []
    except Exception as e:
        return [(T_TOKEN_YT,
                 f"{e}\n\nSe dice `invalid_grant`, il refresh token è morto (revocato, oppure la schermata di "
                 "consenso è tornata in «Testing», oppure sei mesi senza uso). Luigi rilancia "
                 "`strumenti/ottieni_token_youtube.py` e rimette `YT_REFRESH_TOKEN`.")]


def prova_sito():
    """None se Pages è spento (variabile PAGES_ATTIVE diversa da «si»)."""
    if os.environ.get("PAGES_ATTIVE") != "si":
        return None
    rotti = []
    for url in (URL_SITO, URL_SITO + "en/"):
        try:
            codice, testo, _ = http("GET", url, timeout=30)
            if codice != 200 or "Ctrl-Alt-Revenge" not in testo:
                rotti.append(f"- {url}: HTTP {codice}, ma la pagina non è la nostra")
        except Exception as e:
            rotti.append(f"- {url}: {str(e)[:200]}")
    if not rotti:
        return []
    return [(T_SITO, "Pagine che non rispondono come dovrebbero:\n" + "\n".join(rotti)
             + "\n\nDa guardare: le run di «Sito» e Settings → Pages.")]


def veto_di(c):
    """True se Luigi ha chiuso la issue di veto (il contenuto è fermato)."""
    if not c.get("issue") or not gh_disponibile():
        return False
    from comune import leggi_issue
    from coda import BOT
    i = leggi_issue(c["issue"])
    return i.get("state") == "closed" and (i.get("closed_by") or {}).get("login") != BOT


# ------------------------------------------------------------------- main ---

def chiudi_risolte(prefissi_controllati, titoli_aperti_ora):
    """Chiude le issue della sentinella sparite, ma solo per i controlli che
    stasera sono girati davvero (un controllo spento non risolve niente)."""
    if not gh_disponibile():
        return
    for i in _gh("GET", f"issues?state=open&labels={ETICHETTA}&per_page=100"):
        t = i.get("title", "")
        if t in titoli_aperti_ora or "pull_request" in i:
            continue
        if any(t.startswith(p) for p in prefissi_controllati if p in SI_CHIUDONO_DA_SOLE):
            chiudi_issue(i["number"], "Risolto: stasera la sentinella non ha trovato più il problema.")
            print(f"[sentinella] chiusa #{i['number']}: {t}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # la console di Windows è cp1252
    import coda
    contenuti = coda.tutti()
    stato = leggi_stato()
    oggi = oggi_roma()
    problemi, controllati = [], []

    if acceso(contenuti, stato):
        cache = {}

        def fermato(c):
            if c["id"] not in cache:
                cache[c["id"]] = veto_di(c)
            return cache[c["id"]]

        adesso_utc = dt.datetime.now(dt.timezone.utc)
        problemi += controlla_uscite(oggi, contenuti, stato, fermato)
        problemi += controlla_short(adesso_utc, contenuti, stato, fermato)
        problemi += controlla_coda(oggi, contenuti, stato, fermato)
        controllati += [T_USCITA, T_SHORT, T_CODA]
    else:
        print("[sentinella] la pubblicazione non è ancora partita: coda e uscite non si controllano")

    acceso_ig, eta = eta_token_ig()
    if acceso_ig:
        problemi += controlla_token_ig(eta)
        controllati.append(T_TOKEN_IG)
        print(f"[sentinella] token Instagram: {'illeggibile' if eta is None else f'{eta} giorni'}")
        if eta is not None:
            vivo, account = prova_token_ig()
            problemi += vivo
            print(f"[sentinella] token Instagram: {'risponde, account @' + account if not vivo else 'NON risponde'}")
    else:
        print("[sentinella] token Instagram: non ancora impostato")

    yt = prova_token_yt()
    if yt is None:
        print("[sentinella] YouTube: secret non ancora impostati")
    else:
        problemi += yt
        controllati.append(T_TOKEN_YT)
        print(f"[sentinella] YouTube: {'il refresh token risponde' if not yt else 'NON risponde'}")

    sito = prova_sito()
    if sito is None:
        print("[sentinella] sito: Pages spento (PAGES_ATTIVE ≠ si)")
    else:
        problemi += sito
        controllati.append(T_SITO)
        print(f"[sentinella] sito: {'risponde' if not sito else 'NON risponde'}")

    for titolo, corpo in problemi:
        apri_issue(titolo, corpo + "\n\n_— la sentinella, ogni sera alle 23:25_", etichette=(ETICHETTA,))
    chiudi_risolte(controllati, {t for t, _ in problemi})
    print(f"[sentinella] {len(problemi)} problemi" if problemi else "[sentinella] tutto in ordine")


if __name__ == "__main__":
    main()
