#!/usr/bin/env python3
"""
convert_sprites.py - Convert CTRL+ALT REVENGE sprites to Game Boy Color tile data.

Generates GBDK-compatible C header files with tile data, palettes, and
background tiles for a GBC port.

GBC specs used:
  - Tiles: 8x8 pixels, 2bpp (4 colors per palette)
  - Sprites: 8x8 mode, up to 40 on screen
  - Palette: 15-bit RGB (5 bits/channel), little-endian uint16
"""

import sys
import os

# Add project root so we can import the game modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Pygame needs to be initialized before sprite generation
import pygame
pygame.init()

from ctrl_alt_revenge.core.sprite_generator import generate_all_sprites

# ---------------------------------------------------------------------------
# GBC palette definitions (24-bit RGB)
# ---------------------------------------------------------------------------

# Sprite palettes: index 0 = transparent, indices 1-3 = visible colors
SPRITE_PALETTES = {
    "PAL_GIG": [
        (0, 0, 0),         # transparent (ignored by hardware)
        (210, 170, 130),   # skin
        (180, 120, 50),    # jacket_brown
        (0, 229, 255),     # cyber_blue
    ],
    "PAL_THUG": [
        (0, 0, 0),
        (190, 150, 110),   # skin
        (60, 20, 20),      # shirt_dark
        (255, 46, 77),     # bandana_red
    ],
    "PAL_DRONE": [
        (0, 0, 0),
        (70, 75, 90),      # gray_body
        (255, 46, 77),     # red_eye
        (0, 229, 255),     # blue_accent
    ],
    "PAL_WARDEN": [
        (0, 0, 0),
        (40, 45, 60),      # armor_gray
        (255, 46, 77),     # visor_red
        (255, 122, 26),    # trim_orange
    ],
}

# BG palettes: all 4 colors visible
BG_PALETTES = {
    "PAL_BG_GROUND": [
        (13, 11, 43),      # night
        (40, 20, 80),      # dark_purple
        (80, 50, 130),     # mid_purple
        (160, 140, 200),   # light
    ],
    "PAL_BG_NEON": [
        (13, 11, 43),      # night
        (30, 28, 50),      # dark
        (0, 229, 255),     # cyan
        (255, 255, 255),   # white
    ],
    "PAL_BG_BOSS": [
        (13, 11, 43),      # night
        (120, 20, 20),     # dark_red
        (255, 122, 26),    # orange
        (255, 230, 50),    # yellow
    ],
}


def rgb_to_gbc(r, g, b):
    """Convert 24-bit RGB to 15-bit GBC color (little-endian uint16)."""
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def color_distance(c1, c2):
    """Squared Euclidean distance between two RGB tuples."""
    return sum((a - b) ** 2 for a, b in zip(c1, c2))


def nearest_palette_index(pixel_rgba, palette, is_sprite=True):
    """Map an RGBA pixel to the nearest palette index.

    For sprites, transparent pixels (alpha < 128) map to index 0.
    Opaque pixels map to indices 1-3 (sprite) or 0-3 (BG).
    """
    r, g, b = pixel_rgba[0], pixel_rgba[1], pixel_rgba[2]
    a = pixel_rgba[3] if len(pixel_rgba) > 3 else 255

    if is_sprite and a < 128:
        return 0  # transparent

    start = 1 if is_sprite else 0
    best_idx = start
    best_dist = float("inf")
    for i in range(start, 4):
        d = color_distance((r, g, b), palette[i])
        if d < best_dist:
            best_dist = d
            best_idx = i
    return best_idx


def surface_to_pixels(surface):
    """Extract RGBA pixel data from a pygame Surface as a 2D list."""
    w, h = surface.get_size()
    pixels = []
    for y in range(h):
        row = []
        for x in range(w):
            row.append(surface.get_at((x, y)))
        pixels.append(row)
    return pixels, w, h


def downscale_pixels(pixels, src_w, src_h, dst_w, dst_h):
    """Nearest-neighbor downscale of pixel data."""
    result = []
    for dy in range(dst_h):
        row = []
        sy = int(dy * src_h / dst_h)
        for dx in range(dst_w):
            sx = int(dx * src_w / dst_w)
            row.append(pixels[sy][sx])
        result.append(row)
    return result


def pixels_to_tiles(pixels, width, height, palette, is_sprite=True):
    """Convert pixel data to GBC 2bpp tile data.

    Returns a list of tiles, each tile is 16 bytes.
    Tiles are ordered left-to-right, top-to-bottom in 8x8 blocks.
    """
    tiles_x = width // 8
    tiles_y = height // 8
    all_tiles = []

    for ty in range(tiles_y):
        for tx in range(tiles_x):
            tile_bytes = []
            for row in range(8):
                py = ty * 8 + row
                low_byte = 0
                high_byte = 0
                for col in range(8):
                    px = tx * 8 + col
                    if py < height and px < width:
                        idx = nearest_palette_index(pixels[py][px], palette, is_sprite)
                    else:
                        idx = 0
                    # Bit 0 of color index goes to low plane,
                    # bit 1 goes to high plane.
                    # MSB = leftmost pixel (col 0 at bit 7)
                    bit = 7 - col
                    if idx & 1:
                        low_byte |= (1 << bit)
                    if idx & 2:
                        high_byte |= (1 << bit)
                tile_bytes.append(low_byte)
                tile_bytes.append(high_byte)
            all_tiles.append(tile_bytes)

    return all_tiles


