# Fonti esterne dell'audio

Nessuno di questi file è nel repository: la musica sta in `%USERPROFILE%\ctrlaltrevenge-lab\music\`, i suoni di partenza degli effetti in `%USERPROFILE%\ctrlaltrevenge-lab\sources\sfx\`, gli strumenti in `%USERPROFILE%\ctrlaltrevenge-lab\tools\`. Crediti e licenze per il pubblico sono in `THIRD-PARTY-NOTICES.md`; qui resta la prova della verifica.

## Provenienza dei file di terze parti usati fuori dal repo

Musica e strumenti sono stati scaricati il 3 novembre 2026, ognuno in una cartella sua sotto `ctrlaltrevenge-lab/downloads/`. I suoni di partenza degli effetti sono arrivati il 5 novembre 2026: vedi "Effetti sonori", più sotto.

**Musica: Safety Stoat Studios, "Free VGMs".**
- Licenza CC0 1.0. Verificata alla fonte:
  - il file `LICENSE` del repository (sha256 `a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499`) è il testo legale di CC0 1.0 Universal;
  - la pagina https://safetystoatstudios.itch.io/free-vgms dice "This is a pack of CC0-licensed music [...] You can use them for whatever you want!".
- Autore: Zachary Rubenstein (Safety Stoat Studios). Anche la cartella `sharp_in_head/` è sua (commit "adding sharp_in_head" del 20 luglio 2024) ed è coperta dallo stesso `LICENSE` alla radice.
- Fonte: https://github.com/jerellsworth/free_vgms, commit `2e376d0abfa5709f6c0e648095672cd6c1654f93`.
  - I 53 file scaricati hanno lo stesso SHA-1 dei blob git di quel commit.
- File usati, con lo sha256:
  - `MD_tracks/i_wondered_what_i_could_do_with_it.vgm`: `d87e80cb376ae55eea765dff8e45caf83221b33463b3797c203b34e02a90e0a3`
  - `MD_tracks/my_fathers_eyes.wav`: `b5d96aa372a67a5eaf2dac74a77dc5406f01116131022a965453b7a4a27d2cc1`
  - `sharp_in_head/title.wav`: `fec35d9f99a3242fb7318ee704dc3d4b002f513c7e6832086773e8a47cbebd6b`
- Evitati di proposito: `battle_2`, `box_games` e `overworld` contengono campioni presi da Freesound di cui non ho verificato la licenza.
- Il riepilogo sta anche in `ctrlaltrevenge-lab/music/FONTI.md`, e ogni brano ha il campo `source` in `music.json`.

**Effetti sonori: i suoni di partenza di `sfx_pack.py`.**

I 27 WAV di `game/assets/sfx/` sono montati da 35 file di otto pacchetti (le ricette sono in `RECIPES`, dentro `tools/audio/sfx_pack.py`). I pacchetti stanno in `ctrlaltrevenge-lab/sources/sfx/<pacchetto>/` dal 5 novembre 2026. Gli archivi scaricati non sono stati conservati: per questo qui sotto ci sono gli sha256 dei file usati, non quelli degli archivi.

| Pacchetto | Autore, titolo e pagina | Licenza e prova |
|---|---|---|
| `kenney-impact-sounds` | Kenney, Impact Sounds 1.0, https://kenney.nl/assets/impact-sounds | CC0 1.0. `License.txt` del pacchetto: "License: (Creative Commons Zero, CC0)"; sha256 `b49aa9c56b04528b95913de13e506a0f7c5e807b9925db9bfef86af1f91120db` |
| `kenney-interface-sounds` | Kenney, Interface Sounds 1.0, https://kenney.nl/assets/interface-sounds | CC0 1.0. `License.txt` del pacchetto, stessa frase; sha256 `f7966c773bbed0eca6a9c75081c44a178b38eae112724dbb5fdfbd4192d118a9` |
| `kenney-rpg-audio` | Kenney, RPG Audio, https://kenney.nl/assets/rpg-audio | CC0 1.0. `License.txt` del pacchetto: "License (Creative Commons Zero, CC0)"; sha256 `5735dfd72cb64cbbceda4ebc00c380c41ca680edb82ff153aa7c9ab97614c539` |
| `kenney-sci-fi-sounds` | Kenney, Sci-Fi Sounds 1.0, https://kenney.nl/assets/sci-fi-sounds | CC0 1.0. `License.txt` del pacchetto: "License: (Creative Commons Zero, CC0)"; sha256 `a9767b25c3533f69d03af136480efad08efba19a9f0d89616992b34c79fd6186` |
| `oga-thwack` | AntumDeluge (Jordan Irwin), Thwack Sounds 1.0, https://opengameart.org/content/thwack-sounds | CC0 1.0. `README.txt` del pacchetto: "Creative Commons Zero (CC0) (see: LICENSE.txt)"; `LICENSE.txt` è il testo di CC0 1.0 Universal, sha256 `a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499` |
| `oga-rubberduck-100-cc0-sfx-2` | rubberduck, 100 CC0 SFX #2, https://opengameart.org/content/100-cc0-sfx-2 | CC0 1.0, dichiarata sulla pagina: nel pacchetto non c'è un file di licenza |
| `oga-davidw-punch-sfx` | DavidW, Punch SFX, https://opengameart.org/content/punch-sfx | CC BY 4.0, dichiarata sulla pagina: nel pacchetto non c'è un file di licenza. Il credito è obbligatorio |
| `freesound-cc0` | autori vari, dieci suoni singoli; la pagina di ognuno è `https://freesound.org/s/<ID>/`, con l'ID che apre il nome del file | CC0 1.0, dichiarata sulla pagina di ogni suono: i file non portano la licenza |

