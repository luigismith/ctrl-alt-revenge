# -*- coding: utf-8 -*-
"""Pubblica su Instagram la prossima uscita della coda: carosello, immagine
o reel, più la storia. Lo lancia .github/workflows/pubblica-ig.yml, dopo aver
generato i file e averli messi online con Pages (l'API di Instagram scarica
da un indirizzo pubblico, non accetta file).

Uso:
  python strumenti/pubblica_ig.py                      # pubblica davvero (Actions)
  python strumenti/pubblica_ig.py --prova              # tutto tranne le chiamate a Instagram
  python strumenti/pubblica_ig.py --prova --file prove/prova-carosello.yml --media <cartella> --locale

Le guardie (da Elettrofoni, ognuna nata da un errore vero):
- si pubblica solo fra le 17 e le 22 italiane (un cron in ritardo di ore
  pubblicherebbe di notte: meglio perdere la giornata che bruciare il post);
- al massimo un'uscita nel feed al giorno e almeno 20 ore fra due uscite;
- il contenuto deve avere la sua issue di veto aperta da 48 ore;
- su un errore dell'API ci si ferma e si apre una issue: niente retry in loop
  (il budget video dell'account si consuma anche con i tentativi falliti);
- lo stato si salva subito dopo la pubblicazione, prima di ogni altro passo;
- la verifica è vera: il post deve comparire fra quelli dell'account e il suo
  permalink deve aprirsi.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import coda  # noqa: E402
from comune import (RADICE, ROMA, URL_SITO, ErroreHTTP, adesso, apri_issue, chiudi_issue,  # noqa: E402
                    gh_disponibile, http, leggi_stato, online, scrivi_stato, uscite_di)

FINESTRA_ORE = (17, 22)
MAX_AL_GIORNO = 1
DISTANZA_MINIMA_ORE = 20
PRONTO_FRA_UN_ATTIMO = "2207027"   # «media not ready»: il contenitore è pronto, la pubblicazione non ancora


def dentro_la_finestra():
    # Non si deduce l'intenzione dal canale (Elettrofoni, 30/08/2026): anche
    # cron-job.org genera un workflow_dispatch. Scavalca solo chi lo dice.
    return os.environ.get("FORZA_ORARIO") == "1" or FINESTRA_ORE[0] <= dt.datetime.now(ROMA).hour < FINESTRA_ORE[1]


def componi_didascalia(c):
    testo = str(c["didascalia"]).strip()
    tag = " ".join("#" + h for h in c.get("hashtag") or [])
    return f"{testo}\n\n{tag}" if tag else testo


class Instagram:
    """Le chiamate all'API. In prova non parte niente: si scrive cosa partirebbe."""

    def __init__(self, prova):
        self.prova = prova
        self.token = None
        self.contatore = 0

    def accendi(self):
        if self.prova:
            print("[prova] nessun token letto: in prova Instagram non si chiama")
            return "ID_ACCOUNT_DI_PROVA"
        import token_ig
        self.token, _ = token_ig.token_corrente()
        me = self.get("me", fields="user_id,username")
        print(f"[api] account @{me.get('username')}, token {token_ig.redigi(self.token)}")
        return me.get("user_id") or me.get("id")

    def get(self, percorso, **params):
        from token_ig import GRAPH
        params["access_token"] = self.token
        _, testo, _ = http("GET", f"{GRAPH}/{percorso}", params=params)
        return json.loads(testo)

    def post(self, percorso, **dati):
        from token_ig import GRAPH
        if self.prova:
            self.contatore += 1
            visibili = {k: (v if len(str(v)) < 90 else str(v)[:87] + "...") for k, v in dati.items()}
            print(f"[prova] POST /{percorso} {json.dumps(visibili, ensure_ascii=False)}")
            return {"id": f"CONTENITORE_{self.contatore}"}
        dati["access_token"] = self.token        # nel corpo, mai nell'URL
        _, testo, _ = http("POST", f"{GRAPH}/{percorso}", dati=dati)
        return json.loads(testo)

    def attendi(self, cid, video=False):
        """Il contenitore deve arrivare a FINISHED. Non è un retry: è il suo
        ciclo di vita. Meta consiglia un controllo al minuto per 5 minuti;
        le immagini sono pronte in pochi secondi, quindi si guarda più spesso."""
        if self.prova:
            return
        passo, fine = (15, time.time() + 300) if video else (5, time.time() + 120)
        while time.time() < fine:
            st = self.get(cid, fields="status_code,status").get("status_code")
            if st == "FINISHED":
                return
            if st in ("ERROR", "EXPIRED"):
                raise RuntimeError(f"contenitore {cid} in {st}")
            time.sleep(passo)
        raise RuntimeError(f"contenitore {cid} mai arrivato a FINISHED")

    def pubblica(self, ig_user, cid):
        """media_publish, con la sola eccezione del «non ancora pronto»
        (Elettrofoni, 01/10/2026): tre attese crescenti, poi si ferma."""
        for attesa in (8, 20, 45, None):
            try:
                return self.post(f"{ig_user}/media_publish", creation_id=cid)
            except ErroreHTTP as e:
                if PRONTO_FRA_UN_ATTIMO not in e.corpo or attesa is None:
                    raise
                print(f"[attesa] il media non è ancora pubblicabile: aspetto {attesa} s")
                time.sleep(attesa)


