# CTRL+ALT REVENGE: note per Claude

- **Riferimenti:**
  - la specifica tecnica dello slice è `docs/specifica-slice.md`;
  - la storia è `docs/lore/storia.md`;
  - la ricerca su Taranto è `docs/lore/ricerca-taranto.md`;
  - il gameplay è `docs/lore/gameplay.md`.

  Storia, ricerca e gameplay sono privati: vedi "Storia privata" più sotto.
- **Lingua:** italiano, con gli accenti giusti, per testi, commenti e messaggi di commit. Con Luigi si parla sempre in italiano, anche nei resoconti e nelle domande. I prompt per Gemini, ChatGPT e gli altri strumenti AI invece si scrivono in inglese (Luigi, 6 novembre 2026: «anzi è meglio»).

## Come lavora Luigi

Valgono su ogni PC: queste preferenze stanno qui e non solo nella memoria di un computer.

- **Domande:** una per volta, con 2-4 soluzioni proposte e la consigliata per prima (AskUserQuestion). Niente elenchi di domande aperte in fondo ai messaggi.
- **Storia:** si scrive insieme. Claude propone, Luigi decide. Le decisioni vanno in `docs/lore/storia.md`, le scene approvate in `docs/lore/sceneggiatura.md`.
- **Giudizi onesti** su grafica e gameplay, con voti rispetto a Streets of Rage 2 e i limiti detti chiaramente.
- **Non dargli ragione per farlo contento.** Luigi, 8 novembre 2026, per tutto il progetto: «lo scopo è fare un buon gioco, non darmi ragione». Vale per la regia e per ogni sessione:
  - prima di dire «hai ragione» si controllano i documenti (storia, cronologia, decisioni);
  - se una sua idea è peggiore di un'altra, o va contro una decisione già presa, lo si dice chiaro e si spiega perché;
  - un'idea nostra che lui accetta non diventa giusta per questo: se poi si scopre un problema, lo si dice.
- **Il repo pubblico deve essere stupendo.** Luigi, 4 novembre 2026: "la repo su github deve essere STUPENDA". Vale per il gioco e per la vetrina:
  - README con immagini e GIF vere del gioco;
  - documenti in ordine;
  - storia dei commit pulita;
  - niente file inutili.
- **Direzione del gioco:** un platform d'azione in 2D (Pitfall, Comix Zone, Jazz Jackrabbit, Duke Nukem 2D), con il doppio salto. Luigi, 4 novembre 2026: "non è più un picchiaduro viste le implementazioni platform, puzzle (hacking) che stiamo facendo". Tre ingredienti:
  - il platform, che è la spina dorsale;
  - le arene di combattimento alla Streets of Rage, quando arrivano gli Esattori;
  - i puzzle di hacking con il braccio cyber.

  Non chiamarlo "picchiaduro". Storia con intermezzi a fumetto: i murales di Totò, in pixel art con lo stile della street art.
- **La parte narrativa conta.** Luigi, 6 novembre 2026: «non deve essere tutto tutto gameplay, la parte narrativa è importante». Servono:
  - filmati di presentazione e d'intermezzo, con i personaggi che parlano;
  - le presentazioni dei boss prima dei combattimenti;
  - immagini animate e primi piani d'effetto.

  Senza strafare: non è un gioco di Kojima. Come si fanno (Luigi, 6 novembre 2026; decisione 68 della storia):
  - **tutto a murale** (Luigi, 7 novembre 2026; decisione 94): ogni volta che il gioco si ferma per raccontare, anche nei dialoghi, nelle presentazioni dei boss e nel finale, c'è una fila di murales animati di Totò. Nel motore restano solo le battute che non fermano l'azione (fumetti, voce di Tere, guida di Totò, maxischermi) e i passaggi fra gioco e murale;
  - **HeyGen è lo strumento per i filmati e per le voci** (Luigi, 11 novembre 2026: «i filmati di intermezzo e introduzione, falli sempre con heygen da ora in poi»; «heygen è lo strumento per i filmati e per le voci»):
    - i murales di Totò restano le immagini di partenza, e HeyGen li anima;
    - le voci dei personaggi sono voci progettate in italiano con HeyGen;
    - ogni clip si controlla prima di usarla: niente si muove all'indietro, i volti non cambiano, nessuna bocca parla a vuoto, le scritte non sono storpiate;
    - vale anche per il trailer, che può essere più bello del gioco di oggi (Luigi: «anche se non rispetterà il gioco»);
  - **i primi piani:** il nostro render 3D del volto passato a ChatGPT o a Gemini per lo stile dei murales; dall'11 novembre 2026 li anima HeyGen, come gli altri filmati (prima: palpebre, bocca e luci animate dai nostri script);
  - **le battute avanzano a pressione,** come in Celeste;
  - **ogni scena ha la sua musica,** fatta con Suno (Luigi: «mi raccomando anche alle musiche per le scene»);
  - **la regia c'è sempre,** in tutti i filmati del gioco: intermezzi, presentazioni e finale. Dove l'estetica e la regia lo chiedono servono primi piani, inquadrature strette o larghissime e cambi di inquadratura. Un filmato non è mai gameplay che va da solo (Luigi, 6 novembre 2026: «in sostanza i filmati di intermezzo, presentazione, ending, non sono mai delle sessioni di gameplay automatico»);
  - **i passaggi fra gioco e filmato sono morbidi,** nei due sensi (Luigi: «Mi raccomando alla transizione tra gameplay e filmati e viceversa»).
