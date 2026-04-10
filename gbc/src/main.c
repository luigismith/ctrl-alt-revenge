// CTRL+ALT REVENGE! — Game Boy Color Port
// main.c — Entry point, game loop, state machine
#include <gb/gb.h>
#include <gb/cgb.h>
#include <gbdk/platform.h>
#include <string.h>
#include <stdlib.h>

#include "game.h"
#include "../res/sprites.h"
#include "../res/tiles.h"
#include "../res/palettes.h"

// ============================================================
// GLOBALS
// ============================================================
GameState game_state;
Player player;
Enemy enemies[MAX_ENEMIES];
UINT8 num_enemies;
INT16 camera_x;
UINT8 scroll_x_sub;  // sub-pixel scrolling
UINT8 frame_count;
UINT8 joypad_current;
UINT8 joypad_previous;

// Title screen text
const char title_str[] = "CTRL+ALT";
const char title_str2[] = "REVENGE!";
const char sub_str[] = "GBC EDITION";
const char start_str[] = "PRESS START";
const char gameover_str[] = "GAME OVER";
const char retry_str[] = "START:RETRY";
const char win_str[] = "STAGE CLEAR!";

// ============================================================
// JOYPAD HELPERS
// ============================================================
UINT8 joy_pressed(UINT8 btn) {
    return (joypad_current & btn) && !(joypad_previous & btn);
}

UINT8 joy_held(UINT8 btn) {
    return joypad_current & btn;
}

// ============================================================
// SPRITE MANAGEMENT
// ============================================================
UINT8 next_sprite_id;

void sprites_reset(void) {
    next_sprite_id = 0;
}

void sprite_draw(UINT8 x, UINT8 y, UINT8 tile, UINT8 props) {
    if (next_sprite_id >= 40) return;
    move_sprite(next_sprite_id, x, y);
    set_sprite_tile(next_sprite_id, tile);
    set_sprite_prop(next_sprite_id, props);
    next_sprite_id++;
}

// Draw a 16x16 metasprite (4 tiles in 8x8 mode)
void metasprite_draw(UINT8 x, UINT8 y, UINT8 base_tile, UINT8 props) {
    sprite_draw(x,     y,     base_tile,     props);
    sprite_draw(x + 8, y,     base_tile + 1, props);
    sprite_draw(x,     y + 8, base_tile + 2, props);
    sprite_draw(x + 8, y + 8, base_tile + 3, props);
}

void sprites_hide_remaining(void) {
    while (next_sprite_id < 40) {
        move_sprite(next_sprite_id, 0, 0);
        next_sprite_id++;
    }
}

// ============================================================
// INIT
// ============================================================
void init_palettes(void) {
    // Background palettes
    set_bkg_palette(PAL_BG_GROUND, 1, bg_palette_ground);
    set_bkg_palette(PAL_BG_NEON,   1, bg_palette_neon);
    set_bkg_palette(PAL_BG_BOSS,   1, bg_palette_boss);
    set_bkg_palette(PAL_BG_SKY,    1, bg_palette_sky);

    // Sprite palettes
    set_sprite_palette(PAL_GIG,    1, spr_palette_gig);
    set_sprite_palette(PAL_THUG,   1, spr_palette_thug);
    set_sprite_palette(PAL_DRONE,  1, spr_palette_drone);
    set_sprite_palette(PAL_WARDEN, 1, spr_palette_warden);
}

