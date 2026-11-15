# A che punto siamo (15/11/2026, sera)

Il clone di lavoro sta sul PC di casa in `%USERPROFILE%\ctrlaltrevenge-lab\social\` (ramo `main`).
La lista degli spoiler e le catture stanno fuori dal repository, in `%USERPROFILE%\ctrlaltrevenge-lab\social-privato\`.

## Fatto
- **Pubblicatore Instagram** (`strumenti/pubblica_ig.py`, `.github/workflows/pubblica-ig.yml`): finito. Prova a secco verde sul PC e su Actions (run 43699220291). I controlli a ogni push sono verdi dopo la correzione dello YAML (run 43699384335).
- **Pubblicatore YouTube Shorts** (`strumenti/pubblica_yt.py`, `.github/workflows/pubblica-yt.yml`): scritto. Prova a secco verde sul PC; quella su Actions va ancora lanciata (input `prova` = true, `file` = `prove/prova-reel.yml`).
- **Token di YouTube** per Luigi: `strumenti/ottieni_token_youtube.py`. Non l'ha ancora lanciato nessuno: servono il canale e il progetto Google.
- **Sito** (`pages.yml`): deploy a ogni push su `docs/**` e alla fine del workflow YouTube. Non fa niente finché la variabile `PAGES_ATTIVE` non vale `si`. Pages è ancora spento.
- **Privacy e cancellazione dei dati**: `sito/pagine/` → `docs/privacy.html`, `docs/en/privacy.html`, `docs/cancellazione-dati.html`.
- **Il veto**: una issue «In coda: <id>» per ogni contenuto. Se la chiude il bot dopo Instagram, lo Short esce lo stesso; se la chiude Luigi, si ferma tutto.
- **Il primo post** `contenuti/a1-cimitero.yml` è in bozza, senza data e con #gamedev al posto di #stopmotion. La regia l'ha rimandato il 15/11: il set di A1 cambia (sfondo più cupo, colature rosse da correggere) e le catture nuove arriveranno in `inbox/`. Una bozza ora può stare senza `uscita`; un «pronto» no.
- **Sentinella** (`strumenti/sentinella.py`, `.github/workflows/sentinella.yml`, ogni sera 22:25 d'inverno, 23:25 d'estate): uscite mancate, Short mancati, coda sotto i 14 giorni (una issue a settimana), token Instagram (età e prova di `/me`), refresh token di YouTube, sito. Ogni controllo si accende da solo quando la sua parte esiste: oggi tace. La prova con date finte (`prove/prova_sentinella.py`, 22 casi) gira anche nei controlli a ogni push.
- **Pagina dei passi manuali di Luigi**: `ACCENSIONE.md`, sette passi con la verifica di ognuno.

## Giro della regia del 16/11/2026 (la scheda social era chiusa)
- **Testi del sito riscritti** in `sito/testi/it.json` e `en.json`, sulla base del messaggio del gioco: Luigi li vuole meno didascalici, che raccontino ai giocatori e a chi conosce la vicenda di Taranto, senza slogan. Stessa struttura e stesse chiavi di prima.
- **Torretta ARIA+ nuova** (plastica, con la scritta «CHI RESPIRA PAGA») al posto di quella di cartone: `docs/media/torretta-scritta.*`, sorgente e nota in `inbox/2026-11-16-torretta-scritta/`. In `sito/modello.html` sono cambiati solo i due nomi del file.
- **Sei uscite per i social** in `inbox/2026-11-16-messaggio/nota.md`: testi pronti, immagini in parte da fare.
- Sito rigenerato in locale; lista degli spoiler: zero voci trovate. La vista da telefono non è stata verificata.
- **Luigi, 16/11 alle 00:30: «Sostituisci subito il vecchio».** Testi e torretta approvati per il sito. Le sei uscite restano bozze: ognuna aspetta la sua immagine e il via.

## Da fare
1. La prova a secco di YouTube su Actions.
2. Il primo post: aspettare le catture nuove di A1 in `inbox/`, rifare le tavole, data e nome del file, poi la regia lo guarda e dà il via.
3. Con il via della regia: Pages sull'indirizzo `-nuovo` per la prova vera degli URL, la routine, lo scambio dei nomi.
4. I passi di Luigi, in ordine, da `ACCENSIONE.md`: li porta la regia quando ci sono le immagini nuove.
5. Il secret `CARU_PAROLE_VIETATE` va rimesso dalla lista corretta (la riga 8 ora è «# ---»): lo fa Luigi, non è urgente.
