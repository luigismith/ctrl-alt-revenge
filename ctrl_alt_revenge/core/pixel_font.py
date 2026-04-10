# core/pixel_font.py — Pixel font utility for readable text at 480x270
import pygame

# Size presets: name -> SysFont size
_SIZE_PRESETS = {
    "tiny": 10,
    "small": 12,
    "medium": 14,
    "large": 20,
    "title": 28,
    "huge": 36,
}

_font_cache = {}


class PixelFont:
    """Singleton-like pixel font manager with named size presets."""

    @staticmethod
    def get(size_name="medium"):
        """Get a cached font by preset name or raw int size.

        Args:
            size_name: A preset name ("tiny","small","medium","large","title","huge")
                       or an int for a custom size.
        Returns:
            pygame.font.Font instance.
        """
        if isinstance(size_name, int):
            size = size_name
            key = size
        else:
            size = _SIZE_PRESETS.get(size_name, _SIZE_PRESETS["medium"])
            key = size_name

        if key not in _font_cache:
            _font_cache[key] = pygame.font.SysFont("consolas", size, bold=False)
        return _font_cache[key]

    @staticmethod
    def render(text, size_name="medium", color=(245, 241, 216)):
        """Convenience: render text with antialias=False.

        Args:
            text: The string to render.
            size_name: Preset name or int size.
            color: RGB tuple, defaults to warm white.
        Returns:
            pygame.Surface with rendered text.
        """
        font = PixelFont.get(size_name)
        return font.render(text, False, color)