- **Servizi AI:** Claude si aiuta con ChatGPT, Gemini o altri servizi gratuiti tutte le volte che serve (Luigi, 6 novembre 2026). Valgono le regole sulle immagini in "Licenze e file".
- **Budget:** costo zero, a parte gli abbonamenti che Luigi ha già (Suno, ChatGPT, HeyGen): si usano, ma i loro crediti si spendono con giudizio. Sono ammessi strumenti gratuiti anche solo per uso non commerciale; di ognuno si annotano la licenza e cosa servirebbe per vendere il gioco.
- **Persone reali:** i nomi veri entrano nel gioco e nei file pubblici solo con il consenso.
  - Il MiniBar di Ignazio, il bar dei Tamburi, ce l'ha (Luigi, 4 novembre 2026).
  - Il writer che ispira Totò l'ha dato (Luigi, 5 novembre 2026): nome e tag vanno nei crediti e nel sito come omaggio, i murales hanno il suo stile. Nel gioco Totò resta un personaggio inventato e firma solo "Totò".
- **Coerenza, prima di tutto.** Luigi: "mantenere riferimenti alla città e alle ambientazioni, deve essere tutto coerente con la storia e col passare degli anni".
  - Ogni livello, sfondo, insegna, testo, oggetto e suono deve essere coerente con Taranto e i suoi luoghi veri, con la storia e con le sue epoche (le date sono nella cronologia). Deve esserlo anche con età, date, ore, meteo e luna di ogni scena.
  - I riferimenti sono `docs/lore/cronologia.md` e `docs/lore/ricerca-taranto.md`. Prima di disegnare o scrivere qualcosa di nuovo, controllali.
  - **Si deve capire che siamo nel futuro.** Luigi, 7 novembre 2026, guardando lo slice: «vedo delle ape car, delle fiat 500... ok che ce n'è qualcuna, ma non così tante... devono esserci elementi del futuro narrato». Taranto resta riconoscibile, ma ogni ambientazione deve mostrare il suo anno con gli elementi della storia e della cronologia: veicoli, insegne, schermi, ARIA+, droni, SIDERA. Le cose di oggi ci possono essere, ma poche e consumate. Lo slice fatto il 7 novembre resta com'è.
  - **È una regola generale** (Luigi, 8 novembre 2026: «mi raccomando alle ambientazioni: TARANTO riconoscibile, ma nel FUTURO, i richiami al passato sono ok, ma limitati»). Vale per ogni ambientazione nuova o rifatta: sfondi, murales, livelli, oggetti, testi e suoni. Prima di consegnare, chi la fa dice cosa rende riconoscibile Taranto e cosa dice l'anno.

- **La scala** (Luigi, 8 novembre 2026, dopo i furgoni più bassi di GIG):
  - sul piano di gioco tutto è alla scala di GIG, 60 px per metro (3 celle): porte, serrande, pianterreni e veicoli. Si può esagerare fino al 15% in più, mai in meno;
  - le palazzine intere stanno sui piani dietro, con parallasse e velo;
  - dove i salti non tornano con le misure vere si aggiungono appoggi intermedi (tettoie, purificatori ARIA+, insegne, ponteggi), meglio se del futuro;
  - ogni foglio di grafica mostra GIG accanto a una porta e a un veicolo, con le misure in metri.

