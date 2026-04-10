# main.py — Entry point, game loop
# CTRL+ALT REVENGE! — Picchia Duro a Scorrimento
import sys
import os

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
        cam_off = self.camera.get_offset()
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
                        font = pygame.font.SysFont("consolas", 6)
                        txt = font.render("[E] HACK", False, COLOR_GREEN_HACK)
                        surface.blit(txt, (sx - 4, sy - 8))

        # Nemici
        for enemy in self.enemies:
            if not enemy.active:
                continue
            # Visione termica: evidenzia nemici
            if self.player.thermal_vision and enemy.alive:
                thermal_rect = enemy.rect.move(cam_off[0], cam_off[1])
                thermal_surf = pygame.Surface(
                    (thermal_rect.width + 4, thermal_rect.height + 4), pygame.SRCALPHA)
                thermal_surf.fill((255, 100, 0, 60))
                surface.blit(thermal_surf, (thermal_rect.x - 2, thermal_rect.y - 2))
            enemy.draw(surface, cam_off)

        # Proiettili
        for proj in self.projectiles:
            if proj["sprite"]:
                sx = int(proj["x"]) + cam_off[0] - proj["sprite"].get_width() // 2
                sy = int(proj["y"]) + cam_off[1] - proj["sprite"].get_height() // 2
                surface.blit(proj["sprite"], (sx, sy))

        # Player
        self.player.draw(surface, cam_off)

        # Effetti combat
        self.combat.draw_effects(surface, cam_off,
                                 self.game.sprites.get("particles", {}))

        # Indicatore hack vicino
        if self.player.nearby_hackable and not self.hacking.active:
            pass  # già disegnato sopra

        # HUD
        implant_info = self.implants.get_equipped_info()
        self.hud.draw(surface, self.player, implant_info, self.player.heat)

        # Slow-mo overlay
        if self.slow_mo < 1.0:
            overlay = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 40, 30))
            surface.blit(overlay, (0, 0))

    def _draw_background(self, surface, cam_off):
        """Sfondo parallasse cyberpunk."""
        # Strato grattacieli lontani (parallasse lenta)
        parallax_x = cam_off[0] * 0.1
        for i in range(15):
            bx = int(i * 40 + parallax_x) % INTERNAL_WIDTH - 20
            bh = 60 + (i * 37) % 80
            by = INTERNAL_HEIGHT - bh - 20
            pygame.draw.rect(surface, (18, 16, 48), (bx, by, 25, bh))
            # Finestre
            for wy in range(by + 4, by + bh - 4, 8):
                for wx in range(bx + 3, bx + 22, 6):
                    if (wx + wy) % 13 < 5:
                        pygame.draw.rect(surface, (40, 35, 70), (wx, wy, 3, 4))

        # Strato medio (parallasse media)
        parallax_x2 = cam_off[0] * 0.3
        for i in range(10):
            bx = int(i * 55 + parallax_x2) % INTERNAL_WIDTH - 30
            bh = 40 + (i * 53) % 60
            by = INTERNAL_HEIGHT - bh - 5
            pygame.draw.rect(surface, (22, 20, 55), (bx, by, 35, bh))
            # Neon
            if i % 3 == 0:
                neon_color = [COLOR_NEON_BLUE, COLOR_NEON_PURPLE, COLOR_NEON_ORANGE][i % 3]
                pygame.draw.line(surface, neon_color,
                                 (bx, by + bh // 2), (bx + 35, by + bh // 2), 1)

    def _draw_tiles(self, surface, cam_off, visible):
        """Disegna le tile visibili."""
        visual = self.level_data["visual"]
        start_col = max(0, visible.left // TILE_SIZE - 1)
        end_col = min(self.level_data["width"], visible.right // TILE_SIZE + 2)
        start_row = max(0, visible.top // TILE_SIZE - 1)
        end_row = min(self.level_data["height"], visible.bottom // TILE_SIZE + 2)

        tile_colors = {
            1: (35, 32, 60),      # pavimento standard
            2: (45, 42, 70),      # muro/soffitto
            3: (55, 52, 80),      # piattaforma one-way
            4: (50, 50, 65),      # porta/cancello
            5: (40, 38, 55),      # copertura stealth
            6: (55, 25, 25),      # pavimento boss
            7: (65, 30, 30),      # muro boss
        }

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile = visual[row][col]
                if tile == 0:
                    continue
                tx = col * TILE_SIZE + cam_off[0]
                ty = row * TILE_SIZE + cam_off[1]
                color = tile_colors.get(tile, (35, 32, 60))
                pygame.draw.rect(surface, color, (tx, ty, TILE_SIZE, TILE_SIZE))
                # Bordo sottile per visibilità
                pygame.draw.rect(surface, (25, 22, 45), (tx, ty, TILE_SIZE, TILE_SIZE), 1)

                # Dettagli speciali
                if tile == 3:  # one-way: linea superiore luminosa
                    pygame.draw.line(surface, COLOR_NEON_BLUE,
                                     (tx, ty), (tx + TILE_SIZE - 1, ty), 1)
                elif tile == 4:  # cancello: barre
                    for bar_y in range(ty + 2, ty + TILE_SIZE, 4):
                        pygame.draw.line(surface, (70, 70, 90),
                                         (tx + 2, bar_y), (tx + TILE_SIZE - 2, bar_y), 1)
                elif tile == 6:  # boss floor: pattern
                    if (row + col) % 2 == 0:
                        pygame.draw.rect(surface, (60, 28, 28),
                                         (tx + 2, ty + 2, TILE_SIZE - 4, TILE_SIZE - 4))


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
