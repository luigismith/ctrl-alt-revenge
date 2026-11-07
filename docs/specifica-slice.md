# Specifica dello slice verticale

Versione 3 · 4 novembre 2026, aggiornata dopo le correzioni dei verificatori: descrive i file e le regole come sono davvero nello slice. È il contratto comune tra chi produce grafica, suoni e codice dello slice. Se qualcosa qui è sbagliato o impossibile, si corregge prima questo file e poi il resto.

## 1. Obiettivo e decisioni

Uno slice giocabile del livello 1, "Sotto la Linea": un tratto di strada notturna sotto la ferrovia sopraelevata e un'arena finale. Contiene GIG, due tipi di Thug (il punk e il bruto), combattimento con peso, interfaccia, effetti sonori e un brano in loop.

Decisioni di Luigi del 3 novembre 2026:

- **Approccio C, misto, a costo zero**: tutta la grafica nasce dalla pipeline 3D → pixel e dai pack CC0 ammessi, senza ritocchi umani.
- **GIG** parte dall'aspetto della locandina di riferimento, che è generata con ChatGPT e quindi sta fuori dal repo, nella cartella privata (`ctrlaltrevenge-lab-condiviso/riferimenti-estetica/locandina-pixelart-chatgpt-2026-04-09.png`):
  - codino e barba grigi;
  - camicia da lavoro ocra aperta e fuori dai pantaloni, con le maniche arrotolate, sopra una felpa grigia con il cappuccio;
  - pantaloni oliva con la cintura scura, stivali marroni;
  - dal 4 novembre, su richiesta di Luigi, la mano destra è nuda, con una fascia blu sottile al polso: sulla locandina c'erano le fasce da boxe.

  In più ha il braccio sinistro cibernetico (metallo scuro con anelli cyan luminosi) e un occhio cyan che brilla: quello rivolto alla telecamera.
- **Genere**: picchiaduro a scorrimento con profondità, nello stile di Streets of Rage, con elementi platform leggeri: salto sopra un ostacolo pericoloso.

Direzione di Luigi del 4 novembre 2026, che vale per il gioco completo:

- **Estetica retro, tecnologia di oggi**: "non deve sembrare un gioco degli anni 90 in tutto". Le regole pixel perfect del §2 valgono per lo slice così com'è e si rivedono nello step del gameplay. Sono le regole su telecamera a passi interi, interpolazione spenta e assenza di deformazioni a runtime. Sono ammesse telecamera fluida, luci dinamiche, shader, particelle e deformazioni.
- **Genere:** un platform d'azione in 2D, mix fra Pitfall, Comix Zone, Jazz Jackrabbit e Duke Nukem 2D, con il doppio salto. Ha tre ingredienti:
  - il platform, che è la spina dorsale;
  - le arene di combattimento quando arrivano gli Esattori;
  - i puzzle di hacking con il braccio cyber.

  Luigi: "non è più un picchiaduro".
- **Storia:** introduzione e intermezzi a fumetto a schermo intero, in pixel art: i murales di Totò. La storia è privata e sta fuori dal repo pubblico.
- **Grafica, dopo la prova del cel shading.** La prova è nel laboratorio, in `prove-cel-shading`: tre giudici ciechi, voto medio 6,1 contro 5,5 della v7.
  - **Sprite:** cel a 2 toni, con un terzo tono solo dove serve ai volumi.
  - **Sfondi:** a 3 toni, senza retino.
  - **Luci:** restano quelle morbide di oggi, con un tetto ai toni chiari e il contorno scuro escluso dalla luce.
  - **Quando:** si integra insieme alla figura nuova di GIG, da ex pugile a V, in una sola rigenerazione.
  - **Il passo dopo:** volti e pugni disegnati a pixel e agganciati alle ossa, pieghe disegnate sui vestiti, pose chiave più spinte. L'effetto "render 3D" viene da lì, non dall'ombra.

Scelte tecniche già fissate:

- risoluzione 480×270 (dal 5 novembre 2026; prima era 384×216): su uno schermo 1080p sono pixel ×4;
- GIG non si specchia mai (decisione del 4 novembre 2026): braccio cyber sempre a sinistra e occhio cyber a destra, e le animazioni si rendono dal 3D per i due versi. Lo slice di oggi lo specchia ancora;
- prima Windows;
- un solo giocatore;
- musica fuori dal repo.

## 2. Motore e progetto

- Godot 4.7.2 standard con GDScript tipizzato, senza plugin. Il progetto è in `game/`.
- Le impostazioni del progetto sono scritte esplicitamente in `game/project.godot`:
  - 480×270, stretch `viewport`, aspect `keep`, scale `integer`, finestra 1440×810. La misura sta anche in `View` (`game/src/core/view.gd`), che il codice usa al posto dei numeri; un test controlla che le due coincidano;
  - filtro Nearest; snap delle trasformazioni 2D attivo, dei vertici spento;
  - renderer Mobile su Direct3D 12.