def url_media(c, nome):
    return f"{URL_SITO}social/{c['id']}/{nome}"


def file_attesi(c):
    if c["tipo"] == "reel":
        return ["reel.mp4", "copertina.jpg"]
    return [f"{n:02d}.jpg" for n in range(1, len(c["tavole"]) + 1)] + ["storia.jpg"]


def crea_e_pubblica(ig, ig_user, c):
    ai = {"is_ai_generated": "true"} if c.get("ai") else {}
    didascalia = componi_didascalia(c)
    if c["tipo"] == "carosello":
        figli = []
        for n, tv in enumerate(c["tavole"], start=1):
            # alt_text sui figli; is_ai_generated solo sul carosello: sui figli dà errore
            f = ig.post(f"{ig_user}/media", image_url=url_media(c, f"{n:02d}.jpg"),
                        is_carousel_item="true", alt_text=str(tv["alt"])[:1000])
            ig.attendi(f["id"])
            figli.append(f["id"])
        cont = ig.post(f"{ig_user}/media", media_type="CAROUSEL", children=",".join(figli), caption=didascalia, **ai)
        ig.attendi(cont["id"])
    elif c["tipo"] == "immagine":
        cont = ig.post(f"{ig_user}/media", image_url=url_media(c, "01.jpg"), caption=didascalia,
                       alt_text=str(c["tavole"][0]["alt"])[:1000], **ai)
        ig.attendi(cont["id"])
    else:
        cont = ig.post(f"{ig_user}/media", media_type="REELS", video_url=url_media(c, "reel.mp4"),
                       cover_url=url_media(c, "copertina.jpg"), share_to_feed="true", caption=didascalia, **ai)
        ig.attendi(cont["id"], video=True)
    return ig.pubblica(ig_user, cont["id"])["id"]


def verifica(ig, media_id):
    """Il post esiste davvero? Deve stare fra gli ultimi dell'account, e il suo
    permalink deve aprirsi. Restituisce (permalink, nota sulla pagina)."""
    ultimi = ig.get("me/media", fields="id,permalink,timestamp", limit=5).get("data", [])
    voce = next((m for m in ultimi if m["id"] == media_id), None)
    if not voce:
        raise RuntimeError(f"media {media_id} assente dagli ultimi post dell'account: {[m['id'] for m in ultimi]}")
    permalink = voce["permalink"]
    codice = permalink.rstrip("/").rsplit("/", 1)[-1]
    try:
        stato_http, _, finale = http("GET", permalink, timeout=30)
        if codice not in finale:
            return permalink, f"la pagina rimanda altrove ({finale.split('?')[0]})"
        return permalink, f"pagina aperta (HTTP {stato_http})"
    except ErroreHTTP as e:
        if e.codice == 404:
            raise RuntimeError(f"il permalink {permalink} risponde 404")
        # Instagram a volte respinge i runner (429, 403): il post c'è (me/media),
        # la pagina non si è lasciata aprire. Lo si scrive, non si finge.
        return permalink, f"pagina non aperta dal runner (HTTP {e.codice})"


