# A che punto siamo (15/11/2026, prima del riavvio)

Il clone di lavoro sta sul PC di casa in `%USERPROFILE%\ctrlaltrevenge-lab\social\` (ramo `main`).
La lista degli spoiler e le catture stanno fuori dal repository, in `%USERPROFILE%\ctrlaltrevenge-lab\social-privato\`.

## Fatto
- **Pubblicatore Instagram** (`strumenti/pubblica_ig.py`, `.github/workflows/pubblica-ig.yml`): finito. Prova a secco verde sul PC e su Actions (run 43699220291). I controlli a ogni push sono verdi dopo la correzione dello YAML (run 43699384335).
- **Pubblicatore YouTube Shorts** (`strumenti/pubblica_yt.py`, `.github/workflows/pubblica-yt.yml`): scritto. Prova a secco verde sul PC; quella su Actions va ancora lanciata (input `prova` = true, `file` = `prove/prova-reel.yml`).
- **Token di YouTube** per Luigi: `strumenti/ottieni_token_youtube.py`. Non l'ha ancora lanciato nessuno: servono il canale e il progetto Google.
- **Sito** (`pages.yml`): deploy a ogni push su `docs/**` e alla fine del workflow YouTube. Non fa niente finché la variabile `PAGES_ATTIVE` non vale `si`. Pages è ancora spento.
- **Privacy e cancellazione dei dati**: `sito/pagine/` → `docs/privacy.html`, `docs/en/privacy.html`, `docs/cancellazione-dati.html`.
- **Il veto**: una issue «In coda: <id>» per ogni contenuto. Se la chiude il bot dopo Instagram, lo Short esce lo stesso; se la chiude Luigi, si ferma tutto.
- **Il primo post** `contenuti/2026-11-20-a1-cimitero.yml` è in bozza: aspetta il via della regia.

## Da fare
1. La prova a secco di YouTube su Actions.
2. La sentinella (`sentinella.yml`, alle 23:25).
3. La pagina con i passi manuali di Luigi («Accensione di Ctrl-Alt-Revenge»): non è ancora cominciata.
4. Chiedere alla regia se si può accendere Pages sull'indirizzo `-nuovo`, per la prova vera degli URL.
