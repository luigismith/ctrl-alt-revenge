# Ambienti: dalle basi dipinte alla pixel art del gioco

Gli ambienti del prologo partono da immagini generate con l'app Gemini di Google e con ChatGPT di
OpenAI: sfondi dipinti e fogli di oggetti su fondo magenta o trasparente. Gli script di questa
cartella li portano alla scala del gioco (60 px per metro), alla palette di ogni piano e ai blocchi
della mappa. Le basi non stanno nel repository: gli originali e i prompt stanno nella cartella
privata del progetto.

## Gli script

- `pixelizza.py`: un'immagine diventa pixel art. Riduce per media d'area, cerca la palette con
  k-means in OKLab, pulisce i pixel isolati e, se serve, toglie il fondo magenta e aggiunge il
  contorno di 1 px.
- `ritaglia_kit.py`: un foglio di oggetti su magenta diventa tanti sprite, tutti alla stessa scala e
  con la stessa palette.
- `piani.py`: gli strumenti comuni a tutti i livelli:
  - la mappa;
  - i fogli e i loro oggetti;
  - l'àncora che porta un pezzo del disegno su un riquadro del piano;
  - le tinte;
  - le schermate di prova composte come nel gioco.
- `componi_prologo.py`: compone il prologo di prima (`prologo.ldtk`) e lo scrive in
  `game/assets/env/prologo/`, con il suo `layers.json`. Il cimitero di San Brunone sta qui, la fuga
  in `fuga.py`.
  - **I piani dello sfondo,** con la parallasse. Nel cimitero: il cielo con la torre e le cupole,
    tre file di cappelle, le lapidi vicine. Nella fuga: il cielo di pioggia sul Mar Piccolo, le
    palazzine dei Tamburi, il marciapiede di là con le auto.
  - **Il cambio d'ambiente.** Mentre GIG scavalca il muro del cimitero, i piani del cimitero sfumano
    uno dopo l'altro, dal più lontano al più vicino, sopra quelli della fuga. Ogni piano vale per un
    tratto della telecamera (`x_from`, `x_to`), con le sue dissolvenze (`fade_in`, `fade_out`), e
    parte da `origin_x`. Le scene del campo di gioco sono più immagini, una dopo l'altra
    (`scenes`).
  - **La scena,** cioè il campo di gioco: ogni oggetto sta sul suo blocco della mappa. Per ognuno
    si dice quale parte del disegno va sul blocco; per una tomba, per esempio, dalla metà della
    faccia di sopra alla base. Così GIG appoggia i piedi dove si vede la pietra. Se un disegno è
    più stretto del suo blocco, si ripete una campata invece di schiacciarlo.
  - **Il primo piano,** davanti a GIG e più veloce di lui: in basso le cose basse, che non coprono
    mai i suoi piedi; in alto, nella fuga, i panni stesi e i cavi; poche cose alte dove non si
    salta. È scuro, e sta sopra anche agli attori dell'arena.
- `fuga.py`: la fuga per i Tamburi e il garage della madre di GIG, in sezione. La parete di fondo
  del garage è un dipinto più piccolo della stanza: se ne prendono due pezzi alla scala giusta e il
  resto dell'intonaco si dipinge con i suoi colori.
- `componi_slice.py`, `patina_floor.py`, `cavo_rivolo.py`: la strada dello slice (vedi
  `tools/env/README.md`).
- `schermi_torre.py`: i maxischermi della torre di SIDERA.
- `titolo.py`: la schermata del titolo.

Le scene del prologo che il gioco carica oggi (`prologo_v2.ldtk`) stanno in
`game/assets/env/prologo/v2/` e non nascono da questi script: sono tavole in scala fatte nel
laboratorio da basi di ChatGPT, e gli script che le montano non sono nel repo.

Per rifare il prologo di prima:

    python -I tools/ambienti/componi_prologo.py --basi <cartella delle basi> --anteprima <cartella>

La cartella delle basi, se non la si dice, è `tools/out/ambienti/basi`, che git ignora.

Con `--anteprima` escono anche alcune schermate con GIG, composte come nel gioco; con `--uscita` i
piani si scrivono in un'altra cartella, per una prova, invece che nel gioco. Se cambiano i blocchi
di `prologo.ldtk`, si rifanno `prologo.txt` (vedi `docs/ldtk.md`) e la grafica.

## Come si appoggiano le cose

- **Tre strati, in quest'ordine.** Prima quello che sta dietro il pavimento (il muro di fondo della
  galleria, i cumuli di terra), con la base appena sotto il bordo del pavimento; poi il pavimento;
  poi le cose del piano di GIG, con la base sulla riga dove GIG posa i piedi, dentro la fascia della
  ghiaia o dell'asfalto. Se il pavimento coprisse le basi, le cose sembrerebbero sospese o più
  lontane.