void init_tiles(void) {
    // Load background tiles into VRAM
    set_bkg_data(BG_TILE_EMPTY, 1, bg_tile_empty);
    set_bkg_data(BG_TILE_GROUND, 1, bg_tile_ground);
    set_bkg_data(BG_TILE_GROUND2, 1, bg_tile_ground2);
    set_bkg_data(BG_TILE_PLATFORM, 1, bg_tile_platform);
    set_bkg_data(BG_TILE_WALL, 1, bg_tile_wall);
    set_bkg_data(BG_TILE_BOSS_FLOOR, 1, bg_tile_boss_floor);
    set_bkg_data(BG_TILE_GATE, 1, bg_tile_gate);
    set_bkg_data(BG_TILE_BUILDING, 1, bg_tile_building);
    set_bkg_data(BG_TILE_WINDOW, 1, bg_tile_window);

    // Load sprite tiles into VRAM
    set_sprite_data(SPR_GIG_IDLE, 4, spr_gig_idle);
    set_sprite_data(SPR_GIG_RUN1, 4, spr_gig_run1);
    set_sprite_data(SPR_GIG_RUN2, 4, spr_gig_run2);
    set_sprite_data(SPR_GIG_JUMP, 4, spr_gig_jump);
    set_sprite_data(SPR_GIG_PUNCH, 4, spr_gig_punch);
    set_sprite_data(SPR_GIG_HURT, 4, spr_gig_hurt);
    set_sprite_data(SPR_THUG_IDLE, 4, spr_thug_idle);
    set_sprite_data(SPR_THUG_WALK, 4, spr_thug_walk);
    set_sprite_data(SPR_THUG_ATK, 4, spr_thug_attack);
    set_sprite_data(SPR_DRONE, 4, spr_drone_fly);
    set_sprite_data(SPR_WARDEN, 9, spr_warden_idle);
}

// ============================================================
// LEVEL DATA — 32 columns wide (256px), 18 rows (144px)
// Each column is one 8px tile
// ============================================================
#define LEVEL_W 80   // 80 tiles = 640px
#define LEVEL_H 18   // 18 tiles = 144px

// Simplified level map — 0=empty, 1=ground, 2=platform, 3=wall, 4=boss_floor
// Level data is built procedurally in build_level()

// Build the tilemap in VRAM
void build_level(void) {
    UINT8 row, col;
    UINT8 tile_row[32];
    UINT8 attr_row[32];

    // For GBC: we need to set both tiles and attributes
    for (row = 0; row < LEVEL_H; row++) {
        for (col = 0; col < 32; col++) {
            if (row >= 16) {
                // Solid ground
                tile_row[col] = BG_TILE_GROUND + ((col + row) & 1);
                attr_row[col] = PAL_BG_GROUND;
            } else if (row == 15 && col >= 2 && col <= 4) {
                // Starting platform
                tile_row[col] = BG_TILE_PLATFORM;
                attr_row[col] = PAL_BG_NEON;
            } else if (row == 13 && col >= 8 && col <= 11) {
                // Elevated platform
                tile_row[col] = BG_TILE_PLATFORM;
                attr_row[col] = PAL_BG_NEON;
            } else if (row == 15 && col >= 14 && col <= 16) {
                // Another platform
                tile_row[col] = BG_TILE_PLATFORM;
                attr_row[col] = PAL_BG_NEON;
            } else if (row >= 16 && col >= 24 && col <= 31) {
                // Boss area floor
                tile_row[col] = BG_TILE_BOSS_FLOOR;
                attr_row[col] = PAL_BG_BOSS;
            } else if (row < 10 && (col == 0 || col == 31)) {
                // Side walls
                tile_row[col] = BG_TILE_WALL;
                attr_row[col] = PAL_BG_GROUND;
            } else if (row >= 4 && row <= 12 && (col >= 18 && col <= 19)) {
                // Gate
                tile_row[col] = BG_TILE_GATE;
                attr_row[col] = PAL_BG_GROUND;
            } else {
                // Sky with occasional building
                if (row >= 6 && row <= 15 && (col % 7 == 3 || col % 11 == 5)) {
                    tile_row[col] = BG_TILE_BUILDING;
                    attr_row[col] = PAL_BG_SKY;
                } else if (row >= 8 && row <= 13 && col % 7 == 4) {
                    tile_row[col] = BG_TILE_WINDOW;
                    attr_row[col] = PAL_BG_SKY;
                } else {
                    tile_row[col] = BG_TILE_EMPTY;
                    attr_row[col] = PAL_BG_SKY;
                }
            }
        }
        set_bkg_tiles(0, row, 32, 1, tile_row);
        // Set CGB attributes
        VBK_REG = 1;
        set_bkg_tiles(0, row, 32, 1, attr_row);
        VBK_REG = 0;
    }
}

// ============================================================
// PLAYER
// ============================================================
void player_init(void) {
    player.x = 24 << 4;     // Fixed-point 12.4
    player.y = 112 << 4;
    player.vx = 0;
    player.vy = 0;
    player.hp = 4;
    player.facing = FACE_RIGHT;
    player.state = ST_IDLE;
    player.anim_frame = 0;
    player.anim_timer = 0;
    player.iframes = 0;
    player.on_ground = 0;
    player.attack_timer = 0;
}

