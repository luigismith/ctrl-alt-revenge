#!/usr/bin/env python3
"""
SPRITE STUDIO — Tool per progettare, visualizzare e validare sprite pixel-art.

Funzionalità:
1. Renderizza TUTTI gli sprite su un foglio a zoom 8x per ispezione pixel-per-pixel
2. Mostra palette colori usata da ogni personaggio
3. Verifica dimensioni uniformi, trasparenza angoli, outline presente
4. Esporta sprite sheet PNG per reference
5. Modalità "design grid" — griglia interattiva per disegnare nuovi sprite

Uso: python tools/sprite_studio.py [--export] [--validate] [--preview]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.init()
screen = pygame.display.set_mode((100, 100))

from ctrl_alt_revenge.core.sprite_generator import generate_all_sprites

ZOOM = 6  # Ogni pixel dello sprite diventa 6x6 nella preview
PADDING = 4
BG_COLOR = (40, 35, 60)
GRID_COLOR = (60, 55, 80)
LABEL_COLOR = (200, 200, 220)
WARN_COLOR = (255, 80, 80)
OK_COLOR = (80, 255, 120)


def render_sprite_zoomed(sprite, zoom=ZOOM):
    """Renderizza uno sprite a zoom Nx con griglia pixel."""
    w, h = sprite.get_size()
    out = pygame.Surface((w * zoom + 1, h * zoom + 1))
    out.fill(BG_COLOR)

    for py in range(h):
        for px in range(w):
            color = sprite.get_at((px, py))
            if color.a > 0:
                rect = (px * zoom, py * zoom, zoom, zoom)
                pygame.draw.rect(out, (color.r, color.g, color.b), rect)
            # Griglia
            if zoom >= 4:
                pygame.draw.rect(out, GRID_COLOR,
                                (px * zoom, py * zoom, zoom, zoom), 1)
    return out


def analyze_sprite(sprite, name=""):
    """Analizza uno sprite e restituisce un report."""
    w, h = sprite.get_size()
    colors = set()
    opaque_pixels = 0
    has_outline = False
    corner_transparent = True

    for py in range(h):
        for px in range(w):
            c = sprite.get_at((px, py))
            if c.a > 0:
                colors.add((c.r, c.g, c.b))
                opaque_pixels += 1
                # Check outline (dark pixels on edges of opaque regions)
                if c.r < 20 and c.g < 20 and c.b < 30:
                    has_outline = True

    # Check corners
    for pos in [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]:
        if sprite.get_at(pos).a > 0:
            corner_transparent = False

    fill_ratio = opaque_pixels / (w * h) if w * h > 0 else 0

    return {
        "name": name,
        "size": (w, h),
        "colors": len(colors),
        "opaque_pixels": opaque_pixels,
        "fill_ratio": fill_ratio,
        "has_outline": has_outline,
        "corner_transparent": corner_transparent,
        "palette": sorted(colors, key=lambda c: c[0] + c[1] + c[2]),
    }


def create_sprite_sheet(sprites_dict, character_name, zoom=ZOOM):
    """Crea un foglio con tutte le animazioni di un personaggio."""
    font = pygame.font.SysFont("consolas", 11)

    # Filtra solo animazioni _right (le _left sono specchiate)
    right_anims = {k: v for k, v in sprites_dict.items() if "_right" in k}
    if not right_anims:
        right_anims = sprites_dict

    # Calcola dimensioni del foglio
    max_frames = max(len(v) for v in right_anims.values())
    sprite_w, sprite_h = list(right_anims.values())[0][0].get_size()

    cell_w = sprite_w * zoom + PADDING * 2
    cell_h = sprite_h * zoom + PADDING * 2 + 16  # +16 per label

    num_anims = len(right_anims)
    sheet_w = max(cell_w * max_frames + 200, 600)  # 200 per label colonna
    sheet_h = cell_h * num_anims + 60  # +60 per header

    sheet = pygame.Surface((sheet_w, sheet_h))
    sheet.fill((25, 22, 45))

    # Header
    title = font.render(f"=== {character_name.upper()} ===  ({sprite_w}x{sprite_h}px)", True, LABEL_COLOR)
    sheet.blit(title, (10, 8))

    # Righe per animazione
    y_offset = 40
    for anim_name, frames in sorted(right_anims.items()):
        # Label animazione
        short_name = anim_name.replace("_right", "")
        label = font.render(f"{short_name} [{len(frames)}f]", True, LABEL_COLOR)
        sheet.blit(label, (10, y_offset + cell_h // 2 - 6))

        # Frame
        for fi, frame in enumerate(frames):
            zoomed = render_sprite_zoomed(frame, zoom)
            fx = 180 + fi * (cell_w + 4)
            fy = y_offset + PADDING
            sheet.blit(zoomed, (fx, fy))

            # Frame number
            fnum = font.render(f"f{fi}", True, (140, 140, 160))
            sheet.blit(fnum, (fx, fy + sprite_h * zoom + 2))

        y_offset += cell_h + 2

    return sheet


def create_palette_sheet(analysis_list):
    """Crea un foglio che mostra le palette di ogni personaggio."""
    font = pygame.font.SysFont("consolas", 11)

    line_h = 20
    swatch_size = 14
    sheet_h = len(analysis_list) * (line_h + 10) + 40
    sheet_w = 800

    sheet = pygame.Surface((sheet_w, sheet_h))
    sheet.fill((25, 22, 45))

    title = font.render("=== PALETTE ANALYSIS ===", True, LABEL_COLOR)
    sheet.blit(title, (10, 8))

    y = 32
    for analysis in analysis_list:
        name = analysis["name"]
        palette = analysis["palette"]

        label = font.render(f"{name}: {analysis['colors']} colors, "
                           f"fill={analysis['fill_ratio']:.0%}, "
                           f"outline={'Y' if analysis['has_outline'] else 'N'}, "
                           f"corners={'OK' if analysis['corner_transparent'] else 'BAD'}",
                           True, OK_COLOR if analysis['has_outline'] and analysis['corner_transparent'] else WARN_COLOR)
        sheet.blit(label, (10, y))

        # Swatches
        for i, color in enumerate(palette[:20]):  # max 20 colori
            sx = 10 + i * (swatch_size + 2)
            sy = y + 14
            pygame.draw.rect(sheet, color, (sx, sy, swatch_size, swatch_size))
            pygame.draw.rect(sheet, (80, 80, 100), (sx, sy, swatch_size, swatch_size), 1)

        y += line_h + 18

    return sheet


def create_comparison_sheet(all_sprites, zoom=4):
    """Crea un foglio di confronto con tutti i personaggi idle fianco a fianco a 1x e Nx."""
    font = pygame.font.SysFont("consolas", 12)

    chars = ["gig", "thug", "drone", "warden"]
    sheet_w = 900
    sheet_h = 400
    sheet = pygame.Surface((sheet_w, sheet_h))
    sheet.fill((25, 22, 45))

    title = font.render("=== CHARACTER COMPARISON (idle frame 0, right) ===", True, LABEL_COLOR)
    sheet.blit(title, (10, 8))

    x_offset = 20
    for char_name in chars:
        data = all_sprites.get(char_name)
        if not data:
            continue

        idle_key = "idle_right" if "idle_right" in data else "fly_right"
        if idle_key not in data:
            continue

        frame = data[idle_key][0]
        fw, fh = frame.get_size()

        # Label
        label = font.render(f"{char_name} ({fw}x{fh})", True, LABEL_COLOR)
        sheet.blit(label, (x_offset, 30))

        # 1x (actual size)
        sheet.blit(frame, (x_offset, 50))
        l1x = font.render("1x", True, (100, 100, 120))
        sheet.blit(l1x, (x_offset, 50 + fh + 2))

        # 3x
        scaled_3x = pygame.transform.scale(frame, (fw * 3, fh * 3))
        sheet.blit(scaled_3x, (x_offset, 80 + fh))
        l3x = font.render("3x", True, (100, 100, 120))
        sheet.blit(l3x, (x_offset, 80 + fh + fh * 3 + 2))

        # Zoomed with grid
        zoomed = render_sprite_zoomed(frame, zoom)
        zy = 100 + fh + fh * 3 + 20
        if zy + fh * zoom < sheet_h:
            sheet.blit(zoomed, (x_offset, zy))

        x_offset += max(fw * zoom + 20, fw * 3 + 20, 180)

    return sheet


def main():
    print("=== SPRITE STUDIO ===")
    print()

    # Genera tutti gli sprite
    print("Generando sprite...")
    all_sprites = generate_all_sprites()

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(out_dir, exist_ok=True)

    # === VALIDAZIONE ===
    print("\n--- VALIDAZIONE ---")
    all_analyses = []

    for char_name in ["gig", "thug", "drone", "warden"]:
        data = all_sprites.get(char_name, {})

        # Check dimensioni uniformi
        sizes = set()
        for anim_name, frames in data.items():
            for f in frames:
                sizes.add(f.get_size())

        size_ok = len(sizes) <= 1
        print(f"  {char_name}: sizes={sizes} {'OK' if size_ok else 'WARN: non-uniform!'}")

        # Analizza primo frame idle
        idle_key = "idle_right" if "idle_right" in data else "fly_right"
        if idle_key in data:
            analysis = analyze_sprite(data[idle_key][0], f"{char_name}_idle")
            all_analyses.append(analysis)
            print(f"    colors={analysis['colors']}, fill={analysis['fill_ratio']:.0%}, "
                  f"outline={'YES' if analysis['has_outline'] else 'NO'}, "
                  f"corners={'transparent' if analysis['corner_transparent'] else 'OPAQUE!'}")

        # Count totale animazioni e frame
        total_frames = sum(len(v) for v in data.items())
        right_anims = sum(1 for k in data if "_right" in k)
        print(f"    animations: {right_anims} (right), total entries: {len(data)}")

    # === ESPORTAZIONE SPRITE SHEETS ===
    print("\n--- ESPORTAZIONE ---")

    for char_name in ["gig", "thug", "drone", "warden"]:
        data = all_sprites.get(char_name, {})
        sheet = create_sprite_sheet(data, char_name)
        path = os.path.join(out_dir, f"sheet_{char_name}.png")
        pygame.image.save(sheet, path)
        print(f"  {path}")

    # Palette analysis
    palette_sheet = create_palette_sheet(all_analyses)
    path = os.path.join(out_dir, "palette_analysis.png")
    pygame.image.save(palette_sheet, path)
    print(f"  {path}")

    # Comparison
    comparison = create_comparison_sheet(all_sprites)
    path = os.path.join(out_dir, "comparison.png")
    pygame.image.save(comparison, path)
    print(f"  {path}")

    # === SINGOLI SPRITE A ZOOM MASSIMO ===
    print("\n--- ZOOM DETTAGLIO ---")
    for char_name in ["gig", "thug", "drone", "warden"]:
        data = all_sprites.get(char_name, {})
        idle_key = "idle_right" if "idle_right" in data else "fly_right"
        if idle_key in data:
            zoomed = render_sprite_zoomed(data[idle_key][0], zoom=12)
            path = os.path.join(out_dir, f"zoom_{char_name}.png")
            pygame.image.save(zoomed, path)
            print(f"  {path}")

    print(f"\nTutto esportato in: {out_dir}")
    pygame.quit()


if __name__ == "__main__":
    main()
