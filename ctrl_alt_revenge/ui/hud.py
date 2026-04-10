# ui/hud.py — HUD minimalista
import pygame
from ctrl_alt_revenge.settings import (
    COLOR_WHITE_UI, COLOR_RED_ALARM, COLOR_NEON_BLUE, COLOR_NEON_ORANGE,
    COLOR_NEON_PURPLE, COLOR_GREEN_HACK, COLOR_DARK_GRAY, COLOR_YELLOW,
    INTERNAL_WIDTH, INTERNAL_HEIGHT, HEAT_ALARM_THRESHOLD,
    STRINGS,
)


class HUD:
    """HUD minimalista: cuori, slot innesti, barra heat."""

    def __init__(self, heart_full, heart_empty):
        self.heart_full = heart_full
        self.heart_empty = heart_empty
        self.font = pygame.font.SysFont("consolas", 7, bold=False)
        self.show_boss_intro = False
        self.boss_intro_timer = 0
        self.boss_intro_text = ""
        self.notification_text = ""
        self.notification_timer = 0

    def show_notification(self, text, duration=120):
        self.notification_text = text
        self.notification_timer = duration

    def show_boss_intro_text(self, text, duration=180):
        self.boss_intro_text = text
        self.boss_intro_timer = duration
        self.show_boss_intro = True

    def update(self, dt=1.0):
        if self.notification_timer > 0:
            self.notification_timer -= dt
        if self.boss_intro_timer > 0:
            self.boss_intro_timer -= dt
            if self.boss_intro_timer <= 0:
                self.show_boss_intro = False

    def draw(self, surface, player, implant_info, heat):
        """Disegna l'intero HUD."""
        self._draw_hearts(surface, player.hp, player.max_hp)
        self._draw_heat_bar(surface, heat)
        self._draw_implant_slots(surface, implant_info)

        # Notifica
        if self.notification_timer > 0:
            self._draw_notification(surface)

        # Intro boss
        if self.show_boss_intro:
            self._draw_boss_intro(surface)

    def _draw_hearts(self, surface, hp, max_hp):
        """Cuori in alto a sinistra."""
        x_start = 4
        y = 4
        for i in range(max_hp):
            heart = self.heart_full if i < hp else self.heart_empty
            surface.blit(heart, (x_start + i * 9, y))

    def _draw_heat_bar(self, surface, heat):
        """Barra heat sotto i cuori."""
        x = 4
        y = 14
        bar_w = 50
        bar_h = 3

        # Sfondo
        pygame.draw.rect(surface, COLOR_DARK_GRAY, (x, y, bar_w, bar_h))
        # Riempimento
        fill_w = int(bar_w * heat)
        if heat < HEAT_ALARM_THRESHOLD:
            color = COLOR_NEON_BLUE
        elif heat < 0.75:
            color = COLOR_NEON_ORANGE
        else:
            color = COLOR_RED_ALARM
        pygame.draw.rect(surface, color, (x, y, fill_w, bar_h))
        # Bordo
        pygame.draw.rect(surface, COLOR_WHITE_UI, (x, y, bar_w, bar_h), 1)

        # Label
        label = self.font.render("HEAT", False, COLOR_WHITE_UI)
        surface.blit(label, (x + bar_w + 3, y - 1))

    def _draw_implant_slots(self, surface, implant_info):
        """Slot innesti in alto a destra."""
        x_start = INTERNAL_WIDTH - 80
        y = 4
        slot_size = 12
        colors = [COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_NEON_PURPLE, COLOR_GREEN_HACK]

        for i, info in enumerate(implant_info):
            sx = x_start + i * (slot_size + 3)
            # Sfondo slot
            pygame.draw.rect(surface, COLOR_DARK_GRAY, (sx, y, slot_size, slot_size))

            if info:
                # Colore in base a stato
                if info["ready"]:
                    color = colors[i % len(colors)]
                else:
                    color = COLOR_DARK_GRAY
                    # Barra cooldown
                    fill_h = int(slot_size * (1 - info["cooldown_ratio"]))
                    pygame.draw.rect(surface, colors[i % len(colors)],
                                     (sx, y + slot_size - fill_h, slot_size, fill_h))

                pygame.draw.rect(surface, color, (sx, y, slot_size, slot_size), 1)
            else:
                pygame.draw.rect(surface, (40, 40, 40), (sx, y, slot_size, slot_size), 1)

            # Numero slot
            num = self.font.render(str(i + 1), False, COLOR_WHITE_UI)
            surface.blit(num, (sx + 3, y + 2))

    def _draw_notification(self, surface):
        """Notifica al centro dello schermo."""
        text = self.font.render(self.notification_text, False, COLOR_GREEN_HACK)
        x = INTERNAL_WIDTH // 2 - text.get_width() // 2
        y = INTERNAL_HEIGHT // 2 - 30
        # Sfondo
        bg_rect = pygame.Rect(x - 4, y - 2, text.get_width() + 8, text.get_height() + 4)
        pygame.draw.rect(surface, (0, 0, 0, 200), bg_rect)
        pygame.draw.rect(surface, COLOR_GREEN_HACK, bg_rect, 1)
        surface.blit(text, (x, y))

    def _draw_boss_intro(self, surface):
        """Testo intro boss al centro."""
        text = self.font.render(self.boss_intro_text, False, COLOR_RED_ALARM)
        x = INTERNAL_WIDTH // 2 - text.get_width() // 2
        y = INTERNAL_HEIGHT // 2 - 50
        # Flash
        alpha = int(abs(self.boss_intro_timer % 30 - 15) / 15 * 255)
        text.set_alpha(alpha)
        surface.blit(text, (x, y))
