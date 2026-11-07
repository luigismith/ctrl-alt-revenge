# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""Genera gli elementi d'interfaccia (PNG) e ui.json in tools/fxui/out/assets/ui/.

  python -I tools/fxui/make_ui.py

Tutto è disegnato da codice alla risoluzione del gioco, senza ingrandimenti.
Le scritte grandi usano bigfont/title; quelle variabili (nomi, punteggio, menu) restano
al font CAR Pixel e qui compaiono solo nella disposizione consigliata dell'HUD.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bigfont  # noqa: E402
import palette as P  # noqa: E402
import pix  # noqa: E402
import logo  # noqa: E402
import title  # noqa: E402

OUT = HERE / "out" / "assets" / "ui"

GOLD_FILL = [P.GOLD_HI, P.GOLD, P.GOLD_LO]
ORANGE_FILL = [P.ORANGE_HI, P.ORANGE, P.ORANGE_LO]
MSG = title.Style(outline_w=2, extrude_n=1, shadow_d=(1, 2), bands=[0.0, 0.2, 0.68])
SUB = title.Style(fill=ORANGE_FILL, bands=[0.0, 0.25, 0.75], top_light=None, outline=P.INK,
                  outline_w=1, extrude=None, extrude_n=0, shadow=P.INK, shadow_d=(0, 1))


def hexs(c) -> str:
    return "#%02x%02x%02x" % c[:3]


# ------------------------------------------------------------------------------------
# scritte
# ------------------------------------------------------------------------------------

def make_logo() -> np.ndarray:
    # dal 7 novembre 2026 il logo è quello di logo.py (tasti e street art); la variante la sceglie Luigi
    return logo.logo(logo.VARIANTI[logo.SCELTA])


def make_subtitle() -> np.ndarray:
    return logo.sottotitolo(logo.VARIANTI[logo.SCELTA])


def make_stage_card(text: str = "1 · SOTTO LA LINEA") -> np.ndarray:
    return title.render([text], bigfont.metrics(20), MSG, fills={0: GOLD_FILL, 2: ORANGE_FILL})


def make_msg(text: str, H: int = 24) -> np.ndarray:
    return title.render([text], bigfont.metrics(H), MSG)


def make_big_digits(H: int = 24) -> tuple[np.ndarray, list[int]]:
    """Cifre 0-9 grandi nello stile di msg_* (stessa altezza, bordo, estrusione e ombra), su una striscia di
    10 fotogrammi larghi uguali, ogni cifra centrata nel suo: per il conto alla rovescia di CONTINUA?, che
    così non usa il font a scala 2 (pixel 2x2 accanto ai pixel 1x)."""
    imgs = [title.render([str(d)], bigfont.metrics(H), MSG, fills={0: GOLD_FILL}) for d in range(10)]
    fw = max(im.shape[1] for im in imgs)
    fh = max(im.shape[0] for im in imgs)
    strip = np.zeros((fh, fw * 10, 4), np.uint8)
    for d, im in enumerate(imgs):
        x = d * fw + (fw - im.shape[1]) // 2
        y = fh - im.shape[0]
        strip[y:y + im.shape[0], x:x + im.shape[1]] = im
    return strip, [fw, fh]


# ------------------------------------------------------------------------------------
# freccia VAI
# ------------------------------------------------------------------------------------

def _arrow_parts(dim: bool, shift: int) -> np.ndarray:
    """VAI + triangolo, con lo stesso trattamento delle scritte (bordo, estrusione, ombra)."""
    m = bigfont.metrics(16)
    st = title.BANNER
    gap = 2 * st.outline_w + 1
    tm, tw = bigfont.text_mask("VAI", m, gap)
    th = m.H + 6                      # il triangolo sporge di 3 px sopra e sotto il testo
    tri_w = th // 2                   # lati a 45 gradi: gradini di 1 px
    tri = pix.poly_mask(tri_w, th, [[(0, 0), (tri_w, th / 2), (0, th)]])
    pad = st.outline_w + st.extrude_n + max(st.shadow_d) + 4
    ax = tw + 6
    W = ax + 4 + tri_w + 2 * pad
    H = max(tm.shape[0], th) + 2 * pad
    F_text = np.zeros((H, W), bool)
    F_tri = np.zeros((H, W), bool)
    F_text[pad + 3:pad + 3 + tm.shape[0], pad:pad + tw] = tm
    F_tri[pad:pad + th, pad + ax + shift:pad + ax + shift + tri_w] = tri
    F = F_text | F_tri
    O = pix.dilate(F, st.outline_w, square=True)
    E = pix.shift(O, 0, 1) & ~O
    body = O | E
    SH = pix.shift(body, *st.shadow_d) & ~body
    img = pix.new(W, H)

    def darker(c, k=0.55):
        return (int(c[0] * k), int(c[1] * k), int(c[2] * k), 255)

    cream = [P.CREAM_HI, P.CREAM, P.CREAM_LO]
    gold = GOLD_FILL
    outline, extrude = P.RED_DARK, P.RED_DEEP
    if dim:
        cream = [darker(c) for c in cream]
        gold = [darker(c) for c in gold]
        outline, extrude = darker(outline, 0.7), darker(extrude, 0.7)
    pix.paint(img, SH, P.INK)
    pix.paint(img, E, extrude)
    pix.paint(img, O & ~F, outline)
    for F_, cols, y0, hh in ((F_text, cream, pad + 3, m.H), (F_tri, gold, pad, th)):
        ys = np.arange(H)[:, None] - y0
        band = np.where(ys < 0.2 * hh, 0, np.where(ys < 0.68 * hh, 1, 2))
        band = np.broadcast_to(band, (H, W))
        for i, c in enumerate(cols):
            pix.paint(img, F_ & (band == i), c)
    top = F_text & ~pix.shift(F_text, 0, 1)
    pix.paint(img, top, cream[0])
    return img


