# CTRL+ALT REVENGE: note per Claude

- **Riferimenti:**
  - la specifica tecnica dello slice è `docs/specifica-slice.md`;
  - la storia è `docs/lore/storia.md`;
  - la ricerca su Taranto è `docs/lore/ricerca-taranto.md`;
  - il gameplay è `docs/gameplay.md`.

  Storia, ricerca e gameplay sono privati: vedi "Storia privata" più sotto.
- **Lingua:** italiano, con gli accenti giusti, per testi, commenti e messaggi di commit.

## Come lavora Luigi

Valgono su ogni PC: queste preferenze stanno qui e non solo nella memoria di un computer.

- **Domande:** una per volta, con 2-4 soluzioni proposte e la consigliata per prima (AskUserQuestion). Niente elenchi di domande aperte in fondo ai messaggi.
- **Storia:** si scrive insieme. Claude propone, Luigi decide. Le decisioni vanno in `docs/lore/storia.md`, le scene approvate in `docs/lore/sceneggiatura.md`.
- **Giudizi onesti** su grafica e gameplay, con voti rispetto a Streets of Rage 2 e i limiti detti chiaramente.
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
- **Budget:** costo zero. Sono ammessi strumenti gratuiti anche solo per uso non commerciale; di ognuno si annotano la licenza e cosa servirebbe per vendere il gioco.
- **Persone reali:** i nomi veri entrano nel gioco e nei file pubblici solo con il consenso.
  - Il MiniBar di Ignazio, il bar dei Tamburi, ce l'ha (Luigi, 4 novembre 2026).
  - Il writer che ispira Totò l'ha dato (Luigi, 5 novembre 2026): nome e tag vanno nei crediti e nel sito come omaggio, i murales hanno il suo stile. Nel gioco Totò resta un personaggio inventato e firma solo "Totò".
- **Coerenza, prima di tutto.** Luigi: "mantenere riferimenti alla città e alle ambientazioni, deve essere tutto coerente con la storia e col passare degli anni".
  - Ogni livello, sfondo, insegna, testo, oggetto e suono deve essere coerente con Taranto e i suoi luoghi veri, con la storia e con le sue epoche (le date sono nella cronologia). Deve esserlo anche con età, date, ore, meteo e luna di ogni scena.
  - I riferimenti sono `docs/lore/cronologia.md` e `docs/lore/ricerca-taranto.md`. Prima di disegnare o scrivere qualcosa di nuovo, controllali.

## Storia privata

Luigi ha deciso il 4 novembre 2026 che la storia completa non va nel repo pubblico.

- **Dove sta:** `docs/lore/` e `docs/gameplay.md` restano nella cartella del repo, ma il repo pubblico li ignora con `.gitignore`.
- **La copia:** con la cronologia, sta nel repo GitHub privato `luigismith/ctrl-alt-revenge-storia`; `docs/lore/` è un repo git a parte.
- **Fuori dai file privati** (repo pubblico, sito, messaggi dei commit):
  - niente spoiler: colpi di scena, finale, destino dei personaggi, identità dei boss;
  - niente sceneggiatura;
  - niente nomi veri senza consenso.
- **Cosa resta pubblico:** il mondo e i personaggi, senza spoiler, stanno in `docs/mondo.md` e nel sito.

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
- **Immagini generate con AI.** Dal 4 novembre 2026 Luigi le ammette come base dei volti dei murales, con i tool migliori che troviamo; vanno dichiarate nei crediti. Il resto della grafica nasce dalla nostra pipeline. Le due locandine fatte con ChatGPT restano fuori dal repo.
- Prima di ogni commit gira `tools/guard_assets.py`, tramite l'hook in `tools/hooks`.
- Sono ammessi anche strumenti gratuiti per uso non commerciale. Annota la licenza di ognuno e cosa servirebbe per vendere il gioco.