UINT8 check_solid(INT16 px, INT16 py) {
    // Convert pixel coords to tile coords
    UINT8 tx = (UINT8)(px >> 3);
    UINT8 ty = (UINT8)(py >> 3);
    // Ground at row 16+
    if (ty >= 16) return 1;
    // Platforms at specific positions
    if (ty == 15 && tx >= 2 && tx <= 4) return 1;
    if (ty == 13 && tx >= 8 && tx <= 11) return 1;
    if (ty == 15 && tx >= 14 && tx <= 16) return 1;
    // Gate
    if (tx >= 18 && tx <= 19 && ty >= 4 && ty <= 12) return 1;
    // Boss floor
    if (ty >= 16 && tx >= 24) return 1;
    return 0;
}

void player_update(void) {
    INT16 px, py;
    UINT8 on_ground_now;

    if (player.iframes > 0) player.iframes--;
    if (player.attack_timer > 0) player.attack_timer--;

    // Movement
    if (player.attack_timer == 0) {
        if (joy_held(J_LEFT)) {
            player.vx = -PLAYER_SPEED;
            player.facing = FACE_LEFT;
        } else if (joy_held(J_RIGHT)) {
            player.vx = PLAYER_SPEED;
            player.facing = FACE_RIGHT;
        } else {
            // Decelerate
            if (player.vx > 0) player.vx -= 2;
            else if (player.vx < 0) player.vx += 2;
            if (player.vx > -2 && player.vx < 2) player.vx = 0;
        }
    }

    // Gravity
    player.vy += GRAVITY;
    if (player.vy > MAX_FALL) player.vy = MAX_FALL;

    // Move X
    player.x += player.vx;
    px = player.x >> 4;
    // Clamp to level bounds
    if (px < 8) { player.x = 8 << 4; player.vx = 0; }
    if (px > 248) { player.x = 248 << 4; player.vx = 0; }

    // Check X collision
    px = player.x >> 4;
    py = player.y >> 4;
    if (check_solid(px + 14, py + 8) && player.vx > 0) {
        player.x -= player.vx;
        player.vx = 0;
    }
    if (check_solid(px, py + 8) && player.vx < 0) {
        player.x -= player.vx;
        player.vx = 0;
    }

    // Move Y
    player.y += player.vy;
    py = player.y >> 4;

    // Check ground collision
    on_ground_now = 0;
    if (player.vy >= 0) {
        if (check_solid(px + 4, py + 16) || check_solid(px + 10, py + 16)) {
            player.y = (INT16)((py & 0xF8) << 4);  // Snap to tile
            player.vy = 0;
            on_ground_now = 1;
        }
    }
    // Ceiling
    if (player.vy < 0 && check_solid(px + 4, py)) {
        player.vy = 0;
    }

    player.on_ground = on_ground_now;

    // Jump
    if (joy_pressed(J_A) && player.on_ground) {
        player.vy = JUMP_FORCE;
        player.on_ground = 0;
    }

    // Attack
    if (joy_pressed(J_B) && player.attack_timer == 0) {
        player.attack_timer = ATTACK_DURATION;
        player.state = ST_ATTACK;
    }

    // Animation state
    if (player.attack_timer > 0) {
        player.state = ST_ATTACK;
    } else if (!player.on_ground) {
        player.state = ST_JUMP;
    } else if (player.vx != 0) {
        player.state = ST_RUN;
    } else {
        player.state = ST_IDLE;
    }

    // Animate
    player.anim_timer++;
    if (player.anim_timer >= 8) {
        player.anim_timer = 0;
        player.anim_frame = (player.anim_frame + 1) & 1;
    }
}

