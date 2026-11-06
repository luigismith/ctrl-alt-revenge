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
| N | Regia delle scene: filmati, primi piani, presentazioni dei boss, musica delle scene | 20-30 | 3-5 | 1 | |
| M | Murales: le circa 75 vignette della storia | 75-180 | 5-8 | 0 | in parallelo |
| S | Musica: circa 12-15 brani | 20-30 | 6-10 | - | in parallelo |
| T | Sistemi: menu, salvataggi, opzioni, accessibilità, inglese | 30-50 | 3-5 | 1 | in parallelo |
| F | Rifinitura, prove su più PC, build per Windows, pagina del negozio | 40-60 | 10-15 | 5 | |
| | **Totale** | **circa 790-1230** | **circa 75-110** | | |

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
- sporgenze, scivolate, salti a muro, scatti e corse sui muri (il Rampino è spostato a prima del capitolo 4, dove serve);
- il passaggio all'arena, con la telecamera che si inclina e il VAI a fine scontro;
- il primo puzzle di hacking nel livello.

**È finita quando** Luigi, con il pad, dice che il movimento è giusto. Le misure (altezze, distanze, tempi) diventano le regole per disegnare i livelli.

**Fatto il 5 novembre 2026:** il primo blocco. Corsa, salto variabile con coyote time e buffer, Spinta, piattaforme sottili, accovacciarsi, scivolata, sporgenze e scavalco, con la fisica nostra a tick fissi (posizioni a sottopixel interi, quindi replay e hash restano validi) e 20 test. La stanza si apre dal titolo, voce STANZA DI PROVA; i valori di partenza sono in `game/src/platform/platform_moves.gd` e si cambiano in `game/data/platform/gig_moves.tres`. Dopo la prima prova di Luigi: salto meno lunare, aggancio e salita senza scatti, niente tremolio contro i muri, scivolata anche da fermi e camminata accovacciata. Poi il secondo blocco: salto a muro col freno del braccio, scatto in aria e corsa sui muri, con le loro pose. Poi, su richiesta di Luigi, la risoluzione è passata da 384×216 a 480×270 (60 px per metro, tutto più grande del 25%): stanza, sprite, combattimento, livello, sfondi, interfaccia, replay e test. Poi il passaggio all'arena: oltre il cartello ARENA la telecamera si blocca e si inclina, il pavimento si apre in profondità e si combatte a corsie con il sistema dello slice (il livello gira dentro la stanza); a scontro finito compare VAI, la telecamera torna laterale e si riprende a saltare. Poi il rider (decisione 63), il nemico base degli Esattori: veloce e in gruppo, colpisce e scappa, e col pignoramento può lasciare GIG con il braccio sospeso per qualche secondo, se non si divincola. Nell'arena della stanza arrivano due rider e il bruto dello slice. Poi il primo hacking, «Collega e corri»: GIG tiene SU sotto una centralina, alza il braccio cyber (con la sua posa nuova) e appoggia il pugno alla presa; dopo mezzo secondo un cancello si apre per pochi secondi, con il conto alla rovescia. In fondo alla stanza ci sono due prove: un pannello col suo cancello, e due pannelli con tempi diversi, dove chi sbaglia l'ordine trova il cancello lontano già chiuso.

**Il resto della tappa, in quest'ordine** (scelto da Luigi il 5 novembre 2026):
1. la taratura di tempi e distanze dell'hacking, alla prova col pad;
2. l'esattore di professione, che para e carica (fatto il 5 novembre 2026: la guardia salta al terzo colpo parato, e la carica a vuoto lo lascia stordito contro il bordo; con le sue animazioni di guardia, carica e stordimento, e gli effetti sonori nuovi, montati da suoni già pronti con licenza libera);
3. ~~gli sprite veri del rider e dell'esattore~~: spostati dopo il prologo in grigio, insieme alla grafica nuova (scelta di Luigi del 5 novembre 2026: prima il gameplay, poi la grafica, così gli sprite non si fanno due volte). Fino ad allora il rider usa lo sprite del punk e l'esattore quello del bruto, ricolorati;
4. la prova col pad: si fa direttamente sul prologo in grigio, che parte subito (scelta di Luigi: «subito il prologo»).

### 2. Prologo

