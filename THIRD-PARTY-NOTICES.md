# Materiale di terze parti

Ogni voce indica la fonte, la licenza e il credito. Chi aggiunge un pack o un font aggiorna anche questo file.

## Motore

- **Godot Engine 4.7.2**: licenza MIT. Copyright (c) 2014-present Godot Engine contributors; (c) 2007-2014 Juan Linietsky, Ariel Manzur.
  - La schermata dei crediti del gioco mostra la licenza di Godot (`Engine.get_license_text()`), i componenti di terze parti del motore con i loro copyright (`Engine.get_copyright_info()`) e i testi completi delle loro licenze (`Engine.get_license_info()`), presi dall'eseguibile stesso.

## Materiale di terze parti nel repository

- **Warped City**, di Luis Zuno (ansimuz): 4 PNG dello sfondo, in `game/assets/third_party/ansimuz-warped-city/` (fonte, dimensioni e sha256 nel suo `SOURCE.md`).
  - Licenza CC0 1.0, credito facoltativo. Testo in `LICENSES/CC0-1.0.txt`.
  - https://opengameart.org/content/warped-city
  - I piani `sky`, `far` e `mid` di "Sotto la Linea" ne sono una versione ricolorata e ricomposta.
  - La musica del pack (Pascal Belisle) ha un'altra licenza e non è usata.

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
  - Gli sprite di GIG, del punk e del bruto derivano da questi modelli e animazioni (dalla Universal Animation Library anche le mosse platform di prova: ClimbUp_1m, Slide, Crouch).
- **Mesh2Motion** (animazioni: il calcio circolare di GIG).
  - Licenza CC0 1.0.
  - https://github.com/Mesh2Motion/mesh2motion-app
- **Quaternius Downtown City MegaKit (Standard)**: il condizionatore a muro degli sfondi.
  - Licenza CC0 1.0, credito facoltativo.
  - https://quaternius.com/packs/downtowncitymegakit.html
- **Kenney City Kit Roads 2.2**: il cassonetto del vicolo.
  - Licenza CC0 1.0; il credito "Kenney" è gradito ma non obbligatorio.
  - https://kenney.nl/assets/city-kit-roads
- **CMU Graphics Lab Motion Capture Database**: la pipeline sa leggerne i file (`tools/blender/char_asfamc.py`), ma gli sprite attuali non ne usano. Se un giorno si useranno, il credito richiesto è: "I dati usati in questo progetto provengono da mocap.cs.cmu.edu. Il database è stato creato con il finanziamento NSF EIA-0196217."

Il resto è nostro:
- le mosse scritte a mano (presa, ginocchiate, proiezione, gancio cyber, calcio volante, reazioni ai colpi) e le pose delle vittime, in `tools/blender/char_poses.py`, e le pose chiave della pipeline v7 (guardia, jab, gancio, colpo subito, doppio salto, appeso alla sporgenza) in `tools/blender/char_anim.py`;
- gli stivali, il codino con la molla, i timbri del viso, le normal map e le luci dinamiche (`tools/blender/char_boots.py`, `tools/sprites/pix_v7.py`, `game/src/stage/level.gd`);
- gli sfondi oltre ai pezzi citati (edifici, insegne, caratteri pixel delle scritte, travata, piloni) e gli oggetti di scena, geometria e disegno procedurale di `tools/env/` e `tools/blender/env_gbuffer.py`.

Non sono usati Mixamo, Reallusion, CraftPix, Oonquil, Shapeforms, Sonniss, i file grezzi Rokoko né altro materiale che non si può ridistribuire.

## Basi generate con l'AI (fuori dal repository)

Le ambientazioni del prologo (il cimitero di San Brunone, la fuga per i Tamburi e il garage, in `game/assets/env/prologo/`) partono da sfondi dipinti e fogli di oggetti generati con l'intelligenza artificiale. Gli script di `tools/ambienti/` li portano alla scala, alle palette e ai blocchi del gioco. Gli originali e i prompt non sono in questo repository.

- **App Gemini di Google** (gemini.google.com), dal 6 novembre 2026. Google dichiara di non rivendicare la proprietà dei contenuti generati.
- **ChatGPT di OpenAI** (chatgpt.com), dal 6 novembre 2026. I termini di OpenAI cedono all'utente i diritti sull'output e ne ammettono l'uso commerciale.
- Per le ambientazioni i prompt sono di solo testo: nessuna foto né immagine di altri è stata caricata. Le foto di Taranto sono servite soltanto a scriverli.
- **I primi piani dei filmati** (`game/assets/ui/closeups/`) partono da volti in stile murales generati con ChatGPT, a cui abbiamo caricato soltanto i nostri render 3D dei personaggi. `tools/sprites/closeup_ai.py` li porta in pixel art, e palpebre e bocca le animano i nostri script.
- Personaggi, nemici e oggetti animati del gioco non vengono da qui: nascono dalla pipeline da 3D a pixel.
- Le immagini generate con l'AI potrebbero non essere proteggibili col diritto d'autore. Prima di vendere il gioco si ricontrollano i termini dei due servizi.

## Codice nostro sotto GPL

- **Script bpy della pipeline** (`tools/blender/`): codice nostro sotto GPL-3.0-or-later, come chiede blender.org per gli script che usano l'API di Blender. Testo in `LICENSES/GPL-3.0-or-later.txt`.

## Font, effetti e interfaccia

Sono nostri, senza materiale di terze parti: i font **CAR Pixel** (regolare e grassetto), gli effetti visivi e l'interfaccia, disegnati da script in `tools/fxui/`.

## Musica segnaposto (fuori dal repository)

Finché non arrivano i brani definitivi, le build locali usano musica CC0. Questi file non sono in questo repository.

- **Safety Stoat Studios, "Free VGMs"** (musica per Mega Drive, di Zachary Rubenstein): "I Wondered What I Could Do With It", "Title" (Sharp in Head) e il finale di "My Father's Eyes".
  - Licenza CC0 1.0, credito facoltativo.
  - https://github.com/jerellsworth/free_vgms
