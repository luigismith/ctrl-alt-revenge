# -*- coding: utf-8 -*-
"""Prova della sentinella con date e stati finti, senza rete e senza GitHub.

    python -I prove/prova_sentinella.py

Ogni caso dice cosa ci si aspetta; se uno sbaglia, lo script esce con 1.
"""
import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "strumenti"))
import sentinella as s  # noqa: E402

D = dt.date.fromisoformat
sys.stdout.reconfigure(encoding="utf-8")  # la console di Windows è cp1252
mai_fermato = lambda c: False  # noqa: E731
errori = []


def caso(nome, ottenuto, atteso_titoli):
    titoli = [t for t, _ in ottenuto]
    ok = len(titoli) == len(atteso_titoli) and all(t.startswith(a) for t, a in zip(titoli, atteso_titoli))
    print(("ok   " if ok else "NO   ") + nome + ("" if ok else f"\n     atteso {atteso_titoli}, ottenuto {titoli}"))
    if not ok:
        errori.append(nome)


def post(id_, data, stato="pronto", tipo="carosello"):
    return {"id": id_, "uscita": D(data), "stato": stato, "tipo": tipo}


def uscita(id_, quando, rete="instagram", tipo="carosello"):
    return {"id": id_, "rete": rete, "tipo": tipo, "quando": quando}


# 20/11/2026 è venerdì; 21/11 sabato; 23/11 lunedì; 24/11 martedì.
coda = [post("a", "2026-11-20"), post("b", "2026-11-24")]

caso("acceso: senza pronti e senza uscite tace",
     [("x", "")] if s.acceso([post("a", "2026-11-20", "bozza")], {"uscite": []}) else [], [])
caso("acceso: con un pronto si sveglia",
     [("x", "")] if s.acceso(coda, {"uscite": []}) else [], ["x"])

caso("uscita: venerdì saltato → issue il sabato",
     s.controlla_uscite(D("2026-11-21"), coda, {"uscite": []}, mai_fermato), [s.T_USCITA])
caso("uscita: venerdì uscito (alle 18:50 italiane) → niente",
     s.controlla_uscite(D("2026-11-21"), coda, {"uscite": [uscita("a", "2026-11-20T17:50:00+00:00")]}, mai_fermato), [])
caso("uscita: il post di ieri sera tardi conta per ieri (23:30 italiane = 22:30 UTC)",
     s.controlla_uscite(D("2026-11-21"), coda, {"uscite": [uscita("a", "2026-11-20T22:30:00+00:00")]}, mai_fermato), [])
caso("uscita: ieri non era giorno di uscita (sabato) → niente",
     s.controlla_uscite(D("2026-11-22"), coda, {"uscite": []}, mai_fermato), [])
caso("uscita: fermato da Luigi col veto → niente",
     s.controlla_uscite(D("2026-11-21"), coda, {"uscite": []}, lambda c: c["id"] == "a"), [])
caso("uscita: in bozza non conta",
     s.controlla_uscite(D("2026-11-21"), [post("a", "2026-11-20", "bozza")], {"uscite": []}, mai_fermato), [])
caso("uscita: due in coda per venerdì, ne è uscito uno → l'altro slitta, niente",
     s.controlla_uscite(D("2026-11-21"), [post("a", "2026-11-20"), post("a2", "2026-11-20")],
                        {"uscite": [uscita("a", "2026-11-20T18:00:00+00:00")]}, mai_fermato), [])

reel = [post("r", "2026-11-22", tipo="reel")]
ig_reel = {"uscite": [uscita("r", "2026-11-22T17:50:00+00:00", tipo="reel")]}
caso("short: reel su IG da 2 giorni, YouTube niente → issue",
     s.controlla_short(dt.datetime(2026, 11, 24, 22, 25, tzinfo=dt.timezone.utc), reel, ig_reel, mai_fermato), [s.T_SHORT])
caso("short: reel su IG da 5 ore → ancora niente",
     s.controlla_short(dt.datetime(2026, 11, 22, 22, 25, tzinfo=dt.timezone.utc), reel, ig_reel, mai_fermato), [])
caso("short: uscito anche su YouTube → niente",
     s.controlla_short(dt.datetime(2026, 11, 24, 22, 25, tzinfo=dt.timezone.utc), reel,
                       {"uscite": ig_reel["uscite"] + [uscita("r", "2026-11-22T18:50:00+00:00", "youtube", "short")]},
                       mai_fermato), [])
caso("short: un carosello non chiede lo Short",
     s.controlla_short(dt.datetime(2026, 11, 24, 22, 25, tzinfo=dt.timezone.utc), coda,
                       {"uscite": [uscita("a", "2026-11-20T17:50:00+00:00")]}, mai_fermato), [])

caso("coda: copre fino al 24/11, oggi 15/11 → issue",
     s.controlla_coda(D("2026-11-15"), coda, {"uscite": []}, mai_fermato), [s.T_CODA])
caso("coda: copre fino al 01/12, oggi 17/11 → niente",
     s.controlla_coda(D("2026-11-17"), coda + [post("c", "2026-12-01")], {"uscite": []}, mai_fermato), [])
caso("coda: vuota → issue",
     s.controlla_coda(D("2026-11-25"), coda, {"uscite": [uscita("a", "x"), uscita("b", "x")]}, mai_fermato), [s.T_CODA])
caso("coda: il titolo porta la settimana (una issue a settimana)",
     [(t, "") for t, _ in s.controlla_coda(D("2026-11-15"), coda, {"uscite": []}, mai_fermato) if "settimana 46/2026" in t],
     [s.T_CODA])
caso("coda: un contenuto fermato col veto non copre",
     s.controlla_coda(D("2026-11-17"), coda + [post("c", "2026-12-01")], {"uscite": []}, lambda c: c["id"] == "c"), [s.T_CODA])

caso("token IG: 20 giorni → niente", s.controlla_token_ig(20), [])
caso("token IG: 50 giorni → issue (mancano 10)", s.controlla_token_ig(50), [s.T_TOKEN_IG])
caso("token IG: 70 giorni → issue (scaduto)", s.controlla_token_ig(70), [s.T_TOKEN_IG])
caso("token IG: illeggibile → issue", s.controlla_token_ig(None), [s.T_TOKEN_IG])

print(f"\n{'TUTTO VERDE' if not errori else f'{len(errori)} casi sbagliati'}")
sys.exit(1 if errori else 0)