Il cimitero di San Brunone e il garage. È il tutorial, e cresce con GIG: prima del riavvio del braccio niente acrobazie e niente hacking, dopo il riavvio arriva il doppio salto. Comprende gli Esattori con i loro segni di riconoscimento e le prime vignette a fumetto.

**È finito quando** si gioca dall'inizio alla fine, i test e il replay passano, e la lista di coerenza (luoghi, ore, meteo, luna) non ha errori aperti.

**Fatto il 5 novembre 2026:** il prologo in grigio si gioca dall'inizio alla fine, dal titolo (voce PROLOGO). Prima del riavvio GIG ha un braccio solo: corre, salta, scivola e si aggrappa alle sporgenze con la mano destra, a fatica. Il percorso va dal cimitero al garage passando per l'arena del pignoramento e per la fuga sotto la pioggia. Nel garage c'è il riavvio con i tre tasti, poi arriva la Spinta e si esce dal lucernario prima che gli Esattori sfondino la porta. Ci sono le ripartenze ai cartelli, il pilota automatico che lo finisce da solo in circa un minuto, e 7 test.

**Fatto il 6 novembre 2026:** GIG col braccio morto. Finché il braccio è bloccato ha uno sprite suo, `gig_spento`: il braccio sinistro pende spento e lo muove una simulazione, con la gravità e il moto del corpo. Nell'arena combatte con la sola destra: diretto, diretto e, se i due colpi vanno a segno, la mazza, cioè il braccio morto sollevato con la destra e abbattuto sul nemico. Niente prese né calcio in salto.

**Il resto della tappa:** il messo, l'inseguimento nella fuga, la Vista e il primo registro nascosto, le scene vere al posto delle vignette provvisorie (vedi la tappa N), poi la prova col pad.

### N. Regia delle scene

Il gioco non è tutto gameplay. Luigi, 6 novembre 2026: «la parte narrativa è importante». Servono filmati di presentazione e d'intermezzo, con i personaggi che parlano, le presentazioni dei boss, immagini animate e primi piani d'effetto.

Lo stile è misto:
- i murales di Totò, animati, per l'introduzione, i ricordi e i passaggi fra i capitoli;
- le scene nel motore, con le bande nere e i primi piani grandi, per gli Esattori, i boss e le battute brevi.

Le parti del lavoro:
- **Il lettore delle scene.** Un formato di dati per ogni scena (inquadrature, livelli d'immagine, movimenti di camera, battute, suoni e musica) e il nodo che lo riproduce. Le battute avanzano a pressione. Durante una scena la simulazione si ferma, come nella pausa, quindi replay e test non cambiano. 14-20 ore.
- **I testi.** Le battute non stanno nel repo pubblico: stanno in una cartella privata che entra solo nella build. La demo web ha quelle del prologo.
- **I primi piani.** Partono dal nostro render 3D del volto, passato all'AI per lo stile dei murales; palpebre, bocca e luci le animano gli script.
- **La musica delle scene,** con Suno. 3-5 ore.

**È finita quando** le scene del prologo sostituiscono le vignette provvisorie, avanzano a pressione e i test passano.

**Fatto il 6 novembre 2026:**
- la sceneggiatura del prologo e del capitolo 1 è approvata, con la scaletta di tutti i filmati e i passaggi fra i capitoli; i testi stanno nella cartella privata;
- il logo di SIDERA è scelto: lo scudo con lo scorpione dello stemma di Taranto del 1589, e un sigillo per i certificati;
- il piano dei brani delle scene è pronto per Suno;
- c'è la guida pubblica al mondo, [`mondo.md`](mondo.md).

**Prossimo passo:** le scelte sulle voci (quanta voce, sintesi vocale, pronunce), poi i primi brani con Suno.

### 3. Capitolo 1, «I tetti dei Tamburi»

Di pomeriggio, sotto la pioggia, con Totò che fa da guida. Dentro ci sono il primo registro segreto, il cibo come recupero e il murale del capitolo, che fa da mappa e da salvataggio.

**È finito quando** vale lo stesso criterio del prologo, e la durata sta fra 6 e 10 minuti.

**Fatto il 6 novembre 2026:** il livello è sulla carta, in due mappe divise dal covo di Totò: la fuga sui tetti, con la prima arena, e la strada verso la Linea fino al tramonto. Sono stimati 8-10 minuti di gioco più 3 di scene. Cadere nel vuoto costa una vita intera.

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
