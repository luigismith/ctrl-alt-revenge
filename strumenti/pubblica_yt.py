# -*- coding: utf-8 -*-
"""Carica su YouTube come Short il reel della coda: lo stesso video, lo
stesso giorno, circa un'ora dopo Instagram. Lo lancia
.github/workflows/pubblica-yt.yml. YouTube riceve il file dal runner: qui
Pages non serve.

Uso:
  python strumenti/pubblica_yt.py                  # carica davvero (Actions)
  python strumenti/pubblica_yt.py --prova          # tutto tranne le chiamate a YouTube
  python strumenti/pubblica_yt.py --prova --file prove/prova-reel.yml --media <cartella>

Le guardie:
- solo fra le 17 e le 23 italiane, al massimo uno Short al giorno;
- dopo il reel su Instagram, ad almeno 55 minuti; se Instagram non è uscito,
  lo Short aspetta le 21 e poi esce lo stesso (un canale non deve fermare l'altro);
- la issue di veto: chiusa da Luigi ferma anche lo Short;
- si chiede «public», poi si rilegge lo stato del video: se YouTube lo ha
  lasciato privato ci si ferma con una issue, senza riprovare;
- lo stato si salva subito dopo il caricamento;
- la verifica è vera: oEmbed risponde solo per un video pubblico, poi si
  apre youtube.com/shorts/<id>.
I token non si stampano mai: né il refresh token né quello di accesso.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import coda  # noqa: E402
from comune import (RADICE, ROMA, UA, ErroreHTTP, adesso, apri_issue, chiudi_issue, commenta_issue,  # noqa: E402
                    gh_disponibile, http, leggi_issue, leggi_stato, scrivi_stato, uscite_di)

FINESTRA_ORE = (17, 23)
DOPO_INSTAGRAM_MIN = 55
SENZA_INSTAGRAM_DALLE = 21      # se il reel su Instagram non è uscito, lo Short va lo stesso da quest'ora
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://www.googleapis.com/youtube/v3"
UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"
CATEGORIA_GIOCHI = "20"
MAX_MB = 256                     # i nostri reel stanno sotto i 50 MB: oltre c'è un errore a monte


def access_token():
    """Dal refresh token un token di accesso. Lo usa anche la sentinella per
    sapere se il refresh token è ancora vivo. Mai stampato."""
    mancano = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if mancano:
        raise SystemExit(f"secret di YouTube mancanti: {', '.join(mancano)}")
    try:
        _, testo, _ = http("POST", TOKEN_URL, dati={
            "client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
            "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=30)
    except ErroreHTTP as e:
        # il corpo di un errore di token non contiene segreti («invalid_grant» e simili)
        raise RuntimeError(f"il refresh token di YouTube non funziona: HTTP {e.codice} {e.corpo[:200]}") from None
    return json.loads(testo)["access_token"]


def corpo_video(c):
    yt = c.get("youtube") or {}
    hashtag = " ".join(f"#{h}" for h in (c.get("hashtag") or []))
    descrizione = (str(yt.get("descrizione", "")).strip() + ("\n\n" + hashtag if hashtag else "")).strip()
    return {
        "snippet": {
            "title": str(yt["titolo"]).strip(),
            "description": descrizione,
            "tags": list(c.get("hashtag") or []),
            "categoryId": CATEGORIA_GIOCHI,
            "defaultLanguage": "it",
            "defaultAudioLanguage": "it",
        },
        "status": {
            "privacyStatus": "public",
            "embeddable": True,
            "selfDeclaredMadeForKids": False,
            # l'etichetta dei contenuti alterati o sintetici: la chiede YouTube per i video realistici fatti con l'AI
            "containsSyntheticMedia": bool(c.get("ai")),
        },
    }


def _richiesta(metodo, url, corpo, intestazioni, timeout):
    rich = urllib.request.Request(url, data=corpo, method=metodo, headers={"User-Agent": UA, **intestazioni})
    try:
        with urllib.request.urlopen(rich, timeout=timeout) as r:
            return r.status, r.headers, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise ErroreHTTP(metodo, url, e.code, e.read().decode("utf-8", "replace")) from None


def carica(token, video, corpo):
    """Caricamento «resumable» in due passi: si apre la sessione, poi si manda il file intero.
    Un errore ferma tutto: niente secondo tentativo (un doppione su YouTube non si annulla da qui)."""
    dati = video.read_bytes()
    _, intest, _ = _richiesta("POST", UPLOAD + "?uploadType=resumable&part=snippet,status",
                              json.dumps(corpo).encode("utf-8"),
                              {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                               "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(len(dati))}, 60)
    sessione = intest.get("Location")
    if not sessione:
        raise RuntimeError("YouTube non ha aperto la sessione di caricamento (manca Location)")
    _, _, testo = _richiesta("PUT", sessione, dati, {"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"}, 600)
    return json.loads(testo)


def leggi_video(token, video_id):
    _, testo, _ = http("GET", f"{API}/videos", params={"part": "status,processingDetails", "id": video_id},
                       intestazioni={"Authorization": f"Bearer {token}"}, timeout=30)
    voci = json.loads(testo).get("items", [])
    return voci[0] if voci else None


def verifica(video_id, attesa_max=900):
    """oEmbed risponde 200 solo per un video pubblico ed elaborato: si aspetta
    (attesa di cortesia, l'elaborazione dura qualche minuto), poi si apre lo Short."""
    permalink = f"https://www.youtube.com/shorts/{video_id}"
    fine = time.time() + attesa_max
    while True:
        try:
            _, testo, _ = http("GET", "https://www.youtube.com/oembed",
                               params={"url": permalink, "format": "json"}, timeout=30)
            titolo = json.loads(testo).get("title", "")
            break
        except ErroreHTTP as e:
            if time.time() > fine:
                raise RuntimeError(f"oEmbed non risponde dopo {attesa_max // 60} minuti (HTTP {e.codice}): "
                                   "il video non è pubblico o non è ancora elaborato")
            time.sleep(30)
    try:
        codice, pagina, finale = http("GET", permalink, timeout=30)
        nota = (f"oEmbed «{titolo}», Short aperto (HTTP {codice})" if video_id in finale or video_id in pagina
                else f"oEmbed «{titolo}», ma la pagina rimanda altrove ({finale.split('?')[0]})")
    except ErroreHTTP as e:
        nota = f"oEmbed «{titolo}», pagina dello Short non aperta dal runner (HTTP {e.codice})"
    return permalink, nota


def errore(titolo, corpo, prova):
    if prova:
        print(f"[prova] qui si aprirebbe la issue «{titolo}»: {corpo}")
    else:
        stato = leggi_stato()
        stato["ultimo_errore"] = {"quando": adesso().isoformat(), "titolo": f"YouTube: {titolo}"}
        try:
            scrivi_stato(stato, f"stato: errore YouTube, {titolo}")
        except Exception as e:
            print(f"[warn] stato dell'errore non salvato: {e}")
        apri_issue(f"🔴 YouTube: {titolo}", corpo)
    sys.exit(1)


def scegli(stato):
    """Il reel che tocca a YouTube oggi, oppure (None, motivo)."""
    su_yt = {u["id"] for u in uscite_di(stato, "youtube")}
    c = coda.prossimo(coda.tutti(), su_yt, {"reel"})
    if c is None:
        return None, "nessun reel in coda per oggi"
    ig = next((u for u in uscite_di(stato, "instagram") if u["id"] == c["id"]), None)
    ora = dt.datetime.now(ROMA)
    if ig:
        trascorsi = adesso() - dt.datetime.fromisoformat(ig["quando"])
        if trascorsi < dt.timedelta(minutes=DOPO_INSTAGRAM_MIN):
            return None, f"il reel è uscito su Instagram da {int(trascorsi.total_seconds() // 60)} minuti: lo Short aspetta"
    elif ora.hour < SENZA_INSTAGRAM_DALLE:
        return None, f"il reel non è ancora uscito su Instagram: lo Short aspetta (al più tardi dalle {SENZA_INSTAGRAM_DALLE})"
    return c, "ok"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--prova", action="store_true", help="tutto tranne le chiamate a YouTube")
    a.add_argument("--file", help="un contenuto preciso (per la prova)")
    a.add_argument("--media", help="cartella con reel.mp4 (per la prova; di norma docs/social/<id>)")
    arg = a.parse_args()
    prova = arg.prova
    if prova:
        print("=" * 70 + "\n PROVA A SECCO: nessuna chiamata a YouTube, nessuno stato salvato\n" + "=" * 70)

    stato = leggi_stato()
    ora = dt.datetime.now(ROMA)
    if not FINESTRA_ORE[0] <= ora.hour < FINESTRA_ORE[1]:
        msg = f"sono le {ora:%H:%M} italiane, fuori dalla finestra {FINESTRA_ORE[0]}-{FINESTRA_ORE[1]}"
        if not prova:
            print(f"[stop] {msg}: lo Short resta in coda."); return
        print(f"[prova] {msg}: per davvero qui si fermerebbe")
    if not prova and any(dt.datetime.fromisoformat(u["quando"]).astimezone(ROMA).date() == ora.date()
                         for u in uscite_di(stato, "youtube")):
        print("[stop] oggi è già uscito uno Short."); return

    if arg.file:
        c = coda.leggi(arg.file)
    else:
        c, motivo = scegli(stato)
        if c is None:
            print(f"[ok] {motivo}."); return
    print(f"[coda] {c['id']} (Short), uscita prevista {coda.data_uscita(c)}")
    if c.get("tipo") != "reel":
        errore(f"{c['id']} non è un reel", "Su YouTube vanno solo i reel, come Short.", prova)

    errori = coda.valida(c, coda.parole_vietate())
    if errori:
        errore(f"il contenuto {c['id']} non passa i controlli", "\n".join(f"- {x}" for x in errori), prova)
    print("[ok] controlli superati (lunghezze, file, spoiler)")

    via, motivo = coda.veto(c) if not arg.file else (True, "contenuto di prova: veto non applicato")
    print(f"[veto] {motivo}")
    if not via:
        return

    cartella = pathlib.Path(arg.media) if arg.media else RADICE / "docs" / "social" / str(c["id"])
    video = cartella / "reel.mp4"
    if not video.is_file():
        errore(f"manca il video di {c['id']}", f"{video} non c'è. Lanciare genera_media.py.", prova)
    mb = video.stat().st_size / 1e6
    durata = coda.durata_video(video)
    if mb > MAX_MB or durata is None or durata > 180:
        errore(f"video di {c['id']} non adatto a uno Short", f"{mb:.1f} MB, {durata} s (servono al massimo 180 s)", prova)
    print(f"[file] reel.mp4: {mb:.1f} MB, {durata:.1f} s, 1080x1920")

    corpo = corpo_video(c)
    if prova:
        print("[prova] nessun token letto: in prova YouTube non si chiama")
        print(f"[prova] POST {UPLOAD}?uploadType=resumable&part=snippet,status")
        print("[prova]   " + json.dumps(corpo, ensure_ascii=False)[:600])
        print(f"[prova] PUT <sessione> con {mb:.1f} MB di video/mp4")
        print("[prova] qui si salverebbe subito lo stato: uscita su youtube")
        print("[prova] qui si rileggerebbe privacyStatus: se non è «public», issue e stop")
        print("[prova] qui si verificherebbe con oEmbed e aprendo youtube.com/shorts/<id>")
        print("[prova] qui si commenterebbe la issue di veto con il permalink e si rigenererebbe il sito")
        print("=" * 70 + "\n PROVA A SECCO FINITA: tutto in ordine fino alla chiamata che carica\n" + "=" * 70)
        return

    try:
        token = access_token()
        risposta = carica(token, video, corpo)
        video_id = risposta["id"]
    except SystemExit:
        raise
    except Exception as e:
        errore(f"caricamento fallito per {c['id']}", str(e), prova)

    # >>> PRIMA DI QUALUNQUE ALTRA COSA: lo stato, salvato e spinto. <<<
    stato = leggi_stato()
    stato.setdefault("uscite", []).append({
        "id": c["id"], "rete": "youtube", "tipo": "short", "media_id": video_id,
        "quando": adesso().isoformat(), "verificato": False,
        "anteprima": f"social/{c['id']}/copertina.jpg", "titolo": corpo["snippet"]["title"],
    })
    stato["ultimo_errore"] = None
    scrivi_stato(stato, f"stato: uscito {c['id']} su YouTube ({video_id})")
    print(f"[ok] caricato {c['id']} → video {video_id}")

    try:
        v = leggi_video(token, video_id) or {}
    except Exception as e:
        v = {}
        print(f"[warn] stato del video non letto: {e}")
    st = v.get("status", {})
    print(f"[youtube] privacy {st.get('privacyStatus', '?')}, caricamento {st.get('uploadStatus', '?')}")
    if st.get("uploadStatus") in ("rejected", "failed") or st.get("privacyStatus") not in (None, "public"):
        errore(f"lo Short {c['id']} non è pubblico",
               f"Il video {video_id} è stato caricato ma risulta {st.get('privacyStatus')} / {st.get('uploadStatus')} "
               f"({st.get('rejectionReason') or st.get('failureReason') or 'nessun motivo dato'}). "
               "Non si riprova. Se è privato per il progetto API non verificato: modulo di audit "
               "(support.google.com/youtube/contact/yt_api_form) e intanto pubblico a mano da YouTube Studio.", prova)

    try:
        permalink, nota = verifica(video_id)
    except Exception as e:
        errore(f"verifica dello Short fallita per {c['id']}", f"Il video {video_id} risulta caricato. {e}", prova)
    stato = leggi_stato()
    voce = next(u for u in stato["uscite"] if u["id"] == c["id"] and u["rete"] == "youtube")
    voce.update(permalink=permalink, verificato=True, pagina=nota)
    scrivi_stato(stato, f"stato: verificato lo Short {c['id']}")
    print(f"[ok] verificato: {permalink} ({nota})")

    if c.get("issue") and gh_disponibile():
        try:
            if leggi_issue(c["issue"]).get("state") == "closed":
                commenta_issue(c["issue"], f"Uscito anche come Short su YouTube: {permalink}")
            else:
                chiudi_issue(c["issue"], f"Uscito come Short su YouTube: {permalink}")
        except Exception as e:
            print(f"[warn] issue di veto non aggiornata: {e}")
    try:
        import genera_sito
        genera_sito.genera()
    except Exception as e:
        print(f"[warn] sito non rigenerato (lo rifà il prossimo giro): {e}")


if __name__ == "__main__":
    main()
