# Test e replay

Tutti i comandi partono dalla radice del repository e passano da `tools/run_godot.sh`, che usa l'eseguibile console di Godot 4.7.2, mette un timeout, scrive il log e lo controlla.

## Test automatici

```
tools/run_godot.sh 120 --headless --import
REQUIRE_DONE=1 tools/run_godot.sh 300 --headless -s res://tests/run_tests.gd
REQUIRE_DONE=1 tools/run_godot.sh 120 --headless -s "$(cygpath -w "$PWD/tools/audio/godot_tests/test_audio.gd")"
```

Il gioco gira senza tempo reale: i test costruiscono un livello e lo fanno avanzare un tick alla volta con `Level.step()`. L'ultima riga dell'output è `DONE` solo se tutti i test passano.

Il terzo comando lancia sul progetto del gioco le 50 prove dell'audio scritte con la pipeline dei suoni (`tools/audio/godot_tests/test_audio.gd`): ricerca della musica e lettura di `music.json`, loop dei brani, bus, guadagni e pan di `Sfx`. Gli avvisi su `music.json` non valido e sul suono mancante sono voluti: sono i casi di prova.

| Gruppo | Cosa verifica |
|---|---|
| Impostazioni | risoluzione, scala intera, 60 tick, interpolazione spenta, nessuna azione su Shift |
| FrameAnim | ogni fotogramma resta esattamente i suoi tick, eventi e dx all'inizio del fotogramma, loop, `hold`, ritemporizzazione sui tempi dell'AttackData |
| Combo | jab1 → jab2 → gancio → calcio solo se i colpi vanno a segno; a vuoto ripete jab1; buffer di 8 tick |
| Hitstop | 5/7 tick per jab1, attaccante e vittima fermi, lampo bianco di 2 tick |
| Presa | entro 18 px e 4 px di profondità, la vittima arriva all'offset `victim` in 4 tick senza scatti, liberazione dopo 90 tick, due ginocchiate e proiezione, il corpo colpisce un altro nemico; la proiezione (anche all'indietro) tiene tutti i fotogrammi e rilascia la vittima dove è disegnata; contro il muro la coppia resta dentro; una ginocchiata che manda KO chiude la presa e la vittima vola con `knock_air` |
| Nemici | ogni attacco colpisce GIG dalla distanza scelta dall'IA; armatura del bruto |
| AttackDirector | mai due nemici in attacco attivo insieme; 0,35 s fra due attacchi qualsiasi; 1,2 s fra due attacchi dello stesso nemico |
| KO finale | 26 tick di congelamento, poi 24 tick al 35%; GIG resta visibile per tutti i 50 tick anche mentre lampeggia; la vittima non resta bianca per tutto il congelamento |
| Vite | KO di GIG, rientro dall'alto con l'invulnerabilità, CONTINUA? senza vite; ultima vita persa a zona già liberata (KO insieme o a 8 tick): niente CONTINUA? e il livello finisce |
| Colpi in aria | un jab del punk su GIG in salto lo atterra (niente GIG sospeso) |
| Varie | il bruto in armatura tiene il turno d'attacco; un nemico che entra da fuori schermo non si può colpire prima del muro; un colpo subito fa ripartire la combo da jab1; a replay finito nessun tasto resta tenuto; i crediti usano solo caratteri del font e il logo come titolo |
| File | validità dei JSON degli sprite (veri e segnaposto), degli oggetti, di `fx.json`, `layers.json`, del livello e delle risorse `.tres`; tempi delle animazioni d'attacco |
| Replay | vedi sotto; più il determinismo (stesso replay due volte, stesso hash SHA-256 di tutti gli stati), "VAI" solo dopo che il corpo dell'ultimo nemico è sparito, telecamera ferma sull'arena dopo "ZONA LIBERATA" |

## Replay

I file in `replays/` registrano solo gli ingressi, tick per tick (formato descritto in `src/debug/replay.gd`). Si generano facendo giocare il pilota automatico (`src/debug/autopilot.gd`):

```
tools/run_godot.sh 400 --headless -s res://tests/make_replays.gd
tools/run_godot.sh 400 --headless -s res://tests/make_replays.gd -- demo arena
```

| Replay | Contenuto |
|---|---|
| `combo_punk.json` | GIG sconfigge il punk dell'ondata 1 solo con le combo |
| `grab_throw.json` | presa, due ginocchiate e proiezione |
| `cable_touch.json` | GIG cammina dentro il cavo: 10 di danno e atterramento |
| `cable_jump.json` | GIG salta il cavo e passa indenne |
| `arena.json` | punk e bruto nell'arena, fino a "ZONA LIBERATA" |
| `demo.json` | dimostrazione di 60-90 s di tutto il livello (oggi 68,8 s, seme 13) |

Un replay resta valido finché non cambiano le regole del gameplay, i dati in `data/` o le box degli sprite: dopo modifiche del genere si rigenerano i replay e si rilanciano i test.

## Controllo visivo con Movie Maker

```
tools/run_godot.sh 400 --write-movie "C:/percorso/assoluto/f.png" --fixed-fps 60 --quit-after 6000 -- --replay res://tests/replays/demo.json --quit-at-end
tools/run_godot.sh 200 --write-movie "C:/percorso/assoluto/f.png" --fixed-fps 60 --quit-after 900 -s res://tests/ui_gallery.gd
```

La galleria (`ui_gallery.gd`) mostra le schermate che i replay non toccano: titolo, crediti, box di debug, pausa, CONTINUA?, GAME OVER, fine demo. I fotogrammi uguali consecutivi sono attesi solo durante il congelamento del KO finale e sulle schermate ferme.

Il fotogramma k (contando da 0) mostra lo stato dopo il tick k del livello, cioè dopo k + 1 tick di simulazione.

**Chiudere una registrazione senza errori.** Con Movie Maker l'audio si mescola solo dentro i fotogrammi registrati, e l'AudioServer libera un suono fermato solo nei cicli di mix successivi. Se il motore esce per `--quit-after` mentre suona un effetto o la musica, il log riporta `ERROR: 1 resources still in use at exit`. Per questo:
- il replay si chiude con `--quit-at-end`: alla fine del replay `Game.quit_clean()` zittisce l'audio, aspetta dieci fotogrammi e poi esce;
- la galleria si chiude da sola dopo 630 fotogrammi, nello stesso modo;
- `--quit-after` resta solo come sicurezza, con un valore più grande della durata.

Le esecuzioni in tempo reale (finestra normale, `--headless`) non hanno questo problema: lì l'audio gira in un thread suo e alla chiusura `Sfx` e `Music` aspettano al massimo 200 ms che i suoni vengano liberati.

## Argomenti del gioco

Dopo `--` sulla riga di comando: `--autostart`, `--replay <file>`, `--seed <n>`, `--record <file>`, `--start-x <x>`, `--autopilot <scenario>`, `--quit-at-end`, `--print-hash`, `--debug-boxes`. Sono descritti in `src/core/session_options.gd`.