- **L'ombra di contatto.** Sotto ogni cosa posata nel piano di GIG il pavimento si scurisce
  (`ground_shadow` in `piani.py`): forte sulla riga dei piedi, sfumata verso il basso e ai lati, più
  lunga a destra perché la luce viene dall'alto a sinistra. Dev'essere netta: la palette del piano si
  mangia le differenze piccole.
- **La base dentro il terreno.** Nel cimitero, posato tutto, le ultime righe di ogni cosa si
  scuriscono (`settle`) e qualche ciuffo della ghiaia passa davanti alla base, agli angoli e in mezzo
  (`tuft_stamps`, `put_tufts`). I ciuffi si prendono dal viale stesso, così hanno i suoi colori.
- **I fianchi in prospettiva.** Se il disegno mostra il fianco della base visto un poco di lato, come il
  plinto delle tombe, il fianco va più in profondità della ghiaia: sotto resta un triangolo vuoto e
  l'oggetto sembra sollevato. `square_base` porta il fianco fino a terra, in ombra.
- **La faccia di sopra sulla riga del blocco, su tutta la sua larghezza.** Dove il disegno è visto
  un poco dall'alto (un tetto, un piano di lavoro) la riga dei piedi sta a metà della faccia di
  sopra, come per il pavimento. Se il disegno non ha le proporzioni del blocco, lo si deforma poco
  (al massimo un quarto) e i fianchi che scendono vanno fuori dal blocco, non dentro.
- **Il fondo si distingue da quello su cui si salta.** Le cose di fondo, come le transenne, l'Ape
  parcheggiata e i mobili dipinti sulla parete, sono più scure, senza contorno e un poco più in là
  della riga dei piedi. Le cose su cui si sale hanno il contorno scuro, anche sopra un muro o
  l'asfalto, e si disegnano davanti alle decorazioni, così si vedono tutte. Niente che attraversi un
  buco: sembrerebbe un appoggio.
- **Continuità.** Un blocco alto è disegnato tutto, fino dove la telecamera può arrivare: colonne,
  pilastri e muri non s'interrompono. Un oggetto non si taglia a metà: il ritaglio parte dal vuoto
  del foglio, e per l'altro lato lo si specchia. I pezzi che stanno insieme, come un cancello e i
  suoi pilastri, hanno la stessa scala. Se il disegno è più corto del suo blocco, si ripete una
  fascia senza righe orizzontali (`heightened`, `widened`).
- **Le ripetizioni.** Un motivo ripetuto, come le lastre dei loculi, si taglia dentro le sue cornici,
  al passo del disegno, e senza il contorno scuro, che segnerebbe ogni giunta. Le file di sfondo
  messe una dopo l'altra hanno una palette sola, e sopra ogni giunta c'è qualcosa di verticale e
  intero, per esempio un cipresso.
- **Il magenta del fondo.** Fuori dal ritaglio conta come trasparente, così il bordo di un pezzo non
  resta viola. Nei fogli di oggetti si toglie sul foglio grande, prima di ridurlo; dove il disegno ha
  dei vuoti (grate, reti, stecche, vetri) si toglie dappertutto (`despill_all`).

## Come si controlla

- le schermate di prova, composte come nel gioco (`--anteprima`);
- le basi ingrandite a 4×: sotto i fianchi niente ghiaia chiara né sfondo;
- nessun pixel viola rimasto dal fondo magenta;
- i fotogrammi veri del gioco, col pilota automatico, prima, durante e dopo le arene;
- GIG appeso a ogni sporgenza con i piedi sopra il pavimento: dove ci si appende, lo spigolo sta
  almeno 7 blocchi sopra il pavimento sotto (i muri più bassi si scavalcano).

## Le regole

- **Prompt solo di testo, o con foto libere.** I prompt sono in inglese. A Gemini e a ChatGPT si
  caricano soltanto foto con una licenza che lo permette senza obblighi sull'immagine nuova (CC0,
  pubblico dominio, CC BY) e i nostri render. Le foto CC BY-SA o con diritti riservati si guardano
  soltanto, per scrivere i prompt. Si chiede un margine di fondo ai lati, così niente tocca il bordo
  dell'immagine.
- **Coerenza.** Ogni prompt rispetta la storia: luogo, data, ora, meteo, direzione dello sguardo.
  Per esempio, il giovedì pomeriggio del 2087 la fabbrica è ferma e non fuma niente.
- **Crediti.** Le immagini generate si dichiarano nei crediti e in `THIRD-PARTY-NOTICES.md`.
- **Personaggi e oggetti animati** non passano di qui: restano della pipeline 3D.
