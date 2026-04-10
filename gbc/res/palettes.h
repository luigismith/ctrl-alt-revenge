// palettes.h — GBC Color Palettes (15-bit RGB, little-endian)
// Format: (R>>3) | ((G>>3)<<5) | ((B>>3)<<10)
#ifndef PALETTES_H
#define PALETTES_H

#include <gb/gb.h>

// Palette indices
#define PAL_BG_GROUND  0
#define PAL_BG_NEON    1
#define PAL_BG_BOSS    2
#define PAL_BG_SKY     3

#define PAL_GIG     0
#define PAL_THUG    1
#define PAL_DRONE   2
#define PAL_WARDEN  3

// Background palettes (4 colors each)
// Ground: night_dark, dark_purple, mid_purple, light_purple
const UINT16 bg_palette_ground[] = {
    0x1821,  // (13,11,43) -> dark night
    0x3148,  // (35,32,60) -> dark purple
    0x4A4D,  // (50,45,75) -> mid purple
    0x5B53,  // (65,60,90) -> light
};

// Neon: night, dark, cyan, bright_cyan
const UINT16 bg_palette_neon[] = {
    0x1821,  // dark night
    0x2945,  // dark blue
    0x7F60,  // (0,229,255) -> bright cyan
    0x7FFF,  // white
};

// Boss: night, dark_red, orange, yellow
const UINT16 bg_palette_boss[] = {
    0x1821,  // dark night
    0x1D4C,  // dark red
    0x239F,  // (255,122,26) -> orange
    0x2BDF,  // (255,220,50) -> yellow
};

// Sky: night_dark, dark_building, mid_building, window_glow
const UINT16 bg_palette_sky[] = {
    0x1821,  // dark night
    0x2944,  // (25,22,55) building dark
    0x3949,  // (35,30,65) building mid
    0x7F60,  // cyan window glow
};

// Sprite palettes (transparent + 3 colors)
// GIG: transparent, skin, jacket_brown, cyber_blue
const UINT16 spr_palette_gig[] = {
    0x0000,  // transparent
    0x2AD6,  // (210,170,130) skin
    0x11F6,  // (180,120,50) jacket brown
    0x7F60,  // (0,229,255) cyber blue
};

// Thug: transparent, skin, shirt_dark, bandana_red
const UINT16 spr_palette_thug[] = {
    0x0000,
    0x22D3,  // (190,150,110) thug skin
    0x0903,  // (60,20,20) dark shirt
    0x195F,  // (255,46,77) red bandana
};

// Drone: transparent, body_gray, eye_red, accent_blue
const UINT16 spr_palette_drone[] = {
    0x0000,
    0x2D4B,  // (70,75,90) body
    0x195F,  // (255,46,77) red eye
    0x7F60,  // (0,229,255) accent
};

// Warden: transparent, armor_gray, visor_red, trim_orange
const UINT16 spr_palette_warden[] = {
    0x0000,
    0x1D48,  // (40,45,60) armor
    0x195F,  // (255,46,77) visor red
    0x239F,  // (255,122,26) orange trim
};

#endif // PALETTES_H
