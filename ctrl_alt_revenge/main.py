# main.py — Entry point, game loop
# CTRL+ALT REVENGE! — Picchia Duro a Scorrimento
import sys
import os
import random

# Aggiungi la directory padre al path per gli import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()
pygame.mixer.init()

from ctrl_alt_revenge.settings import (
    TITLE, INTERNAL_WIDTH, INTERNAL_HEIGHT, SCALE,
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TILE_SIZE,
    COLOR_BG_NIGHT, COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
    COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_WHITE_UI,
    COLOR_GREEN_HACK, COLOR_DARK_GRAY, COLOR_MID_GRAY,
    HACK_SLOWMO_FACTOR, HEAT_DECAY_RATE, HEAT_MAX,
    STRINGS, EMP_COOLDOWN, BULLET_TIME_DURATION,
    PLAYER_IFRAMES,
)
from ctrl_alt_revenge.core.state_machine import StateMachine, State
from ctrl_alt_revenge.core.input import InputManager
from ctrl_alt_revenge.core.camera import Camera
from ctrl_alt_revenge.core.assets import AssetManager
from ctrl_alt_revenge.core.sprite_generator import generate_all_sprites
from ctrl_alt_revenge.entities.player import Player
from ctrl_alt_revenge.entities.enemies.thug import Thug
from ctrl_alt_revenge.entities.enemies.drone import Drone
from ctrl_alt_revenge.entities.enemies.boss_warden import BossWarden
from ctrl_alt_revenge.systems.physics import PhysicsSystem
from ctrl_alt_revenge.systems.combat import CombatSystem
from ctrl_alt_revenge.systems.hacking import HackingMinigame
from ctrl_alt_revenge.systems.implants import ImplantSystem
from ctrl_alt_revenge.systems.dialog import DialogSystem
from ctrl_alt_revenge.ui.hud import HUD
from ctrl_alt_revenge.ui.dialog_box import DialogBox
from ctrl_alt_revenge.ui.menu import (
    MainMenu, PauseMenu, ControlsScreen,
    GameOverScreen, LevelCompleteScreen
)
from ctrl_alt_revenge.data.levels.level_01 import generate_level_01
from ctrl_alt_revenge.data.dialogs.level_01_dialogs import DIALOG_INTRO, DIALOG_BOSS_INTRO


class Game:
    """Classe principale del gioco."""

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.internal_surface = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        self.input_mgr = InputManager()
        self.asset_mgr = AssetManager()
        self.sprites = generate_all_sprites()

        self.fsm = StateMachine()
        self._register_states()
        self.fsm.change("menu")

    def _register_states(self):
        self.fsm.register("menu", MenuState(self))
        self.fsm.register("controls", ControlsState(self))
        self.fsm.register("play", PlayState(self))
        self.fsm.register("pause", PauseState(self))
        self.fsm.register("hack", HackState(self))
        self.fsm.register("dialog", DialogState(self))
        self.fsm.register("game_over", GameOverState(self))
        self.fsm.register("level_complete", LevelCompleteState(self))

    def run(self):
        """Game loop principale."""
        while self.running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False

            self.input_mgr.update(events)
            self.fsm.handle_events(events)
            self.fsm.update(1.0)

            self.internal_surface.fill(COLOR_BG_NIGHT)
            self.fsm.draw(self.internal_surface)

            # Scala pixel-perfect senza smoothing
            scaled = pygame.transform.scale(self.internal_surface,
                                            (SCREEN_WIDTH, SCREEN_HEIGHT))
            self.screen.blit(scaled, (0, 0))
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


# ============================================================
# STATI DEL GIOCO
# ============================================================

class MenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.menu = MainMenu()

    def enter(self, **kwargs):
        self.menu.selected = 0

    def update(self, dt):
        result = self.menu.update(self.game.input_mgr, dt)
        if result == "INIZIA":
            self.game.fsm.change("play", reload=True)
        elif result == "COMANDI":
            self.game.fsm.change("controls")
        elif result == "ESCI":
            self.game.running = False

    def draw(self, surface):
        self.menu.draw(surface)


class ControlsState(State):
    def __init__(self, game):
        super().__init__(game)
        self.screen = ControlsScreen()

    def update(self, dt):
        result = self.screen.update(self.game.input_mgr, dt)
        if result == "back":
            self.game.fsm.go_back()

    def draw(self, surface):
        self.screen.draw(surface)


