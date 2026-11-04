# Font dell'interfaccia: CAR Pixel

Due font pixel disegnati apposta per il gioco e generati da `tools/fxui/make_fonts.py`:

| File | Nome | Uso consigliato |
|---|---|---|
| `car_pixel_bold.ttf` | CAR Pixel Bold | nomi, punteggio, vite, voci dei menu, avvisi brevi |
| `car_pixel_regular.ttf` | CAR Pixel Regular | testi lunghi con le minuscole, crediti, licenze |

**Glifi**: ASCII completo; lettere accentate italiane à è é ì ò ù À È É Ì Ò Ù, più á í ó ú Á Í Ó Ú; × · ° « » © ‘ ’ “ ” … – — ▶ ◀ ▲ ▼ ♥.

**Misure**:
- maiuscole e cifre alte 7 px, minuscole con occhio di 5 px, discendenti di 2 px;
- gli accenti delle maiuscole arrivano a 10 px sopra la linea di base;
- ascendente 10 px e discendente 2 px: una riga è alta 12 px;
- larghezze: regolare 5 px più 1 di spazio, grassetto 6 px più 1 (M, N, W 7 px);
- le cifre sono tutte larghe uguali, così il punteggio non balla.

## Come usarlo in Godot 4.7

- **Dimensione esatta: 12** (`font_size` = 12). Così un pixel del font è un pixel del gioco. Per scritte più grandi usare solo i multipli: 24, 36, 48. Qualunque altra misura deforma i pixel.
- **Importazione**: le impostazioni sono già nei file `.import` accanto ai TTF. Nel pannello Importa di Godot:
  - Antialiasing: **Nessuno** (`antialiasing=0`);
  - Hinting: **Nessuno** (`hinting=0`);
  - Posizionamento subpixel: **Disattivato** (`subpixel_positioning=0`);
  - niente mipmap, niente MSDF, niente fallback di sistema.
- Le stesse impostazioni si possono forzare da codice (lo fa già `src/ui/ui_font.gd`):

  ```gdscript
  var font := load("res://assets/fonts/car_pixel_bold.ttf") as FontFile
  font.antialiasing = TextServer.FONT_ANTIALIASING_NONE
  font.hinting = TextServer.HINTING_NONE
  font.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
  label.add_theme_font_override("font", font)
  label.add_theme_font_size_override("font_size", 12)
  ```

- **Perché l'hinting va su "Nessuno"**: con l'hinting "Leggero", che Godot usa di solito per i TTF importati, FreeType sposta di un pixel gli accenti del regolare. In `tools/fxui/out/godot_font_check_diff_3x.png` la riga verde mostra l'effetto.
- **Posizioni intere**: Label e `draw_string` vanno su coordinate intere (lo snap 2D del progetto aiuta). La linea di base sta 10 px sotto il bordo superiore della riga; le maiuscole occupano le righe 3-9 della riga.
- **Ombra del testo**: per un'ombra netta di 1 px usare `shadow_offset_x` = 1, `shadow_offset_y` = 1 e `shadow_outline_size` = 0. In Godot l'ombra cade esattamente a +1,+1. Meglio evitare `outline_size`: il contorno di FreeType non segue la griglia dei pixel.
- **`font.json`**: indica a `UiFont` il file e la dimensione predefiniti (grassetto, 12). Ha anche i dati del regolare.

## Verifica

- `python -I tools/fxui/make_fonts.py`
  - rilegge i TTF senza FreeType e ne rasterizza i contorni, che devono coincidere pixel per pixel col disegno, avanzamenti compresi;
  - poi FreeType, tramite Pillow, deve caricarli e disegnare ogni glifo.
- `python -I tools/fxui/godot_check.py fonts`
  - in Godot 4.7.2, in un progetto temporaneo con le stesse impostazioni di `game/`, scrive sette frasi con tutti i glifi in entrambi i font;
  - risultato: 8560 pixel di testo su 8560 uguali al disegno, e l'ombra di un Label esattamente a +1,+1.

## Licenza

È un asset originale del gioco, disegnato da script per CTRL+ALT REVENGE: `LicenseRef-CAR-Assets` (vedi `LICENSES/LicenseRef-CAR-Assets.txt`). Non è un font di terze parti, quindi non serve il testo dell'OFL.
