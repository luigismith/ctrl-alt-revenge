# I livelli in LDtk

I livelli platform si disegnano con [LDtk](https://ldtk.io), l'editor di livelli 2D di Sébastien Bénard. È gratuito e open source, con licenza MIT, e va bene anche per un gioco in vendita. Il gioco legge da solo i file `.ldtk`, con un importatore nostro (`game/src/platform/ldtk_map.gd`, MIT): non serve nessun plugin.

## Aprire un livello

1. Apri `%USERPROFILE%\ctrlaltrevenge-lab\tools\ldtk-1.5.3\LDtk.exe`. Se il laboratorio non ce l'ha, lo installa `tools/setup/prepara_laboratorio.ps1 -Solo ldtk`: lo script scarica l'installer ufficiale, ne controlla l'hash e lo estrae con 7-Zip, senza installare niente.
2. Scegli **Load** e apri `game/data/platform/prologo_v2.ldtk` (il prologo che il gioco carica; `prologo.ldtk` è quello di prima, in un livello solo, che resta per i test).
3. Salva con Ctrl+S, poi rilancia il gioco (`-- --prologo`): legge il file salvato, senza import.

## Cosa c'è nel progetto

I tipi sono quelli della legenda della sessione mappe. Il progetto ha quattro livelli di disegno:

| Livello | Cosa ci va |
|---|---|
| `Collisioni` | le piastrelle: Pieno, Sottile, Vuoto (la fossa senza fondo, dove si perde una vita) e gli altri tipi della legenda |
| `Greybox` | i colori del greybox, che LDtk disegna da solo dalle Collisioni |
| `Entita` | partenze, ripartenze, cartelli (con titolo e riga d'aiuto), scene, nemici, leve, persone, oggetti, power-up... |
| `Zone` | i rettangoli: arene, zone tossiche, segreti, telecamera, meteo |

Il gioco oggi usa le celle Pieno, Sottile e Vuoto, le partenze, i cartelli con le loro ripartenze, la scena di Mimmo, la porta del garage, l'arena, le leve con i loro cancelli, le zone Meteo, le zone Tossica, i PowerUp e l'uscita. L'arena è la sua zona: la telecamera si ferma sul lato sinistro del rettangolo, il fondo è il pavimento, e lo scontro parte quando GIG è entrato di 130 px. Nella Tossica i campi numerici cambiano i valori del tipo solo se sono maggiori di zero: lasciati a 0 valgono quelli del tipo (`game/data/tossiche/`). Per una zona sempre accesa si mette `attiva_s` uguale a `ciclo_s`. Un PowerUp senza «ricompare» non torna alle ripartenze, solo a partita nuova. Gli altri tipi si possono già disegnare, ma il gioco non li fa ancora. Le piastrelle che non conosce le gioca come la cella più vicina (per esempio Bagnato come Pieno) e lo segnala.

## Più livelli in un file

Un `.ldtk` può avere più livelli, come il prologo nuovo con A e B. Il gioco legge il primo, oppure quello scelto con `nome.ldtk#B`. Se l'`Uscita` ha in `prossima` il nome di un altro livello dello stesso file, quello è il livello dopo (`LdtkMap.next_path`); altrimenti `prossima` è una scena o il capitolo dopo. Nel prologo l'uscita di A porta a B con un breve nero; da riga di comando si può partire da B con `-- --prologo --livello Prologo_B_Fuga`.

## I controlli

Il gioco controlla ogni livello con le regole della legenda, e i test le provano sul prologo:

- ogni fossa ha una ripartenza prima, e nessuna ripartenza sta sopra una fossa;
- prima del riavvio nessuna fossa supera 6 celle;
- pannelli, leve e persone puntano a qualcosa che esiste;
- ogni arena chiude su una ripartenza che esiste, e un'uscita senza `prossima` dà un avviso;
- fuori dalle arene ci sono solo i droni (colomba, vedetta, segugio, ragno);
- un avviso, non un errore, per i blocchi pieni sospesi nel vuoto.

## La mappa di testo

`game/data/platform/prologo.txt` è la stessa mappa in lettere (`#` pieno, `=` sottile, `.` vuoto). La leggono ancora gli script della grafica (`tools/ambienti/`). Non si cambia a mano: dopo ogni modifica in LDtk si rifà dal `.ldtk`, dalla radice del repo:

```
python tools/ldtk/livelli_ldtk.py txt game/data/platform/prologo.ldtk game/data/platform/prologo.txt
```

Lo stesso script crea il progetto dalla legenda (`crea`). Se la legenda cambia, si può rifare il progetto: prima si rifà la mappa di testo come sopra, poi si lancia `crea <mappa> <progetto> --sovrascrivi`. Le celle e i testi dei cartelli restano, ma le altre entità disegnate a mano si perdono. Per non perderle, i tipi nuovi si aggiungono dall'editor.
