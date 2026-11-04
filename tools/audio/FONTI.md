# Fonti esterne dell'audio

Nessuno di questi file è nel repository: la musica sta in `%USERPROFILE%\ctrlaltrevenge-lab\music\`, gli strumenti in `%USERPROFILE%\ctrlaltrevenge-lab\tools\`. Crediti e licenze per il pubblico sono in `THIRD-PARTY-NOTICES.md`; qui resta la prova della verifica.

## Provenienza dei file di terze parti usati fuori dal repo

Tutto è stato scaricato il 3 novembre 2026, ognuno in una cartella sua sotto `ctrlaltrevenge-lab/downloads/`.

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

**Strumenti** (non distribuiti, servono solo a preparare i file).
- **ffmpeg 9.0.2 "essentials"** di gyan.dev, GPL-3.0.
  - https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip, 114.768.076 byte.
  - sha256 `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`, uguale a quello pubblicato in `ffmpeg-release-essentials.zip.sha256`.
  - Estratti in `ctrlaltrevenge-lab/tools/ffmpeg/` solo `ffmpeg.exe`, `ffprobe.exe`, `LICENSE` e `README.txt`.
  - Contiene libgme (LGPL), usata per rendere i VGM.
- **PyMusicLooper 3.6.0**, MIT. https://pypi.org/project/pymusiclooper/
  - Installato con `uv tool install pymusiclooper==3.6.0 --python 3.14` in `ctrlaltrevenge-lab/tools/pymusiclooper/`.
