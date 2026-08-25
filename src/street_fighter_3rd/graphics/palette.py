"""Per-player palette swaps, applied once per sprite at load time.

Both fighters are Akuma and the extracted sprites carry a single (P1) palette,
so without this a side switch was indistinguishable from a control swap. A
palette is a pure ``rgba -> rgba`` rule over the sprite's *distinct* colours;
``recolor_surface`` applies it with C-speed ``PixelArray.replace`` calls (the
CPS3 cels have only a few dozen distinct colours each), so the cost is a few
hundred microseconds per cel on first load.

Provenance: the P2 colour is a PyKuma choice (a blue gi), not a ROM palette
dump -- the ROM's alternate palettes are a rom_extract TODO.
"""

from __future__ import annotations

import colorsys
from typing import Callable, Dict, Optional, Tuple

import pygame
from PIL import Image

RGBA = Tuple[int, int, int, int]
PaletteRule = Callable[[RGBA], RGBA]


def _hsv(rgba: RGBA):
    r, g, b, _ = rgba
    return colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)


def _rgb(h: float, s: float, v: float, a: int) -> RGBA:
    r, g, b = colorsys.hsv_to_rgb(h, min(1.0, s), min(1.0, v))
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255)), a


def akuma_p2(rgba: RGBA) -> RGBA:
    """Akuma P2: the dark purple/blue-grey gi becomes a blue gi.

    The gi is the only purple/blue family in the sprite (hue 210..330 deg);
    skin (orange), hair (red), the rope belt (yellow) and the black outlines
    (no hue) are left untouched.
    """
    if rgba[3] == 0:
        return rgba
    h, s, v = _hsv(rgba)
    if 0.58 <= h <= 0.92 and v > 0.02:
        return _rgb(0.60, s + 0.35, v * 1.9, rgba[3])
    return rgba


def recolor_surface(surface: pygame.Surface, rule: PaletteRule) -> pygame.Surface:
    """Return a copy of ``surface`` with ``rule`` applied to every colour.

    Replacement goes through unique temporary colours so a mapping whose
    target equals another source colour can never chain (a -> b -> c).
    """
    w, h = surface.get_size()
    im = Image.frombytes("RGBA", (w, h), pygame.image.tobytes(surface, "RGBA"))
    colors = im.getcolors(maxcolors=w * h) or []
    mapping: Dict[RGBA, RGBA] = {}
    for _, c in colors:
        c = tuple(c)
        m = rule(c)
        if m != c:
            mapping[c] = m
    if not mapping:
        return surface

    out = surface.copy()
    taken = set(mapping) | set(mapping.values())
    temps = []
    i = 0
    while len(temps) < len(mapping):
        cand = (i % 256, (i // 256) % 256, 17, 255)
        if cand not in taken:
            temps.append(cand)
        i += 1
    pa = pygame.PixelArray(out)
    try:
        for (src, _), tmp in zip(mapping.items(), temps):
            pa.replace(src, tmp)
        for (_, dst), tmp in zip(mapping.items(), temps):
            pa.replace(tmp, dst)
    finally:
        pa.close()
    return out


_PLAYER_RULES: Dict[Tuple[str, int], PaletteRule] = {
    ("akuma", 2): akuma_p2,
}


def player_recolor(character: str, player_number: int) -> Optional[Callable[[pygame.Surface], pygame.Surface]]:
    """The load-time recolour for this character/player slot, or None (P1)."""
    rule = _PLAYER_RULES.get((character, player_number))
    if rule is None:
        return None
    return lambda surf: recolor_surface(surf, rule)