void player_draw(void) {
    UINT8 sx, sy, base_tile, props;

    if (player.iframes > 0 && (player.iframes & 2)) return;  // Blink

    sx = (UINT8)((player.x >> 4) - (camera_x) + 8);
    sy = (UINT8)((player.y >> 4) + 16);

    props = (player.facing == FACE_LEFT) ? S_FLIPX : 0;
    props |= PAL_GIG;  // CGB palette

    switch (player.state) {
        case ST_IDLE:
            base_tile = SPR_GIG_IDLE;
            break;
        case ST_RUN:
            base_tile = player.anim_frame ? SPR_GIG_RUN1 : SPR_GIG_RUN2;
            break;
        case ST_JUMP:
            base_tile = SPR_GIG_JUMP;
            break;
        case ST_ATTACK:
            base_tile = SPR_GIG_PUNCH;
            break;
        case ST_HURT:
            base_tile = SPR_GIG_HURT;
            break;
        default:
            base_tile = SPR_GIG_IDLE;
            break;
    }

    // Draw 16x16 metasprite
    if (player.facing == FACE_LEFT) {
        sprite_draw(sx + 8, sy,     base_tile + 1, props);
        sprite_draw(sx,     sy,     base_tile,     props);
        sprite_draw(sx + 8, sy + 8, base_tile + 3, props);
        sprite_draw(sx,     sy + 8, base_tile + 2, props);
    } else {
        metasprite_draw(sx, sy, base_tile, props);
    }
}

// ============================================================
// ENEMIES
// ============================================================
void enemies_init(void) {
    UINT8 i;
    num_enemies = 3;

    // Thug 1
    enemies[0].x = 80 << 4;
    enemies[0].y = 112 << 4;
    enemies[0].vx = 8;  // patrol speed
    enemies[0].hp = 3;
    enemies[0].type = ENEMY_THUG;
    enemies[0].state = ST_IDLE;
    enemies[0].facing = FACE_LEFT;
    enemies[0].anim_frame = 0;
    enemies[0].anim_timer = 0;
    enemies[0].patrol_min = 64;
    enemies[0].patrol_max = 120;
    enemies[0].iframes = 0;
    enemies[0].attack_timer = 0;

    // Thug 2
    enemies[1] = enemies[0];
    enemies[1].x = 140 << 4;
    enemies[1].patrol_min = 120;
    enemies[1].patrol_max = 170;

    // Drone
    enemies[2].x = 100 << 4;
    enemies[2].y = 60 << 4;
    enemies[2].vx = 6;
    enemies[2].hp = 2;
    enemies[2].type = ENEMY_DRONE;
    enemies[2].state = ST_IDLE;
    enemies[2].facing = FACE_LEFT;
    enemies[2].anim_frame = 0;
    enemies[2].anim_timer = 0;
    enemies[2].patrol_min = 80;
    enemies[2].patrol_max = 150;
    enemies[2].iframes = 0;
    enemies[2].attack_timer = 0;
}

void enemy_update(Enemy *e) {
    INT16 px, dx;

    if (e->hp == 0) return;
    if (e->iframes > 0) e->iframes--;

    // Simple patrol AI
    px = e->x >> 4;
    if (px <= e->patrol_min) {
        e->vx = abs(e->vx);
        e->facing = FACE_RIGHT;
    }
    if (px >= e->patrol_max) {
        e->vx = -abs(e->vx);
        e->facing = FACE_LEFT;
    }

    e->x += e->vx;

    // Drone bobs vertically
    if (e->type == ENEMY_DRONE) {
        e->y += (frame_count & 16) ? 2 : -2;
    }

    // Chase player if close
    dx = (player.x >> 4) - px;
    if (dx > -60 && dx < 60 && e->type == ENEMY_THUG) {
        if (dx > 8) { e->vx = 12; e->facing = FACE_RIGHT; }
        else if (dx < -8) { e->vx = -12; e->facing = FACE_LEFT; }

        // Attack if very close
        if (dx > -16 && dx < 16 && e->attack_timer == 0) {
            e->attack_timer = 30;
            e->state = ST_ATTACK;
        }
    }

    // Animation
    e->anim_timer++;
    if (e->anim_timer >= 10) {
        e->anim_timer = 0;
        e->anim_frame = (e->anim_frame + 1) & 1;
    }
    if (e->attack_timer > 0) {
        e->attack_timer--;
        e->state = ST_ATTACK;
    } else {
        e->state = (e->vx != 0) ? ST_RUN : ST_IDLE;
    }
}

