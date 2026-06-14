"""Visual effects system for hit sparks and other game effects."""

import logging
import os
from typing import List, Tuple, Optional
import pygame

from street_fighter_3rd.util.logging_config import get_logger, log_once

log = get_logger(__name__)


class VisualEffect:
    """A single visual effect instance."""

    def __init__(self, sprites: List[pygame.Surface], x: float, y: float,
                 frame_duration: int = 1, offset_x: int = 0, offset_y: int = 0):
        """Initialize a visual effect.

        Args:
            sprites: List of sprite surfaces for the animation
            x: X position (center)
            y: Y position (center)
            frame_duration: How many game frames each sprite shows
            offset_x: X offset from position
            offset_y: Y offset from position
        """
        self.sprites = sprites
        self.x = x
        self.y = y
        self.frame_duration = frame_duration
        self.offset_x = offset_x
        self.offset_y = offset_y

        self.current_frame = 0
        self.frame_counter = 0
        self.finished = False

    def update(self):
        """Update the effect animation."""
        if self.finished:
            return

        self.frame_counter += 1

        if self.frame_counter >= self.frame_duration:
            self.frame_counter = 0
            self.current_frame += 1

            if self.current_frame >= len(self.sprites):
                self.finished = True

    def render(self, screen: pygame.Surface):
        """Render the effect.

        Args:
            screen: Surface to render to
        """
        if self.finished or self.current_frame >= len(self.sprites):
            return

        sprite = self.sprites[self.current_frame]

        # Center sprite at position with offset
        rect = sprite.get_rect()
        rect.centerx = int(self.x) + self.offset_x
        rect.centery = int(self.y) + self.offset_y

        screen.blit(sprite, rect)

    def is_finished(self) -> bool:
        """Check if effect is finished."""
        return self.finished


class HitSparkType:
    """Types of hit sparks."""
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"
    SPECIAL = "special"
    BLOCK = "block"
    PARRY = "parry"


# Single source of truth: each spark type -> (category subdir, inclusive id range).
# All current sparks live under hitsparks/, but the subdir is explicit so block/
# parry/ground effects from other categories can be added without code changes.
SPARK_TABLE = {
    HitSparkType.LIGHT:   ("hitsparks", 29361, 29369),  # small white spark
    HitSparkType.MEDIUM:  ("hitsparks", 29383, 29388),
    HitSparkType.HEAVY:   ("hitsparks", 30319, 30328),  # punchy orange burst
    HitSparkType.SPECIAL: ("hitsparks", 29846, 29854),
    HitSparkType.BLOCK:   ("hitsparks", 30599, 30609),  # blue guard ring
    HitSparkType.PARRY:   ("hitsparks", 30619, 30628),  # blue parry starburst
}

# Resolve against the repo root so effects load regardless of working directory
# (src/street_fighter_3rd/systems/vfx.py -> parents[3] == repo root).
from pathlib import Path as _Path
_EFFECTS_ROOT = str(_Path(__file__).resolve().parents[3] / "assets" / "vfx" / "ingame_effects")


class VFXManager:
    """Manages all visual effects in the game."""

    def __init__(self):
        """Initialize VFX manager."""
        self.effects: List[VisualEffect] = []
        self.sprite_cache = {}  # loaded sprites, keyed by sprite id
        self.shake_request = 0   # screen-shake intensity requested this frame (drained by Game)

        # Per-type id sequences derived from the table (kept for callers that
        # read hit_spark_sequences directly).
        self.hit_spark_sequences = {
            t: list(range(lo, hi + 1)) for t, (_sub, lo, hi) in SPARK_TABLE.items()
        }

        self._preload_hit_sparks()

    def _preload_hit_sparks(self):
        """Preload every spark sequence from its category subdir into the cache."""
        for spark_type, (subdir, lo, hi) in SPARK_TABLE.items():
            effects_dir = os.path.join(_EFFECTS_ROOT, subdir)
            if not os.path.isdir(effects_dir):
                log_once(log, ("vfx_dir", subdir), logging.WARNING,
                         "Effects directory not found: %s", effects_dir)
                continue
            for sprite_id in range(lo, hi + 1):
                sprite_path = os.path.join(effects_dir, f"{sprite_id}.png")
                if os.path.exists(sprite_path):
                    try:
                        self.sprite_cache[sprite_id] = pygame.image.load(sprite_path).convert_alpha()
                    except (pygame.error, OSError, FileNotFoundError) as e:
                        log_once(log, ("vfx_load_err", sprite_path), logging.WARNING,
                                 "Error loading sprite %s: %s", sprite_path, e)

    def request_shake(self, intensity: int):
        """Ask for a screen shake (Game drains this once per frame)."""
        self.shake_request = max(self.shake_request, intensity)

    def spawn_hit_spark(self, x: float, y: float, spark_type: str = HitSparkType.LIGHT,
                       offset_x: int = 0, offset_y: int = 0):
        """Spawn a hit spark effect.

        Args:
            x: X position
            y: Y position
            spark_type: Type of hit spark (light, medium, heavy, special)
            offset_x: X offset from position
            offset_y: Y offset from position
        """
        if spark_type not in self.hit_spark_sequences:
            spark_type = HitSparkType.LIGHT

        sprite_ids = self.hit_spark_sequences[spark_type]
        sprites = []

        for sprite_id in sprite_ids:
            if sprite_id in self.sprite_cache:
                sprites.append(self.sprite_cache[sprite_id])

        if sprites:
            # Hit sparks display 1 frame per sprite in SF3
            effect = VisualEffect(sprites, x, y, frame_duration=1,
                                offset_x=offset_x, offset_y=offset_y)
            self.effects.append(effect)

    def update(self):
        """Update all active effects."""
        # Update all effects
        for effect in self.effects:
            effect.update()

        # Remove finished effects
        self.effects = [e for e in self.effects if not e.is_finished()]

    def render(self, screen: pygame.Surface):
        """Render all active effects.

        Args:
            screen: Surface to render to
        """
        for effect in self.effects:
            effect.render(screen)

    def clear(self):
        """Clear all active effects and any pending shake request."""
        self.effects.clear()
        self.shake_request = 0
