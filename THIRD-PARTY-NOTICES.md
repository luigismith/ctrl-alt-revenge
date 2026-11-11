# Materiale di terze parti

Ogni voce indica la fonte, la licenza e il credito. Chi aggiunge un pack o un font aggiorna anche questo file.

## Motore

- **Godot Engine 4.7.2**: licenza MIT. Copyright (c) 2014-present Godot Engine contributors; (c) 2007-2014 Juan Linietsky, Ariel Manzur.
  - La schermata dei crediti del gioco mostra la licenza di Godot (`Engine.get_license_text()`), i componenti di terze parti del motore con i loro copyright (`Engine.get_copyright_info()`) e i testi completi delle loro licenze (`Engine.get_license_info()`), presi dall'eseguibile stesso.

## Effetti sonori

Gli effetti sonori in `game/assets/sfx/` li monta `tools/audio/sfx_pack.py` da suoni già pronti: taglio, intonazione, filtri, strati sovrapposti, saturazione e livelli. I file di partenza non sono in questo repository: restano nel laboratorio (`sources/sfx/`).

- **Kenney**: Impact Sounds, Interface Sounds, RPG Audio e Sci-Fi Sounds.
  - Licenza CC0 1.0; il credito "Kenney" è gradito ma non obbligatorio.
  - https://kenney.nl/assets/impact-sounds, https://kenney.nl/assets/interface-sounds, https://kenney.nl/assets/rpg-audio, https://kenney.nl/assets/sci-fi-sounds
- **Freesound**, suoni singoli CC0 1.0 (la pagina di ognuno è `https://freesound.org/s/<ID>/`): 389590 (whoosh_light), 475135 (whoosh_heavy), 507466 (throw), 667271 (grab), 504626 (body_fall), 540272 (land), 545238 (glint), 512471 (zap), 498434 (bin_break), 816237 (pickup).
- **rubberduck, "100 CC0 SFX #2"** (OpenGameArt): i passi bagnati.
  - Licenza CC0 1.0.
  - https://opengameart.org/content/100-cc0-sfx-2
- **AntumDeluge, "Thwack Sounds"** (OpenGameArt): la parata.
  - Licenza CC0 1.0.
  - https://opengameart.org/content/thwack-sounds
- **DavidW, "Punch SFX"** (OpenGameArt): uno strato di `hit_medium`, `hit_heavy`, `hit_kick` e `ko`.
  - Licenza CC BY 4.0, https://creativecommons.org/licenses/by/4.0/. Il credito è obbligatorio e sta nei crediti del gioco e fra le fonti del sito.
  - I suoni sono stati modificati: tagliati, filtrati, sovrapposti ad altri e saturati.
  - https://opengameart.org/content/punch-sfx

## Sorgenti usate dalla pipeline da 3D a pixel

I file di queste sorgenti non sono in questo repository: restano nel laboratorio di chi produce la grafica. Gli sprite, i ritratti e gli sfondi derivati sono opera nostra.