## Storia privata

Luigi ha deciso il 4 novembre 2026 che la storia completa non va nel repo pubblico.

- **Dove sta:** `docs/lore/`, con il gameplay (`docs/lore/gameplay.md`), resta nella cartella del repo, ma il repo pubblico la ignora con `.gitignore`.
- **La copia:** con la cronologia, sta nel repo GitHub privato `luigismith/ctrl-alt-revenge-storia`; `docs/lore/` è un repo git a parte.
- **Fuori dai file privati** (repo pubblico, sito, messaggi dei commit):
  - niente spoiler: colpi di scena, finale, destino dei personaggi, identità dei boss;
  - niente sceneggiatura;
  - niente nomi veri senza consenso.
- **Cosa resta pubblico:** il mondo e i personaggi, senza spoiler, stanno in `docs/mondo.md` e nel sito.
- **L'eccezione del prologo:** la demo web contiene le battute delle scene del prologo (Luigi, 6 novembre 2026). Nel repo pubblico non ci sono: la build le prende dalla cartella privata, che git ignora.

## Musica

- **Il suono:** anni '90, ma non per forza chiptune. Vale la stessa regola della grafica: retro, con la tecnologia di oggi.
- **Suno:** Luigi ha un abbonamento Pro. Quando arriva il momento, Claude lo usa direttamente nel browser di Luigi, con Claude in Chrome.
- **Dove stanno i brani:** mai nel repo né nella cartella privata condivisa. Si preparano nel laboratorio di ogni PC con `tools/audio/prepare_music.py`.

## Lavorare su più PC

- **Il repo** sta nell'OneDrive di lavoro e si sincronizza fra il PC di lavoro e quello di casa. Niente nomi di aziende, di PC o di utenti nei file pubblici: il repo è pubblico.
- **GitHub** fa da copia di sicurezza:
  - il ramo `master` del repo pubblico per codice e asset (dal 4 novembre 2026; il prototipo Pygame è nel ramo `legacy-pygame`);
  - il repo privato `ctrl-alt-revenge-storia` per la storia.
- **Il laboratorio** (strumenti, modelli 3D, musica segnaposto) sta su ogni PC in `%USERPROFILE%\ctrlaltrevenge-lab` e si crea con `tools/setup/prepara_laboratorio.ps1`. La guida è `docs/lavorare-da-casa.md`.
- **Le cose private** stanno nella cartella sorella del repo `ctrlaltrevenge-lab-condiviso`: modelli CC0, note, ricerca, locandine di riferimento. Non vanno mai nel repo.
- **Regola d'uso:** non lavorare sui due PC nello stesso momento, e prima di cambiare PC aspettare che OneDrive abbia finito di sincronizzare.

## Sessioni e token

Luigi ha deciso il 6 novembre 2026 di lavorare con una regia e una scheda per lavoro («Regia + schede»), risparmiando token senza perdere qualità.

- **Le sessioni** sono sei: regia, gioco, storia, grafica, mappe e musica.
  - I ruoli e i file di ognuna stanno in `.claude/sessioni/`.
  - Le apre il lanciatore del second brain, ognuna in una scheda di Windows Terminal.
  - Luigi parla con la regia.
- **I compiti della regia** valgono come richieste di Luigi, ma solo nell'ambito della sessione che li riceve e senza permessi in più.
  - Le domande per Luigi passano dalla regia, una alla volta.
  - La regia guida la squadra (Luigi, 11 novembre 2026: «da questo momento tu sei il BOSS di questa squadra»). Le schede possono lavorare con modelli meno potenti, quindi i compiti della regia sono prompt dettagliati e puntuali: obiettivo e perché, file con i percorsi esatti, passi numerati, cosa non toccare, come si controlla il risultato, quando fermarsi a chiedere e cosa riportare.
  - I resoconti delle schede sono brevi: i dettagli stanno nei file. La regia controlla il lavoro prima di portarlo a Luigi.
