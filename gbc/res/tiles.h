// tiles.h — Background tile data (8x8, 2bpp, 16 bytes each)
#ifndef TILES_H
#define TILES_H

#include <gb/gb.h>

// Tile indices in VRAM
#define BG_TILE_EMPTY     0
#define BG_TILE_GROUND    1
#define BG_TILE_GROUND2   2
#define BG_TILE_PLATFORM  3
#define BG_TILE_WALL      4
#define BG_TILE_BOSS_FLOOR 5
#define BG_TILE_GATE      6
#define BG_TILE_BUILDING  7
#define BG_TILE_WINDOW    8

// Empty/sky tile — solid color 0
const UINT8 bg_tile_empty[] = {
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
    0x00, 0x00,
};

// Ground tile — textured with noise (color 1 base, scattered color 2 pixels)
const UINT8 bg_tile_ground[] = {
    0xFE, 0x01,  // row 0: mostly color 1, one color 2 pixel
    0xFF, 0x00,  // row 1: all color 1
    0xFB, 0x04,  // row 2: noise
    0xFF, 0x00,  // row 3
    0xDF, 0x20,  // row 4: noise
    0xFF, 0x00,  // row 5
    0xF7, 0x08,  // row 6: noise
    0xFF, 0x00,  // row 7
};

// Ground variant 2 — different noise pattern
const UINT8 bg_tile_ground2[] = {
    0xFF, 0x00,
    0xEF, 0x10,
    0xFF, 0x00,
    0x7F, 0x80,
    0xFF, 0x00,
    0xFD, 0x02,
    0xFF, 0x00,
    0xBF, 0x40,
};

// Platform — bright top line (color 3), supports below (color 1)
const UINT8 bg_tile_platform[] = {
    0xFF, 0xFF,  // row 0: color 3 (bright cyan) — full line
    0xFF, 0xFF,  // row 1: color 3
    0x00, 0x00,  // row 2: transparent
    0x24, 0x00,  // row 3: support dots (color 1)
    0x00, 0x00,  // row 4: transparent
    0x24, 0x00,  // row 5: support dots
    0x00, 0x00,  // row 6
    0x00, 0x00,  // row 7
};

// Wall — solid with border (color 2 body, color 3 edge highlight)
const UINT8 bg_tile_wall[] = {
    0xFF, 0xFF,  // row 0: color 3 top edge
    0x01, 0xFE,  // row 1: left edge color 3, body color 2
    0x01, 0xFE,  // row 2
    0x01, 0xFE,  // row 3
    0xFF, 0x00,  // row 4: horizontal line color 1
    0x01, 0xFE,  // row 5
    0x01, 0xFE,  // row 6
    0x01, 0xFE,  // row 7
};

// Boss floor — warning stripes (diagonal, color 2 + color 3)
const UINT8 bg_tile_boss_floor[] = {
    0xC3, 0xC3,  // ##....## pattern in color 3
    0xE1, 0xE1,  // ###...#.
    0xF0, 0xF0,  // ####....
    0x78, 0x78,  // .####...
    0x3C, 0x3C,  // ..####..
    0x1E, 0x1E,  // ...####.
    0x0F, 0x0F,  // ....####
    0x87, 0x87,  // #...####
};

// Gate — vertical bars (color 1 bars, transparent between)
const UINT8 bg_tile_gate[] = {
    0xDB, 0x00,  // ##.##.## color 1 bars
    0xDB, 0x00,
    0xDB, 0x00,
    0xDB, 0x00,
    0xDB, 0x00,
    0xDB, 0x00,
    0xDB, 0x00,
    0xDB, 0x00,
};

// Building silhouette — solid dark (color 1)
const UINT8 bg_tile_building[] = {
    0xFF, 0x00,  // all color 1
    0xFF, 0x00,
    0xFF, 0x00,
    0xFF, 0x00,
    0xFF, 0x00,
    0xFF, 0x00,
    0xFF, 0x00,
    0xFF, 0x00,
};

// Building with lit window — color 1 body with color 3 window pixels
const UINT8 bg_tile_window[] = {
    0xFF, 0x00,  // color 1
    0xE7, 0x18,  // color 1 body, color 2 window (2x2 in center)
    0xE7, 0x18,  // window continues
    0xFF, 0x00,  // color 1
    0xFF, 0x00,
    0x9F, 0x60,  // another window offset
    0x9F, 0x60,
    0xFF, 0x00,
};

#endif // TILES_H