def format_tile_data(name, tiles):
    """Format tile data as a C array for GBDK."""
    total_bytes = len(tiles) * 16
    lines = []
    lines.append(f"/* {len(tiles)} tile(s), {total_bytes} bytes */")
    lines.append(f"const unsigned char {name}[] = {{")
    for i, tile in enumerate(tiles):
        hex_vals = ", ".join(f"0x{b:02X}" for b in tile)
        lines.append(f"  {hex_vals},")
    lines.append("};")
    lines.append(f"#define {name}_TILE_COUNT {len(tiles)}")
    lines.append("")
    return "\n".join(lines)


def make_bg_tile(pattern_func):
    """Create an 8x8 background tile from a function(x, y) -> palette_index."""
    tile_bytes = []
    for row in range(8):
        low_byte = 0
        high_byte = 0
        for col in range(8):
            idx = pattern_func(col, row) & 0x03
            bit = 7 - col
            if idx & 1:
                low_byte |= (1 << bit)
            if idx & 2:
                high_byte |= (1 << bit)
        tile_bytes.append(low_byte)
        tile_bytes.append(high_byte)
    return tile_bytes


# ---------------------------------------------------------------------------
# Background tile patterns
# ---------------------------------------------------------------------------

def sky_tile(x, y):
    """Solid dark sky (palette index 0)."""
    return 0


def ground_tile(x, y):
    """Dark ground with noise pattern."""
    # Mostly index 1 (dark_purple) with scattered index 2 (mid_purple) noise
    noise = ((x * 7 + y * 13 + 5) % 11)
    if noise < 2:
        return 2  # mid_purple speckle
    if noise == 3 and y > 5:
        return 3  # occasional light speck at bottom
    return 1  # dark_purple base


def platform_tile(x, y):
    """Platform with bright cyan top edge."""
    if y == 0:
        return 3  # bright top line (white in neon palette)
    if y == 1:
        return 2  # cyan accent line
    return 1  # dark body


