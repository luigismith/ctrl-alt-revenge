# ui/intro.py — Animated cyberpunk intro cutscene
import pygame
import math
import random
from ctrl_alt_revenge.settings import (
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
    COLOR_BG_NIGHT, COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
    COLOR_NEON_ORANGE, COLOR_RED_ALARM, COLOR_WHITE_UI,
    COLOR_GREEN_HACK, COLOR_YELLOW,
)


class IntroSequence:
    """Animated intro cutscene played before the title screen.

    Phases:
        0. Black screen with flicker (~1s)
        1. CTRL+ALT REVENGE! logo zoom-in with glitch (~3s)
        2. City skyline reveal with rain (~3s)
        3. GIG silhouette appears, cyber eye glows (~2s)
        4. Text crawl: "Sotto la Linea, 2087..." (~5s)
        5. Title flash and transition to menu (~1s)
    Total: ~15 seconds. Skippable with any key.
    """

    PHASE_FLICKER = 0
    PHASE_LOGO = 1
    PHASE_CITY = 2
    PHASE_GIG = 3
    PHASE_TEXT = 4
    PHASE_OUTRO = 5
    PHASE_DONE = 6

    def __init__(self, audio=None):
        self.audio = audio
        self.frame = 0
        self.phase = self.PHASE_FLICKER

        # Phase durations in frames (60 FPS)
        self.phase_durations = {
            self.PHASE_FLICKER: 60,    # 1s
            self.PHASE_LOGO: 180,      # 3s
            self.PHASE_CITY: 180,      # 3s
            self.PHASE_GIG: 120,       # 2s
            self.PHASE_TEXT: 300,      # 5s
            self.PHASE_OUTRO: 60,      # 1s
        }

        self.phase_frame = 0
        self.skip = False
        self.done = False

        # Fonts
        self.font_logo = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_sub = pygame.font.SysFont("consolas", 10)
        self.font_text = pygame.font.SysFont("consolas", 11)
        self.font_press = pygame.font.SysFont("consolas", 9)

        # Pre-generated cityscape
        self.city_surf = self._generate_cityscape()

        # Rain drops
        self.rain = [(random.randint(0, INTERNAL_WIDTH - 1),
                      random.randint(-50, INTERNAL_HEIGHT),
                      random.randint(2, 4))
                     for _ in range(40)]

        # Glitch chars for logo phase
        self.glitch_chars = "!@#$%^&*<>?/\\|"
        self.glitched_logo = "CTRL+ALT REVENGE!"

        # Text crawl lines
        self.crawl_text = [
            "ANNO 2087.",
            "",
            "I MEGACORP HANNO MANGIATO LA CITTA'.",
            "I CYBORG SONO TORNATI A FARSI MARTELLO.",
            "",
            "TU SEI GIG.",
            "TI HANNO RUBATO TUTTO.",
            "",
            "OGGI RIPRENDI IL CONTO.",
        ]

        # Cyber eye glow phase (sine-wave pulse)
        self.eye_glow = 0.0

    def _generate_cityscape(self):
        """Generate the cyberpunk city silhouette background."""
        s = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))

        # Sky gradient
        for y in range(INTERNAL_HEIGHT):
            t = y / INTERNAL_HEIGHT
            r = int(13 + (25 - 13) * t)
            g = int(11 + (22 - 11) * t)
            b = int(43 + (60 - 43) * t)
            pygame.draw.line(s, (r, g, b), (0, y), (INTERNAL_WIDTH, y))

        # Distant buildings
        random.seed(42)
        x = 0
        while x < INTERNAL_WIDTH:
            bw = random.randint(20, 45)
            bh = random.randint(60, 130)
            by = INTERNAL_HEIGHT - bh - 30
            color = (25, 22, 55)
            pygame.draw.rect(s, color, (x, by, bw, bh))
            # Lit windows
            for wy in range(by + 6, by + bh - 6, 5):
                for wx in range(x + 3, x + bw - 3, 5):
                    if random.random() < 0.35:
                        wcolor = random.choice([
                            (0, 200, 230), (255, 220, 100),
                            (255, 122, 26), (200, 50, 100)
                        ])
                        pygame.draw.rect(s, wcolor, (wx, wy, 2, 2))
            x += bw + random.randint(2, 8)

        # Mid buildings (closer)
        x = 0
        while x < INTERNAL_WIDTH:
            bw = random.randint(28, 55)
            bh = random.randint(80, 150)
            by = INTERNAL_HEIGHT - bh - 15
            color = (35, 30, 65)
            pygame.draw.rect(s, color, (x, by, bw, bh))
            # Lit windows brighter
            for wy in range(by + 6, by + bh - 6, 4):
                for wx in range(x + 3, x + bw - 3, 4):
                    if random.random() < 0.45:
                        wcolor = random.choice([
                            (0, 229, 255), (255, 220, 80),
                            (255, 122, 26)
                        ])
                        pygame.draw.rect(s, wcolor, (wx, wy, 2, 2))
            # Neon sign
            if random.random() < 0.5:
                sign_y = by + 30 + random.randint(0, 30)
                sign_color = random.choice([
                    COLOR_NEON_BLUE, COLOR_NEON_PURPLE, COLOR_NEON_ORANGE
                ])
                pygame.draw.rect(s, sign_color,
                                (x + bw // 2 - 5, sign_y, 5, 2))
            x += bw + random.randint(4, 10)

        # Street level
        pygame.draw.rect(s, (15, 13, 35),
                         (0, INTERNAL_HEIGHT - 15, INTERNAL_WIDTH, 15))
        # Reflections
        for i in range(20):
            rx = random.randint(0, INTERNAL_WIDTH)
            rc = random.choice([(0, 100, 130), (100, 50, 100)])
            pygame.draw.line(s, rc, (rx, INTERNAL_HEIGHT - 6),
                            (rx + random.randint(5, 15), INTERNAL_HEIGHT - 6))

        return s

    def _draw_gig_silhouette(self, surface, x, y, eye_brightness):
        """Draw a simplified GIG silhouette for the intro."""
        # Body silhouette (dark gray rectangle with details)
        # Head
        pygame.draw.rect(surface, (40, 38, 55), (x, y, 18, 18))
        # Torso
        pygame.draw.rect(surface, (40, 38, 55), (x - 6, y + 16, 30, 28))
        # Legs
        pygame.draw.rect(surface, (35, 33, 50), (x + 2, y + 42, 6, 28))
        pygame.draw.rect(surface, (35, 33, 50), (x + 10, y + 42, 6, 28))

        # Outline
        for ox in range(-7, 25):
            for oy in range(-1, 71):
                px, py = x + ox, y + oy
                if 0 <= px < INTERNAL_WIDTH and 0 <= py < INTERNAL_HEIGHT:
                    pass  # silhouette drawn

        # CYBER EYE — glowing cyan with halo
        eye_x = x + 3
        eye_y = y + 7
        # Halo
        halo_color = (
            int(0 * eye_brightness),
            int(229 * eye_brightness * 0.3),
            int(255 * eye_brightness * 0.3),
        )
        pygame.draw.circle(surface, halo_color, (eye_x + 1, eye_y + 1), 4)
        # Bright core
        core_color = (
            int(0 * eye_brightness),
            min(255, int(229 * eye_brightness)),
            min(255, int(255 * eye_brightness)),
        )
        pygame.draw.rect(surface, core_color, (eye_x, eye_y, 2, 2))

        # Beard hint
        pygame.draw.rect(surface, (80, 75, 70), (x + 3, y + 12, 12, 4))

    def update(self, input_mgr, dt=1.0):
        """Update intro. Returns True when done."""
        if self.done:
            return True

        self.frame += int(dt)
        self.phase_frame += int(dt)

        # Skip on any key
        if input_mgr.is_just_pressed("confirm") or \
           input_mgr.is_just_pressed("jump") or \
           input_mgr.is_just_pressed("punch") or \
           input_mgr.is_just_pressed("pause"):
            self.skip = True

        if self.skip:
            self.done = True
            return True

        # Advance phase
        if self.phase_frame >= self.phase_durations.get(self.phase, 60):
            self.phase_frame = 0
            self.phase += 1
            # Play sfx on phase changes
            if self.audio and self.phase == self.PHASE_LOGO:
                try:
                    self.audio.play_sfx("hack_success")
                except Exception:
                    pass
            if self.phase >= self.PHASE_DONE:
                self.done = True
                return True

        # Update rain
        self.rain = [
            (x, (y + speed) % (INTERNAL_HEIGHT + 50), speed)
            for x, y, speed in self.rain
        ]

        # Eye glow oscillation
        self.eye_glow = 0.5 + 0.5 * math.sin(self.frame * 0.1)

        return False

    def draw(self, surface):
        """Draw the current intro frame."""
        surface.fill(COLOR_BG_NIGHT)

        if self.phase == self.PHASE_FLICKER:
            self._draw_flicker(surface)
        elif self.phase == self.PHASE_LOGO:
            self._draw_logo(surface)
        elif self.phase == self.PHASE_CITY:
            self._draw_city_reveal(surface)
        elif self.phase == self.PHASE_GIG:
            self._draw_gig_reveal(surface)
        elif self.phase == self.PHASE_TEXT:
            self._draw_text_crawl(surface)
        elif self.phase == self.PHASE_OUTRO:
            self._draw_outro(surface)

        # Scanlines overlay always
        for y in range(0, INTERNAL_HEIGHT, 3):
            pygame.draw.line(surface, (0, 0, 0, 60), (0, y),
                            (INTERNAL_WIDTH, y))

        # Skip indicator
        if self.phase < self.PHASE_OUTRO:
            if (self.frame // 30) % 2 == 0:
                skip = self.font_press.render("PRESS ANY KEY", False,
                                              (100, 100, 130))
                surface.blit(skip,
                            (INTERNAL_WIDTH - skip.get_width() - 6,
                             INTERNAL_HEIGHT - 12))

    def _draw_flicker(self, surface):
        """Black screen with random flickers."""
        # Random horizontal noise lines
        for _ in range(3):
            y = random.randint(0, INTERNAL_HEIGHT - 1)
            color = random.choice([
                (50, 50, 80, 40),
                (100, 50, 100, 30),
            ])
            pygame.draw.line(surface, color[:3], (0, y),
                            (INTERNAL_WIDTH, y))
        # Static dots
        for _ in range(20):
            x = random.randint(0, INTERNAL_WIDTH - 1)
            y = random.randint(0, INTERNAL_HEIGHT - 1)
            surface.set_at((x, y), (80, 80, 100))

        # "BOOTING NEURAL LINK..." text appearing
        if self.phase_frame > 20:
            text = self.font_sub.render(">> BOOTING NEURAL LINK...",
                                        False, COLOR_GREEN_HACK)
            surface.blit(text, (20, INTERNAL_HEIGHT // 2 - 5))

    def _draw_logo(self, surface):
        """Logo zoom-in with glitch effect."""
        # Sub-phase: 0-30 zoom in, 30-120 hold with glitch, 120-180 settle
        sf = self.phase_frame

        if sf < 30:
            # Zoom in: scale from 0.3 to 1.0
            scale = 0.3 + (sf / 30) * 0.7
        else:
            scale = 1.0

        # Glitch text occasionally
        display_text = "CTRL+ALT REVENGE!"
        if 30 <= sf < 120 and random.random() < 0.15:
            # Random char replacement
            chars = list(display_text)
            for _ in range(random.randint(1, 3)):
                idx = random.randint(0, len(chars) - 1)
                if chars[idx] != ' ' and chars[idx] != '+':
                    chars[idx] = random.choice(self.glitch_chars)
            display_text = ''.join(chars)

        # Render at high res then scale
        text_surf = self.font_logo.render(display_text, False, COLOR_WHITE_UI)

        if scale < 1.0:
            w = int(text_surf.get_width() * scale)
            h = int(text_surf.get_height() * scale)
            if w > 0 and h > 0:
                text_surf = pygame.transform.scale(text_surf, (w, h))

        # Glow layers
        glow_offset = int(math.sin(sf * 0.1) * 1.5) + 2
        glow = self.font_logo.render(display_text, False, COLOR_NEON_BLUE)
        if scale < 1.0:
            w = int(glow.get_width() * scale)
            h = int(glow.get_height() * scale)
            if w > 0 and h > 0:
                glow = pygame.transform.scale(glow, (w, h))

        tx = INTERNAL_WIDTH // 2 - text_surf.get_width() // 2
        ty = INTERNAL_HEIGHT // 2 - text_surf.get_height() // 2 - 10

        surface.blit(glow, (tx + glow_offset, ty + glow_offset))
        surface.blit(text_surf, (tx, ty))

        # Subtitle after main logo appears
        if sf > 60:
            sub = self.font_sub.render("PICCHIA DURO A SCORRIMENTO",
                                       False, COLOR_NEON_ORANGE)
            surface.blit(sub, (INTERNAL_WIDTH // 2 - sub.get_width() // 2,
                              ty + text_surf.get_height() + 8))

        # Chromatic aberration line slicing during glitch
        if random.random() < 0.1:
            slice_y = random.randint(ty - 5, ty + text_surf.get_height() + 5)
            slice_h = random.randint(2, 6)
            offset_x = random.randint(-4, 4)
            slice_rect = pygame.Rect(0, slice_y, INTERNAL_WIDTH, slice_h)
            slice_surf = surface.subsurface(slice_rect).copy()
            surface.fill(COLOR_BG_NIGHT, slice_rect)
            surface.blit(slice_surf, (offset_x, slice_y))

    def _draw_city_reveal(self, surface):
        """Fade in cityscape with rain."""
        sf = self.phase_frame
        # Fade alpha from 0 to 255
        alpha = min(255, int(sf * 4))
        city = self.city_surf.copy()
        city.set_alpha(alpha)
        surface.blit(city, (0, 0))

        # Rain
        for x, y, speed in self.rain:
            color = (180, 200, 230, 100)
            length = speed + 2
            pygame.draw.line(surface, color[:3], (x, y), (x, y + length))

        # Subtitle text
        if sf > 60:
            text = self.font_text.render("ZONA C-7  ::  SOTTO LA LINEA",
                                         False, COLOR_NEON_BLUE)
            tx = INTERNAL_WIDTH // 2 - text.get_width() // 2
            ty = 30
            # Glow
            glow = self.font_text.render("ZONA C-7  ::  SOTTO LA LINEA",
                                         False, (0, 100, 130))
            surface.blit(glow, (tx + 1, ty + 1))
            surface.blit(text, (tx, ty))

    def _draw_gig_reveal(self, surface):
        """GIG silhouette appears with glowing cyber eye."""
        # City background
        surface.blit(self.city_surf, (0, 0))

        # Rain
        for x, y, speed in self.rain:
            pygame.draw.line(surface, (180, 200, 230),
                            (x, y), (x, y + speed + 2))

        # GIG silhouette position
        gx = INTERNAL_WIDTH // 2 - 9
        gy = INTERNAL_HEIGHT // 2 - 20

        # Bright ground glow under GIG
        glow_alpha = min(255, self.phase_frame * 3)
        glow_surf = pygame.Surface((50, 8), pygame.SRCALPHA)
        for i in range(8):
            a = int((1 - i / 8) * glow_alpha * 0.4)
            pygame.draw.ellipse(glow_surf, (0, 100, 130, a),
                              (5 + i, i, 40 - i * 2, 4))
        surface.blit(glow_surf, (gx - 20, gy + 65))

        # Fade in
        alpha_factor = min(1.0, self.phase_frame / 40)
        eye_brightness = self.eye_glow * alpha_factor

        # Draw silhouette (only draws when phase started)
        if self.phase_frame > 10:
            self._draw_gig_silhouette(surface, gx, gy, eye_brightness)

    def _draw_text_crawl(self, surface):
        """Scrolling text crawl over dark background."""
        # Dim cityscape background
        bg = self.city_surf.copy()
        bg.set_alpha(80)
        surface.blit(bg, (0, 0))

        # Each line appears over time
        line_height = 14
        total_height = len(self.crawl_text) * line_height
        start_y = (INTERNAL_HEIGHT - total_height) // 2

        for i, line in enumerate(self.crawl_text):
            # Line fade-in delay
            line_appear_frame = i * 25
            if self.phase_frame < line_appear_frame:
                continue

            local_frame = self.phase_frame - line_appear_frame
            alpha = min(255, local_frame * 10)
            color = COLOR_WHITE_UI
            if i == 5:  # "TU SEI GIG"
                color = COLOR_NEON_ORANGE
            elif i == 8:  # final line
                color = COLOR_NEON_BLUE

            text = self.font_text.render(line, False, color)
            text.set_alpha(alpha)
            tx = INTERNAL_WIDTH // 2 - text.get_width() // 2
            ty = start_y + i * line_height
            surface.blit(text, (tx, ty))

    def _draw_outro(self, surface):
        """Final flash transitioning to title."""
        # Bright flash fading to black
        sf = self.phase_frame
        if sf < 20:
            flash_alpha = int(255 * (1 - sf / 20))
            flash = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT))
            flash.fill(COLOR_WHITE_UI)
            flash.set_alpha(flash_alpha)
            surface.blit(flash, (0, 0))
