# ui/menu.py — Main menu, pause, controls, game over, level complete
import pygame
import math
import random
import ctrl_alt_revenge.settings as settings
from ctrl_alt_revenge.settings import (
    COLOR_BG_NIGHT, COLOR_WHITE_UI, COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
    COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_GREEN_HACK,
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
    STRINGS,
)


class MainMenu:
    """Cyberpunk title screen with cityscape, rain, GIG character, and neon glow."""

    def __init__(self):
        self.font_title = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_sub = pygame.font.SysFont("consolas", 10)
        self.font_opt = pygame.font.SysFont("consolas", 12)
        self.font_small = pygame.font.SysFont("consolas", 10)
        self.timer = 0
        self.selected = 0
        self.options = ["INIZIA", "COMANDI", "ESCI"]
        self.state = "main"  # "main" or "difficulty"
        self.diff_selected = 0
        self.diff_options = list(settings.DIFFICULTIES.keys())
        self.scanline_offset = 0
        self.cursor_blink = 0

        # --- Pre-generate cityscape background ---
        self.bg_surface = self._generate_cityscape()

        # --- Rain drops ---
        self.rain_drops = [(random.randint(0, INTERNAL_WIDTH - 1),
                            random.randint(0, INTERNAL_HEIGHT - 1),
                            random.randint(3, 5))
                           for _ in range(35)]
        self.rain_offset = 0

        # --- GIG character sprite ---
        self.gig_sprite = None
        self.gig_frame = 0
        self.gig_anim_timer = 0
        self.gig_frames = []
        try:
            from ctrl_alt_revenge.core.sprite_generator import generate_gig_sprites
            sprites = generate_gig_sprites()
            idle_frames = sprites.get("idle_right", [])
            if idle_frames:
                for frame in idle_frames[:2]:
                    scaled = pygame.transform.scale(
                        frame,
                        (frame.get_width() * 2, frame.get_height() * 2)
                    )
                    # Flip to face left (toward title)
                    flipped = pygame.transform.flip(scaled, True, False)
                    self.gig_frames.append(flipped)
                self.gig_sprite = self.gig_frames[0]
        except Exception:
            self.gig_sprite = None

        # --- Window flicker state ---
        self.window_flicker_timer = 0
        self.flicker_windows = []  # list of (x, y, on/off)

        # --- Neon sign pulse ---
        self.neon_pulse_phase = 0.0

    def _generate_cityscape(self):
        """Pre-render the cyberpunk city background."""
        W, H = INTERNAL_WIDTH, INTERNAL_HEIGHT
        bg = pygame.Surface((W, H), pygame.SRCALPHA)

        # Sky gradient: dark purple top to blue-purple at horizon
        sky_top = (13, 11, 43)
        sky_bottom = (24, 21, 63)
        horizon_y = int(H * 0.72)
        for y in range(horizon_y):
            t = y / max(horizon_y - 1, 1)
            r = int(sky_top[0] + (sky_bottom[0] - sky_top[0]) * t)
            g = int(sky_top[1] + (sky_bottom[1] - sky_top[1]) * t)
            b = int(sky_top[2] + (sky_bottom[2] - sky_top[2]) * t)
            pygame.draw.line(bg, (r, g, b), (0, y), (W - 1, y))

        # Stars / distant lights in the sky
        rng = random.Random(42)
        for _ in range(25):
            sx = rng.randint(0, W - 1)
            sy = rng.randint(5, horizon_y - 60)
            brightness = rng.randint(100, 200)
            bg.set_at((sx, sy), (brightness, brightness, brightness + 30))

        # Buildings: multiple layers for depth
        buildings_data = []
        # Far buildings (darker, shorter variation)
        far_buildings = [
            (0, 85), (22, 70), (42, 95), (62, 60), (85, 80),
            (108, 100), (130, 65), (150, 90), (172, 75), (195, 105),
            (218, 55), (240, 88), (260, 72), (280, 95), (300, 68)
        ]
        for bx, bh in far_buildings:
            bw = rng.randint(18, 28)
            by = horizon_y - bh
            col_base = (18 + rng.randint(0, 8), 16 + rng.randint(0, 8), 40 + rng.randint(0, 10))
            pygame.draw.rect(bg, col_base, (bx, by, bw, bh))
            buildings_data.append((bx, by, bw, bh, "far"))

            # Windows on far buildings (sparse)
            for wy in range(by + 3, by + bh - 4, 5):
                for wx in range(bx + 2, bx + bw - 3, 4):
                    if rng.random() < 0.15:
                        wc = rng.choice([
                            (0, 180, 210), (200, 190, 80), (220, 210, 180),
                            (0, 200, 230), (180, 160, 60)
                        ])
                        bg.set_at((wx, wy), wc)
                        bg.set_at((wx + 1, wy), wc)

        # Near buildings (taller, more detail)
        near_buildings = [
            (5, 110), (30, 80), (55, 120), (85, 70), (110, 105),
            (140, 130), (170, 75), (195, 100), (225, 115), (255, 85),
            (285, 125)
        ]
        for bx, bh in near_buildings:
            bw = rng.randint(22, 35)
            by = horizon_y - bh
            col_r = 22 + rng.randint(0, 12)
            col_g = 20 + rng.randint(0, 10)
            col_b = 48 + rng.randint(0, 12)
            col_base = (col_r, col_g, col_b)
            col_edge = (col_r - 5, col_g - 5, col_b - 5)
            pygame.draw.rect(bg, col_base, (bx, by, bw, bh))
            # Darker edge on the right side
            pygame.draw.rect(bg, col_edge, (bx + bw - 2, by, 2, bh))

            # Rooftop details
            detail = rng.choice(["antenna", "tank", "ac", "none"])
            if detail == "antenna":
                ax = bx + bw // 2
                pygame.draw.line(bg, (40, 38, 60), (ax, by - 8), (ax, by), 1)
                bg.set_at((ax, by - 8), (255, 50, 50))  # red light on top
            elif detail == "tank":
                pygame.draw.rect(bg, (35, 33, 55), (bx + bw // 2 - 1, by - 3, 3, 3))
            elif detail == "ac":
                pygame.draw.rect(bg, (28, 26, 45), (bx + 3, by - 2, 3, 2))

            # Windows with proper 2x2 density
            window_positions = []
            for wy in range(by + 4, by + bh - 4, 5):
                for wx in range(bx + 3, bx + bw - 4, 5):
                    if rng.random() < 0.22:
                        wc = rng.choice([
                            (0, 210, 240),    # cyan
                            (220, 200, 80),   # yellow
                            (230, 220, 190),  # warm white
                            (0, 190, 220),    # blue-cyan
                            (200, 180, 60),   # dim yellow
                        ])
                        pygame.draw.rect(bg, wc, (wx, wy, 2, 2))
                        window_positions.append((wx, wy, wc))

            # Neon signs (occasional)
            if rng.random() < 0.3 and bh > 60:
                sign_y = by + rng.randint(10, bh // 2)
                sign_x = bx + rng.randint(2, max(3, bw - 6))
                sign_w = rng.randint(3, 5)
                sign_h = 2
                sign_color = rng.choice([
                    (255, 100, 20),   # orange
                    (180, 40, 255),   # purple
                    (0, 220, 255),    # cyan
                    (255, 50, 80),    # pink-red
                ])
                pygame.draw.rect(bg, sign_color, (sign_x, sign_y, sign_w, sign_h))
                # Glow around sign (subtle)
                glow_surf = pygame.Surface((sign_w + 4, sign_h + 4), pygame.SRCALPHA)
                glow_surf.fill((*sign_color[:3], 25))
                bg.blit(glow_surf, (sign_x - 2, sign_y - 2))

        # Neon haze at city/street boundary
        for y in range(horizon_y - 5, horizon_y + 10):
            haze = pygame.Surface((W, 1), pygame.SRCALPHA)
            intensity = max(0, 20 - abs(y - horizon_y) * 3)
            haze.fill((160, 40, 220, intensity))
            bg.blit(haze, (0, y))
        for y in range(horizon_y - 3, horizon_y + 8):
            haze2 = pygame.Surface((W, 1), pygame.SRCALPHA)
            intensity2 = max(0, 15 - abs(y - (horizon_y + 2)) * 3)
            haze2.fill((255, 120, 30, intensity2))
            bg.blit(haze2, (0, y))

        # Street level: dark strip with neon reflections
        street_color = (10, 9, 30)
        pygame.draw.rect(bg, street_color, (0, horizon_y, W, H - horizon_y))

        # Wet street reflections
        for _ in range(80):
            rx = rng.randint(0, W - 1)
            ry = rng.randint(horizon_y + 2, H - 5)
            ref_color = rng.choice([
                (0, 80, 100, 50),
                (80, 60, 20, 40),
                (100, 90, 60, 35),
                (60, 20, 100, 40),
                (0, 100, 120, 45),
                (120, 50, 10, 35),
            ])
            stretch = rng.randint(1, 3)
            ref_surf = pygame.Surface((stretch, 1), pygame.SRCALPHA)
            ref_surf.fill(ref_color)
            bg.blit(ref_surf, (rx, ry))

        return bg

    def update(self, input_mgr, dt=1.0):
        self.timer += dt
        self.scanline_offset = (self.scanline_offset + dt * 0.3) % 3
        self.cursor_blink = (self.cursor_blink + dt) % 30

        # Rain animation
        self.rain_offset = (self.rain_offset + dt) % INTERNAL_HEIGHT

        # GIG breathing animation
        if self.gig_frames:
            self.gig_anim_timer += dt
            if self.gig_anim_timer >= 30:
                self.gig_anim_timer = 0
                self.gig_frame = (self.gig_frame + 1) % len(self.gig_frames)
                self.gig_sprite = self.gig_frames[self.gig_frame]

        # Window flicker
        self.window_flicker_timer += dt

        # Neon pulse
        self.neon_pulse_phase += dt * 0.03

        # Input
        if self.state == "main":
            if input_mgr.is_just_pressed("up"):
                self.selected = (self.selected - 1) % len(self.options)
            if input_mgr.is_just_pressed("down"):
                self.selected = (self.selected + 1) % len(self.options)
            if input_mgr.is_just_pressed("confirm"):
                chosen = self.options[self.selected]
                if chosen == "INIZIA":
                    self.state = "difficulty"
                    self.diff_selected = self.diff_options.index(settings.CURRENT_DIFFICULTY)
                    return None
                return chosen
        elif self.state == "difficulty":
            if input_mgr.is_just_pressed("up"):
                self.diff_selected = (self.diff_selected - 1) % len(self.diff_options)
            if input_mgr.is_just_pressed("down"):
                self.diff_selected = (self.diff_selected + 1) % len(self.diff_options)
            if input_mgr.is_just_pressed("confirm"):
                settings.CURRENT_DIFFICULTY = self.diff_options[self.diff_selected]
                self.state = "main"
                return "INIZIA"
            if input_mgr.is_just_pressed("pause"):
                self.state = "main"
                return None
        return None

    def draw(self, surface):
        # Draw pre-rendered cityscape
        surface.blit(self.bg_surface, (0, 0))

        # Rain streaks
        rain_surf = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        for rx, ry, rlen in self.rain_drops:
            actual_y = (ry + int(self.rain_offset)) % INTERNAL_HEIGHT
            rain_color = (180, 200, 255, 60)
            for p in range(rlen):
                py = actual_y + p
                if 0 <= py < INTERNAL_HEIGHT:
                    rain_surf.set_at((rx, py), rain_color)
        surface.blit(rain_surf, (0, 0))

        # Neon sign pulse overlay (subtle brightness oscillation on a band)
        pulse = int(12 + 8 * math.sin(self.neon_pulse_phase))
        pulse_surf = pygame.Surface((INTERNAL_WIDTH, 3), pygame.SRCALPHA)
        pulse_surf.fill((255, 80, 20, pulse))
        surface.blit(pulse_surf, (0, int(INTERNAL_HEIGHT * 0.58)))

        # GIG character
        if self.gig_sprite is not None:
            gig_x, gig_y = INTERNAL_WIDTH - 70, INTERNAL_HEIGHT - 90
            # Cyan glow under feet
            glow_foot = pygame.Surface((50, 8), pygame.SRCALPHA)
            glow_foot.fill((0, 180, 220, 30))
            surface.blit(glow_foot, (gig_x + 5, gig_y + self.gig_sprite.get_height() - 4))
            # Draw GIG
            surface.blit(self.gig_sprite, (gig_x, gig_y))

        # --- Title: "CTRL+ALT REVENGE!" with neon glow layers ---
        title_text = STRINGS["title"]
        # Layer 1: distant glow (neon blue offset +2,+2)
        glow_far = self.font_title.render(title_text, False, (0, 229, 255))
        # Layer 2: near glow with alpha
        glow_near_base = self.font_title.render(title_text, False, (0, 200, 240))
        glow_near = pygame.Surface(glow_near_base.get_size(), pygame.SRCALPHA)
        glow_near.blit(glow_near_base, (0, 0))
        glow_near.set_alpha(150)
        # Layer 3: main text (bright cream white)
        title_main = self.font_title.render(title_text, False, (245, 241, 216))

        tx = INTERNAL_WIDTH // 2 - title_main.get_width() // 2
        ty = 30
        surface.blit(glow_far, (tx + 2, ty + 2))
        surface.blit(glow_near, (tx + 1, ty + 1))
        surface.blit(title_main, (tx, ty))

        # --- Subtitle ---
        sub = self.font_sub.render(STRINGS["subtitle"], False, COLOR_NEON_ORANGE)
        surface.blit(sub, (INTERNAL_WIDTH // 2 - sub.get_width() // 2, 58))

        # --- Thin neon separator line above menu ---
        sep_x = 60
        sep_y = 100
        pygame.draw.line(surface, (0, 180, 220), (sep_x, sep_y), (sep_x + 40, sep_y), 1)

        # --- Menu options ---
        opt_y_start = 108
        show_cursor = self.cursor_blink < 15
        for i, opt in enumerate(self.options):
            oy = opt_y_start + i * 20
            if i == self.selected:
                color = COLOR_NEON_ORANGE
                prefix = "> " if show_cursor else "  "
            else:
                color = (160, 155, 170)
                prefix = "  "
            text = self.font_opt.render(prefix + opt, False, color)
            surface.blit(text, (60, oy))

        # --- Version footer ---
        ver = self.font_small.render("v0.1 -- AGOSTO 2026", False, (60, 58, 80))
        surface.blit(ver, (INTERNAL_WIDTH // 2 - ver.get_width() // 2, INTERNAL_HEIGHT - 14))

        # --- Scanlines ---
        scanline_surf = pygame.Surface((INTERNAL_WIDTH, 1), pygame.SRCALPHA)
        scanline_surf.fill((0, 0, 0, 35))
        offset = int(self.scanline_offset)
        for row in range(offset, INTERNAL_HEIGHT, 3):
            surface.blit(scanline_surf, (0, row))

        # --- Difficulty sub-menu overlay ---
        if self.state == "difficulty":
            overlay = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            surface.blit(overlay, (0, 0))

            diff_title = self.font_opt.render("SCEGLI DIFFICOLTA'", False, COLOR_NEON_BLUE)
            surface.blit(diff_title, (INTERNAL_WIDTH // 2 - diff_title.get_width() // 2, 70))

            show_cursor = self.cursor_blink < 15
            for i, opt in enumerate(self.diff_options):
                oy = 95 + i * 22
                if i == self.diff_selected:
                    color = COLOR_NEON_ORANGE
                    prefix = "> " if show_cursor else "  "
                else:
                    color = (160, 155, 170)
                    prefix = "  "
                text = self.font_opt.render(prefix + opt, False, color)
                surface.blit(text, (INTERNAL_WIDTH // 2 - text.get_width() // 2, oy))

            desc = self.font_small.render("ESC per tornare", False, (100, 98, 120))
            surface.blit(desc, (INTERNAL_WIDTH // 2 - desc.get_width() // 2, 170))


class PauseMenu:
    """Pause overlay with scanlines."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 12, bold=True)
        self.font_opt = pygame.font.SysFont("consolas", 12)
        self.selected = 0
        self.options = ["CONTINUA", "COMANDI", "MENU PRINCIPALE"]
        self.scanline_offset = 0

    def update(self, input_mgr, dt=1.0):
        self.scanline_offset = (self.scanline_offset + dt * 0.3) % 3
        if input_mgr.is_just_pressed("up"):
            self.selected = (self.selected - 1) % len(self.options)
        if input_mgr.is_just_pressed("down"):
            self.selected = (self.selected + 1) % len(self.options)
        if input_mgr.is_just_pressed("confirm") or input_mgr.is_just_pressed("pause"):
            return self.options[self.selected]
        return None

    def draw(self, surface):
        # Dark overlay
        overlay = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        # Scanlines
        scanline_surf = pygame.Surface((INTERNAL_WIDTH, 1), pygame.SRCALPHA)
        scanline_surf.fill((0, 0, 0, 30))
        offset = int(self.scanline_offset)
        for row in range(offset, INTERNAL_HEIGHT, 3):
            surface.blit(scanline_surf, (0, row))

        # Title
        title = self.font.render(STRINGS["pause_text"], False, COLOR_WHITE_UI)
        surface.blit(title, (INTERNAL_WIDTH // 2 - title.get_width() // 2, 80))

        # Options
        for i, opt in enumerate(self.options):
            color = COLOR_NEON_ORANGE if i == self.selected else COLOR_WHITE_UI
            prefix = "> " if i == self.selected else "  "
            text = self.font_opt.render(prefix + opt, False, color)
            surface.blit(text, (INTERNAL_WIDTH // 2 - text.get_width() // 2, 115 + i * 22))


class ControlsScreen:
    """Controls reference screen."""

    def __init__(self):
        self.font_title = pygame.font.SysFont("consolas", 12, bold=True)
        self.font = pygame.font.SysFont("consolas", 10)
        self.controls = [
            ("Frecce / WASD", "Movimento"),
            ("SPAZIO / Z", "Salto"),
            ("J / X", "Pugno"),
            ("K / C", "Calcio"),
            ("L / V", "Parry"),
            ("E / Y", "Hack"),
            ("GIU'", "Accovacciati"),
            ("GIU' + SALTO (corsa)", "Slide"),
            ("1-4", "Innesti"),
            ("ESC / P", "Pausa"),
        ]

    def update(self, input_mgr, dt=1.0):
        if input_mgr.is_just_pressed("confirm") or input_mgr.is_just_pressed("pause"):
            return "back"
        return None

    def draw(self, surface):
        surface.fill(COLOR_BG_NIGHT)

        # Title
        title = self.font_title.render("< COMANDI >", False, COLOR_NEON_BLUE)
        surface.blit(title, (INTERNAL_WIDTH // 2 - title.get_width() // 2, 20))

        # Key-action pairs with proper 14px spacing
        for i, (key, action) in enumerate(self.controls):
            key_surf = self.font.render(key, False, COLOR_NEON_ORANGE)
            act_surf = self.font.render(action, False, COLOR_WHITE_UI)
            y = 46 + i * 14
            surface.blit(key_surf, (20, y))
            surface.blit(act_surf, (160, y))

        # Footer
        back = self.font.render("Premi INVIO per tornare", False, COLOR_WHITE_UI)
        surface.blit(back, (INTERNAL_WIDTH // 2 - back.get_width() // 2, INTERNAL_HEIGHT - 20))


class GameOverScreen:
    """Game Over screen with glitch offset effect."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 10)
        self.timer = 0

    def update(self, input_mgr, dt=1.0):
        self.timer += dt
        if self.timer > 60 and input_mgr.is_just_pressed("confirm"):
            return "retry"
        return None

    def draw(self, surface):
        surface.fill(COLOR_BG_NIGHT)

        text_str = STRINGS["game_over"]
        text = self.font.render(text_str, False, COLOR_RED_ALARM)
        x = INTERNAL_WIDTH // 2 - text.get_width() // 2
        y = INTERNAL_HEIGHT // 2 - 20

        # Glitch offset effect: periodic horizontal shift with color split
        frame = int(self.timer)
        if frame % 8 < 2:
            glitch = self.font.render(text_str, False, COLOR_NEON_BLUE)
            surface.blit(glitch, (x + 2, y - 1))
            surface.blit(text, (x - 1, y + 1))
        elif frame % 12 < 3:
            glitch = self.font.render(text_str, False, (255, 46, 77))
            surface.blit(glitch, (x - 2, y + 1))
            surface.blit(text, (x + 1, y))
        else:
            surface.blit(text, (x, y))

        if self.timer > 60:
            retry = self.font_small.render("Premi INVIO per riprovare", False, COLOR_WHITE_UI)
            surface.blit(retry, (INTERNAL_WIDTH // 2 - retry.get_width() // 2, y + 35))


class LevelCompleteScreen:
    """Level complete screen."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 10, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 10)
        self.timer = 0

    def update(self, input_mgr, dt=1.0):
        self.timer += dt
        if self.timer > 90 and input_mgr.is_just_pressed("confirm"):
            return "menu"
        return None

    def draw(self, surface):
        surface.fill(COLOR_BG_NIGHT)
        # Split long level complete text into two lines
        full_text = STRINGS["level_complete"]
        if ". " in full_text:
            line1, line2 = full_text.split(". ", 1)
            line1 += "."
        else:
            line1 = full_text
            line2 = ""
        text1 = self.font.render(line1, False, COLOR_GREEN_HACK)
        surface.blit(text1, (INTERNAL_WIDTH // 2 - text1.get_width() // 2,
                             INTERNAL_HEIGHT // 2 - 26))
        if line2:
            text2 = self.font.render(line2, False, COLOR_GREEN_HACK)
            surface.blit(text2, (INTERNAL_WIDTH // 2 - text2.get_width() // 2,
                                 INTERNAL_HEIGHT // 2 - 12))
        if self.timer > 90:
            cont = self.font_small.render("Premi INVIO", False, COLOR_WHITE_UI)
            surface.blit(cont, (INTERNAL_WIDTH // 2 - cont.get_width() // 2,
                                INTERNAL_HEIGHT // 2 + 14))
