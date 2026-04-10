# ui/hud.py — HUD with cyberpunk styling
import pygame
from ctrl_alt_revenge.settings import (
    COLOR_WHITE_UI, COLOR_RED_ALARM, COLOR_NEON_BLUE, COLOR_NEON_ORANGE,
    COLOR_NEON_PURPLE, COLOR_GREEN_HACK, COLOR_DARK_GRAY, COLOR_YELLOW,
    INTERNAL_WIDTH, INTERNAL_HEIGHT, HEAT_ALARM_THRESHOLD,
    STRINGS,
)


class HUD:
    """HUD: hearts, implant slots, heat bar, notifications, boss intro."""

    def __init__(self, heart_full, heart_empty):
        self.heart_full = heart_full
        self.heart_empty = heart_empty
        self.font = pygame.font.SysFont("consolas", 12, bold=False)
        self.font_notif = pygame.font.SysFont("consolas", 14, bold=False)
        self.font_boss = pygame.font.SysFont("consolas", 20, bold=True)
        self.show_boss_intro = False
        self.boss_intro_timer = 0
        self.boss_intro_text = ""
        self.notification_text = ""
        self.notification_timer = 0

        # Pre-build the dark top strip (semi-transparent)
        self._top_strip = pygame.Surface((INTERNAL_WIDTH, 28), pygame.SRCALPHA)
        self._top_strip.fill((5, 5, 20, 180))

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
        """Draw the entire HUD."""
        # Dark background strip behind HUD area
        surface.blit(self._top_strip, (0, 0))

        self._draw_hearts(surface, player.hp, player.max_hp)
        self._draw_heat_bar(surface, heat)
        self._draw_implant_slots(surface, implant_info)

        # Notification
        if self.notification_timer > 0:
            self._draw_notification(surface)

        # Boss intro
        if self.show_boss_intro:
            self._draw_boss_intro(surface)

    def _draw_hearts(self, surface, hp, max_hp):
        """Hearts at top-left."""
        x_start = 6
        y = 6
        for i in range(max_hp):
            heart = self.heart_full if i < hp else self.heart_empty
            surface.blit(heart, (x_start + i * 10, y))

    def _draw_heat_bar(self, surface, heat):
        """Heat bar below hearts."""
        x = 6
        y = 18
        bar_w = 60
        bar_h = 5

        # Background fill
        pygame.draw.rect(surface, COLOR_DARK_GRAY, (x, y, bar_w, bar_h))

        # Colored fill
        fill_w = int(bar_w * heat)
        if heat < HEAT_ALARM_THRESHOLD:
            color = COLOR_NEON_BLUE
        elif heat < 0.75:
            color = COLOR_NEON_ORANGE
        else:
            color = COLOR_RED_ALARM
        if fill_w > 0:
            pygame.draw.rect(surface, color, (x, y, fill_w, bar_h))

        # 1px white border
        pygame.draw.rect(surface, COLOR_WHITE_UI, (x, y, bar_w, bar_h), 1)

        # Label
        label = self.font.render("HEAT", False, COLOR_WHITE_UI)
        surface.blit(label, (x + bar_w + 3, y - 2))

    def _draw_implant_slots(self, surface, implant_info):
        """Implant slots at top-right."""
        slot_size = 14
        slot_spacing = 3
        total_w = len(implant_info) * slot_size + (len(implant_info) - 1) * slot_spacing
        x_start = INTERNAL_WIDTH - total_w - 6
        y = 4
        colors = [COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_NEON_PURPLE, COLOR_GREEN_HACK]

        for i, info in enumerate(implant_info):
            sx = x_start + i * (slot_size + slot_spacing)

            # Slot background
            pygame.draw.rect(surface, COLOR_DARK_GRAY, (sx, y, slot_size, slot_size))

            if info:
                slot_color = colors[i % len(colors)]
                if info["ready"]:
                    # Ready: colored border
                    pygame.draw.rect(surface, slot_color, (sx, y, slot_size, slot_size), 1)
                else:
                    # Cooldown: fill proportional bar from bottom
                    fill_h = int(slot_size * (1 - info["cooldown_ratio"]))
                    if fill_h > 0:
                        pygame.draw.rect(surface, slot_color,
                                         (sx, y + slot_size - fill_h, slot_size, fill_h))
                    pygame.draw.rect(surface, COLOR_DARK_GRAY, (sx, y, slot_size, slot_size), 1)
            else:
                pygame.draw.rect(surface, (40, 40, 40), (sx, y, slot_size, slot_size), 1)

            # Slot number
            num = self.font.render(str(i + 1), False, COLOR_WHITE_UI)
            num_x = sx + (slot_size - num.get_width()) // 2
            num_y = y + (slot_size - num.get_height()) // 2
            surface.blit(num, (num_x, num_y))

    def _draw_notification(self, surface):
        """Centered notification with dark background and neon border."""
        text = self.font_notif.render(self.notification_text, False, COLOR_GREEN_HACK)
        tw = text.get_width()
        th = text.get_height()
        x = INTERNAL_WIDTH // 2 - tw // 2
        y = INTERNAL_HEIGHT // 2 - 30

        pad_x = 8
        pad_y = 4
        bg = pygame.Surface((tw + pad_x * 2, th + pad_y * 2), pygame.SRCALPHA)
        bg.fill((5, 5, 20, 210))
        surface.blit(bg, (x - pad_x, y - pad_y))
        pygame.draw.rect(surface, COLOR_GREEN_HACK,
                         (x - pad_x, y - pad_y, tw + pad_x * 2, th + pad_y * 2), 1)
        surface.blit(text, (x, y))

    def _draw_boss_intro(self, surface):
        """Boss intro text centered with pulsing alpha."""
        text = self.font_boss.render(self.boss_intro_text, False, COLOR_RED_ALARM)
        x = INTERNAL_WIDTH // 2 - text.get_width() // 2
        y = INTERNAL_HEIGHT // 2 - 50

        # Pulsing alpha
        alpha = int(abs(self.boss_intro_timer % 30 - 15) / 15 * 255)
        text.set_alpha(alpha)
        surface.blit(text, (x, y))