void enemy_draw(Enemy *e) {
    UINT8 sx, sy, base_tile, props, pal;

    if (e->hp == 0) return;
    if (e->iframes > 0 && (e->iframes & 2)) return;

    sx = (UINT8)((e->x >> 4) - camera_x + 8);
    sy = (UINT8)((e->y >> 4) + 16);

    // Off-screen culling
    if (sx < 4 || sx > 164) return;

    props = (e->facing == FACE_LEFT) ? S_FLIPX : 0;

    if (e->type == ENEMY_THUG) {
        pal = PAL_THUG;
        if (e->state == ST_ATTACK) base_tile = SPR_THUG_ATK;
        else if (e->anim_frame) base_tile = SPR_THUG_WALK;
        else base_tile = SPR_THUG_IDLE;
        props |= pal;
        metasprite_draw(sx, sy, base_tile, props);
    } else if (e->type == ENEMY_DRONE) {
        pal = PAL_DRONE;
        base_tile = SPR_DRONE;
        props |= pal;
        // Drone is smaller — draw as 16x16 but only top tiles matter
        metasprite_draw(sx, sy + 4, base_tile, props);
    }
}

// ============================================================
// COMBAT
// ============================================================
void check_combat(void) {
    UINT8 i;
    INT16 px, py, ex, ey, dx, dy;
    Enemy *e;

    px = player.x >> 4;
    py = player.y >> 4;

    for (i = 0; i < num_enemies; i++) {
        e = &enemies[i];
        if (e->hp == 0) continue;

        ex = e->x >> 4;
        ey = e->y >> 4;
        dx = px - ex;
        dy = py - ey;

        // Player attack hits enemy
        if (player.attack_timer > ATTACK_DURATION - 6 && player.attack_timer <= ATTACK_DURATION) {
            INT16 range_x = (player.facing == FACE_RIGHT) ? 16 : -16;
            if (dx > (range_x - 14) && dx < (range_x + 14) && dy > -12 && dy < 12) {
                if (e->iframes == 0) {
                    e->hp--;
                    e->iframes = 20;
                    e->vx = (player.facing == FACE_RIGHT) ? 24 : -24;
                }
            }
        }

        // Enemy contact damages player
        if (player.iframes == 0 && e->hp > 0) {
            if (dx > -12 && dx < 12 && dy > -12 && dy < 12) {
                player.hp--;
                player.iframes = 40;
                player.vx = (dx < 0) ? 20 : -20;
                player.vy = -16;
                if (player.hp == 0) {
                    game_state = STATE_GAMEOVER;
                }
            }
        }
    }
}

// ============================================================
// HUD
// ============================================================
void draw_hud(void) {
    UINT8 i;
    // Hearts using window layer
    // For simplicity, use BG tiles in top row
    // We'll draw hearts as sprites instead
    for (i = 0; i < 4; i++) {
        UINT8 sx = 8 + i * 10;
        if (i < player.hp) {
            sprite_draw(sx, 20, SPR_GIG_IDLE, PAL_GIG);  // placeholder heart
        }
    }
}

// ============================================================
// CAMERA
// ============================================================
void update_camera(void) {
    INT16 target = (player.x >> 4) - 72;  // Center player
    if (target < 0) target = 0;
    if (target > LEVEL_W * 8 - 160) target = LEVEL_W * 8 - 160;

    // Smooth follow
    if (camera_x < target) camera_x += 1;
    if (camera_x > target) camera_x -= 1;

    SCX_REG = (UINT8)camera_x;
}

