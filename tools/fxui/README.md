# tools/fxui: effetti visivi, interfaccia e font

Script Python (MIT) che disegnano gli effetti, l'interfaccia e i font del gioco alla risoluzione nativa (480×270; fino al 5 novembre 2026 era 384×216). Non usano AI generativa né file scaricati. Gli script sono deterministici: semi fissi, niente antialiasing, PNG e TTF identici a ogni esecuzione.

```
python -I tools/fxui/build_all.py                    # genera tutto in tools/fxui/out/
python -I tools/fxui/build_all.py --godot            # più le verifiche in Godot 4.7.2
python -I tools/fxui/build_all.py --godot --install  # e installa in game/assets/
```

Usare il Python del laboratorio (`%USERPROFILE%\ctrlaltrevenge-lab\venv\Scripts\python.exe`, con Pillow, NumPy e SciPy). Godot si lancia sempre tramite `tools/run_godot.sh`, su un progetto temporaneo in `out/godot_check/` con le stesse impostazioni di `game/project.godot`. Il progetto `game/` non viene mai aperto.

| File | Cosa fa |
|---|---|
| `pix.py` | utilità: rasterizzazione di poligoni sul centro dei pixel, dilatazioni, retinature, composizione |
| `palette.py` | colori; quelli del logo sono misurati sulla locandina |
| `font_glyphs.py` | glifi dei font CAR Pixel: regolare disegnato a mano, grassetto derivato e corretto a mano |
| `bitfont.py` | disegna testo con quei glifi, con lo stesso risultato del TTF a 1x |
| `ttf.py` | scrive e rilegge TTF con contorni rettilinei, senza librerie esterne |
| `make_fonts.py` | costruisce i due TTF e li verifica (andata e ritorno esatti, poi FreeType) |
| `bigfont.py`, `title.py` | lettering a blocchi parametrico e stile della locandina (riempimento a fasce, bordo, estrusione, ombra) |
| `make_ui.py` | logo, sottotitolo, cartello del livello, scritte, freccia VAI, ritratto, barre, `ui.json` |
| `make_fx.py` | scintille, polvere, glint, scarica cyber, ombre, pioggia, lampo del KO, `fx.json` |
| `make_sheets.py` | tavole degli effetti a 4x |
| `make_mockups.py` | mockup a 1x e 3x: HUD in scena e su fondo scuro, titolo, scritte |
| `godot_check.py`, `hud_check.py`, `godot/*.gd` | verifiche in Godot: font pixel per pixel, HUD pixel per pixel contro il mockup |
| `build_all.py` | esegue tutto; con `--install` copia negli asset del gioco (nome temporaneo, poi rinomina) |
| `docs_assets/` | README e `font.json` che vanno accanto agli asset |
