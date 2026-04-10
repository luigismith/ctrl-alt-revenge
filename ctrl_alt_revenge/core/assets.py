# core/assets.py — Asset loader con cache
import os
import pygame
from ctrl_alt_revenge.settings import (
    COLOR_BG_NIGHT, COLOR_NEON_BLUE, COLOR_NEON_PURPLE,
    COLOR_WHITE_UI
)


class AssetManager:
    """Carica e gestisce asset con cache. Genera placeholder se mancano."""

    def __init__(self):
        self._cache = {}
        self._font_cache = {}
        self._base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

    def get_font(self, size=14):
        """Font pixel monospace senza antialias."""
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.SysFont("consolas", size, bold=False)
        return self._font_cache[size]

    def render_text(self, text, size=14, color=COLOR_WHITE_UI, antialias=False):
        """Renderizza testo con font pixel."""
        font = self.get_font(size)
        return font.render(text, antialias, color)

    def load_image(self, path, alpha=True):
        """Carica immagine da disco, con cache."""
        if path in self._cache:
            return self._cache[path]
        full_path = os.path.join(self._base_path, path)
        if os.path.exists(full_path):
            if alpha:
                img = pygame.image.load(full_path).convert_alpha()
            else:
                img = pygame.image.load(full_path).convert()
            self._cache[path] = img
            return img
        return None

    def load_sound(self, path):
        """Carica suono, restituisce None se manca."""
        full_path = os.path.join(self._base_path, "audio", path)
        if os.path.exists(full_path):
            return pygame.mixer.Sound(full_path)
        return None

    def make_placeholder(self, width, height, color, key=None):
        """Crea superficie placeholder colorata."""
        if key and key in self._cache:
            return self._cache[key]
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        surf.fill(color)
        if key:
            self._cache[key] = surf
        return surf

    def clear_cache(self):
        self._cache.clear()