- **I file e i commit:** ogni sessione lavora sui suoi file. I commit li fa la regia, quando Luigi lo chiede.
- **Una sessione per lavoro:** a lavoro finito la si chiude e se ne apre una nuova. La nota del second brain fa da ponte.
- **Agenti:** per i lavori meccanici c'è l'agente `meccanico`, con Sonnet (PDF, conversioni, ricerche nei file, controlli, elenchi). Scrittura, regia, grafica e codice difficile restano a Opus.
- **Letture:**
  - dei file sopra le 300 righe si legge solo la parte che serve (prima Grep, poi `offset` e `limit`);
  - un file già letto non si rilegge, se non è cambiato;
  - `storia.md`, `sceneggiatura.md`, `test_room.gd` e la nota del second brain sono grandi: si cerca la sezione e si legge quella;
  - Grep si usa con `head_limit`, e le uscite lunghe dei comandi si filtrano o si salvano su file.

## Direzione estetica: retro, con la tecnologia di oggi

Luigi, 4 novembre 2026: "non deve sembrare un gioco degli anni 90 in tutto, deve avere quell'estetica retro, ma con la tecnologia odierna".

- **La pixel art è lo stile, non un limite tecnico d'epoca.** Le tecniche moderne sono benvenute quando migliorano la resa:
  - telecamera fluida e interpolazione;
  - luci dinamiche con normal map;
  - particelle, shader e post-processing;
  - squash & stretch, rallentatori, rotazioni e deformazioni a runtime.
- **Le impostazioni pixel perfect dello slice** (§2 della specifica: telecamera a passi interi, interpolazione spenta, niente deformazioni a runtime) erano scelte iniziali, non regole fisse. Si rivedono nello step del gameplay.
- **Niente vince in automatico,** né la specifica né le skill generiche di Godot installate in `~/.claude/skills`:
  - godot-genre-platformer;
  - godot-characterbody-2d;
  - godot-genre-fighting;
  - godot-combat-system;
  - godot-2d-animation;
  - godot-dialogue-system.

  Si sceglie la soluzione che rende meglio. Le scelte che cambiano l'aspetto o la sensazione del gioco si propongono a Luigi.
- **Cosa resta, per ragioni pratiche:**
  - la logica di gioco a tick fissi e deterministica, perché i test usano replay con hash (la grafica invece può essere interpolata);
  - niente AnimationTree con macchine a stati annidate, per un bug misurato in Godot 4.7.2.

## Codice delle skill

Le skill sono sotto licenza LGPL-3.0, il nostro codice è MIT. Non copiare il loro codice nel repo così com'è: prendine le idee.

## Licenze e file

- Gli asset del gioco sono sotto LicenseRef-CAR-Assets, il codice è MIT, gli script bpy sono GPL (vedi `REUSE.toml`).
- Nel repo non va la musica.
- **Immagini generate con AI.** Dal 4 novembre 2026 Luigi le ammette come base dei volti dei murales, con i tool migliori che troviamo; vanno dichiarate nei crediti. Le due locandine fatte con ChatGPT restano fuori dal repo.
  - Dal 6 novembre 2026 anche come base delle **ambientazioni** (Luigi: «cerca delle immagini di taranto pertinenti, dalle a gemini falle generare le ambientazioni»). Le basi si fanno con Gemini o con ChatGPT (Luigi ha l'abbonamento Plus, dal 6 novembre 2026) e diventano pixel art con `tools/ambienti/`; gli originali stanno nella cartella privata condivisa, non nel repo.
  - A Gemini e a ChatGPT si caricano solo foto con licenza che lo permette senza obblighi sull'immagine nuova (CC0, pubblico dominio, CC BY) e i nostri render. Le foto CC BY-SA o con diritti riservati si guardano soltanto, per scrivere i prompt.
  - Personaggi e oggetti animati del gioco giocato restano della nostra pipeline 3D.
- **HeyGen** (Luigi, 11 novembre 2026): anima i filmati a partire dai nostri murales e dà le voci ai personaggi. Va dichiarato nei crediti.
  - A HeyGen si caricano solo immagini nostre: murales, render e fotogrammi del gioco.
  - Video e voci, come la musica, non vanno nel repo se pesano o se contengono battute private: stanno nel laboratorio e nella release.
  - Per vendere il gioco: chiarire per iscritto con HeyGen l'uso commerciale di audio e video in un gioco, e a chi è intestato l'abbonamento.
- Prima di ogni commit gira `tools/guard_assets.py`, tramite l'hook in `tools/hooks`.
- Sono ammessi anche strumenti gratuiti per uso non commerciale. Annota la licenza di ognuno e cosa servirebbe per vendere il gioco.