File usati, con lo sha256:

| File | sha256 |
|---|---|
| `freesound-cc0/389590_Swing-Woosh.ogg` | `99e6ecf3464ae980f3a4df2cb954f24c2c9d0a9d3359f690570fdbe6097ab3b7` |
| `freesound-cc0/475135_FX-Swoosh-Low-Pitch.ogg` | `f20c8e13f42139bd0b3a632413d772b4f6e7553dc5b41a37b138da29efc72505` |
| `freesound-cc0/498434_Trash-can-falling.ogg` | `3be5e1d43f5285639f4acd739fca5145286857ca3df06875311421844c35bb1b` |
| `freesound-cc0/504626_BODY-FALL-V-HVY-DIRT.ogg` | `7d50922d1789c5470ef0abcd755f4f85bf9949af097b027d21636ba31381b9ec` |
| `freesound-cc0/507466_Clean-fast-Swoosh-aiff.ogg` | `26b606a201d69b940732e32ecdd96e68d8741b1bd1a753d99c09651bd9aca14b` |
| `freesound-cc0/512471_Electric-zap-wav.ogg` | `cca8d4161c5cf2daca229b571c7d0566953b59f8b84746f7155fc99fdb685fce` |
| `freesound-cc0/540272_land-a-jump-wav.ogg` | `cd97cbb553a672acbe24a35d59e29abf48cbb8efc00ab4fab00f4f49df1b075a` |
| `freesound-cc0/545238_Item-Sparkle.ogg` | `33e2128fb8d11693e90f74d08dfd55711862e528fe5a5efe3f29cb772b9a99d2` |
| `freesound-cc0/667271_Cloth-Grab.ogg` | `fb6d61222d4599d20472d92e7cc899125fe67081044518d8ef80fb33790f9134` |
| `freesound-cc0/816237_Crunch.ogg` | `922977ec647b09a2eae454f1975693137188cd519528bd40f19eb00d786371e7` |
| `kenney-impact-sounds/Audio/impactGeneric_light_000.ogg` | `f0e982611e97512fee5f777986b67e8b435434b601f94992ec044f7e89fb5acb` |
| `kenney-impact-sounds/Audio/impactPunch_heavy_000.ogg` | `b33a8f14068aec24ec69ba85e5e87fdc41228975f6a1a3e44a6e7d6fc3d9f8d8` |
| `kenney-impact-sounds/Audio/impactPunch_heavy_002.ogg` | `7993dd4c156b9979ad69f17be5ebe31850b16039a3857f8477141be54dfee1b3` |
| `kenney-impact-sounds/Audio/impactPunch_heavy_003.ogg` | `4ab53b26f4ea575120dcc1348526c9e0db2afc6af7a442aa0489bdead2ca80b6` |
| `kenney-impact-sounds/Audio/impactPunch_medium_000.ogg` | `486988aa2d6440ffc4c62a0e8ccf3c23673ba84424bd4723378d451b7255eb5c` |
| `kenney-impact-sounds/Audio/impactPunch_medium_003.ogg` | `2d7c719c05999e0532f4384e1018e04cd916db715140bf16dee2dff3f820e908` |
| `kenney-impact-sounds/Audio/impactSoft_heavy_000.ogg` | `49e7ca88743fca974bb8676ea138b751cfd8f9033b5e7af8736c2a215d6edbc1` |
| `kenney-impact-sounds/Audio/impactSoft_heavy_002.ogg` | `d130ae541951243d3f6ed963d0057450a445ffe117fbf9a084d34eb1635cb563` |
| `kenney-interface-sounds/Audio/confirmation_001.ogg` | `063564703b6094d70718a3e787a55cc9141611e4ecd6b6637f8828f79b4a8c3a` |
| `kenney-interface-sounds/Audio/glitch_002.ogg` | `1da06a2e63ce131f5e0316ca27c75fc0d672db7a8f9b986c70693f2bd992eabc` |
| `kenney-interface-sounds/Audio/question_001.ogg` | `abb8f9e4eb2071491b0b15f84ee302386b1847609310c1b000ae174639a6cc5a` |
| `kenney-interface-sounds/Audio/select_002.ogg` | `4cc6ac5341b9b2c86fef80c347de028e9ab9f2e037586ac7d9fa59a403a1c012` |
| `kenney-interface-sounds/Audio/switch_002.ogg` | `6fc395be2ad1f99ce318a5d28f98fb76dbeb676d83a0b28239d8c1fb90736180` |
| `kenney-rpg-audio/Audio/cloth1.ogg` | `ddb93a3671233f95da0e0b10367f082f7eb42fa6caaddcf776410aa8833c747d` |
| `kenney-rpg-audio/Audio/cloth4.ogg` | `e7ab9a6c4466dea874196c61f59bf1da05cfe58748f42fadd695d441a154a99b` |
| `kenney-rpg-audio/Audio/clothBelt.ogg` | `f29560a2aea95bbfeb643e1e8f56ec2b6f7e32f32ce4e140645a36db81de3253` |
| `kenney-sci-fi-sounds/Audio/forceField_002.ogg` | `051b0eafc479695af4ca3607d41fd4be41bae7c21f4f9508d004722b09f1bd63` |
| `kenney-sci-fi-sounds/Audio/impactMetal_000.ogg` | `956c6612a256aa1a67a2327fffe2454f6b1d82e4c1c2be28fd66916335d5b1d6` |
| `oga-davidw-punch-sfx/punch_1_0.wav` | `9656b014980815cc1d43cb58d632f695d0264940c1b677aca1dc37f5558dc8d2` |
| `oga-davidw-punch-sfx/punch_2_0.wav` | `b1032c683cf2b4e05c473fcb42dbb13cbc5738e50c52bacbea4860f6c2c0c0b4` |
| `oga-davidw-punch-sfx/punch_6_0.wav` | `0639bd69b8e627a7413d63f059969c6ce350b8918fbe757347214914a815b8ef` |
| `oga-davidw-punch-sfx/punch_9_0.wav` | `430a87c6cb6a61a4264aa7863e7873f57cc2920e3ff236a7ff87d447670f03da` |
| `oga-rubberduck-100-cc0-sfx-2/sfx100v2_footstep_wet_01.ogg` | `c2663b62fc7239972c044719b95daec4004976fc9bd0a1678c06170d99a3d408` |
| `oga-rubberduck-100-cc0-sfx-2/sfx100v2_footstep_wet_02.ogg` | `b2cfbdd75ee970dcb68cc157fec818eda2f5802989b0da684aa67817cb914b52` |
| `oga-thwack/PCM/thwack-02.wav` | `ce97b3a0bd775841c895150b8d563ca05ecf9d56211565c54a5497f04ce83545` |

**Strumenti** (non distribuiti, servono solo a preparare i file).
- **ffmpeg 9.0.2 "essentials"** di gyan.dev, GPL-3.0.
  - https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip, 114.768.076 byte.
  - sha256 `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`, uguale a quello pubblicato in `ffmpeg-release-essentials.zip.sha256`.
  - Estratti in `ctrlaltrevenge-lab/tools/ffmpeg/` solo `ffmpeg.exe`, `ffprobe.exe`, `LICENSE` e `README.txt`.
  - Contiene libgme (LGPL), usata per rendere i VGM.
- **PyMusicLooper 3.6.0**, MIT. https://pypi.org/project/pymusiclooper/
  - Installato con `uv tool install pymusiclooper==3.6.0 --python 3.14` in `ctrlaltrevenge-lab/tools/pymusiclooper/`.