class PlayState(State):
    """Stato di gioco principale — contiene tutto il gameplay."""

    def __init__(self, game):
        super().__init__(game)
        self.player = None
        self.enemies = []
        self.hackables = []  # terminali, telecamere
        self.projectiles = []
        self.camera = None
        self.physics = None
        self.combat = CombatSystem()
        self.hacking = HackingMinigame()
        self.implants = ImplantSystem()
        self.dialog_sys = DialogSystem()
        self.dialog_box = DialogBox()
        self.hud = None
        self.level_data = None
        self.slow_mo = 1.0
        self.dialog_triggers = []
        self.triggered_dialogs = set()
        self.gate_tiles = {}  # mapping terminale -> tile del cancello
        self.boss = None
        self.boss_intro_shown = False
        self.level_complete = False
        self._loaded = False
        self.screen_shake_timer = 0
        self.parry_flash_timer = 0
        self.particles = []

    def enter(self, **kwargs):
        # Carica il livello solo la prima volta o se esplicitamente richiesto
        if not self._loaded or kwargs.get("reload", False):
            self._load_level()
            self._loaded = True

    def _load_level(self):
        """Carica il livello 1."""
        self.level_data = generate_level_01()
        self.physics = PhysicsSystem(self.level_data)

        ent = self.level_data["entities"]
        sprites = self.game.sprites

        # Player
        px, py = ent["player_spawn"]
        self.player = Player(px, py)
        self.player.set_sprites(sprites["gig"])
        self.player.can_double_jump = True  # innesto attivo di default

        # Camera
        self.camera = Camera(self.level_data["width_px"],
                             self.level_data["height_px"])

        # HUD
        self.hud = HUD(sprites["heart_full"], sprites["heart_empty"])

        # Nemici
        self.enemies = []
        for t_data in ent.get("thugs", []):
            thug = Thug(t_data["x"], t_data["y"], t_data.get("patrol", 80))
            thug.set_sprites(sprites["thug"])
            self.enemies.append(thug)

        for d_data in ent.get("drones", []):
            drone = Drone(d_data["x"], d_data["y"], d_data.get("patrol", 100))
            drone.set_sprites(sprites["drone"])
            self.enemies.append(drone)

        # Hackables (terminali)
        self.hackables = []
        self.gate_tiles = {}
        for term in ent.get("terminals", []):
            hackable = type("Terminal", (), {
                "x": term["x"], "y": term["y"],
                "width": 16, "height": 16,
                "hackable": True, "hacked": False,
                "hack_type": term.get("type", "generic"),
                "hack_difficulty": 1, "hack_range": 50,
                "gate_tiles": term.get("gate_tiles", []),
                "sprite": sprites["terminal"],
                "on_hack_success": lambda s: None,
                "on_hack_fail": lambda s: None,
                "is_in_hack_range": None,  # impostato dopo
            })()
            def make_range_check(h):
                def check(px, py):
                    return abs(h.x + 8 - px) + abs(h.y + 8 - py) < h.hack_range
                return check
            hackable.is_in_hack_range = make_range_check(hackable)
            # Bind corretto per on_hack_success
            def make_success_callback(h):
                def callback():
                    h.hacked = True
                    # Apri il cancello rimuovendo le tile solide
                    for gx, gy in h.gate_tiles:
                        if 0 <= gy < len(self.level_data["collision"]) and \
                           0 <= gx < len(self.level_data["collision"][0]):
                            self.level_data["collision"][gy][gx] = 0
                            self.level_data["visual"][gy][gx] = 0
                    self.physics.rebuild(self.level_data)
                    self.hud.show_notification(STRINGS["hack_success"])
                return callback
            hackable.on_hack_success = make_success_callback(hackable)
            def make_fail_callback(h):
                def callback():
                    self.player.heat = min(self.player.heat + 0.3, HEAT_MAX)
                    self.hud.show_notification(STRINGS["hack_fail"])
                return callback
            hackable.on_hack_fail = make_fail_callback(hackable)
            self.hackables.append(hackable)

        # Aggiungi droni alla lista hackables
        for enemy in self.enemies:
            if isinstance(enemy, Drone):
                self.hackables.append(enemy)

        # Boss
        bx, by = ent.get("boss_spawn", (160 * TILE_SIZE, 22 * TILE_SIZE))
        self.boss = BossWarden(bx, by)
        self.boss.set_sprites(sprites["warden"])
        self.boss.set_arena(140 * TILE_SIZE, 179 * TILE_SIZE)
        self.boss.spawn_callback = self._spawn_boss_drone
        self.enemies.append(self.boss)

        # Dialoghi
        self.dialog_sys.add_dialog_data("intro", DIALOG_INTRO)
        self.dialog_sys.add_dialog_data("boss_intro", DIALOG_BOSS_INTRO)

        self.dialog_triggers = ent.get("dialogs", [])
        self.triggered_dialogs = set()
        self.boss_intro_shown = False
        self.level_complete = False
        self.projectiles = []
        self.slow_mo = 1.0
        self.screen_shake_timer = 0
        self.parry_flash_timer = 0
        self.particles = []

        # Pre-generate slow-mo overlay
        self.slowmo_overlay = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        self.slowmo_overlay.fill((0, 15, 50, 45))
        for y in range(0, INTERNAL_HEIGHT, 3):
            pygame.draw.line(self.slowmo_overlay, (0, 0, 0, 25), (0, y), (INTERNAL_WIDTH, y))

        # Pre-generate tile surfaces and background layers
        self._generate_tile_surfaces()
        self._generate_bg_layers()

    def _generate_tile_surfaces(self):
        """Pre-render 16x16 tile surfaces for each tile type."""
        TS = TILE_SIZE
        self.tile_surfaces = {}

        # --- Type 1: Ground (dark concrete) - 4 variants ---
        variants = []
        for v in range(4):
            rng = random.Random(1000 + v)
            surf = pygame.Surface((TS, TS))
            surf.fill((50, 45, 75))
            # Random noise pixels for texture
            for py in range(TS):
                for px in range(TS):
                    if rng.random() < 0.2:
                        offset = rng.randint(-8, 10)
                        c = (max(0, min(255, 50 + offset)),
                             max(0, min(255, 45 + offset)),
                             max(0, min(255, 75 + offset)))
                        surf.set_at((px, py), c)
            # Top edge highlight (subtle lighter line)
            for px in range(TS):
                surf.set_at((px, 0), (62, 57, 90))
            # Occasional crack line
            if v in (0, 2):
                cx = rng.randint(3, 12)
                for cy in range(rng.randint(2, 5), rng.randint(10, 14)):
                    surf.set_at((cx + rng.randint(-1, 1), cy), (38, 34, 58))
            variants.append(surf)
        self.tile_surfaces[1] = variants

        # --- Type 2: Wall/ceiling (metal panel) ---
        surf = pygame.Surface((TS, TS))
        surf.fill((55, 50, 80))
        # Panel border (bright)
        pygame.draw.rect(surf, (75, 70, 105), (0, 0, TS, TS), 1)
        # Inner panel line for depth
        pygame.draw.rect(surf, (48, 43, 72), (2, 2, TS - 4, TS - 4), 1)
        # Rivet dots in corners and mid-edges
        for rx, ry in [(2, 2), (TS - 3, 2), (2, TS - 3), (TS - 3, TS - 3),
                        (TS // 2, 2), (TS // 2, TS - 3), (2, TS // 2), (TS - 3, TS // 2)]:
            surf.set_at((rx, ry), (100, 98, 135))
        self.tile_surfaces[2] = surf

        # --- Type 3: Platform (thin neon blue gradient + support dots) ---
        surf = pygame.Surface((TS, TS), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        for py in range(3):
            t = py / 2.0  # 0.0 -> 1.0
            r = int(0 * (1 - t) + 15 * t)
            g = int(229 * (1 - t) + 50 * t)
            b = int(255 * (1 - t) + 80 * t)
            pygame.draw.line(surf, (r, g, b), (0, py), (TS - 1, py))
        # Small support dots below the platform
        for px in (3, 7, 11):
            surf.set_at((px, 4), (0, 140, 160, 180))
            surf.set_at((px, 5), (0, 100, 120, 120))
        self.tile_surfaces[3] = surf

        # --- Type 4: Gate (vertical bars) ---
        surf = pygame.Surface((TS, TS), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        for px in range(0, TS, 3):
            pygame.draw.line(surf, (55, 55, 75), (px, 0), (px, TS - 1))
            if px + 1 < TS:
                pygame.draw.line(surf, (40, 38, 60), (px + 1, 0), (px + 1, TS - 1))
        self.tile_surfaces[4] = surf

        # --- Type 5: Crate (cover) ---
        surf = pygame.Surface((TS, TS))
        surf.fill((60, 55, 80))
        # X pattern — lighter lines for visibility
        pygame.draw.line(surf, (80, 75, 110), (1, 1), (TS - 2, TS - 2))
        pygame.draw.line(surf, (80, 75, 110), (TS - 2, 1), (1, TS - 2))
        # Border
        pygame.draw.rect(surf, (85, 80, 115), (0, 0, TS, TS), 1)
        # Bright corner pixels
        for cx, cy in [(1, 1), (TS - 2, 1), (1, TS - 2), (TS - 2, TS - 2)]:
            surf.set_at((cx, cy), (110, 105, 145))
        self.tile_surfaces[5] = surf

        # --- Type 6: Boss floor (warning stripes) ---
        surf = pygame.Surface((TS, TS))
        surf.fill((70, 30, 30))
        # Diagonal warning stripes (2px wide, brighter orange)
        for i in range(-TS, TS * 2, 6):
            pygame.draw.line(surf, (255, 140, 30), (i, 0), (i + TS, TS), 2)
        # Dark separator between stripes for contrast
        for i in range(-TS + 3, TS * 2, 6):
            pygame.draw.line(surf, (45, 18, 18), (i, 0), (i + TS, TS), 1)
        self.tile_surfaces[6] = surf

        # --- Type 7: Boss wall (reinforced with neon orange trim) ---
        surf = pygame.Surface((TS, TS))
        surf.fill((50, 32, 32))
        # More visible horizontal neon orange trim lines
        pygame.draw.line(surf, (255, 140, 30), (0, 3), (TS - 1, 3))
        pygame.draw.line(surf, COLOR_NEON_ORANGE, (0, 4), (TS - 1, 4))
        pygame.draw.line(surf, (255, 140, 30), (0, 11), (TS - 1, 11))
        pygame.draw.line(surf, COLOR_NEON_ORANGE, (0, 12), (TS - 1, 12))
        # Subtle rivet dots between trim lines
        for rx in (3, 7, 11):
            surf.set_at((rx, 7), (90, 55, 55))
            surf.set_at((rx, 8), (90, 55, 55))
        self.tile_surfaces[7] = surf

    def _generate_bg_layers(self):
        """Pre-generate 3 parallax background layers as wide surfaces."""
        BG_W = 800
        H = INTERNAL_HEIGHT

        rng = random.Random(42)

        # --- Horizon gradient layer (rendered once, blitted first) ---
        self.bg_horizon = pygame.Surface((BG_W, H), pygame.SRCALPHA)
        self.bg_horizon.fill((0, 0, 0, 0))
        grad_height = 60
        for gy in range(grad_height):
            t = 1.0 - gy / grad_height  # 1.0 at bottom, 0.0 at top
            r = int(20 * t)
            g = int(15 * t)
            b = int(45 * t)
            a = int(180 * t)
            pygame.draw.line(self.bg_horizon, (r, g, b, a),
                             (0, H - grad_height + gy), (BG_W - 1, H - grad_height + gy))

        # --- Layer 1 (far): Tall building silhouettes ---
        self.bg_layer_far = pygame.Surface((BG_W, H), pygame.SRCALPHA)
        self.bg_layer_far.fill((0, 0, 0, 0))
        x = 0
        for i in range(20):
            bw = rng.randint(20, 45)
            gap = rng.randint(2, 8)
            bh = rng.randint(60, 120)
            by = H - bh
            pygame.draw.rect(self.bg_layer_far, (25, 22, 55), (x, by, bw, bh))
            # Rooftop edge highlight
            pygame.draw.line(self.bg_layer_far, (35, 32, 70), (x, by), (x + bw - 1, by))
            # Lit windows — more frequent, brighter colors
            for wy in range(by + 4, by + bh - 4, 6):
                for wx in range(x + 3, x + bw - 3, 5):
                    if rng.random() < 0.35:
                        c = rng.choice([
                            (90, 85, 130), (110, 100, 150), (70, 110, 140),
                            (130, 120, 80), (80, 130, 110),
                        ])
                        self.bg_layer_far.set_at((wx, wy), c)
                        if wx + 1 < x + bw - 2:
                            self.bg_layer_far.set_at((wx + 1, wy), c)
            x += bw + gap

        # --- Layer 2 (mid): Medium buildings ---
        self.bg_layer_mid = pygame.Surface((BG_W, H), pygame.SRCALPHA)
        self.bg_layer_mid.fill((0, 0, 0, 0))
        x = 0
        for i in range(18):
            bw = rng.randint(25, 50)
            gap = rng.randint(3, 10)
            bh = rng.randint(40, 80)
            by = H - bh
            pygame.draw.rect(self.bg_layer_mid, (35, 30, 65), (x, by, bw, bh))
            # Rooftop edge highlight
            pygame.draw.line(self.bg_layer_mid, (50, 45, 85), (x, by), (x + bw - 1, by))
            # Lit windows — even more frequent and brighter
            for wy in range(by + 3, by + bh - 3, 5):
                for wx in range(x + 2, x + bw - 2, 4):
                    if rng.random() < 0.45:
                        c = rng.choice([
                            (110, 100, 160), (140, 130, 180),
                            (80, 150, 170), (160, 140, 90),
                            (0, 200, 220), (180, 120, 60),
                        ])
                        self.bg_layer_mid.set_at((wx, wy), c)
                        if wx + 1 < x + bw - 1:
                            self.bg_layer_mid.set_at((wx + 1, wy), c)
                        if wy + 1 < by + bh - 2:
                            self.bg_layer_mid.set_at((wx, wy + 1), c)
            # Neon accent lines on most buildings
            if rng.random() < 0.55:
                ny = by + rng.randint(5, max(6, bh - 5))
                nc = rng.choice([COLOR_NEON_BLUE, COLOR_NEON_PURPLE, COLOR_NEON_ORANGE])
                pygame.draw.line(self.bg_layer_mid, nc, (x, ny), (x + bw - 1, ny))
            # Second accent line for some buildings
            if rng.random() < 0.25:
                ny2 = by + rng.randint(2, max(3, bh - 8))
                nc2 = rng.choice([COLOR_NEON_BLUE, COLOR_NEON_PURPLE])
                pygame.draw.line(self.bg_layer_mid, nc2, (x + 2, ny2), (x + bw - 3, ny2))
            x += bw + gap

        # --- Layer 3 (near): Close details, neon signs, power lines ---
        self.bg_layer_near = pygame.Surface((BG_W, H), pygame.SRCALPHA)
        self.bg_layer_near.fill((0, 0, 0, 0))
        x = 0
        for i in range(15):
            bw = rng.randint(15, 35)
            gap = rng.randint(8, 20)
            bh = rng.randint(15, 40)
            by = H - bh
            pygame.draw.rect(self.bg_layer_near, (35, 32, 70), (x, by, bw, bh))
            # Edge highlight
            pygame.draw.line(self.bg_layer_near, (50, 45, 90), (x, by), (x + bw - 1, by))
            x += bw + gap
        # Neon signs (bright colored rectangles, larger 4x3)
        for _ in range(20):
            sx = rng.randint(10, BG_W - 20)
            sy = rng.randint(H - 110, H - 25)
            sc = rng.choice([COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
                             COLOR_NEON_ORANGE, COLOR_RED_ALARM,
                             (0, 220, 255), (255, 100, 40), (180, 50, 255)])
            sw = rng.randint(3, 5)
            sh = rng.randint(2, 3)
            pygame.draw.rect(self.bg_layer_near, sc, (sx, sy, sw, sh))
            # Subtle glow around sign (1px border, dimmer)
            gr = min(255, sc[0] // 3)
            gg = min(255, sc[1] // 3)
            gb = min(255, sc[2] // 3)
            pygame.draw.rect(self.bg_layer_near, (gr, gg, gb, 100),
                             (sx - 1, sy - 1, sw + 2, sh + 2), 1)
        # Power line cables (horizontal lines with glow dots)
        for _ in range(5):
            ly = rng.randint(H - 130, H - 45)
            lx1 = rng.randint(0, BG_W // 3)
            lx2 = rng.randint(BG_W // 3, BG_W - 1)
            cable_color = (45, 42, 75)
            # Slight sag in middle
            mx = (lx1 + lx2) // 2
            pygame.draw.line(self.bg_layer_near, cable_color,
                             (lx1, ly), (mx, ly + 3))
            pygame.draw.line(self.bg_layer_near, cable_color,
                             (mx, ly + 3), (lx2, ly))
            # Small glow dots along cable
            num_dots = rng.randint(2, 5)
            for d in range(num_dots):
                t = (d + 1) / (num_dots + 1)
                dx = int(lx1 + (lx2 - lx1) * t)
                sag = int(3 * (1 - abs(2 * t - 1)))
                dy = ly + sag
                dot_c = rng.choice([(0, 200, 255), (255, 140, 30), (200, 80, 255)])
                self.bg_layer_near.set_at((dx, dy), dot_c)
                if dx + 1 < BG_W:
                    self.bg_layer_near.set_at((dx + 1, dy), dot_c)

    def _spawn_boss_drone(self, x, y, count):
        """Callback per il boss per spawnare droni."""
        sprites = self.game.sprites
        for i in range(count):
            drone = Drone(x + i * 30, y, 60)
            drone.set_sprites(sprites["drone"])
            drone.ai_state = "chase"
            drone.target = self.player
            self.enemies.append(drone)

    def update(self, dt):
        if self.level_complete:
            return

        # Slow-mo
        effective_dt = dt * self.slow_mo

        # Bullet time
        if self.player.bullet_time_active:
            self.player.bullet_time_timer -= dt
            if self.player.bullet_time_timer <= 0:
                self.player.bullet_time_active = False
                self.slow_mo = 1.0
            else:
                self.slow_mo = 0.4
        elif self.slow_mo != 1.0 and not self.hacking.active:
            self.slow_mo = 1.0

        # Player
        self.player.update(self.game.input_mgr, effective_dt)
        self.physics.apply_gravity(self.player, effective_dt)
        self.physics.move_and_collide(self.player, effective_dt)

        # Morte per caduta
        if self.player.y > self.level_data["height_px"] + 100:
            self.player.hp = 0
            self.player.alive = False

        # Nemici
        dead_enemies = []
        for enemy in self.enemies:
            enemy.update(effective_dt, self.player)
            if not isinstance(enemy, Drone) or not enemy.hacked_ally:
                self.physics.apply_gravity(enemy, effective_dt)
            self.physics.move_and_collide(enemy, effective_dt)

            # Pulizia nemici morti (dopo animazione)
            if not enemy.alive and enemy != self.boss:
                if hasattr(enemy, "anim_timer") and enemy.anim_frame >= len(
                    enemy.sprites.get(
                        enemy.current_anim + ("_right" if enemy.facing == 1 else "_left"), [None]
                    )
                ) - 1:
                    dead_enemies.append(enemy)
                    self.implants.on_enemy_killed(self.player)

        for de in dead_enemies:
            if de in self.enemies:
                self.enemies.remove(de)

        # Boss morto = livello completato
        if self.boss and not self.boss.alive:
            self.level_complete = True
            self.game.fsm.change("level_complete")
            return

        # Combat
        self.combat.update(self.player, self.enemies, effective_dt)

        # Screen shake on player hit
        if self.player.iframes > 0 and self.player.iframes > PLAYER_IFRAMES - 2:
            self.screen_shake_timer = 12
        if self.screen_shake_timer > 0:
            self.screen_shake_timer -= 1

        # Parry flash
        if self.player.parry_success:
            self.parry_flash_timer = 4
            self.player.parry_success = False
        if self.parry_flash_timer > 0:
            self.parry_flash_timer -= 1

        # Landing particles
        if self.player.on_ground and not self.player._was_on_ground and self.player.vel_y >= -0.1:
            for _ in range(5):
                self.particles.append({
                    "x": self.player.x + self.player.collision_width // 2 + random.randint(-8, 8),
                    "y": self.player.y + self.player.collision_height,
                    "vx": random.uniform(-0.8, 0.8),
                    "vy": random.uniform(-1.5, -0.3),
                    "timer": random.randint(8, 16),
                })

        # Update particles
        for p in self.particles:
            p["x"] += p["vx"]; p["y"] += p["vy"]; p["vy"] += 0.05; p["timer"] -= 1
        self.particles = [p for p in self.particles if p["timer"] > 0]

        # Heat decay
        self.player.heat = max(0, self.player.heat - HEAT_DECAY_RATE * effective_dt)

        # Hack: controlla vicinanza a oggetti hackabili
        self.player.nearby_hackable = None
        for h in self.hackables:
            if getattr(h, "hacked", False):
                continue
            if h.is_in_hack_range(self.player.x, self.player.y):
                self.player.nearby_hackable = h
                break

        # Tasto hack
        if (self.game.input_mgr.is_just_pressed("hack") and
                self.player.nearby_hackable and self.player.alive):
            self.hacking.start(self.player.nearby_hackable)
            self.game.fsm.change("hack")

        # Innesti
        self.implants.update(effective_dt)
        for i in range(4):
            key = f"implant{i + 1}"
            if self.game.input_mgr.is_just_pressed(key):
                result = self.implants.use_implant(i, self.player, self)
                if result == "emp_shot":
                    self._fire_emp()

        # Dialog triggers
        for trig in self.dialog_triggers:
            if trig["dialog_id"] in self.triggered_dialogs:
                continue
            dist = abs(self.player.x - trig["x"]) + abs(self.player.y - trig["y"])
            if dist < 40:
                if self.dialog_sys.start_dialog(trig["dialog_id"]):
                    self.triggered_dialogs.add(trig["dialog_id"])
                    self.game.fsm.change("dialog")
                    return

        # Boss intro
        if not self.boss_intro_shown and self.player.x > 142 * TILE_SIZE:
            self.boss_intro_shown = True
            if self.dialog_sys.start_dialog("boss_intro"):
                self.triggered_dialogs.add("boss_intro")
                self.game.fsm.change("dialog")
                return

        # Pausa
        if self.game.input_mgr.is_just_pressed("pause"):
            self.game.fsm.change("pause")
            return

        # Game over
        if not self.player.alive:
            self.game.fsm.change("game_over")
            return

        # Camera
        self.camera.update(self.player.collision_rect, effective_dt)

        # HUD
        self.hud.update(dt)

        # Proiettili
        self._update_projectiles(effective_dt)

    def _fire_emp(self):
        """Spara un proiettile EMP nella direzione del player."""
        px = self.player.x + self.player.collision_width // 2
        py = self.player.y + self.player.collision_height // 2
        vel_x = self.player.facing * 5
        self.projectiles.append({
            "x": px, "y": py, "vel_x": vel_x, "vel_y": 0,
            "type": "emp", "timer": 60,
            "sprite": self.game.sprites["emp"],
        })

    def _update_projectiles(self, dt):
        """Aggiorna proiettili."""
        to_remove = []
        for proj in self.projectiles:
            proj["x"] += proj["vel_x"] * dt
            proj["y"] += proj["vel_y"] * dt
            proj["timer"] -= dt

            if proj["timer"] <= 0:
                to_remove.append(proj)
                continue

            # Collisione EMP con nemici
            if proj["type"] == "emp":
                proj_rect = pygame.Rect(int(proj["x"]) - 4, int(proj["y"]) - 4, 8, 8)
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    if proj_rect.colliderect(enemy.hurtbox_rect):
                        enemy.stun(120)
                        to_remove.append(proj)
                        break

        for p in to_remove:
            if p in self.projectiles:
                self.projectiles.remove(p)

    def draw(self, surface):
        cam_off = list(self.camera.get_offset())
        if self.screen_shake_timer > 0:
            cam_off[0] += random.randint(-2, 2)
            cam_off[1] += random.randint(-2, 2)
        cam_off = tuple(cam_off)
        visible = self.camera.get_visible_rect()

        # Sfondo parallasse semplice
        self._draw_background(surface, cam_off)

        # Tilemap
        self._draw_tiles(surface, cam_off, visible)

        # Hackables (terminali)
        for h in self.hackables:
            if hasattr(h, "sprite") and h.sprite:
                if not getattr(h, "hacked", False):
                    sx = int(h.x) + cam_off[0]
                    sy = int(h.y) + cam_off[1]
                    surface.blit(h.sprite, (sx, sy))
                    # Indicatore hack range
                    if h == self.player.nearby_hackable:
                        font = pygame.font.SysFont("consolas", 12)
                        txt = font.render("[E] HACK", False, COLOR_GREEN_HACK)
                        surface.blit(txt, (sx - 4, sy - 16))

        # Nemici
        for enemy in self.enemies:
            if not enemy.active:
                continue
            # Visione termica: evidenzia nemici
            if self.player.thermal_vision and enemy.alive:
                er = enemy.rect.move(cam_off[0], cam_off[1])
                pygame.draw.rect(surface, (255, 120, 0), er.inflate(4, 4), 2)
                glow = pygame.Surface((er.width + 8, er.height + 8), pygame.SRCALPHA)
                pygame.draw.rect(glow, (255, 100, 0, 35), glow.get_rect(), 3)
                surface.blit(glow, (er.x - 4, er.y - 4))
            enemy.draw(surface, cam_off)

        # Proiettili
        for proj in self.projectiles:
            if proj["sprite"]:
                sx = int(proj["x"]) + cam_off[0] - proj["sprite"].get_width() // 2
                sy = int(proj["y"]) + cam_off[1] - proj["sprite"].get_height() // 2
                surface.blit(proj["sprite"], (sx, sy))

        # Player
        self.player.draw(surface, cam_off)

        # Landing dust particles
        for p in self.particles:
            alpha = int(200 * p["timer"] / 16)
            px = int(p["x"]) + cam_off[0]
            py = int(p["y"]) + cam_off[1]
            ps_surf = pygame.Surface((2, 2), pygame.SRCALPHA)
            ps_surf.fill((180, 180, 200, alpha))
            surface.blit(ps_surf, (px, py))

        # Effetti combat
        self.combat.draw_effects(surface, cam_off,
                                 self.game.sprites.get("particles", {}))

        # Indicatore hack vicino
        if self.player.nearby_hackable and not self.hacking.active:
            pass  # già disegnato sopra

        # Parry flash
        if self.parry_flash_timer > 0:
            flash = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 60))
            surface.blit(flash, (0, 0))

        # Slow-mo overlay
        if self.slow_mo < 1.0:
            surface.blit(self.slowmo_overlay, (0, 0))

        # HUD
        implant_info = self.implants.get_equipped_info()
        self.hud.draw(surface, self.player, implant_info, self.player.heat)

    def _draw_background(self, surface, cam_off):
        """Sfondo parallasse cyberpunk — blit pre-generated layers."""
        BG_W = 800
        W = INTERNAL_WIDTH

        # Horizon gradient (static, no parallax)
        surface.blit(self.bg_horizon, (0, 0))

        # Layer 1 (far, parallax 0.05)
        ox = int(cam_off[0] * 0.05) % BG_W
        surface.blit(self.bg_layer_far, (-ox, 0))
        if ox > BG_W - W:
            surface.blit(self.bg_layer_far, (BG_W - ox, 0))

        # Layer 2 (mid, parallax 0.2)
        ox = int(cam_off[0] * 0.2) % BG_W
        surface.blit(self.bg_layer_mid, (-ox, 0))
        if ox > BG_W - W:
            surface.blit(self.bg_layer_mid, (BG_W - ox, 0))

        # Layer 3 (near, parallax 0.4)
        ox = int(cam_off[0] * 0.4) % BG_W
        surface.blit(self.bg_layer_near, (-ox, 0))
        if ox > BG_W - W:
            surface.blit(self.bg_layer_near, (BG_W - ox, 0))

    def _draw_tiles(self, surface, cam_off, visible):
        """Disegna le tile visibili usando superfici pre-generate."""
        visual = self.level_data["visual"]
        start_col = max(0, visible.left // TILE_SIZE - 1)
        end_col = min(self.level_data["width"], visible.right // TILE_SIZE + 2)
        start_row = max(0, visible.top // TILE_SIZE - 1)
        end_row = min(self.level_data["height"], visible.bottom // TILE_SIZE + 2)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile = visual[row][col]
                if tile == 0:
                    continue
                tx = col * TILE_SIZE + cam_off[0]
                ty = row * TILE_SIZE + cam_off[1]
                tile_surf = self.tile_surfaces.get(tile)
                if tile_surf is None:
                    continue
                # Type 1 has 4 variants, pick by position
                if tile == 1:
                    variant_idx = (col * 7 + row * 13) % 4
                    surface.blit(tile_surf[variant_idx], (tx, ty))
                else:
                    surface.blit(tile_surf, (tx, ty))


class HackState(State):
    """Stato hacking — il gioco rallenta, si gioca il mini-puzzle."""

    def __init__(self, game):
        super().__init__(game)

    def enter(self, **kwargs):
        play_state = self.game.fsm._states.get("play")
        if play_state:
            play_state.slow_mo = HACK_SLOWMO_FACTOR

    def update(self, dt):
        play_state = self.game.fsm._states.get("play")
        if not play_state:
            return

        # Aggiorna il gioco al rallentatore
        play_state.update(dt * HACK_SLOWMO_FACTOR)

        # Aggiorna il mini-gioco
        play_state.hacking.update(self.game.input_mgr, dt)

        if not play_state.hacking.active:
            play_state.slow_mo = 1.0
            if play_state.hacking.failed:
                play_state.player.heat = min(
                    play_state.player.heat + 0.3, HEAT_MAX)
            self.game.fsm.change("play")

    def draw(self, surface):
        play_state = self.game.fsm._states.get("play")
        if play_state:
            play_state.draw(surface)
            play_state.hacking.draw(surface)


class DialogState(State):
    """Stato dialogo — il gioco è in pausa, si interagisce col dialogo."""

    def __init__(self, game):
        super().__init__(game)

    def update(self, dt):
        play_state = self.game.fsm._states.get("play")
        if not play_state:
            return

        play_state.dialog_sys.update(self.game.input_mgr, dt)

        if not play_state.dialog_sys.active:
            self.game.fsm.change("play")

    def draw(self, surface):
        play_state = self.game.fsm._states.get("play")
        if play_state:
            play_state.draw(surface)
            dialog_data = play_state.dialog_sys.get_display_data()
            play_state.dialog_box.draw(surface, dialog_data)


class PauseState(State):
    def __init__(self, game):
        super().__init__(game)
        self.menu = PauseMenu()

    def enter(self, **kwargs):
        self.menu.selected = 0

    def update(self, dt):
        result = self.menu.update(self.game.input_mgr, dt)
        if result == "CONTINUA":
            self.game.fsm.change("play")
        elif result == "COMANDI":
            self.game.fsm.change("controls")
        elif result == "MENU PRINCIPALE":
            # Reset per ricaricare il livello al prossimo avvio
            play_state = self.game.fsm._states.get("play")
            if play_state:
                play_state._loaded = False
            self.game.fsm.change("menu")

    def draw(self, surface):
        play_state = self.game.fsm._states.get("play")
        if play_state:
            play_state.draw(surface)
        self.menu.draw(surface)


class GameOverState(State):
    def __init__(self, game):
        super().__init__(game)
        self.screen = GameOverScreen()

    def enter(self, **kwargs):
        self.screen.timer = 0

    def update(self, dt):
        result = self.screen.update(self.game.input_mgr, dt)
        if result == "retry":
            self.game.fsm.change("play", reload=True)

    def draw(self, surface):
        self.screen.draw(surface)


class LevelCompleteState(State):
    def __init__(self, game):
        super().__init__(game)
        self.screen = LevelCompleteScreen()

    def enter(self, **kwargs):
        self.screen.timer = 0

    def update(self, dt):
        result = self.screen.update(self.game.input_mgr, dt)
        if result == "menu":
            self.game.fsm.change("menu")

    def draw(self, surface):
        self.screen.draw(surface)


if __name__ == "__main__":
    game = Game()
    game.run()
