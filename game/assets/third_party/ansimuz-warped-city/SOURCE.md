# Warped City (ansimuz) - file usati

- **Pack**: Warped City, di Luis Zuno (ansimuz).
- **Pagina**: https://opengameart.org/content/warped-city (copia dell'autore su OpenGameArt; pagina del pack: https://ansimuz.itch.io/warped-city).
- **File scaricato**: `warped_city_files.zip`, 4 264 805 byte, sha256 `cf0e69a203206f529adbaf1f82d4c5f165ca9cdb49d3995ec88d135b37e40e3e`. È lo zip elencato su OpenGameArt (`warped_city_files.zip`, 4,3 MB). Copia di lavoro in `%USERPROFILE%\ctrlaltrevenge-lab\sources\chars\oga-warped-city\`.
- **Licenza**: CC0 1.0 (testo completo in `LICENSES/CC0-1.0.txt`). Il file `public-license.txt` dello zip dice: "Artwork created by Luis Zuno @ansimuz. License for Everyone. Public domain and free to use on whatever you want, personal or commercial. Credit is not required but appreciated."
- **Esclusi**: la musica di Pascal Belisle (licenza diversa: chiede il credito), `phaser.min.js`, la demo, i suoni, gli add-on a pagamento. L'insegna "COKE" non è nei file usati.
- **Credito** (facoltativo): "Warped City by Luis Zuno (ansimuz), CC0".
- **Verifica**: 3 novembre 2026. La licenza è letta nel file dello zip e confermata dalla ricerca del 3 novembre (`ricerca-2026-11-03/relazioni/asset_summary.txt`). Lo stesso giorno OpenGameArt ha rifiutato l'accesso automatico alla pagina (HTTP 403); una ricerca web conferma il nome e la dimensione dello zip sulla pagina.

## File di questa cartella (identici a quelli dello zip)

| File nello zip | Byte | sha256 |
|---|---|---|
| `warped city files/ENVIRONMENT/background/skyline-a.png` | 4051 | `396a8ed4cc3027f38737319ebf78dd55452e0f6d56a28179dd6bd268e9870344` |
| `warped city files/ENVIRONMENT/background/skyline-b.png` | 4994 | `96deb29230a929a7464791195ea81c637736353e99f48ba309552ee06536a695` |
| `warped city files/ENVIRONMENT/background/buildings-bg.png` | 4612 | `2bcf93444924a333a340920ad773421137bc2d59d629017d5eb886239e70e7df` |
| `warped city files/ENVIRONMENT/background/near-buildings-bg.png` | 21635 | `70eca49ce42f7c57135ade657d669ee9c7850f1bd02ba3eeece5f3f33c731205` |

## Dove finiscono

`tools/env/warped.py` li ricolora verso la palette della locandina (tabelle colore esplicite) e li ricompone nei piani `sky.png` (skyline-a, skyline-b senza il pianeta ad anelli), `far.png` (buildings-bg quattro volte, diritto e specchiato, più la torre cyan disegnata da noi) e `mid.png` (i cinque palazzi di near-buildings-bg in posizioni fisse) di `game/assets/env/sotto_la_linea/`.