- Fisica a 60 tick al secondo, interpolazione spenta. Tutto il gameplay gira in `_physics_process`, un tick alla volta, in modo deterministico: niente `randf()` senza seme e niente tempi reali.
- L'hitstop congela i singoli attori. Non usare mai `get_tree().paused` (ferma anche la musica) né `Engine.time_scale`.
- Le azioni di input si creano da codice in `Controls` (autoload). Non assegnare azioni al tasto Shift (bug #122554 di Godot 4.7.2). La tabella dei comandi, da tastiera e da gamepad, è nel README.
- Chiudendo la pausa o CONTINUA? gli ingressi si riallineano (`PlayerInput.resync()`): un tasto ancora tenuto dal menu non diventa un attacco o un salto. RICOMINCIA ed ESCI AL TITOLO lasciano il livello fermo durante la dissolvenza.
- Bug noti da evitare:
  - AnimationTree con macchine a stati annidate: non si usa;
  - limiti di Camera2D: la telecamera calcola i limiti da sé, con posizioni intere;
  - Vulkan sulla Radeon 780M: si resta su Direct3D 12.
- Lingua del gioco: italiano. Identificatori del codice in inglese, commenti in italiano.

## 3. Scala del mondo e pseudo-profondità

- **Densità**: 60 px per metro sul piano del pavimento (`tools/sprites/camera.json` e `View.PPM`). Fino al 5 novembre 2026 erano 48: con la risoluzione nuova tutto è cresciuto del 25%, e i numeri del progetto vecchio si convertono con `floor(p × 1,25 + 0,5)`. Le misure in guardia, dai piedi alla cima della testa:
  - **GIG**: 111-112 px in guardia (113-116 nel passo) e 58-60 px di larghezza con le braccia. Dal 4 novembre 2026 ha la figura da ex pugile di cinquant'anni: forma a V, torace largo con le braccia attaccate al busto, vita non stretta, camicia che cade dritta, pantaloni asciutti. Di spalle, a 60 px/m come nei murales e negli sprite: spalle 47,5 px, busto all'ascella 32,5, vita 20,8, bacino 23,2, collo 14,5. Nella vista degli sprite: sommità del busto 28 px, bacino 24. Testa (1,45) e mani (1,8) restano ingrandite; le proporzioni stanno in `tools/sprites/chars/gig.json`;
  - **punk**: circa 114 px, 54 di larghezza;
  - **bruto**, il nemico pesante, lo supera nettamente: circa 126 px in guardia e 71 px di larghezza, con i pantaloni da lavoro blu che lo staccano dall'ocra della camicia di GIG.
- **Coordinate di ogni entità**:
  - `x` orizzontale, in px del mondo;
  - `y` è la linea dei piedi sullo schermo, cioè la profondità;
  - `h` è l'altezza dal suolo (≥ 0, verso l'alto).

  Lo sprite si disegna in (x, y − h), l'ombra in (x, y).
- **Fascia calpestabile**: y da 188 a 260.
- **Ordine di disegno**: per `y` crescente.
- **Tolleranza di profondità per i colpi**: ±12,5 px per gli attacchi di GIG, ±10 px per quelli dei nemici.
- **Direzione**: tutti gli sprite sono disegnati rivolti a destra. Verso sinistra si specchiano, insieme a hitbox, hurtbox e offset.

## 4. Formato degli sprite

È il contratto tra grafica e codice. Ogni personaggio ha una cartella `game/assets/sprites/<id>/` con questi file:

