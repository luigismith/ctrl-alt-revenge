# ui/dialog_box.py — Box dialogo con ritratto e typewriter
import pygame
from ctrl_alt_revenge.settings import (
    COLOR_WHITE_UI, COLOR_BG_NIGHT, COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
    COLOR_DARK_GRAY, COLOR_GREEN_HACK, COLOR_NEON_ORANGE,
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
)


class DialogBox:
    """Box dialogo in basso con ritratto pixel-art e effetto typewriter."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 7)
        self.box_height = 60
        self.box_margin = 8
        self.portrait_size = 40
        self.portraits = {}
        self._generate_portraits()

    def _generate_portraits(self):
        """Genera ritratti pixel-art per i personaggi."""
        # GIG
        surf = pygame.Surface((self.portrait_size, self.portrait_size), pygame.SRCALPHA)
        surf.fill(COLOR_BG_NIGHT)
        # Viso
        pygame.draw.rect(surf, (210, 170, 130), (10, 8, 20, 22))
        # Capelli
        pygame.draw.rect(surf, (160, 155, 150), (10, 5, 20, 6))
        # Barba
        pygame.draw.rect(surf, (160, 155, 150), (10, 24, 18, 6))
        # Occhi
        pygame.draw.rect(surf, (200, 220, 255), (14, 16, 3, 2))
        pygame.draw.rect(surf, (200, 220, 255), (23, 16, 3, 2))
        # Impianto occhio
        pygame.draw.rect(surf, COLOR_NEON_BLUE, (12, 16, 2, 2))
        # Bordo
        pygame.draw.rect(surf, COLOR_NEON_BLUE, (0, 0, self.portrait_size, self.portrait_size), 1)
        self.portraits["GIG"] = surf

        # WARDEN
        surf = pygame.Surface((self.portrait_size, self.portrait_size), pygame.SRCALPHA)
        surf.fill(COLOR_BG_NIGHT)
        # Elmo
        pygame.draw.rect(surf, (40, 45, 60), (8, 5, 24, 28))
        # Visiera
        pygame.draw.rect(surf, (255, 46, 77), (10, 14, 20, 6))
        pygame.draw.rect(surf, (255, 150, 150), (12, 16, 16, 2))
        # Trim
        pygame.draw.rect(surf, COLOR_NEON_ORANGE, (8, 5, 24, 2))
        pygame.draw.rect(surf, (255, 46, 77), (0, 0, self.portrait_size, self.portrait_size), 1)
        self.portraits["WARDEN"] = surf

        # Generico (per NPC)
        surf = pygame.Surface((self.portrait_size, self.portrait_size), pygame.SRCALPHA)
        surf.fill(COLOR_BG_NIGHT)
        pygame.draw.rect(surf, COLOR_DARK_GRAY, (10, 10, 20, 20))
        pygame.draw.rect(surf, COLOR_GREEN_HACK, (14, 16, 3, 2))
        pygame.draw.rect(surf, COLOR_GREEN_HACK, (23, 16, 3, 2))
        pygame.draw.rect(surf, COLOR_GREEN_HACK, (0, 0, self.portrait_size, self.portrait_size), 1)
        self.portraits["NPC"] = surf
        self.portraits["???"] = surf
        self.portraits["SISTEMA"] = surf

    def draw(self, surface, dialog_data):
        """Disegna il box dialogo."""
        if not dialog_data:
            return

        box_y = INTERNAL_HEIGHT - self.box_height - self.box_margin
        box_x = self.box_margin
        box_w = INTERNAL_WIDTH - self.box_margin * 2

        # Sfondo box
        bg = pygame.Surface((box_w, self.box_height), pygame.SRCALPHA)
        bg.fill((10, 10, 30, 220))
        surface.blit(bg, (box_x, box_y))

        # Bordo
        border_color = COLOR_NEON_BLUE
        speaker = dialog_data["speaker"]
        if speaker == "WARDEN":
            border_color = (255, 46, 77)
        elif speaker == "SISTEMA":
            border_color = COLOR_GREEN_HACK
        pygame.draw.rect(surface, border_color,
                         (box_x, box_y, box_w, self.box_height), 1)

        # Ritratto
        portrait = self.portraits.get(speaker, self.portraits["???"])
        portrait_x = box_x + 4
        portrait_y = box_y + (self.box_height - self.portrait_size) // 2
        surface.blit(portrait, (portrait_x, portrait_y))

        # Nome speaker
        name_surf = self.font.render(speaker, False, border_color)
        text_x = portrait_x + self.portrait_size + 8
        surface.blit(name_surf, (text_x, box_y + 4))

        # Testo con word-wrap
        text = dialog_data["text"]
        self._draw_wrapped_text(surface, text, text_x, box_y + 14,
                                box_w - self.portrait_size - 24, COLOR_WHITE_UI)

        # Scelte
        if dialog_data["text_complete"] and dialog_data["choices"]:
            choices = dialog_data["choices"]
            choice_y = box_y + 36
            for i, choice in enumerate(choices):
                color = COLOR_NEON_ORANGE if i == dialog_data["selected_choice"] else COLOR_WHITE_UI
                prefix = "> " if i == dialog_data["selected_choice"] else "  "
                choice_text = self.font.render(prefix + choice["text"], False, color)
                surface.blit(choice_text, (text_x, choice_y + i * 10))

        # Indicatore "continua"
        elif dialog_data["text_complete"]:
            indicator = self.font.render("▼", False, COLOR_WHITE_UI)
            surface.blit(indicator, (box_x + box_w - 12, box_y + self.box_height - 10))

    def _draw_wrapped_text(self, surface, text, x, y, max_width, color):
        """Disegna testo con a capo automatico."""
        words = text.split(" ")
        line = ""
        line_y = y
        for word in words:
            test_line = line + word + " "
            test_surf = self.font.render(test_line, False, color)
            if test_surf.get_width() > max_width:
                if line:
                    line_surf = self.font.render(line, False, color)
                    surface.blit(line_surf, (x, line_y))
                    line_y += 9
                line = word + " "
            else:
                line = test_line
        if line:
            line_surf = self.font.render(line.strip(), False, color)
            surface.blit(line_surf, (x, line_y))