- **Quaternius**: Universal Base Characters, Universal Animation Library 1 e 2 (versione Standard).
  - Licenza CC0 1.0, credito facoltativo.
  - https://quaternius.com
  - Gli sprite dei personaggi (GIG, il punk e il bruto, il rider, il messo, l'esattore e i passanti del prologo) derivano da questi modelli e animazioni (dalla Universal Animation Library anche le mosse platform: ClimbUp_1m, Slide, Crouch).
- **Mesh2Motion** (animazioni: il calcio circolare di GIG).
  - Licenza CC0 1.0.
  - https://github.com/Mesh2Motion/mesh2motion-app
- **Quaternius Downtown City MegaKit (Standard)**: il condizionatore a muro del nostro render da cui è ridipinta la strada del capitolo 2.
  - Licenza CC0 1.0, credito facoltativo.
  - https://quaternius.com/packs/downtowncitymegakit.html
- **Kenney City Kit Roads 2.2**: il cassonetto dello stesso render.
  - Licenza CC0 1.0; il credito "Kenney" è gradito ma non obbligatorio.
  - https://kenney.nl/assets/city-kit-roads
- **CMU Graphics Lab Motion Capture Database**: la pipeline sa leggerne i file (`tools/blender/char_asfamc.py`), ma gli sprite attuali non ne usano. Se un giorno si useranno, il credito richiesto è: "I dati usati in questo progetto provengono da mocap.cs.cmu.edu. Il database è stato creato con il finanziamento NSF EIA-0196217."

Il resto è nostro:
- le mosse scritte a mano (presa, ginocchiate, proiezione, gancio cyber, calcio volante, reazioni ai colpi) e le pose delle vittime, in `tools/blender/char_poses.py`, e le pose chiave della pipeline v7 (guardia, jab, gancio, colpo subito, doppio salto, appeso alla sporgenza) in `tools/blender/char_anim.py`;
- gli stivali, il codino con la molla, i timbri del viso, le normal map e le luci dinamiche (`tools/blender/char_boots.py`, `tools/sprites/pix_v7.py`, `game/src/stage/level.gd`);
- gli oggetti di scena 3D e i caratteri pixel delle scritte, geometria e disegno procedurale di `tools/env/` e `tools/blender/env_gbuffer.py`;
- il pavimento e il cavo del capitolo 2, disegnati da `tools/ambienti/patina_floor.py` e `tools/ambienti/cavo_rivolo.py`.

Non sono usati Mixamo, Reallusion, CraftPix, Oonquil, Shapeforms, Sonniss, i file grezzi Rokoko né altro materiale che non si può ridistribuire.

## Basi generate con l'AI (fuori dal repository)

Le ambientazioni del prologo (il cimitero di San Brunone, la fuga per i Tamburi e il garage, in `game/assets/env/prologo/`) e la strada del capitolo 2, «Il Wind Day» (`game/assets/env/sotto_la_linea/`: tutti i piani tranne il pavimento), partono da sfondi dipinti e fogli di oggetti generati con l'intelligenza artificiale. Gli script di `tools/ambienti/` li portano alla scala, alle palette e ai blocchi del gioco; quelli delle tavole del prologo di oggi (`game/assets/env/prologo/v2/`) sono ancora nella cartella di lavoro, fuori dal repository. Gli originali e i prompt non sono in questo repository.

- **App Gemini di Google** (gemini.google.com), dal 6 novembre 2026. Google dichiara di non rivendicare la proprietà dei contenuti generati.
- **ChatGPT di OpenAI** (chatgpt.com), dal 6 novembre 2026. I termini di OpenAI cedono all'utente i diritti sull'output e ne ammettono l'uso commerciale.
- Per le prime ambientazioni del prologo i prompt sono di solo testo. Per la strada del capitolo 2, dal 7 novembre 2026, e per le tavole del prologo di oggi, dall'8 novembre 2026, a ChatGPT abbiamo caricato soltanto i nostri render, i nostri schizzi e le nostre basi. Nessuna foto né immagine di altri è stata caricata: le foto di Taranto e Street View sono servite soltanto a scrivere i prompt.
- **I primi piani dei filmati** (`game/assets/ui/closeups/`) partono da volti in stile murales generati con ChatGPT, a cui abbiamo caricato soltanto i nostri render 3D dei personaggi. `tools/sprites/closeup_ai.py` li porta in pixel art, e palpebre e bocca le animano i nostri script.
- **I murales dei filmati** (`game/assets/murales/`), dal 7 novembre 2026, partono da basi di ChatGPT. Per gli sfondi abbiamo usato prompt di solo testo; per le figure abbiamo caricato soltanto i nostri render 3D dei personaggi e le nostre basi. `tools/murales/` le porta in pixel art; le scritte e i tag li disegna il nostro carattere pixel. Nel gioco i murales li animano i nostri script.
- **Il fondale della schermata del titolo** (`game/assets/ui/titolo/`), dal 7 novembre 2026, parte da una base di ChatGPT a cui abbiamo caricato soltanto una nostra base. `tools/ambienti/titolo.py` la porta in pixel art; GIG viene dal nostro render 3D (`tools/sprites/titolo_gig.py`) e i panni stesi li disegna il codice.
- Personaggi, nemici e oggetti animati del gioco non vengono da qui: nascono dalla pipeline da 3D a pixel.
- Le immagini generate con l'AI potrebbero non essere proteggibili col diritto d'autore. Prima di vendere il gioco si ricontrollano i termini dei due servizi.

## Codice nostro sotto GPL

- **Script bpy della pipeline** (`tools/blender/`): codice nostro sotto GPL-3.0-or-later, come chiede blender.org per gli script che usano l'API di Blender. Testo in `LICENSES/GPL-3.0-or-later.txt`.

## Font, effetti e interfaccia

Sono nostri, senza materiale di terze parti: i font **CAR Pixel** (regolare e grassetto), gli effetti visivi e l'interfaccia, disegnati da script in `tools/fxui/`.

## Voci sintetiche e trailer (fuori dal repository)

Le voci dei personaggi, nei filmati e nelle battute del prologo, sono sintetiche: voci progettate in italiano con HeyGen, da una descrizione scritta, non clonate da persone vere. Gli script di `tools/voci/` le portano al formato del gioco. I file audio non stanno in questo repository: la demo web li prende dagli allegati della release `musica-demo`.

- **HeyGen** (heygen.com), dall'11 novembre 2026, con un abbonamento a pagamento. Dai suoi termini, letti quel giorno: l'output è di chi lo genera e l'uso commerciale non è vietato; HeyGen si tiene una licenza sui contenuti generati.
- **Il trailer** monta i nostri murales e due scene d'arena del gioco, animati con HeyGen (image_to_video) a partire da nostre immagini. Le altre clip sono gioco vero, ritoccato nel colore. Nel gioco di oggi i murales li animano i nostri script. Il video non sta in questo repository.
- **Whisper base**, di OpenAI, sotto licenza MIT. Trascrive ogni battuta: controlla che dica il testo e dà i tempi delle parole per la bocca dei personaggi. Non finisce nel gioco.
- Prima di vendere il gioco c'è da chiarire per iscritto con HeyGen l'uso commerciale di audio e video in un gioco e a chi è intestato l'abbonamento.

## Musica (fuori dal repository)

I brani della demo e la musica del trailer li ha creati Luigi Massari con **Suno** (piano Pro, novembre 2026). Non stanno in questo repository: sono fra gli allegati della release `musica-demo`. Prima di vendere il gioco si ricontrollano i termini di Suno per i brani fatti con il piano a pagamento.

Un laboratorio nuovo, senza i brani, parte con musica CC0. Nemmeno questi file sono in questo repository.

- **Safety Stoat Studios, "Free VGMs"** (musica per Mega Drive, di Zachary Rubenstein): "I Wondered What I Could Do With It", "Title" (Sharp in Head) e il finale di "My Father's Eyes".
  - Licenza CC0 1.0, credito facoltativo.
  - https://github.com/jerellsworth/free_vgms
