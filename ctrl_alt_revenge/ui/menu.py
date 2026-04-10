# ui/menu.py — Menu principale e pause
import pygame
import math
from ctrl_alt_revenge.settings import (
    COLOR_BG_NIGHT, COLOR_WHITE_UI, COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
    COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_GREEN_HACK,
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
    STRINGS,
)


class MainMenu:
    """Schermata titolo."""

    def __init__(self):
        self.font_title = pygame.font.SysFont("consolas", 16, bold=True)
        self.font_sub = pygame.font.SysFont("consolas", 8)
        self.font_small = pygame.font.SysFont("consolas", 7)
        self.timer = 0
        self.selected = 0
        self.options = ["INIZIA", "COMANDI", "ESCI"]

    def update(self, input_mgr, dt=1.0):
        self.timer += dt * 0.05
        if input_mgr.is_just_pressed("up"):
            self.selected = (self.selected - 1) % len(self.options)
        if input_mgr.is_just_pressed("down"):
            self.selected = (self.selected + 1) % len(self.options)
        if input_mgr.is_just_pressed("confirm"):
            return self.options[self.selected]
        return None

    def draw(self, surface):
        surface.fill(COLOR_BG_NIGHT)

        # Sfondo: griglia cyberpunk animata
        for i in range(0, INTERNAL_WIDTH, 20):
            alpha = int(30 + 20 * math.sin(self.timer + i * 0.1))
            pygame.draw.line(surface, (*COLOR_NEON_PURPLE[:3],), (i, 0), (i, INTERNAL_HEIGHT), 1)
        for j in range(0, INTERNAL_HEIGHT, 20):
            pygame.draw.line(surface, (*COLOR_NEON_BLUE[:3],),
                             (0, j), (INTERNAL_WIDTH, j), 1)

        # Titolo
        title = self.font_title.render(STRINGS["title"], False, COLOR_WHITE_UI)
        tx = INTERNAL_WIDTH // 2 - title.get_width() // 2
        # Glow effect
        glow_offset = int(math.sin(self.timer * 2) * 2)
        title_glow = self.font_title.render(STRINGS["title"], False, COLOR_NEON_BLUE)
        surface.blit(title_glow, (tx + 1, 50 + glow_offset + 1))
        surface.blit(title, (tx, 50 + glow_offset))

        # Sottotitolo
        sub = self.font_sub.render(STRINGS["subtitle"], False, COLOR_NEON_ORANGE)
        surface.blit(sub, (INTERNAL_WIDTH // 2 - sub.get_width() // 2, 75))

        # Opzioni menu
        for i, opt in enumerate(self.options):
            color = COLOR_NEON_ORANGE if i == self.selected else COLOR_WHITE_UI
            prefix = "> " if i == self.selected else "  "
            text = self.font_sub.render(prefix + opt, False, color)
            surface.blit(text, (INTERNAL_WIDTH // 2 - text.get_width() // 2, 120 + i * 18))

        # Footer
        ver = self.font_small.render("v0.1 — prototipo", False, (80, 80, 100))
        surface.blit(ver, (INTERNAL_WIDTH // 2 - ver.get_width() // 2, INTERNAL_HEIGHT - 15))


class PauseMenu:
    """Schermata di pausa."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 10)
        self.font_small = pygame.font.SysFont("consolas", 7)
        self.selected = 0
        self.options = ["CONTINUA", "COMANDI", "MENU PRINCIPALE"]

    def update(self, input_mgr, dt=1.0):
        if input_mgr.is_just_pressed("up"):
            self.selected = (self.selected - 1) % len(self.options)
        if input_mgr.is_just_pressed("down"):
            self.selected = (self.selected + 1) % len(self.options)
        if input_mgr.is_just_pressed("confirm") or input_mgr.is_just_pressed("pause"):
            return self.options[self.selected]
        return None

    def draw(self, surface):
        # Overlay scuro
        overlay = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        surface.blit(overlay, (0, 0))

        # Titolo
        title = self.font.render(STRINGS["pause_text"], False, COLOR_WHITE_UI)
        surface.blit(title, (INTERNAL_WIDTH // 2 - title.get_width() // 2, 80))

        # Opzioni
        for i, opt in enumerate(self.options):
            color = COLOR_NEON_ORANGE if i == self.selected else COLOR_WHITE_UI
            prefix = "> " if i == self.selected else "  "
            text = self.font_small.render(prefix + opt, False, color)
            surface.blit(text, (INTERNAL_WIDTH // 2 - text.get_width() // 2, 110 + i * 14))


class ControlsScreen:
    """Schermata comandi."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 7)
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
        title = self.font.render("< COMANDI >", False, COLOR_NEON_BLUE)
        surface.blit(title, (INTERNAL_WIDTH // 2 - title.get_width() // 2, 20))

        for i, (key, action) in enumerate(self.controls):
            key_surf = self.font.render(key, False, COLOR_NEON_ORANGE)
            act_surf = self.font.render(action, False, COLOR_WHITE_UI)
            y = 40 + i * 12
            surface.blit(key_surf, (40, y))
            surface.blit(act_surf, (200, y))

        back = self.font.render("Premi INVIO per tornare", False, COLOR_WHITE_UI)
        surface.blit(back, (INTERNAL_WIDTH // 2 - back.get_width() // 2, INTERNAL_HEIGHT - 20))


class GameOverScreen:
    """Schermata Game Over."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 12)
        self.font_small = pygame.font.SysFont("consolas", 8)
        self.timer = 0

    def update(self, input_mgr, dt=1.0):
        self.timer += dt
        if self.timer > 60 and input_mgr.is_just_pressed("confirm"):
            return "retry"
        return None

    def draw(self, surface):
        surface.fill(COLOR_BG_NIGHT)
        # Glitch effect
        text = self.font.render(STRINGS["game_over"], False, COLOR_RED_ALARM)
        x = INTERNAL_WIDTH // 2 - text.get_width() // 2
        y = INTERNAL_HEIGHT // 2 - 20
        if int(self.timer) % 8 < 2:
            surface.blit(text, (x + 2, y))
        else:
            surface.blit(text, (x, y))

        if self.timer > 60:
            retry = self.font_small.render("Premi INVIO per riprovare", False, COLOR_WHITE_UI)
            surface.blit(retry, (INTERNAL_WIDTH // 2 - retry.get_width() // 2, y + 30))


class LevelCompleteScreen:
    """Schermata livello completato."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 10)
        self.font_small = pygame.font.SysFont("consolas", 7)
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
                                INTERNAL_HEIGHT // 2 + 10))
