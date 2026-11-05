# Il piano di CTRL+ALT REVENGE

Aggiornato il 4 novembre 2026. Il piano dice in che ordine si fa il gioco, cosa blocca cosa, quanto costa ogni tappa e quando una tappa è finita. È pubblico, quindi non contiene spoiler: la trama per capitolo sta nei file privati della storia.

## Come leggere le stime

- **Ore assistite:** ore di lavoro con Claude, comprese le prove e le correzioni, quindi non ore di una persona che lavora da sola. A queste si aggiungono le ore di Luigi: decisioni, prove con il pad, voti.
- **Margine:** è largo, perché nessun capitolo è ancora stato fatto. Dopo il capitolo 1 le stime si rifanno con i tempi veri.
- **Calendario:** dipende dal ritmo delle sessioni, quindi qui non ci sono date. A 10-15 ore assistite a settimana, la demo 2 arriva in 2-5 mesi e il gioco completo in 1-2,5 anni.

## In breve

| # | Tappa | Ore assistite | Ore di Luigi | Dipende da | Stato |
|---|---|---|---|---|---|
| 0 | Fondamenta: grafica nuova, GIG che non si specchia, volti dei murales | 15-25 | 2-3 | - | in corso |
| 1 | Stanza di prova in grigio: tutto il movimento e l'arena | 25-40 | 3-5 | 0 | in corso |
| 2 | Prologo, il pignoramento | 30-50 | 3-4 | 1 | |
| 3 | Capitolo 1, «I tetti dei Tamburi» | 40-60 | 3-4 | 2 | |
| **D2** | **Demo 2 sul sito: prologo più capitolo 1** | 5-10 | 1 | 3 | |
| 4 | Gli altri capitoli dell'atto I | 140-200 | 10-15 | D2 | |
| 5 | Atti II e III, con i boss | 350-500 | 25-35 | 4 | |
| M | Murales: le circa 75 vignette della storia | 75-180 | 5-8 | 0 | in parallelo |
| S | Musica: circa 12-15 brani | 20-30 | 6-10 | - | in parallelo |
| T | Sistemi: menu, salvataggi, opzioni, accessibilità, inglese | 30-50 | 3-5 | 1 | in parallelo |
| F | Rifinitura, prove su più PC, build per Windows, pagina del negozio | 40-60 | 10-15 | 5 | |
| | **Totale** | **circa 770-1200** | **circa 70-105** | | |

## Le tappe

### 0. Fondamenta (in corso)

Servono a non rifare il lavoro dopo: tutto quello che viene si appoggia sulla grafica nuova.

- **Grafica nuova nel gioco:** cel shading a 2 toni più un terzo mirato, sfondi a 3 toni, luci morbide con un tetto ai chiari, e la figura nuova di GIG da ex pugile. Si rigenerano sprite e sfondi in un solo passaggio. 6-10 ore.
- **GIG non si specchia mai:** le animazioni si rendono dal 3D per i due versi, così il braccio cyber resta sempre lo stesso. 4-6 ore.
- **Volti dei murales:** la prova con le basi AI è fatta. Restano il giudizio alla cieca, lo stencil vero sui volti e la riga nei crediti. 3-5 ore.
- **Sito:** il video, la GIF e i numeri della dimostrazione si rifanno con i nemici nuovi. 1 ora.

**È finita quando** i test passano con la grafica nuova, Luigi l'ha vista in gioco e la vignetta di prova dei volti ha preso il voto dai giudici.

### 1. Stanza di prova in grigio (in corso)

Una stanza senza grafica in cui si tarano tutte le mosse con Luigi, prima di costruirci sopra i livelli:
- doppio salto e Spinta;
- sporgenze, scivolate, salti a muro, scatti, corse sui muri e il Rampino;
- il passaggio all'arena, con la telecamera che si inclina e il VAI a fine scontro;
- il primo puzzle di hacking nel livello.

**È finita quando** Luigi, con il pad, dice che il movimento è giusto. Le misure (altezze, distanze, tempi) diventano le regole per disegnare i livelli.

