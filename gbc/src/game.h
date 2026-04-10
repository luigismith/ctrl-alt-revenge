// game.h — Game constants, structs, types
#ifndef GAME_H
#define GAME_H

#include <gb/gb.h>
#include <gbdk/platform.h>

// ============================================================
// CONSTANTS
// ============================================================
#define PLAYER_SPEED    16    // Fixed-point 12.4
#define JUMP_FORCE     -48    // Negative = up
#define GRAVITY          3
#define MAX_FALL        48
#define ATTACK_DURATION 12
#define MAX_ENEMIES      8

// Facing direction
#define FACE_RIGHT  0
#define FACE_LEFT   1

// Entity state
#define ST_IDLE    0
#define ST_RUN     1
#define ST_JUMP    2
#define ST_ATTACK  3
#define ST_HURT    4
#define ST_DEAD    5

// Game states
#define STATE_TITLE    0
#define STATE_PLAY     1
#define STATE_GAMEOVER 2
#define STATE_WIN      3

// Enemy types
#define ENEMY_THUG   0
#define ENEMY_DRONE  1
#define ENEMY_WARDEN 2

// ============================================================
// TYPES
// ============================================================
typedef UINT8 GameState;

typedef struct {
    INT16 x, y;         // Fixed-point 12.4 position
    INT16 vx, vy;       // Velocity
    UINT8 hp;
    UINT8 facing;       // FACE_RIGHT or FACE_LEFT
    UINT8 state;        // ST_IDLE, ST_RUN, etc.
    UINT8 anim_frame;
    UINT8 anim_timer;
    UINT8 on_ground;
    UINT8 iframes;      // Invincibility frames
    UINT8 attack_timer;
} Player;

typedef struct {
    INT16 x, y;
    INT16 vx;
    UINT8 hp;
    UINT8 type;         // ENEMY_THUG, ENEMY_DRONE, ENEMY_WARDEN
    UINT8 facing;
    UINT8 state;
    UINT8 anim_frame;
    UINT8 anim_timer;
    UINT8 patrol_min;   // Patrol left bound (tile x)
    UINT8 patrol_max;   // Patrol right bound (tile x)
    UINT8 iframes;
    UINT8 attack_timer;
} Enemy;

// ============================================================
// EXTERN GLOBALS
// ============================================================
extern GameState game_state;
extern Player player;
extern Enemy enemies[MAX_ENEMIES];
extern UINT8 num_enemies;
extern INT16 camera_x;
extern UINT8 frame_count;
extern UINT8 joypad_current;
extern UINT8 joypad_previous;

// Function declarations
extern UINT8 joy_pressed(UINT8 btn);
extern UINT8 joy_held(UINT8 btn);

#endif // GAME_H