def boss_floor_tile(x, y):
    """Warning stripe pattern for boss area."""
    # Diagonal stripes
    stripe = (x + y) % 4
    if stripe < 2:
        return 2  # orange
    return 1  # dark_red


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def main():
    print("Generating sprites from game engine...")
    all_sprites = generate_all_sprites()

    # Extract idle_right frame 0 for each character
    sprite_configs = {
        "gig": {
            "src": all_sprites["gig"]["idle_right"][0],
            "dst_size": (16, 16),
            "palette": SPRITE_PALETTES["PAL_GIG"],
            "c_name": "spr_gig",
        },
        "thug": {
            "src": all_sprites["thug"]["idle_right"][0],
            "dst_size": (16, 16),
            "palette": SPRITE_PALETTES["PAL_THUG"],
            "c_name": "spr_thug",
        },
        "drone": {
            "src": all_sprites["drone"]["idle_right"][0],
            "dst_size": (8, 8),
            "palette": SPRITE_PALETTES["PAL_DRONE"],
            "c_name": "spr_drone",
        },
        "warden": {
            "src": all_sprites["warden"]["idle_right"][0],
            "dst_size": (24, 24),
            "palette": SPRITE_PALETTES["PAL_WARDEN"],
            "c_name": "spr_warden",
        },
    }

    # --- Generate sprite tile data ---
    sprite_sections = []
    for name, cfg in sprite_configs.items():
        src_surf = cfg["src"]
        dst_w, dst_h = cfg["dst_size"]
        pixels, src_w, src_h = surface_to_pixels(src_surf)
        scaled = downscale_pixels(pixels, src_w, src_h, dst_w, dst_h)
        tiles = pixels_to_tiles(scaled, dst_w, dst_h, cfg["palette"], is_sprite=True)
        sprite_sections.append(format_tile_data(cfg["c_name"], tiles))
        tiles_x = dst_w // 8
        tiles_y = dst_h // 8
        print(f"  {name}: {src_w}x{src_h} -> {dst_w}x{dst_h} "
              f"({tiles_x}x{tiles_y} tiles = {len(tiles)} tiles)")

    # --- Generate background tiles ---
    bg_tiles_data = []
    bg_patterns = [
        ("tile_sky", sky_tile),
        ("tile_ground", ground_tile),
        ("tile_platform", platform_tile),
        ("tile_boss_floor", boss_floor_tile),
    ]
    for tile_name, pattern_fn in bg_patterns:
        tile = make_bg_tile(pattern_fn)
        bg_tiles_data.append(format_tile_data(tile_name, [tile]))

    # --- Write sprites.h ---
    sprites_h_path = os.path.join(os.path.dirname(__file__), "res", "sprites.h")
    with open(sprites_h_path, "w") as f:
        f.write("/* sprites.h - GBC sprite tile data for CTRL+ALT REVENGE\n")
        f.write(" * Auto-generated by convert_sprites.py\n")
        f.write(" * Format: GBDK 2bpp tile data (8x8 tiles, 16 bytes each)\n")
        f.write(" */\n\n")
        f.write("#ifndef SPRITES_H\n#define SPRITES_H\n\n")
        for section in sprite_sections:
            f.write(section + "\n")
        f.write("#endif /* SPRITES_H */\n")
    print(f"Wrote {sprites_h_path}")

    # --- Write tiles.h ---
    tiles_h_path = os.path.join(os.path.dirname(__file__), "res", "tiles.h")
    with open(tiles_h_path, "w") as f:
        f.write("/* tiles.h - GBC background tile data for CTRL+ALT REVENGE\n")
        f.write(" * Auto-generated by convert_sprites.py\n")
        f.write(" * Format: GBDK 2bpp tile data (8x8 tiles, 16 bytes each)\n")
        f.write(" */\n\n")
        f.write("#ifndef TILES_H\n#define TILES_H\n\n")
        f.write("/* Tile indices (for use with set_bkg_tiles) */\n")
        f.write("#define TILE_SKY        0\n")
        f.write("#define TILE_GROUND     1\n")
        f.write("#define TILE_PLATFORM   2\n")
        f.write("#define TILE_BOSS_FLOOR 3\n\n")
        for section in bg_tiles_data:
            f.write(section + "\n")
        f.write("/* Combined background tileset for set_bkg_data() */\n")
        f.write("const unsigned char bg_tiles[] = {\n")
        for tile_name, _ in bg_patterns:
            f.write(f"  /* {tile_name} */\n")
            # Re-generate tile inline for the combined array
            tile = make_bg_tile(dict(bg_patterns)[tile_name])
            hex_vals = ", ".join(f"0x{b:02X}" for b in tile)
            f.write(f"  {hex_vals},\n")
        f.write("};\n")
        f.write(f"#define BG_TILES_COUNT {len(bg_patterns)}\n\n")
        f.write("#endif /* TILES_H */\n")
    print(f"Wrote {tiles_h_path}")

    # --- Write palettes.h ---
    palettes_h_path = os.path.join(os.path.dirname(__file__), "res", "palettes.h")
    with open(palettes_h_path, "w") as f:
        f.write("/* palettes.h - GBC palette data for CTRL+ALT REVENGE\n")
        f.write(" * Auto-generated by convert_sprites.py\n")
        f.write(" * Format: 15-bit RGB (5 bits/channel), little-endian uint16\n")
        f.write(" * GBC color = (R>>3) | ((G>>3)<<5) | ((B>>3)<<10)\n")
        f.write(" */\n\n")
        f.write("#ifndef PALETTES_H\n#define PALETTES_H\n\n")

        # Sprite palette indices
        f.write("/* Sprite palette indices (transparent + 3 colors) */\n")
        for i, name in enumerate(SPRITE_PALETTES):
            f.write(f"#define {name:<16s} {i}\n")
        f.write("\n")

        # BG palette indices
        f.write("/* BG palette indices (4 colors) */\n")
        for i, name in enumerate(BG_PALETTES):
            f.write(f"#define {name:<16s} {i}\n")
        f.write("\n")

        # Sprite palette data
        f.write("/* Sprite palette data (4 colors x N palettes) */\n")
        f.write("const unsigned int sprite_palettes[] = {\n")
        for pal_name, colors in SPRITE_PALETTES.items():
            gbc_colors = [rgb_to_gbc(*c) for c in colors]
            hex_vals = ", ".join(f"0x{c:04X}" for c in gbc_colors)
            f.write(f"  /* {pal_name}: */ {hex_vals},\n")
        f.write("};\n\n")

        # BG palette data
        f.write("/* BG palette data (4 colors x N palettes) */\n")
        f.write("const unsigned int bg_palettes[] = {\n")
        for pal_name, colors in BG_PALETTES.items():
            gbc_colors = [rgb_to_gbc(*c) for c in colors]
            hex_vals = ", ".join(f"0x{c:04X}" for c in gbc_colors)
            f.write(f"  /* {pal_name}: */ {hex_vals},\n")
        f.write("};\n\n")

        f.write("#endif /* PALETTES_H */\n")
    print(f"Wrote {palettes_h_path}")

    print("\nDone! Generated GBC tile data for GBDK.")
    pygame.quit()


if __name__ == "__main__":
    main()
