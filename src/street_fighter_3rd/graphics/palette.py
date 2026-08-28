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
import json
from pathlib import Path
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


_ROM_PALETTES_JSON = Path(__file__).resolve().parents[3] / "data" / "characters"
_ROM_RULE_CACHE: Dict[Tuple[str, int], Optional[PaletteRule]] = {}


def rom_palette_rule(character: str, player_number: int) -> Optional[PaletteRule]:
    """The game's own P2 palette for the ROM cels: data/characters/<char>/
    rom_palettes.json holds P1's and P2's 64 pen colours as the PPU renders
    them (cel_decode.py --palettes-out), and the cels are stored in P1's
    colours, so P2 is an exact pen-for-pen substitution. None for P1 or when
    the file is absent (the cels then keep P1's colours)."""
    key = (character, player_number)
    if key not in _ROM_RULE_CACHE:
        rule = None
        path = _ROM_PALETTES_JSON / character / "rom_palettes.json"
        if player_number == 2 and path.exists():
            try:
                pals = json.loads(path.read_text())
                table = {tuple(a): tuple(b) for a, b in zip(pals["p1"], pals["p2"])}

                def rule(rgba: RGBA, _t=table) -> RGBA:
                    rgb = _t.get(rgba[:3])
                    return (*rgb, rgba[3]) if rgb else rgba
            except (OSError, ValueError, KeyError):
                rule = None
        _ROM_RULE_CACHE[key] = rule
    return _ROM_RULE_CACHE[key]


_NEAREST_RULE_CACHE: Dict[Tuple[str, int], Optional[PaletteRule]] = {}


def rom_nearest_rule(character: str, player_number: int) -> Optional[PaletteRule]:
    """The ROM P2 palette for sprites that are NOT stored in ROM colours (the
    zweifuss folder clips, GIF-quantised): each colour goes to the nearest P1
    ROM pen and takes that pen's P2 colour, so folder clips and ROM cels agree
    (no colour flip when a reaction clip plays). The zweifuss gi is a
    purple-grey family the ROM draws olive, so gi-family colours are matched by
    brightness against the ROM gi pens instead of by RGB distance."""
    key = (character, player_number)
    if key not in _NEAREST_RULE_CACHE:
        rule = None
        path = _ROM_PALETTES_JSON / character / "rom_palettes.json"
        if player_number == 2 and path.exists():
            try:
                pals = json.loads(path.read_text())
                pairs = [(tuple(a), tuple(b)) for a, b in zip(pals["p1"], pals["p2"]) if any(a)]
                # gi pens: the P1 colours that P2 turns near-grey (the gi family)
                gi = [(a, b) for a, b in pairs if max(b) - min(b) <= 40 and max(b) >= 100]
                memo: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}

                def rule(rgba: RGBA, _pairs=pairs, _gi=gi, _memo=memo) -> RGBA:
                    if rgba[3] == 0:
                        return rgba
                    rgb = rgba[:3]
                    out = _memo.get(rgb)
                    if out is None:
                        h, s, v = _hsv(rgba)
                        if 0.58 <= h <= 0.92 and v > 0.02 and _gi:
                            lum = sum(rgb) / 3
                            out = min(_gi, key=lambda ab: abs(sum(ab[0]) / 3 - lum))[1]
                        else:
                            out = min(_pairs, key=lambda ab: sum((x - y) ** 2 for x, y in zip(ab[0], rgb)))[1]
                        _memo[rgb] = out
                    return (*out, rgba[3])
            except (OSError, ValueError, KeyError):
                rule = None
        _NEAREST_RULE_CACHE[key] = rule
    return _NEAREST_RULE_CACHE[key]


def cel_recolor(character: str, player_number: int) -> Optional[Callable[[pygame.Surface], pygame.Surface]]:
    """Surface -> Surface for ROM cels: the ROM palette when known, else the
    same rule as the folder sprites."""
    rule = rom_palette_rule(character, player_number)
    if rule is None:
        return player_recolor(character, player_number)
    return lambda surface: recolor_surface(surface, rule)


def player_recolor(character: str, player_number: int) -> Optional[Callable[[pygame.Surface], pygame.Surface]]:
    """The load-time recolour for this character/player slot, or None (P1)."""
    rule = rom_nearest_rule(character, player_number) or _PLAYER_RULES.get((character, player_number))
    if rule is None:
        return None
    return lambda surf: recolor_surface(surf, rule)