// ============================================================
// TITLE SCREEN
// ============================================================
void state_title(void) {
    UINT8 blink = 0;

    // Clear screen
    DISPLAY_OFF;
    init_palettes();
    init_tiles();

    // Build a simple title background
    UINT8 row, col;
    UINT8 tile_row[20];
    UINT8 attr_row[20];
    for (row = 0; row < 18; row++) {
        for (col = 0; col < 20; col++) {
            if (row >= 14) {
                tile_row[col] = BG_TILE_GROUND;
                attr_row[col] = PAL_BG_GROUND;
            } else if (row >= 6 && (col == 3 || col == 7 || col == 12 || col == 16)) {
                tile_row[col] = BG_TILE_BUILDING;
                attr_row[col] = PAL_BG_SKY;
            } else if (row >= 8 && (col == 4 || col == 8 || col == 13)) {
                tile_row[col] = BG_TILE_WINDOW;
                attr_row[col] = PAL_BG_SKY;
            } else {
                tile_row[col] = BG_TILE_EMPTY;
                attr_row[col] = PAL_BG_SKY;
            }
        }
        set_bkg_tiles(0, row, 20, 1, tile_row);
        VBK_REG = 1;
        set_bkg_tiles(0, row, 20, 1, attr_row);
        VBK_REG = 0;
    }

    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;
    SCX_REG = 0;
    SCY_REG = 0;

    while (game_state == STATE_TITLE) {
        joypad_previous = joypad_current;
        joypad_current = joypad();

        if (joy_pressed(J_START) || joy_pressed(J_A)) {
            game_state = STATE_PLAY;
        }

        // Draw GIG sprite on title screen
        sprites_reset();
        metasprite_draw(120, 100, SPR_GIG_IDLE, PAL_GIG);
        sprites_hide_remaining();

        blink++;
        // Print title text (using BG tiles since no font tiles loaded)
        // Just rely on the visual sprites for now

        wait_vbl_done();
        frame_count++;
    }
}

// ============================================================
// GAMEPLAY
// ============================================================
void state_play(void) {
    UINT8 i;

    DISPLAY_OFF;
    init_palettes();
    init_tiles();
    build_level();
    player_init();
    enemies_init();
    camera_x = 0;

    SHOW_BKG;
    SHOW_SPRITES;
    DISPLAY_ON;

    while (game_state == STATE_PLAY) {
        joypad_previous = joypad_current;
        joypad_current = joypad();

        // Pause
        if (joy_pressed(J_START)) {
            // Simple pause: freeze until START pressed again
            while (1) {
                wait_vbl_done();
                joypad_previous = joypad_current;
                joypad_current = joypad();
                if (joy_pressed(J_START)) break;
            }
        }

        player_update();
        for (i = 0; i < num_enemies; i++) {
            enemy_update(&enemies[i]);
        }
        check_combat();
        update_camera();

        // Draw
        sprites_reset();
        player_draw();
        for (i = 0; i < num_enemies; i++) {
            enemy_draw(&enemies[i]);
        }
        sprites_hide_remaining();

        // Check win condition: all enemies dead
        {
            UINT8 alive = 0;
            for (i = 0; i < num_enemies; i++) {
                if (enemies[i].hp > 0) alive++;
            }
            if (alive == 0) {
                game_state = STATE_WIN;
            }
        }

        wait_vbl_done();
        frame_count++;
    }
}

// ============================================================
// GAME OVER
// ============================================================
void state_gameover(void) {
    UINT8 wait = 0;

    while (game_state == STATE_GAMEOVER) {
        joypad_previous = joypad_current;
        joypad_current = joypad();

        wait++;
        if (wait > 60 && joy_pressed(J_START)) {
            game_state = STATE_TITLE;
        }

        sprites_reset();
        sprites_hide_remaining();
        wait_vbl_done();
    }
}

// ============================================================
// WIN
// ============================================================
void state_win(void) {
    UINT8 wait = 0;

    while (game_state == STATE_WIN) {
        joypad_previous = joypad_current;
        joypad_current = joypad();

        wait++;
        if (wait > 90 && joy_pressed(J_START)) {
            game_state = STATE_TITLE;
        }

        sprites_reset();
        // Draw GIG celebrating
        metasprite_draw(72, 80, SPR_GIG_IDLE, PAL_GIG);
        sprites_hide_remaining();
        wait_vbl_done();
    }
}

// ============================================================
// MAIN
// ============================================================
void main(void) {
    // Detect CGB and set double-speed
    if (_cpu == CGB_TYPE) {
        cpu_fast();
    }

    SPRITES_8x8;

    game_state = STATE_TITLE;
    frame_count = 0;
    joypad_current = 0;
    joypad_previous = 0;

    while (1) {
        switch (game_state) {
            case STATE_TITLE:
                state_title();
                break;
            case STATE_PLAY:
                state_play();
                break;
            case STATE_GAMEOVER:
                state_gameover();
                break;
            case STATE_WIN:
                state_win();
                break;
        }
    }
}