- `<id>.png`: atlante RGBA con i fotogrammi impacchettati, senza spazio sprecato oltre 1 px di margine; al massimo 30 colori. Dal 4 novembre 2026 gli sprite sono in cel shading (blocco `pixel_cfg.cel` dei JSON in `tools/sprites/chars/`): due toni per materiale, ombra e luce, più un terzo tono solo dove serve ai volumi (tono medio su giacca e pelle, e sui pantaloni di GIG; luce piena sui pantaloni dei nemici; riflesso sul metallo del braccio cyber). GIG ha 26 colori, punk e bruto 20.
- `<id>_n.png` (opzionale, campo `normal_image` del JSON): atlante delle normali per le luci dinamiche, stesso impacchettamento e stessa misura di `<id>.png`. RGB = 0,5 + 0,5 × normale (x verso destra, y verso l'alto, z verso chi guarda: la convenzione delle `CanvasTexture` di Godot 4), alfa uguale a quella dell'atlante dei colori. Sul contorno la normale punta verso l'esterno (luce di taglio). La produce la pipeline dal G-buffer, a costo zero; nel cel le normali sono lisciate dentro ogni parte del corpo, quindi la luce segue i volumi grandi.
- `<id>.json`, con questa struttura:

```json
{
  "id": "gig",
  "format": 1,
  "image": "gig.png",
  "pixels_per_meter": 60,
  "animations": {
    "jab1": {
      "loop": false,
      "frames": [
        {"rect": [0, 0, 88, 120], "anchor": [38, 116], "ticks": 3,
         "hurt": [[-14, -108, 28, 108]], "hit": [], "events": ["sfx:whoosh_light"], "tags": [], "dx": 0},
        {"rect": [88, 0, 110, 120], "anchor": [38, 116], "ticks": 2,
         "hurt": [[-14, -108, 28, 108]], "hit": [[18, -83, 38, 15]], "events": [], "tags": ["active"], "dx": 1}
      ]
    }
  }
}
```

**Campi di ogni fotogramma:**
- `rect`: [x, y, w, h] nell'atlante.
- `anchor`: il punto a terra fra i piedi, in pixel dentro `rect`.
  - Nei salti e nel calcio volante l'ancora tiene il bacino all'altezza della guardia: le gambe raccolte salgono, quindi l'ancora può stare sotto `rect`.
  - Nelle cadute, nel rialzo e in `thrown` l'ancora è il punto a terra sotto il bacino.
- `ticks`: durata a 60 tick al secondo.
- `hurt` e `hit`: box [x, y, w, h] relativi all'ancora, con il personaggio rivolto a destra; y negativo vuol dire sopra il suolo. `hit` è vuoto quando il colpo non è attivo.
  - Gli sprite mettono le `hurt` su busto e testa; `hurt_low` ha anche le gambe. Le regole con cui il gioco completa il volume colpibile sono al §5.
- `events`: stringhe che scattano quando il fotogramma inizia:
  - `sfx:<nome>`;
  - `fx:<nome>`: la polvere (`dust_*`) nasce ai piedi, gli altri effetti al centro della prima hitbox del fotogramma (senza hitbox, all'altezza del petto);
  - `glint` (lampo che annuncia un attacco caricato);
  - `step` (passo): il codice alterna `step_a` e `step_b`; i passi dei nemici suonano 6 dB più bassi.

  Alcuni suoni e polveri li fa il codice e non stanno negli sprite: salto (`jump`), presa (`grab`), proiezione (`throw`), corpo che cade (`body_fall`, `body_thud`), polvere dell'atterraggio. Il codice suona `land` e i whoosh degli attacchi solo se la clip non ha già l'evento.
- `tags`:
  - `active`: hitbox attiva;
  - `cancel`: finestra in cui, se il colpo è andato a segno, si concatena la mossa successiva;
  - `invuln`;
  - `armor`: non si interrompe con i colpi leggeri;
  - `hold`: fotogramma tenuto dal codice, per esempio a terra;
  - `air`.

  Hanno `hold` sull'ultimo fotogramma `jump_rise`, `jump_fall`, `air_kick`, `knock_air`, `knock_down`, `grab_hold` e `grabbed`; `thrown` lo ha sul fotogramma 1 (vedi sotto). `air_kick` resta sul fotogramma `hold` finché GIG è in aria; all'atterraggio il codice fa i 6 tick di recupero con `land`.
- `dx`: spostamento in avanti in px quando il fotogramma inizia (root motion), opzionale.
- `dy`: spostamento verso l'alto in px quando il fotogramma inizia (root motion verticale delle mosse platform, per esempio salire su una sporgenza), opzionale. Lo slice lo legge ma non lo usa ancora.
- `points` (opzionale): punti del fotogramma relativi all'ancora, con il personaggio rivolto a destra, come le box: `fist_l`, `fist_r` (punte dei pugni), `foot_l`, `foot_r` (punte dei piedi), `head` (centro della testa), `grip` (in mezzo alle mani: serve ad allineare le mani a una sporgenza o a un cavo). Esempio: `"points": {"fist_l": [24, -70], "grip": [10, -66]}`.
- Negli eventi, `fx:<nome>@<punto>` fa nascere l'effetto in quel punto del fotogramma (per esempio `fx:cyber_spark@fist_l`, la scarica del doppio salto al pugno cibernetico); se il punto manca vale la regola normale degli effetti.

**Mosse a coppie (presa, ginocchiate, proiezione).** I fotogrammi di GIG `grab_hold`, `knee` e `throw` hanno in più un campo `victim` con una voce per ogni tipo di nemico:

```json
"victim": {"thug_punk": [6, 0, "kneed", 1], "thug_bruiser": [9, 0, "kneed", 1], "behind": false}
```

- Ogni voce vale: ancora della vittima = ancora di GIG + (dx, dy), con il personaggio rivolto a destra, e la vittima mostra quel fotogramma della sua animazione.
  - `dx` sposta davvero la vittima; `dy` è solo uno scostamento di disegno: la vittima resta alla profondità di GIG.
- `behind: true` vuol dire che la vittima va disegnata dietro GIG in quel fotogramma.
- Gli offset vengono da `author.py`, ricalcolati per ogni corpo (`tools/blender/char_poses.py`).
- **Proiezione.** `throw` non ha fotogrammi `active`: il rilascio avviene al tick 8 (fine dell'avvio), senza evento, all'inizio del fotogramma 2. In quel momento la vittima parte dal `dx` della sua voce (circa 38 px), dove è già disegnata con `thrown` 0, e da lì riproduce `thrown` dall'inizio.
- **Ordine di `thrown`** nei nemici: 0 rilasciato, 1 in volo (`hold`, `air`), 2 afferrato, 3 sollevato. Dopo il rilascio si vedono solo 0 e 1; il 2 e il 3 compaiono solo durante la presa, tramite `victim`.
- **Proiezione all'indietro** (attacco più la direzione opposta): GIG si gira quando la clip arriva al fotogramma 1, con la vittima sollevata sopra la testa, così la vittima atterra dall'altra parte senza salti.

**Animazioni in più (prova delle mosse platform):** l'atlante di GIG contiene anche `double_jump`, `ledge_hang`, `ledge_climb`, `slide`, `crouch`, `crouch_walk`, `wall_slide`, `wall_run` e `air_dash` (camminata accovacciata e mosse sui muri, aggiunte il 5 novembre 2026). Il gioco dello slice non le usa: le usa la stanza di prova. Il validatore le segnala come avvisi, non come errori.

**Animazioni richieste**, con nomi esatti:

| Personaggio | Animazioni |
|---|---|
| GIG (`gig`) | `idle` (guardia, loop), `walk`, `run`, `jump_rise`, `jump_fall`, `land`, `jab1`, `jab2`, `hook`, `kick` (finale), `air_kick`, `grab_hold`, `knee`, `throw`, `hurt_high`, `hurt_low`, `knock_air`, `knock_down` (a terra, `hold`), `getup` |
| Punk (`thug_punk`) | `idle`, `walk`, `jab`, `haymaker`, `hurt_high`, `hurt_low`, `knock_air`, `knock_down`, `getup`, `grabbed`, `kneed`, `thrown` |
| Bruto (`thug_bruiser`) | `idle`, `walk`, `punch`, `hurt_high`, `hurt_low`, `knock_air`, `knock_down`, `getup`, `grabbed`, `kneed`, `thrown` |

La morte usa `knock_down` più un lampeggio gestito dal codice.

Il fotogramma 0 di `knock_air` è un contraccolpo all'indietro (posa scritta, `knock_recoil` in `char_poses.py`): testa e busto indietro, baricentro dietro l'ancora. Il corpo è respinto e non si piega verso chi colpisce durante l'hitstop.

**Ritratti per l'interfaccia**: `game/assets/ui/portraits/<id>.png`, 32×32, dal render del volto.

**Oggetti di scena** (§6): `game/assets/props/<id>.json` oppure `game/assets/props/<id>/<id>.json`, stesso formato.
- `bin`: `idle`, `hit` (con `sfx:bin_hit`), `break` (con `sfx:bin_break`, ultimo fotogramma `hold`).
- `apple`: `idle`; la `hurt` è l'area di raccolta.
- `cable`: `idle` in loop di 6 fotogrammi, con `sfx:zap` sul primo (il codice lo suona a -12 dB e solo se il cavo è vicino allo schermo). L'ancora è dove il cavo che pende dal palo del fondale tocca terra, e il codice la posa in x 1563, y 188. Nei fotogrammi 0 e 3 c'è il lampo: archi bianco-azzurri di 16-24 px e la luce sull'acqua e sull'asfalto intorno, già dipinta nell'immagine (più larga della pozza per l'alone).

**Segnaposto**: se manca lo sprite vero il codice usa `game/assets/sprites/_placeholder/<id>.json`, e se manca anche quello disegna rettangoli di debug. Così il gioco resta giocabile.

## 5. Tempi e valori di combattimento

Tick a 60 Hz. Sono valori di partenza: si tarano con le prove di Luigi. Stanno in `game/data/attacks/*.tres` (risorse `AttackData`), non nel codice.

| Mossa | Avvio | Attivo | Recupero | Danno | Hitstop attaccante/vittima | Effetto |
|---|---|---|---|---|---|---|
| GIG `jab1` | 3 | 2 | 9 | 4 | 5/7 | stordimento 14 |
| GIG `jab2` | 3 | 2 | 9 | 4 | 5/7 | stordimento 14 |
| GIG `hook` (gancio cyber) | 6 | 3 | 12 | 7 | 7/9 | stordimento 18 |
| GIG `kick` (finale) | 10 | 3 | 20 | 12 | 9/12 | atterra; lancio 212,5 px/s in avanti e 275 px/s in alto, gravità 1125 px/s² |
| GIG `air_kick` | 4 | 8 | 6 all'atterraggio | 8 | 6/8 | atterra |
| GIG `knee` (in presa) | 4 | 3 | 10 | 6 | 6/8 | — |
| GIG `throw` | 8 | — | 14 | 14, più 8 a chi viene colpito dal corpo | 11/11 | proiezione |
| Punk `jab` | 18 | 4 | 18 | 5 | 5/7 | stordimento 14 |
| Punk `haymaker` | 33 (lampo al tick 20) | 4 | 28 | 10 | 8/10 | atterra |
| Bruto `punch` | 26, con `armor` | 5 | 26 | 12 | 8/10 | atterra |

**I tempi dell'AttackData vincono su quelli del JSON.** Le animazioni d'attacco vengono ritemporizzate perché avvio, attivo e recupero durino esattamente i tick della tabella:
- i fotogrammi prima del primo `active` fanno l'avvio, quelli `active` l'attivo, gli altri il recupero; i tick si distribuiscono in proporzione alla durata scritta nel JSON;
- nelle mosse in aria (`air_kick`) i fotogrammi dopo l'attivo restano come sono;
- una mossa senza fotogrammi `active` (`throw`) si divide alla quota avvio / (avvio + recupero) della durata del JSON, senza perdere fotogrammi.

**Regole della combo:**
- Il tasto attacco concatena `jab1 → jab2 → hook → kick` solo se il colpo precedente è andato a segno; a vuoto ripete `jab1`.
- Buffer di input: 8 tick, contando il tick della pressione.
- Massimo 3 punti di giocoleria.
- Il KO finale di ogni ondata congela tutto per 26 tick, poi 0,4 s al 35% della velocità. Per tutti i 50 tick della sequenza i lampeggi (invulnerabilità, sparizione) restano sulla fase visibile; la vittima è bianca nei primi 4 tick del congelamento, poi alterna colori normali e bianco ogni 4 tick.

**Volume colpibile.** Le `hurt` degli sprite coprono busto e testa; il gioco le completa così:
- in piedi si è colpibili fino ai piedi: se le box del fotogramma finiscono sopra il suolo, si aggiunge sotto il busto un riquadro per le gambe (altrimenti l'affondo basso del punk non colpirebbe mai);
- durante lo stordimento e la presa resta anche il volume in piedi (le box del fotogramma 0 di `idle`), così una combo iniziata non passa sopra la posa piegata;
- a terra, nel rialzo e in volo valgono solo le box del fotogramma.

**Reazioni ai colpi:**
- un colpo che prende un combattente in aria (salto, calcio volante), anche leggero, lo atterra, come in Streets of Rage;
- lampo bianco sulla vittima per 2 tick;
- lo sprite trema, la hurtbox no;
- tremolio dello schermo solo per colpi pesanti, KO e proiezioni: massimo 6 px, solo traslazione, decadimento 1,5 al secondo.

**Valori dei personaggi:**
- **Vita**: GIG 120, punk 48, bruto 110. GIG ha 3 vite. Se perde l'ultima a zona già liberata (KO quasi insieme a quello dell'ultimo nemico) rientra senza CONTINUA? e il livello finisce lo stesso.
- **Invulnerabilità dopo il rialzo**: GIG 60 tick, nemici 20.
- **Movimento di GIG**:
  - camminata 1,875 px per tick in orizzontale e 1,25 px per tick in profondità;
  - corsa con doppio tocco della direzione entro 12 tick, a 3,75 px per tick;
  - salto con velocità iniziale 5,5 px per tick e gravità 0,325 px per tick².
- **Presa automatica**: scatta quando GIG cammina contro un nemico entro 22,5 px in orizzontale e 5 px in profondità, se il nemico non sta attaccando, non è in aria e non è a terra.
  - Dalla presa: attacco = ginocchiata (al massimo 2); il terzo attacco, oppure attacco più la direzione opposta, = proiezione.
  - Dopo 90 tick il nemico si libera.
  - La vittima scivola fino all'offset della voce `victim` (circa 38 px) in 4 tick, senza scatti. Vicino ai muri GIG arretra, così la coppia resta dentro; la proiezione rilascia la vittima sempre dentro i muri.
  - Una ginocchiata che manda KO chiude la presa: la vittima vola via con `knock_air`.
  - Un colpo subito fa ripartire la combo da `jab1`.
- **Punteggio**:
  - per colpo: jab 10, gancio 20, calcio 50, ginocchiata 30, calcio in salto 30, proiezione 100, corpo proiettato che colpisce un altro nemico 50 (con 8 di danno e atterramento);
  - per KO: punk 500, bruto 1000.
- **Fine di un'ondata**: quando l'ultimo nemico è sparito, cioè dopo la caduta e il lampeggio, non appena va KO. Solo allora compaiono "VAI ▶" o "ZONA LIBERATA". Dopo l'ultima ondata la telecamera resta ferma sull'arena.

**Intelligenza dei nemici:**
- Un `AttackDirector` (autoload) dà il permesso di attaccare a un solo nemico alla volta, con almeno 0,35 s fra due attacchi nemici qualsiasi e 0,6-1,0 s fra due attacchi dello stesso nemico (erano 1,2-2,0 s: Luigi, 4 novembre 2026, li ha voluti molto più aggressivi).
- Chi aspetta resta a 50-80 px da GIG (il bruto a 55-82), fuori dalla sua corsia, e si sposta di lato.
- Il gancio caricato del punk si annuncia con il lampo (`glint`).
- Il bruto è lento e pesante: non si ferma per i jab durante l'avvio del pugno e tiene il turno d'attacco finché il pugno non finisce. Il pugno avanza con il corpo (dx dei fotogrammi): la distanza d'attacco dell'IA ne tiene conto.
- Un nemico che entra da fuori schermo diventa colpibile solo dentro i muri invisibili.

## 6. Livello "Sotto la Linea"

Mondo largo 2400 px, cioè 5 schermate. La telecamera segue GIG su posizioni intere, con zona morta di ±30 px e velocità massima di 5 px per tick; l'altezza della telecamera è fissa. I muri invisibili stanno a 32,5 px dai bordi della vista e del livello (mezza larghezza di uno sprite in guardia più 2), così nessuno resta tagliato a metà dal bordo dello schermo.

| x | Contenuto |
|---|---|
| 0-480 | Partenza; cartello "1 · SOTTO LA LINEA" (immagine dell'interfaccia, non dello sfondo) |
| 720-1200 | Ondata 1, con la telecamera bloccata: un punk |
| 1313 | Bidone dell'immondizia da rompere; dentro c'è una mela (+30 di vita) |
| 1538-1588 | Ostacolo da saltare: cavo dell'alta tensione strappato in una pozzanghera; scintille animate, 10 di danno e atterramento |
| 1920-2400 | Arena sotto i piloni della ferrovia, con la telecamera bloccata: un punk e un bruto, il bruto entra 3 s dopo |
| fine | "ZONA LIBERATA", poi la schermata di fine demo |

Fra un'ondata e l'altra compare la freccia "VAI ▶". Le ondate, il punto di partenza di GIG e gli oggetti di scena sono descritti in `game/data/levels/sotto_la_linea.json`.

**Atmosfera:**
- sera di Wind Day: il vento porta la polvere rossa del minerale e non piove (7 novembre 2026);
- una luce rosso-arancio sui piani dipinti, che lascia viola le ombre; neon rossi e arancioni, e il cyan solo per GIG;
- asfalto scuro con le pozze orlate di fango rosso (il fondale si sta rifacendo partendo da basi di ChatGPT);
- la ferrovia sopraelevata in primo piano in alto.

**Sfondi** in `game/assets/env/sotto_la_linea/`: un PNG per piano più `layers.json`:

```json
{
  "format": 1,
  "level_width": 2400,
  "floor_band": [188, 260],
  "layers": [
    {"name": "sky", "image": "sky.png", "scroll": 0.0, "y": 0, "repeat_x": 0, "z": -100},
    {"name": "far", "image": "far.png", "scroll": 0.125, "y": 33, "repeat_x": 0, "z": -90, "emissive": "far_emis.png"},
    {"name": "mid", "image": "mid.png", "scroll": 0.25, "y": 18, "repeat_x": 0, "z": -80, "emissive": "mid_emis.png"},
    {"name": "near", "image": "near.png", "scroll": 0.5, "y": 0, "repeat_x": 0, "z": -70, "emissive": "near_emis.png"},
    {"name": "backdrop", "image": "backdrop.png", "scroll": 1.0, "y": 0, "repeat_x": 0, "z": -20, "emissive": "backdrop_emis.png"},
    {"name": "floor", "image": "floor.png", "scroll": 1.0, "y": 162, "repeat_x": 0, "z": -10, "emissive": "floor_emis.png"},
    {"name": "fg", "image": "fg.png", "scroll": 1.25, "y": 0, "repeat_x": 0, "z": 100, "emissive": "fg_emis.png"}
  ]
}
```

È il `layers.json` vero dello slice: sette piani, nessuno ripetuto.

- `scroll` è il fattore di parallasse, `y` lo scostamento verticale in px dello schermo. Le posizioni sono `-round(telecamera × scroll)`: con passi interi nessun pixel trema.
- `repeat_x` è il periodo di ripetizione in px; 0 vuol dire che il piano non si ripete.
- `emissive` (opzionale) è una maschera disegnata in modalità additiva, per bagliori e sfarfallio dei neon (il codice fa sfarfallare tre gruppi di colonne).

**Luci dinamiche** (direzione del §1: tecnologia di oggi). Il JSON del livello ha un elenco `lights`, una luce per riga: `{"kind", "x", "y", "color", "energy", "radius", "height"}` in coordinate del mondo (`height` in px, per la normal map; `lamp` ha anche `scroll`). Tipi:
- `neon`: le insegne dello sfondo (posizioni e colori presi dai gruppi luminosi di `backdrop_emis.png`), con la stessa pulsazione lenta dei neon;
- `lamp`: le lampade al sodio della travata `fg`, che si spostano con la sua parallasse (1,25);
- `cable`: la luce del cavo nel rivolo del pluviale (1565,232), accesa nei fotogrammi del lampo (0 e 3 del ciclo), di un bianco lavanda (#d8c8ff); le scintille sono viola e arancio, perché il cyan spetta a GIG.

Il JSON ha anche `"weather": "wind_day"` e `beacons`, le luci della torre sul piano `far` che lampeggiano in sincrono. Il lampo del temporale (`lightning`) non c'è più.

Le luci illuminano solo gli attori con la normal map (maschera `Fighter.LIGHT_MASK_ACTORS`), mai gli sfondi, che hanno la luce già dipinta. La luce è a 3 bande (come le ombre della pixel art): sul bordo della sagoma arriva il colore della luce, dentro schiarisce senza cambiare tinta, così l'ocra di GIG non vira. Sui colori chiari conta meno (× 1 − 0,6 × la luminanza del colore: barba, capelli e scintille non bruciano) e il contorno scuro, con le linee interne dello stesso colore, ne resta fuori come l'inchiostro. Sono solo disegno e non toccano la simulazione: replay e hash non cambiano. F5 le accende e spegne (build di debug); `--no-lights` parte spento.
- Dal 7 novembre 2026 `backdrop`, `near` e `fg` partono da basi fatte con ChatGPT, guardando i Tamburi veri (il bordo nord-ovest del quartiere, verso le collinette), e diventano pixel art con `tools/ambienti/componi_slice.py`, che fa anche le maschere emissive. Il `floor` è quello di prima, con una velatura di minerale a grani (`tools/ambienti/patina_floor.py`). Nella fascia calpestabile i riflessi restano più scuri, per non confondersi con gli stivali.
- I piani a fattore 1,0 coprono tutti i 2400 px. Quelli più lenti coprono almeno `480 + 1920 × scroll` px, oppure si ripetono: far 720, mid 960, near 1440; `fg` (1,25) è largo 2880 px.
- I piani con `z` < 0 stanno dietro agli attori, quelli con `z` ≥ 0 davanti.
- `backdrop` (facciate, alto 187 px) e `floor` (da y 162: contiene anche la base delle cose basse davanti alle facciate) non si sovrappongono. `fg` è la travata del viadotto vista dal basso, con lampade al sodio piatte attaccate sotto: resta sopra y 33, perché le insegne del fondale stanno fra y 34 e 56 e devono leggersi a telecamera ferma, e non copre la fascia calpestabile.
- I piani `sky`, `far` e `mid` (il cielo del Wind Day, la torre e le cupole, i Tamburi di notte) li disegna a codice `tools/env/taranto.py` (`--mid` per il piano dei palazzi). `tools/env/build_all.py --install` rifà solo il bidone e la mela.

**Oggetti di scena**, in `game/assets/props/`: bidone (intero, colpito, rotto), mela, cavo con scintille (6 fotogrammi). Ognuno ha un JSON con lo stesso formato degli sprite (dettagli al §4). Il bidone è in x 1313, y 200; la pozzanghera del cavo va da x 1528 a 1603 su tutta la fascia ed è un'unica forma irregolare che in ogni riga copre la zona del danno (x 1538-1588).

## 7. Effetti visivi, interfaccia, suoni

**Effetti** in `game/assets/fx/`, ognuno con un PNG a strisce più `fx.json`:

```json
{"hit_spark_light": {"image": "hit_spark_light.png", "frame": [24, 24], "count": 4, "ticks": 2, "anchor": [12, 12]}}
```

Servono `hit_spark_light`, `hit_spark_heavy`, `dust_land`, `dust_skid`, `glint`, `cyber_spark` (per il gancio cyber) e `ombra` (ellisse). Se uno manca, il codice lo disegna da sé.

Campi in più di `fx.json`:
- `mode`: `anim` (striscia animata) oppure `variants` (fotogrammi alternativi, non un'animazione);
- `flip`: l'effetto è asimmetrico e va specchiato con la direzione del colpo (il codice specchia comunque tutti gli effetti secondo la direzione);
- `ombra` ha tre varianti: 0 grande (58×12, bruto e corpi a terra), 1 media (44×10, GIG e punk), 2 piccola (30×8, oggetti). Il codice sceglie dalla larghezza dell'ombra del personaggio e passa a quella più piccola sopra i 45 px d'altezza; si disegna a 1x in (x, y), prima dello sprite.

Effetti in più: `rain_streak` (quattro gocce lunghe 7, 10, 13 e 16 px, pendenza 0,25), `rain_splash` (schizzo a terra), `rain_sheet` (tessera di pioggia 128×128, facoltativa, non usata) e `ko_flash` (lampo del KO finale di un'ondata). Dal 7 novembre 2026 nello slice e nel titolo non piove: c'è il Wind Day (`game/src/fx/wind_day.gd`), con la polvere su tre piani, le raffiche ogni 4-8 s, la tinta rossa e le pozze. È solo disegno, con un generatore suo: replay e hash non lo vedono.

**Interfaccia** in `game/assets/ui/`, descritta da `ui.json` (una chiave per elemento, con `image` e `size`):
- `logo` e `subtitle`: il logo "CTRL+ALT REVENGE!" con riempimento crema e bordo rosso scuro, come la locandina, e la scritta "PICCHIA DURO A SCORRIMENTO";
- scritte grandi già disegnate, da usare a 1x centrate su coordinate intere: `stage_card_1` ("1 · SOTTO LA LINEA"), `msg_zone_clear`, `msg_pause`, `msg_continue`, `msg_game_over`, `msg_demo_end`;
- `go_arrow`: striscia di 3 fotogrammi da 56×24, 8 tick ciascuno, in ciclo;
- `big_digits`: le cifre 0-9 grandi nello stile delle scritte `msg_*`, striscia di 10 fotogrammi da 23×31 (il fotogramma k è la cifra k), per il conto alla rovescia di CONTINUA?. Tutte le scritte stanno a 1x: niente testo del font a scala 2;
- `portrait_frame` (e `portrait_frame_enemy`): cornice 34×34 con il foro 32×32 in (1, 1); si disegna `portrait_back`, poi il ritratto in (x + 1, y + 1), poi la cornice;
- barre: `bar_back`, `bar_ghost`, `bar_fill` e `bar_frame` (108×10, interno 104×6), con le varianti `_enemy` (cornice 108×8, interno 104×4). I pezzi si ritagliano da (0, 0, larghezza, altezza); la cornice va sopra, in (x − 2, y − 2);
- chiavi che non sono immagini: `fonts`, `colors` (colori dei testi) e `hud_layout` (posizioni dell'HUD in coordinate dello schermo).

**Font**: CAR Pixel, disegnato da noi (`tools/fxui/`), regolare e grassetto, in `game/assets/fonts/` con `font.json`. Ha tutte le lettere accentate italiane. Si usa a 12 px (ascendente 10, discendente 2), senza antialiasing e con hinting "Nessuno": il `.ttf.import` lo imposta e `UiFont` lo forza anche da codice, perché con l'hinting leggero predefinito gli accenti del regolare si spostano di un pixel. Il grassetto serve per nomi, punteggio e menu, il regolare per i testi lunghi (crediti e licenze).

**HUD** in stile Streets of Rage 2:
- in alto a sinistra: ritratto, nome, barra della vita e vite di GIG;
- sotto, la barra del nemico colpito per ultimo, con il suo nome ("PUNK", "BRUTO");
- in alto a destra, il punteggio a 6 cifre.

**Suoni** in `game/assets/sfx/<nome>.wav`: mono, 16 bit, 44,1 kHz. Dal 5 novembre 2026 li monta `tools/audio/sfx_pack.py` da suoni già pronti CC0 e CC BY, con le fonti in `THIRD-PARTY-NOTICES.md`; prima erano sintetizzati da `tools/audio/sfx_gen.py`. Nomi:
- colpi e movimenti: `whoosh_light`, `whoosh_heavy`, `hit_light`, `hit_medium`, `hit_heavy`, `hit_kick`, `knee`, `grab`, `throw`, `body_fall`, `body_thud`, `step_a`, `step_b`, `jump`, `land`, `glint`;
- scena: `zap` (cavo), `bin_hit`, `bin_break`, `pickup`, `ko`;
- interfaccia: `ui_move`, `ui_confirm`, `ui_pause`, `go_arrow`;
- stanza di prova: `block` (la parata dell'esattore), `hack` (il pugno cyber sulla centralina).

Accanto ai WAV:
- i `.wav.import` li importano in PCM, senza compressione e senza loop;
- `mix.json` (`{"format": 1, "gain_db": {"<nome>": dB, ...}}`) dà il guadagno di missaggio di ogni suono: i file hanno tutti il picco a -1 dBFS, il bilanciamento sta lì.

Bus (`game/default_bus_layout.tres`): `Master` con un limitatore (`AudioEffectHardLimiter`, tetto -0,5 dB), `Music` a -6 dB, `SFX` a 0 dB. All'avvio `Sfx` crea come figli di `SFX` i bus del pan `SFX_L2`, `SFX_L1`, `SFX_R1` e `SFX_R2`. Un menu delle opzioni dovrà regolare il volume dei bus `Music` e `SFX`, non quello dei player.

Interfaccia degli autoload:
- `Sfx.play(nome, jitter = 0.05, volume_db = 0.0)` e `Sfx.play_at(nome, x_del_mondo, ...)`, che aggiunge un leggero pan secondo la posizione sullo schermo (ricavata dalla Camera2D della viewport principale). Dodici voci; lo stesso suono chiesto due volte nello stesso tick suona una volta sola; un suono mancante dà al massimo un avviso.
- `Music.play(id)`, `Music.stop()`, `Music.set_layer(id_strato, acceso)`, `Music.play_jingle(id)`, `Music.duck(acceso)`, `Music.has_track(id)`, `Music.current_track()`. `play()` del brano già in corso non lo fa ripartire ma spegne i suoi strati; il titolo e il livello tolgono l'abbassamento all'avvio (dopo un GAME OVER la musica era ancora abbassata). Il livello chiama `play(&"stage1")` all'inizio, `set_layer(&"arena", true)` quando parte l'ondata dell'arena e `play_jingle(&"clear")` a "ZONA LIBERATA"; il titolo chiama `play(&"title")`; pausa e CONTINUA? abbassano la musica con `duck`; il game over la ferma. Le scene nel motore chiedono `Music.has_track(id)` e `Music.current_track()`: se c'è il brano della scena lo suonano e alla fine rimettono quello di prima, altrimenti abbassano la musica con `duck`.
- `Sfx.silence()` e `Music.silence()` fermano tutto prima di chiudere il gioco (`Game.quit_clean()`, vedi §10).

**Musica**: mai nel repo (vedi `LICENSES/` e README). L'autoload `Music` cerca i file in quest'ordine:
1. `res://assets_private/music/`;
2. la cartella `music/` accanto all'eseguibile;
3. `%USERPROFILE%/ctrlaltrevenge-lab/music/`, solo durante lo sviluppo: le build esportate (feature `template`) non la cercano.

Vince la prima cartella con un `music.json` valido e almeno un brano il cui file esiste. Senza musica il gioco resta muto e non dà errori. Gli id dei brani sono `title`, `stage1` (con lo strato facoltativo `arena`, file `stage1_arena.ogg`) e `clear`.

Formato di `music.json` (lo scrive `tools/audio/prepare_music.py`):

```json
{"format": 1, "tracks": [
  {"id": "stage1", "file": "stage1.ogg", "loop": true,
   "loop_start": 67.73, "loop_end": 173.38, "loop_start_sample": 2987012, "loop_end_sample": 7646245,
   "sample_rate": 44100, "bpm": 149.93, "bar_beats": 4, "gain_db": 0.0,
   "layers": [{"id": "arena", "file": "stage1_arena.ogg", "gain_db": 0.0}],
   "placeholder": true, "source": "..."}
]}
```

- I tempi sono in secondi; i campioni, se ci sono, sono esatti e vincono.
- Gli OGG sono tagliati alla fine del loop e ripartono da `loop_start`. Un brano con strati diventa un `AudioStreamSynchronized`: gli strati partono muti e `set_layer` li accende con una dissolvenza di 0,8 s (accetta anche l'id lungo `stage1_arena`).
- `placeholder: true` segna la musica segnaposto: oggi brani CC0 di Safety Stoat Studios, solo nel laboratorio. I brani di Suno si preparano con `prepare_music.py` (comandi in `tools/audio/LEGGIMI.md`).

## 8. Struttura del repo

```
game/                 progetto Godot
  project.godot
  export_presets.cfg  preset "Windows Desktop" (vedi sotto)
  default_bus_layout.tres  bus Master, Music e SFX (§7)
  scenes/             scene .tscn (minime: i nodi si costruiscono soprattutto da codice)
  src/core/           Game, Controls, flusso delle schermate, opzioni della riga di comando
  src/combat/         Fighter, FrameAnim, CombatSystem, AttackDirector, AttackData
  src/actors/         GIG, Thug (IA)
  src/stage/          livello, telecamera, parallasse, ondate, oggetti di scena, effetti, ombre (il Wind Day sta in src/fx/)
  src/ui/             HUD, titolo, pausa, game over, fine demo, crediti
  src/audio/          Music, Sfx
  src/debug/          sovrapposizione hitbox, replay, pilota automatico
  data/attacks/       AttackData .tres
  data/fighters/      FighterData .tres (vita, velocità, IA)
  data/levels/        sotto_la_linea.json (ondate, partenza, oggetti di scena)
  data/credits.txt    testo dei crediti
  assets/             sprites/, env/, props/, fx/, ui/, sfx/, fonts/, third_party/
  tests/              run_tests.gd, test_suite.gd, replays/*.json, galleria per Movie Maker
tools/
  blender/            script bpy delle pipeline (GPL-3.0-or-later)
  sprites/            pipeline dei personaggi (MIT): python -I tools/sprites/build_chars.py all
  env/                pipeline degli sfondi e degli oggetti (MIT): python -I tools/env/build_all.py --install
  fxui/               effetti, interfaccia e font (MIT): python -I tools/fxui/build_all.py --godot --install
  audio/              effetti sonori, preparazione della musica, prove dell'audio
  run_godot.sh        lancia Godot con timeout, log e controllo degli errori
  guard_assets.py     blocca audio e file pesanti non ammessi (--all: file tracciati e nuovi non ignorati)
docs/                 questa specifica e i riferimenti estetici
```

**Esportazione.** Il codice legge con `FileAccess` file che non sono risorse: i JSON degli asset e dei livelli, `data/credits.txt`, `assets/sfx/mix.json`. Il preset in `game/export_presets.cfg` li include (`include_filter = "*.json, *.txt, THIRD-PARTY-NOTICES.md"`) ed esclude `tests/`. Prima di esportare:
- copiare `THIRD-PARTY-NOTICES.md` della radice in `game/` (la schermata dei crediti lo legge da `res://`; durante lo sviluppo lo trova nella radice del repository);
- mettere la musica e il suo `music.json` in `game/assets_private/music/` (ignorata da git) oppure in `music/` accanto all'eseguibile;
- servono i modelli d'esportazione di Godot 4.7.2, che nel laboratorio non ci sono ancora.

**Strumenti e sorgenti fuori dal repo**, in `%USERPROFILE%\ctrlaltrevenge-lab\`, che in Python si legge con `os.environ["USERPROFILE"]`:
- `tools\godot-4.7.2\`: usare `Godot_v4.7.2-stable_win64_console.exe` per le esecuzioni da riga di comando;
- `tools\blender-4.5.15\blender.exe`;
- `sources\chars`: Quaternius UBC, UAL1, UAL2, Warped City;
- `sources\anim`: CMU, Mesh2Motion, Rokoko, e in `spike-out` i dump JSON di Mesh2Motion e le pose di `author.py`;
- `sources\env`: kit Quaternius e Kenney;
- `ricerca-2026-11-03\prove\`: gli script delle prove (`spike2-chars`, `spike-anim`, `spike-env`) da cui partire;
- `music\`: la musica (oggi segnaposto CC0) con il suo `music.json`;
- `Gioca.bat`: importa il progetto e avvia il gioco in finestra;
- `build\`: catture di Movie Maker e anteprime.

## 9. Licenze dei file

- `REUSE.toml` assegna la licenza a ogni percorso.
- **Ogni pack di terze parti** va in `game/assets/third_party/<pack>/` con questi file:
  - `SOURCE.md`: URL, nome e dimensione del file, sha256, licenza, credito, data;
  - una tabella in `REUSE.toml`;
  - una riga in `THIRD-PARTY-NOTICES.md`;
  - il testo della licenza in `LICENSES/`, per esempio `CC0-1.0.txt`.
- **Ammessi nel repo pubblico**: CC0 e CC-BY (con credito), font OFL (con OFL.txt).
- **Mai nel repo pubblico**:
  - musica Suno;
  - Mixamo, Reallusion, CraftPix, Oonquil, Shapeforms, Sonniss;
  - i file grezzi del pack Rokoko.
- **Script bpy**: vanno in `tools/blender/` con l'intestazione GPL. Il primo che si aggiunge porta con sé `LICENSES/GPL-3.0-or-later.txt`.
- **Codice nuovo**: MIT. Gli asset originali (sprite, sfondi, effetti, interfaccia, suoni, livelli) sono `LicenseRef-CAR-Assets`.

## 10. Verifica

- **Esecuzioni da riga di comando**:
  - si lanciano con `tools/run_godot.sh`, che usa l'eseguibile console, un timeout e `--log-file`; il progetto si sceglie con la variabile `GODOT_PROJECT` (predefinito `game/`), mai con un secondo `--path`;
  - una prova passa solo se il codice d'uscita è 0, se il log non contiene `SCRIPT ERROR`, `Parse Error` o `ERROR:` e se termina con la riga `DONE`.
- **Test**: `godot --headless --path game -s res://tests/run_tests.gd`; le prove dell'audio sono in `tools/audio/godot_tests/test_audio.gd` e girano anche su `game/` (comandi in `game/tests/README.md`).
- **Replay**: file JSON con gli input tick per tick, iniettati alla fine del tick precedente. Servono a verificare combo, danni, prese e ondate. Registrano solo gli ingressi: quando cambiano regole, dati o box degli sprite si rigenerano con `game/tests/make_replays.gd` (pilota automatico) e si rilanciano i test.
- **Controllo visivo**: Movie Maker con `--write-movie <percorso assoluto>/f.png --fixed-fps 60`, in una finestra visibile.
  - Il fotogramma k (contando da 0) mostra lo stato dopo il tick k del livello, cioè dopo k + 1 tick di simulazione.
  - Bisogna verificare che i fotogrammi consecutivi siano diversi.
  - Le tavole di fotogrammi si guardano ingrandite.
  - La registrazione deve finire dal gioco: `-- --replay <file> --quit-at-end` per i replay, la galleria `tests/ui_gallery.gd` si chiude da sola. Con Movie Maker l'audio si mescola solo dentro i fotogrammi registrati: se il motore esce per `--quit-after` mentre suona qualcosa, nel log compare `resources still in use at exit`. `Game.quit_clean()` prima zittisce l'audio e aspetta dieci fotogrammi. `--quit-after` resta solo come sicurezza.