def storia(ig, ig_user, c):
    """Facoltativa per scelta: il post è la missione, la storia il megafono.
    Un solo tentativo, nessuna issue se fallisce."""
    try:
        if c["tipo"] == "reel":
            s = ig.post(f"{ig_user}/media", media_type="STORIES", video_url=url_media(c, "reel.mp4"))
            ig.attendi(s["id"], video=True)
        else:
            s = ig.post(f"{ig_user}/media", media_type="STORIES", image_url=url_media(c, "storia.jpg"))
            ig.attendi(s["id"])
        ig.pubblica(ig_user, s["id"])
        print("[prova] storia: qui uscirebbe" if ig.prova else "[ok] storia pubblicata")
    except Exception as e:
        print(f"[warn] storia non pubblicata (non blocca il post): {e}")


def errore(titolo, corpo, prova):
    if prova:
        print(f"[prova] qui si aprirebbe la issue «{titolo}»: {corpo}")
    else:
        stato = leggi_stato()
        stato["ultimo_errore"] = {"quando": adesso().isoformat(), "titolo": titolo}
        try:
            scrivi_stato(stato, f"stato: errore, {titolo}")
        except Exception as e:
            print(f"[warn] stato dell'errore non salvato: {e}")
        apri_issue(f"🔴 Instagram: {titolo}", corpo)
    sys.exit(1)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--prova", action="store_true", help="tutto tranne le chiamate che pubblicano")
    a.add_argument("--file", help="un contenuto preciso (per la prova)")
    a.add_argument("--media", help="cartella con i file generati (per la prova; di norma docs/social/<id>)")
    a.add_argument("--locale", action="store_true", help="non controllare gli indirizzi pubblici (PC senza Pages)")
    arg = a.parse_args()
    prova = arg.prova
    if prova:
        print("=" * 70 + "\n PROVA A SECCO: nessuna chiamata a Instagram, nessuno stato salvato\n" + "=" * 70)

    stato = leggi_stato()
    feed = uscite_di(stato, "instagram")

    if not dentro_la_finestra():
        msg = f"sono le {dt.datetime.now(ROMA):%H:%M} italiane, fuori dalla finestra {FINESTRA_ORE[0]}-{FINESTRA_ORE[1]}"
        if not prova:
            print(f"[stop] {msg}: il contenuto resta in coda."); return
        print(f"[prova] {msg}: per davvero qui si fermerebbe")
    oggi = dt.datetime.now(ROMA).date()
    di_oggi = [u for u in feed if dt.datetime.fromisoformat(u["quando"]).astimezone(ROMA).date() == oggi]
    if len(di_oggi) >= MAX_AL_GIORNO and not prova:
        print("[stop] oggi è già uscito un post: niente da fare."); return
    if feed and not prova:
        ultimo = dt.datetime.fromisoformat(feed[-1]["quando"])
        if adesso() - ultimo < dt.timedelta(hours=DISTANZA_MINIMA_ORE):
            print(f"[stop] l'ultimo post ha meno di {DISTANZA_MINIMA_ORE} ore: niente da fare."); return

    if arg.file:
        c = coda.leggi(arg.file)
    else:
        c = coda.prossimo(coda.tutti(), {u["id"] for u in feed}, coda.TIPI)
        if c is None:
            # Mai riempitivi: la coda vuota non è un errore qui, la sentinella la segnala.
            print("[ok] niente in coda per oggi."); return
    print(f"[coda] {c['id']} ({c['tipo']}), uscita prevista {coda.data_uscita(c)}")

    errori = coda.valida(c, coda.parole_vietate())
    if errori:
        errore(f"il contenuto {c['id']} non passa i controlli", "\n".join(f"- {x}" for x in errori), prova)
    print("[ok] controlli superati (lunghezze, file, spoiler)")

    via, motivo = coda.veto(c) if not arg.file else (True, "contenuto di prova: veto non applicato")
    print(f"[veto] {motivo}")
    if not via:
        return

    cartella = pathlib.Path(arg.media) if arg.media else RADICE / "docs" / "social" / str(c["id"])
    mancano = [f for f in file_attesi(c) if not (cartella / f).is_file()]
    if mancano:
        errore(f"mancano i file di {c['id']}", f"in {cartella}: {', '.join(mancano)}. Lanciare genera_media.py.", prova)
    for f in file_attesi(c):
        print(f"[file] {f}: {(cartella / f).stat().st_size // 1024} KB")

    if arg.locale:
        print("[prova] indirizzi pubblici non controllati (--locale)")
    else:
        for f in file_attesi(c):
            u = url_media(c, f)
            if not online(u, attesa_max=30 if prova else 240):
                errore(f"file non online: {f}", f"{u} non risponde con un'immagine o un video. Pages è acceso e aggiornato?", prova)
            print(f"[pages] online: {u}")

    ig = Instagram(prova)
    ig_user = ig.accendi()
    try:
        media_id = crea_e_pubblica(ig, ig_user, c)
    except Exception as e:
        errore(f"pubblicazione fallita per {c['id']}", str(e), prova)

    if prova:
        print(f"[prova] qui si salverebbe subito lo stato: uscita {c['id']} su instagram")
        print("[prova] qui si verificherebbe il post: fra gli ultimi dell'account, poi il permalink aperto")
        storia(ig, ig_user, c)
        print("[prova] qui si chiuderebbe la issue di veto con il permalink e si rigenererebbe il sito")
        print("=" * 70 + "\n PROVA A SECCO FINITA: tutto in ordine fino alla chiamata che pubblica\n" + "=" * 70)
        return

    # >>> PRIMA DI QUALUNQUE ALTRA COSA: lo stato, salvato e spinto. <<<
    from token_ig import FILE_TOKEN
    anteprima = f"social/{c['id']}/" + ("copertina.jpg" if c["tipo"] == "reel" else "01.jpg")
    stato = leggi_stato()
    stato.setdefault("uscite", []).append({
        "id": c["id"], "rete": "instagram", "tipo": c["tipo"], "media_id": media_id,
        "quando": adesso().isoformat(), "verificato": False, "anteprima": anteprima,
        "titolo": str(c["tavole"][0].get("testo", "")) if c.get("tavole") else str((c.get("youtube") or {}).get("titolo", "")),
    })
    stato["ultimo_errore"] = None
    scrivi_stato(stato, f"stato: uscito {c['id']} su Instagram ({media_id})", altri_file=[FILE_TOKEN])
    print(f"[ok] pubblicato {c['id']} → media {media_id}")

    try:
        permalink, nota = verifica(ig, media_id)
    except Exception as e:
        errore(f"verifica dopo la pubblicazione fallita per {c['id']}", f"Il media {media_id} risulta creato. {e}", prova)
    stato = leggi_stato()
    voce = next(u for u in stato["uscite"] if u["id"] == c["id"] and u["rete"] == "instagram")
    voce.update(permalink=permalink, verificato=True, pagina=nota)
    scrivi_stato(stato, f"stato: verificato {c['id']}")
    print(f"[ok] verificato: {permalink} ({nota})")

    storia(ig, ig_user, c)

    if c.get("issue") and gh_disponibile():
        try:
            chiudi_issue(c["issue"], f"Uscito su Instagram: {permalink}")
        except Exception as e:
            print(f"[warn] issue di veto non chiusa: {e}")
    try:
        import genera_sito
        genera_sito.genera()
    except Exception as e:
        print(f"[warn] sito non rigenerato (lo rifà il prossimo giro): {e}")


if __name__ == "__main__":
    main()