def make_go_arrow() -> tuple[np.ndarray, list[int], int]:
    frames = [_arrow_parts(False, 0), _arrow_parts(False, 3), _arrow_parts(True, 0)]
    h = max(f.shape[0] for f in frames)
    w = max(f.shape[1] for f in frames)
    fr = []
    for f in frames:
        c = pix.new(w, h)
        pix.over(c, f, 0, 0)
        fr.append(c)
    # ritaglio comune (stessa origine per tutti i fotogrammi)
    union = np.zeros((h, w), bool)
    for f in fr:
        union |= f[..., 3] > 0
    x0, y0, x1, y1 = pix.bbox(union)
    fr = [f[y0:y1, x0:x1] for f in fr]
    return pix.strip(fr), [x1 - x0, y1 - y0], 3


# ------------------------------------------------------------------------------------
# ritratto
# ------------------------------------------------------------------------------------

def make_portrait_back() -> np.ndarray:
    """Fondo da mettere DIETRO al ritratto 32x32: schermo scuro con righe di scansione."""
    img = pix.new(34, 34)
    tops = [pix.hexc("#2f2452"), pix.hexc("#271e46"), pix.hexc("#20183a"), pix.hexc("#1a1430")]
    for y in range(1, 33):
        c = tops[min(3, (y - 1) // 8)]
        if y % 2 == 0:
            c = (max(0, c[0] - 6), max(0, c[1] - 5), max(0, c[2] - 8), 255)
        img[y, 1:33] = c
    return img


def make_portrait_frame(light, dark, accent) -> np.ndarray:
    """Cornice 34x34 con il foro 32x32 in (1, 1): bordo smussato e staffe agli angoli."""
    img = pix.new(34, 34)
    img[0, 1:33] = light
    img[1:33, 0] = light
    img[33, 1:33] = dark
    img[1:33, 33] = dark
    # staffe a L negli angoli, sopra al bordo del ritratto (3 px per lato)
    for (cx, cy, sx, sy) in ((1, 1, 1, 1), (32, 1, -1, 1), (1, 32, 1, -1), (32, 32, -1, -1)):
        for k in range(3):
            img[cy, cx + sx * k] = accent
            img[cy + sy * k, cx] = accent
    return img


# ------------------------------------------------------------------------------------
# barre della vita (9-slice)
# ------------------------------------------------------------------------------------

def strip_rows(w: int, rows: list) -> np.ndarray:
    """Striscia di riempimento larga w: una riga per colore (luce in alto, ombra in basso)."""
    img = pix.new(w, len(rows))
    for i, c in enumerate(rows):
        img[i, :] = c
    return img


def bar_rows(cols: list, inner: int) -> list:
    if inner == 6:
        return [cols[0], cols[1], cols[1], cols[2], cols[3], cols[4]]
    if inner == 4:
        return [cols[0], cols[1], cols[2], cols[4]]
    raise ValueError(inner)


def bar_frame(w: int, h: int, light, dark) -> np.ndarray:
    """Cornice di 2 px attorno a un'area w x h: anello esterno scuro, interno a rilievo.

    L'immagine è (w + 4) x (h + 4), con l'interno trasparente: va disegnata SOPRA alla
    barra, spostata di (-2, -2). Gli angoli esterni sono smussati.
    """
    W, H = w + 4, h + 4
    img = pix.new(W, H)
    img[0, 1:W - 1] = P.INK
    img[H - 1, 1:W - 1] = P.INK
    img[1:H - 1, 0] = P.INK
    img[1:H - 1, W - 1] = P.INK
    img[1, 1:W - 1] = light
    img[1:H - 1, 1] = light
    img[H - 2, 2:W - 1] = dark
    img[2:H - 1, W - 2] = dark
    return img


# ------------------------------------------------------------------------------------
# principale
# ------------------------------------------------------------------------------------

BAR_W = 104


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    ui = {
        "format": 1,
        "note": ("Elementi d'interfaccia di CTRL+ALT REVENGE, in px del gioco (480x270). Ogni chiave "
                 "è un elemento con 'image' e 'size'; nine_slice = margini [sinistra, sopra, destra, "
                 "sotto] da non stirare; frame/count/ticks = striscia orizzontale di fotogrammi da "
                 "'frame' px, ognuno per 'ticks' tick a 60 Hz. Le chiavi 'fonts', 'colors' e "
                 "'hud_layout' non sono immagini. Le scritte variabili usano i font di "
                 "res://assets/fonts/ (vedi il README lì)."),
    }

    def put(name: str, file: str, img: np.ndarray, **extra):
        pix.save(img, OUT / file)
        d = {"image": file, "size": [int(img.shape[1]), int(img.shape[0])]}
        d.update(extra)
        ui[name] = d

    # --- titolo e scritte grandi ---
    put("logo", "title_logo.png", make_logo(),
        note="Logo del titolo (tools/fxui/logo.py): tasti CTRL e ALT, REVENGE! a spray; contorno, rilievo e colature compresi.")
    put("subtitle", "title_subtitle.png", make_subtitle(),
        note="Sottotitolo TARANTO · 2087 fra due trattini, da centrare sotto il logo (2-4 px sotto).")
    put("stage_card_1", "stage_card_1.png", make_stage_card(),
        note="Cartello d'inizio del livello 1 ('1' oro, punto arancio), da centrare sullo schermo.")
    put("stage_card_2", "stage_card_2.png", make_stage_card("2 · IL WIND DAY"),
        note="Cartello d'inizio del capitolo 2 ('2' oro, punto arancio), da centrare sullo schermo.")
    put("msg_zone_clear", "msg_zone_clear.png", make_msg("ZONA LIBERATA"), note="Fine del livello.")
    put("msg_pause", "msg_pause.png", make_msg("PAUSA"), note="Pausa (sopra al menu).")
    put("msg_continue", "msg_continue.png", make_msg("CONTINUA?"), note="Dopo l'ultima vita.")
    put("msg_game_over", "msg_game_over.png", make_msg("GAME OVER"),
        note="Facoltativo: se il conto alla rovescia di CONTINUA? arriva a zero.")
    put("msg_demo_end", "msg_demo_end.png", make_msg("FINE DELLA DEMO"), note="Schermata finale.")
    digits, dframe = make_big_digits()
    put("big_digits", "big_digits.png", digits, frame=dframe, count=10, ticks=1,
        note=("Cifre 0-9 grandi in oro, stesso stile di msg_*: striscia di 10 fotogrammi, il fotogramma k è la "
              "cifra k (non un'animazione). Conto alla rovescia di CONTINUA?, centrato a 1x."))

    arrow, fsize, count = make_go_arrow()
    put("go_arrow", "go_arrow.png", arrow, frame=fsize, count=count, ticks=8, loop=True,
        note=("Freccia VAI: fotogrammi 0 = accesa, 1 = triangolo spinto avanti di 3 px, 2 = "
              "spenta (scurita). In ciclo 0-1-2, 8 tick ciascuno. Bordo destro dello schermo, "
              "nella parte alta del campo (vedi hud_layout)."))

    # --- ritratto ---
    put("portrait_frame", "portrait_frame.png", make_portrait_frame(P.CREAM, P.GOLD_LO, P.GOLD),
        inner=[1, 1, 32, 32],
        note=("Cornice 34x34 di GIG: va SOPRA al ritratto 32x32, che sta in (1, 1) rispetto alla "
              "cornice. Le staffe agli angoli coprono 3 px di ogni angolo del ritratto."))
    put("portrait_frame_enemy", "portrait_frame_enemy.png",
        make_portrait_frame(P.BAR_ENEMY[1], P.BAR_ENEMY[4], P.BAR_ENEMY[0]), inner=[1, 1, 32, 32],
        note="Come portrait_frame, nei rossi dei nemici (facoltativa).")
    put("portrait_back", "portrait_back.png", make_portrait_back(), inner=[1, 1, 32, 32],
        note="Fondo 'schermo' da disegnare DIETRO al ritratto, se il ritratto ha parti trasparenti.")

    # --- barre: pezzi da comporre (fondo, scia del danno, riempimento, cornice sopra) ---
    W = BAR_W
    fill_note = ("Striscia uniforme in orizzontale: si disegna la parte sinistra larga quanto la "
                 "vita (regione (0, 0, larghezza, altezza)), oppure la si stira in larghezza.")
    put("bar_back", "bar_back.png", strip_rows(W, bar_rows(P.BAR_EMPTY, 6)), nine_slice=[0, 0, 0, 0],
        note="Barra di GIG, fondo vuoto 104x6. " + fill_note)
    put("bar_ghost", "bar_ghost.png", strip_rows(W, bar_rows(P.BAR_GHOST, 6)), nine_slice=[0, 0, 0, 0],
        note="Scia del danno appena subito (scende in ritardo), sotto a bar_fill. " + fill_note)
    put("bar_fill", "bar_fill.png", strip_rows(W, bar_rows(P.BAR_GIG, 6)), nine_slice=[0, 0, 0, 0],
        note="Vita di GIG, giallo-ocra. " + fill_note)
    put("bar_frame", "bar_frame.png", bar_frame(W, 6, P.CREAM, P.CREAM_LO2), nine_slice=[2, 2, 2, 2],
        inner=[2, 2, W, 6],
        note=("Cornice della barra di GIG, 108x10 con l'interno trasparente: va SOPRA ai pezzi, "
              "in (x - 2, y - 2) se la barra sta in (x, y). Per altre lunghezze: 9-slice."))
    put("bar_back_enemy", "bar_back_enemy.png", strip_rows(W, bar_rows(P.BAR_EMPTY, 4)),
        nine_slice=[0, 0, 0, 0], note="Barra del nemico, fondo vuoto 104x4. " + fill_note)
    put("bar_ghost_enemy", "bar_ghost_enemy.png", strip_rows(W, bar_rows(P.BAR_GHOST, 4)),
        nine_slice=[0, 0, 0, 0], note="Scia del danno del nemico. " + fill_note)
    put("bar_fill_enemy", "bar_fill_enemy.png", strip_rows(W, bar_rows(P.BAR_ENEMY, 4)),
        nine_slice=[0, 0, 0, 0], note="Vita del nemico, rossa. " + fill_note)
    put("bar_frame_enemy", "bar_frame_enemy.png", bar_frame(W, 4, P.METAL_HI, P.METAL_LO),
        nine_slice=[2, 2, 2, 2], inner=[2, 2, W, 4],
        note="Cornice della barra del nemico, 108x8, come bar_frame.")

    ui["fonts"] = {
        "bold": {"file": "res://assets/fonts/car_pixel_bold.ttf", "size": 12,
                 "use": "nomi, punteggio, vite, voci dei menu, avvisi brevi"},
        "regular": {"file": "res://assets/fonts/car_pixel_regular.ttf", "size": 12,
                    "use": "testi lunghi e con le minuscole, crediti, licenze"},
    }
    ui["colors"] = {
        "text": hexs(P.CREAM),
        "text_dim": hexs(P.CREAM_LO2),
        "score": hexs(P.GOLD_HI),
        "lives": hexs(P.GOLD_HI),
        "menu_selected": hexs(P.GOLD_HI),
        "menu_other": hexs(P.CREAM),
        "accent_orange": hexs(P.ORANGE),
        "accent_red": hexs(P.RED_DARK),
        "shadow": hexs(P.INK),
    }
    ui["hud_layout"] = {
        "note": ("Disposizione del mockup (tools/fxui/out/check/hud_mockup_*.png), in coordinate "
                 "dello schermo. Testi: angolo in alto a sinistra della riga del font a 12 px "
                 "(le maiuscole occupano le righe 3-9), con ombra di 1 px in basso a destra; "
                 "'_right' = testo allineato a destra su quella x. Barre: (x, y, larghezza, altezza) "
                 "dell'area colorata; la cornice va in (x - 2, y - 2)."),
        "portrait_frame": [6, 4],
        "portrait": [7, 5],
        "gig_name": [44, 2],
        "gig_lives_right": [152, 2],
        "gig_bar": [46, 15, W, 6],
        "enemy_name": [44, 21],
        "enemy_bar": [46, 34, W, 4],
        "score_right": [474, 2],
        "go_arrow_right_center_y": [477, 80],
    }
    (OUT / "ui.json").write_text(json.dumps(ui, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ui


def elements(ui: dict) -> dict:
    return {k: v for k, v in ui.items() if isinstance(v, dict) and "image" in v}


if __name__ == "__main__":
    ui = build()
    for k, v in elements(ui).items():
        print(f"{k:22s} {v['image']:26s} {v['size']}")
