# ui/menu.py — Main menu, pause, controls, game over, level complete
import pygame
import math
from ctrl_alt_revenge.settings import (
    COLOR_BG_NIGHT, COLOR_WHITE_UI, COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
    COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_GREEN_HACK,
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
    STRINGS,
)


class MainMenu:
    """Title screen with animated scanlines and cyberpunk grid."""

    def __init__(self):
        self.font_title = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_sub = pygame.font.SysFont("consolas", 14)
        self.font_opt = pygame.font.SysFont("consolas", 18)
        self.font_small = pygame.font.SysFont("consolas", 12)
        self.timer = 0
        self.selected = 0
        self.options = ["INIZIA", "COMANDI", "ESCI"]
        self.scanline_offset = 0

    def update(self, input_mgr, dt=1.0):
        self.timer += dt * 0.05
        self.scanline_offset = (self.scanline_offset + dt * 0.3) % 3
        if input_mgr.is_just_pressed("up"):
            self.selected = (self.selected - 1) % len(self.options)
        if input_mgr.is_just_pressed("down"):
            self.selected = (self.selected + 1) % len(self.options)
        if input_mgr.is_just_pressed("confirm"):
            return self.options[self.selected]
        return None

    def draw(self, surface):
        surface.fill(COLOR_BG_NIGHT)

        # Cyberpunk grid background
        for i in range(0, INTERNAL_WIDTH, 20):
            pygame.draw.line(surface, COLOR_NEON_PURPLE, (i, 0), (i, INTERNAL_HEIGHT), 1)
        for j in range(0, INTERNAL_HEIGHT, 20):
            pygame.draw.line(surface, COLOR_NEON_BLUE, (0, j), (INTERNAL_WIDTH, j), 1)

        # Title with 1px offset shadow in neon blue
        title_text = STRINGS["title"]
        title_shadow = self.font_title.render(title_text, False, COLOR_NEON_BLUE)
        title_main = self.font_title.render(title_text, False, COLOR_WHITE_UI)
        tx = INTERNAL_WIDTH // 2 - title_main.get_width() // 2
        ty = 50
        surface.blit(title_shadow, (tx + 1, ty + 1))
        surface.blit(title_main, (tx, ty))

        # Subtitle in neon orange
        sub = self.font_sub.render(STRINGS["subtitle"], False, COLOR_NEON_ORANGE)
        surface.blit(sub, (INTERNAL_WIDTH // 2 - sub.get_width() // 2, ty + 30))

        # Menu options
        opt_y_start = 120
        for i, opt in enumerate(self.options):
            color = COLOR_NEON_ORANGE if i == self.selected else COLOR_WHITE_UI
            prefix = "> " if i == self.selected else "  "
            text = self.font_opt.render(prefix + opt, False, color)
            surface.blit(text, (INTERNAL_WIDTH // 2 - text.get_width() // 2,
                                opt_y_start + i * 22))

        # Version footer
        ver = self.font_small.render("v0.1 -- prototipo", False, (80, 80, 100))
        surface.blit(ver, (INTERNAL_WIDTH // 2 - ver.get_width() // 2, INTERNAL_HEIGHT - 15))

        # Animated scanlines: darken every 3rd row, scrolling
        scanline_surf = pygame.Surface((INTERNAL_WIDTH, 1), pygame.SRCALPHA)
        scanline_surf.fill((0, 0, 0, 40))
        offset = int(self.scanline_offset)
        for row in range(offset, INTERNAL_HEIGHT, 3):
            surface.blit(scanline_surf, (0, row))


class PauseMenu:
    """Pause overlay with scanlines."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 20, bold=True)
        self.font_opt = pygame.font.SysFont("consolas", 16)
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
        self.font_title = pygame.font.SysFont("consolas", 16, bold=True)
        self.font = pygame.font.SysFont("consolas", 12)
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
            surface.blit(key_surf, (60, y))
            surface.blit(act_surf, (240, y))

        # Footer
        back = self.font.render("Premi INVIO per tornare", False, COLOR_WHITE_UI)
        surface.blit(back, (INTERNAL_WIDTH // 2 - back.get_width() // 2, INTERNAL_HEIGHT - 20))


class GameOverScreen:
    """Game Over screen with glitch offset effect."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 24, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 14)
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
        self.font = pygame.font.SysFont("consolas", 20, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 14)
        self.timer = 0

    def update(self, input_mgr, dt=1.0):
        self.timer += dt
        if self.timer > 90 and input_mgr.is_just_pressed("confirm"):
            return "menu"
        return None

    def draw(self, surface):
        surface.fill(COLOR_BG_NIGHT)
        text = self.font.render(STRINGS["level_complete"], False, COLOR_GREEN_HACK)
        surface.blit(text, (INTERNAL_WIDTH // 2 - text.get_width() // 2,
                            INTERNAL_HEIGHT // 2 - 20))
        if self.timer > 90:
            cont = self.font_small.render("Premi INVIO", False, COLOR_WHITE_UI)
            surface.blit(cont, (INTERNAL_WIDTH // 2 - cont.get_width() // 2,
                                INTERNAL_HEIGHT // 2 + 14))
