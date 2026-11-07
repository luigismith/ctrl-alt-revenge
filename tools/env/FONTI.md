# Fonti esterne della pipeline degli sfondi

Dal 7 novembre 2026 nessuna di queste fonti entra più nel gioco: i piani di Warped City e i modelli dei kit li usava la vecchia pipeline degli sfondi, tolta quel giorno (vedi `README.md`). Questa pagina resta come prova della verifica. I file stanno nel laboratorio. Crediti e licenze per il pubblico sono in `THIRD-PARTY-NOTICES.md`; qui resta la prova della verifica.

## Fonti verificate (3 novembre 2026)

Per ogni fonte la licenza è stata letta nel file dentro il pacchetto.

| Fonte | URL | Licenza e prova | File usati | sha256 |
|---|---|---|---|---|
| Warped City (ansimuz) | https://opengameart.org/content/warped-city | CC0. `public-license.txt` dello zip: "Public domain and free to use on whatever you want, personal or commercial" | `warped_city_files.zip`, 4 264 805 byte | `cf0e69a203206f529adbaf1f82d4c5f165ca9cdb49d3995ec88d135b37e40e3e` |
| | | | `skyline-a.png`, `skyline-b.png`, `buildings-bg.png`, `near-buildings-bg.png` | vedi `SOURCE.md` del pack |
| Quaternius Downtown City MegaKit [Standard] | https://quaternius.com/packs/downtowncitymegakit.html | CC0 1.0. `License_Standard.txt`: "CC0 1.0 Universal (CC0 1.0) Public Domain Dedication" | `Downtown City MegaKit[Standard].zip`, 234 753 092 byte | `5b1a945576d54cdbb4ccc9c3d52711e6d530da74c74c586407ecc28b165335da` |
| | | | `Prop_ACUnit.gltf` / `.bin` | `f81fae2b49804312d23cc5c56fdf36f6bec89f342df9d135c1565ed31a7e968d` / `71c8dcc458ec8fa31ca7c3f391b1b95dc17864c6bb5c1addbdde899849c3324a` |
| Kenney City Kit Roads 2.2 | https://kenney.nl/assets/city-kit-roads | CC0. `License.txt`: "License: (Creative Commons Zero, CC0)" | `kenney_city-kit-roads.zip`, 2 852 289 byte | `374a4552115cbd11b4ec5c930ee31a533562dc78a09af249a655d03f7ea3b959` |
| | | | `dumpster.glb` | `d87d4a812567d0e8b91c545387d758aa18f7652eb8fc0aed2513a83abb988dd6` |
| Creative Commons, testo CC0 | https://creativecommons.org/publicdomain/zero/1.0/legalcode.txt | testo della licenza | `LICENSES/CC0-1.0.txt` | `a2010f343487d3f7618affe54f789f5487602331c0a8d03f49e9a7c547cf0499` |

Note:
- OpenGameArt ha rifiutato l'accesso automatico alla pagina di Warped City (HTTP 403) e non è stato aggirato. Il nome e la dimensione dello zip sulla pagina sono confermati da una ricerca web. La licenza CC0 è confermata anche dalla ricerca del 3 novembre (`ricerca-2026-11-03/relazioni/asset_summary.txt`).
- Il Cyberpunk Game Kit di Quaternius **non** è usato: il suo `License.txt` non era scaricabile (quota di Google Drive), quindi il condizionatore viene dal Downtown City MegaKit.
- Non sono usati il carattere "Bfont" di Blender, Poly Haven, ambientCG, CraftPix, Oonquil o altro materiale non ridistribuibile. Le scritte sono un carattere pixel disegnato in `tools/env/pixfont.py`.
- Nessuna AI generativa nella vecchia pipeline: tutto veniva da script deterministici con semi fissi. Le basi di `taranto.py` e di `tools/ambienti/` invece sono di ChatGPT (dal 6 novembre 2026), con prompt e originali nella cartella privata condivisa.