**Fatto il 5 novembre 2026:** il primo blocco. Corsa, salto variabile con coyote time e buffer, Spinta, piattaforme sottili, accovacciarsi, scivolata, sporgenze e scavalco, con la fisica nostra a tick fissi (posizioni a sottopixel interi, quindi replay e hash restano validi) e 20 test. La stanza si apre dal titolo, voce STANZA DI PROVA; i valori di partenza sono in `game/src/platform/platform_moves.gd` e si cambiano in `game/data/platform/gig_moves.tres`. Dopo la prima prova di Luigi: salto meno lunare, aggancio e salita senza scatti, niente tremolio contro i muri, scivolata anche da fermi e camminata accovacciata. Poi il secondo blocco: salto a muro col freno del braccio, scatto in aria e corsa sui muri, con le loro pose. Poi, su richiesta di Luigi, la risoluzione è passata da 384×216 a 480×270 (60 px per metro, tutto più grande del 25%): stanza, sprite, combattimento, livello, sfondi, interfaccia, replay e test. Poi il passaggio all'arena: oltre il cartello ARENA la telecamera si blocca e si inclina, il pavimento si apre in profondità e si combatte a corsie con il sistema dello slice (il livello gira dentro la stanza); a scontro finito compare VAI, la telecamera torna laterale e si riprende a saltare. Per ora arrivano punk e bruto dello slice, al posto del rider e dell'esattore di professione (decisione 63). Restano l'intelligenza e lo sprite del rider, il Rampino e il primo hacking.

### 2. Prologo

Il cimitero di San Brunone e il garage. È il tutorial, e cresce con GIG: prima del riavvio del braccio niente acrobazie e niente hacking, dopo il riavvio arriva il doppio salto. Comprende gli Esattori con i loro segni di riconoscimento e le prime vignette a fumetto.

**È finito quando** si gioca dall'inizio alla fine, i test e il replay passano, e la lista di coerenza (luoghi, ore, meteo, luna) non ha errori aperti.

### 3. Capitolo 1, «I tetti dei Tamburi»

Di pomeriggio, sotto la pioggia, con Totò che fa da guida. Dentro ci sono il primo registro segreto, il cibo come recupero e il murale del capitolo, che fa da mappa e da salvataggio.

**È finito quando** vale lo stesso criterio del prologo, e la durata sta fra 6 e 10 minuti.

### D2. Demo 2

Il prologo più il capitolo 1 vanno sul sito al posto dello slice, con la musica. Dopo la demo 2 si rifanno le stime del resto con i tempi veri dei due capitoli.

### 4 e 5. Il resto dei capitoli

Tredici capitoli in tutto, divisi in tre atti, più il prologo. Ogni capitolo dura da 6 a 10 minuti. Per capitolo la stima di partenza è 35-50 ore assistite, più i boss.

### In parallelo

- **Murales:** circa 75 vignette. La stima di 100-180 ore era senza basi AI; con le basi AI può scendere verso 75-110 ore, da misurare sulle prime dieci.
- **Musica:** un tema per atto, i brani dei capitoli, i boss e i jingle. Si fanno con Suno, e i brani non entrano nel repo.
- **Sistemi:** menu, salvataggi per capitolo, opzioni, comandi rimappabili, modalità arcade con il CONTINUA?, testi in inglese.

### F. Rifinitura e uscita

Difficoltà, prove su più PC e con più controller, build per Windows, pagina del negozio con la dichiarazione dell'AI. Prima dell'uscita vanno chiusi i consensi per le persone e i luoghi reali, e va fatto rileggere il testo legale delle licenze.

## Cosa blocca cosa

- **La grafica nuova (0) viene prima di tutto:** altrimenti si rifanno sprite, sfondi e media due volte.
- **La stanza di prova (1) viene prima dei livelli:** le misure del movimento decidono come si disegnano piattaforme e salti.
- **I murales aspettano il voto sui volti (0),** ma poi vanno avanti da soli, insieme ai capitoli.
- **I testi pubblici e i crediti** si aggiornano a ogni tappa: README, sito e crediti devono dire il vero.

## Decisioni ancora aperte

Non bloccano la tappa 1, ma vanno prese prima di disegnare i capitoli in cui servono:
- l'aspetto di alcuni personaggi secondari, per i murales;
- alcuni nomi del mondo di SIDERA, come i piani di abbonamento del braccio;
- nome e tag del writer che ispira Totò, per i crediti e il sito: il consenso c'è.
