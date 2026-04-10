# ui/dialog_box.py — Dialog box with portrait, typewriter, and cyberpunk styling
import pygame
from ctrl_alt_revenge.settings import (
    COLOR_WHITE_UI, COLOR_BG_NIGHT, COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
    COLOR_DARK_GRAY, COLOR_GREEN_HACK, COLOR_NEON_ORANGE,
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
)


class DialogBox:
    """Dialog box at bottom with pixel-art portrait, typewriter effect, and neon styling."""

    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 12)
        self.font_speaker = pygame.font.SysFont("consolas", 14)
        self.box_height = 70
        self.box_margin = 8
        self.portrait_size = 44
        self.portraits = {}
        self._blink_timer = 0
        self._generate_portraits()

    def _generate_portraits(self):
        """Generate pixel-art portraits for characters."""
        ps = self.portrait_size

        # GIG
        surf = pygame.Surface((ps, ps), pygame.SRCALPHA)
        surf.fill(COLOR_BG_NIGHT)
        # Face
        pygame.draw.rect(surf, (210, 170, 130), (12, 9, 20, 24))
        # Hair
        pygame.draw.rect(surf, (160, 155, 150), (12, 5, 20, 7))
        # Beard
        pygame.draw.rect(surf, (160, 155, 150), (12, 27, 18, 6))
        # Eyes
        pygame.draw.rect(surf, (200, 220, 255), (16, 18, 3, 2))
        pygame.draw.rect(surf, (200, 220, 255), (25, 18, 3, 2))
        # Cyber implant eye
        pygame.draw.rect(surf, COLOR_NEON_BLUE, (14, 18, 2, 2))
        # 1px colored border
        pygame.draw.rect(surf, COLOR_NEON_BLUE, (0, 0, ps, ps), 1)
        self.portraits["GIG"] = surf

        # WARDEN
        surf = pygame.Surface((ps, ps), pygame.SRCALPHA)
        surf.fill(COLOR_BG_NIGHT)
        # Helmet
        pygame.draw.rect(surf, (40, 45, 60), (9, 5, 26, 30))
        # Visor
        pygame.draw.rect(surf, (255, 46, 77), (11, 15, 22, 7))
        pygame.draw.rect(surf, (255, 150, 150), (13, 17, 18, 3))
        # Trim
        pygame.draw.rect(surf, COLOR_NEON_ORANGE, (9, 5, 26, 2))
        pygame.draw.rect(surf, (255, 46, 77), (0, 0, ps, ps), 1)
        self.portraits["WARDEN"] = surf

        # Generic NPC
        surf = pygame.Surface((ps, ps), pygame.SRCALPHA)
        surf.fill(COLOR_BG_NIGHT)
        pygame.draw.rect(surf, COLOR_DARK_GRAY, (12, 12, 20, 20))
        pygame.draw.rect(surf, COLOR_GREEN_HACK, (16, 18, 3, 2))
        pygame.draw.rect(surf, COLOR_GREEN_HACK, (25, 18, 3, 2))
        pygame.draw.rect(surf, COLOR_GREEN_HACK, (0, 0, ps, ps), 1)
        self.portraits["NPC"] = surf
        self.portraits["???"] = surf
        self.portraits["SISTEMA"] = surf

    def _get_border_color(self, speaker):
        """Get neon border color based on speaker."""
        if speaker == "WARDEN":
            return (255, 46, 77)
        elif speaker == "SISTEMA":
            return COLOR_GREEN_HACK
        elif speaker == "GIG":
            return COLOR_NEON_BLUE
        else:
            return COLOR_NEON_PURPLE

    def _draw_corner_brackets(self, surface, rect, color, length=4):
        """Draw small L-shaped pixel decorations in corners of a rect."""
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        # Top-left
        pygame.draw.line(surface, color, (x, y), (x + length, y))
        pygame.draw.line(surface, color, (x, y), (x, y + length))
        # Top-right
        pygame.draw.line(surface, color, (x + w - 1 - length, y), (x + w - 1, y))
        pygame.draw.line(surface, color, (x + w - 1, y), (x + w - 1, y + length))
        # Bottom-left
        pygame.draw.line(surface, color, (x, y + h - 1), (x + length, y + h - 1))
        pygame.draw.line(surface, color, (x, y + h - 1 - length), (x, y + h - 1))
        # Bottom-right
        pygame.draw.line(surface, color, (x + w - 1 - length, y + h - 1), (x + w - 1, y + h - 1))
        pygame.draw.line(surface, color, (x + w - 1, y + h - 1 - length), (x + w - 1, y + h - 1))

    def draw(self, surface, dialog_data):
        """Draw the dialog box."""
        if not dialog_data:
            return

        self._blink_timer += 1

        box_y = INTERNAL_HEIGHT - self.box_height - self.box_margin
        box_x = self.box_margin
        box_w = INTERNAL_WIDTH - self.box_margin * 2

        speaker = dialog_data["speaker"]
        border_color = self._get_border_color(speaker)

        # Semi-transparent dark fill
        bg = pygame.Surface((box_w, self.box_height), pygame.SRCALPHA)
        bg.fill((10, 10, 30, 220))
        surface.blit(bg, (box_x, box_y))

        # 1px neon-colored border
        box_rect = pygame.Rect(box_x, box_y, box_w, self.box_height)
        pygame.draw.rect(surface, border_color, box_rect, 1)

        # Corner bracket decorations
        self._draw_corner_brackets(surface, box_rect, border_color, length=5)

        # Portrait with 1px colored border
        portrait = self.portraits.get(speaker, self.portraits["???"])
        portrait_x = box_x + 5
        portrait_y = box_y + (self.box_height - self.portrait_size) // 2
        surface.blit(portrait, (portrait_x, portrait_y))

        # Speaker name in speaker color
        name_surf = self.font_speaker.render(speaker, False, border_color)
        text_x = portrait_x + self.portrait_size + 8
        surface.blit(name_surf, (text_x, box_y + 4))

        # Dialog text with word-wrap, 11px line spacing
        text = dialog_data["text"]
        self._draw_wrapped_text(surface, text, text_x, box_y + 18,
                                box_w - self.portrait_size - 26, COLOR_WHITE_UI)

        # Choices
        if dialog_data["text_complete"] and dialog_data["choices"]:
            choices = dialog_data["choices"]
            choice_y = box_y + 40
            for i, choice in enumerate(choices):
                color = COLOR_NEON_ORANGE if i == dialog_data["selected_choice"] else COLOR_WHITE_UI
                prefix = "> " if i == dialog_data["selected_choice"] else "  "
                choice_text = self.font.render(prefix + choice["text"], False, color)
                surface.blit(choice_text, (text_x, choice_y + i * 12))

        # "Continue" indicator: blinking triangle at bottom-right
        elif dialog_data["text_complete"]:
            if (self._blink_timer // 20) % 2 == 0:
                tri_x = box_x + box_w - 12
                tri_y = box_y + self.box_height - 10
                # Small downward-pointing triangle
                pygame.draw.polygon(surface, COLOR_WHITE_UI, [
                    (tri_x, tri_y),
                    (tri_x + 6, tri_y),
                    (tri_x + 3, tri_y + 4),
                ])

    def _draw_wrapped_text(self, surface, text, x, y, max_width, color):
        """Draw text with word wrapping and 11px line spacing."""
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
                    line_y += 11
                line = word + " "
            else:
                line = test_line
        if line:
            line_surf = self.font.render(line.strip(), False, color)
            surface.blit(line_surf, (x, line_y))
