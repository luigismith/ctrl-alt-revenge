# A che punto siamo (15/11/2026, sera)

Il clone di lavoro sta sul PC di casa in `%USERPROFILE%\ctrlaltrevenge-lab\social\` (ramo `main`).
La lista degli spoiler e le catture stanno fuori dal repository, in `%USERPROFILE%\ctrlaltrevenge-lab\social-privato\`.

## Fatto
- **Pubblicatore Instagram** (`strumenti/pubblica_ig.py`, `.github/workflows/pubblica-ig.yml`): finito. Prova a secco verde sul PC e su Actions (run 43699220291). I controlli a ogni push sono verdi dopo la correzione dello YAML (run 43699384335).
- **Pubblicatore YouTube Shorts** (`strumenti/pubblica_yt.py`, `.github/workflows/pubblica-yt.yml`): scritto. Prova a secco verde sul PC e su Actions (run 43778944788, 16/11 con il via della regia): video di prova fatto sul runner, controlli superati, ci si ferma prima del token e del caricamento.
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

## Ripasso della scheda social, 16/11/2026 notte
- **Controlli** (`strumenti/controlli.py`) e **prova della sentinella** (22 casi) verdi in locale.
- **Sentinella** lanciata a mano dopo lo scambio (run 43776134969): «sito: risponde», nessuna issue. L'indirizzo lo prende da `GITHUB_REPOSITORY`, quindi è già quello nuovo.
- **Riferimenti a `-nuovo`:** nel codice, nei workflow e nelle pagine non ne resta nessuno; restano solo nei documenti che raccontano lo scambio. Variabili: `PAGES_ATTIVE`=si e `CARU_PAROLE_VIETATE`. Pages: build da workflow, HTTPS forzato; 404, privacy, cancellazione dei dati e media rispondono sull'indirizzo nuovo.
- **Inglese del sito:** sette ritocchi in `sito/testi/en.json`, senza cambiare il senso (Carmine church, staccato, «take them down», «struck his name off the patents», «young hands, but skilled ones», «not a fingerprint on them»).
- **Difetto nel generatore delle tavole** (`strumenti/genera_media.py`): il post e la storia usavano la stessa pagina e lo stesso profilo di Chrome, e a volte la storia usciva con la tavola del post. Ora ogni scatto ha un nome suo; provato due volte di fila.
- **Uscita 1 in bozza:** `contenuti/torretta-scritta.yml` (immagine singola, senza data), con la didascalia in italiano e in inglese e con «Cattura di laboratorio» nella riga di onestà.
- **Regia, 00:48:** il primo post resta `a1-cimitero`, la torretta è la seconda uscita (voto alla tavola: 6,5). La scritta ora va a capo dove si vuole (`white-space: pre-line` in `sito/tavola.html`, `\n` nel testo), e la scritta delle storie è scesa da 44 a 40 px perché la riga di ARIA+ ci stia intera. Quando arrivano da `caru-3d` le due catture nuove (torretta pulita e con lo strato della gente, GIG intero, fondo chiaro), l'uscita diventa un carosello di due tavole: sulla prima la riga di ARIA+, sulla seconda «La scritta non è di SIDERA.». L'immagine singola resta come ripiego.
- **Carosello della torretta pronto a ricevere le catture** (regia, 01:12): `contenuti/torretta-carosello.yml`, fonte `inbox/2026-11-16-torretta-carosello/` con due segnaposto che hanno già i nomi di `caru-3d` (`social_torretta_pulita.png`, `social_torretta_gente.png`). Quando arrivano: sostituire i due file, cancellare `SEGNAPOSTO`, rileggere gli alt e scegliere l'inquadratura. Finché `SEGNAPOSTO` c'è, `coda.py` non lascia passare il contenuto a «pronto».

## Da fare
1. Le catture della torretta da `caru-3d`: sostituire i segnaposto del carosello (vedi sopra).
2. Il primo post: aspettare le catture nuove di A1 in `inbox/`, rifare le tavole, data e nome del file, poi la regia lo guarda e dà il via.
3. Con il via della regia: la routine settimanale (Pages e lo scambio dei nomi sono fatti, 16/11).
4. I passi di Luigi, in ordine, da `ACCENSIONE.md`: li porta la regia quando ci sono le immagini nuove.
5. Il secret `CARU_PAROLE_VIETATE` va rimesso dalla lista corretta (la riga 8 ora è «# ---»): lo fa Luigi, non è urgente. Nei log delle Actions i «#» degli hashtag escono come `***`: GitHub maschera ogni riga del secret, e a quanto pare una riga è un «#» da solo. Si vede solo nei log, ma è un'altra ragione per ricaricarlo.
