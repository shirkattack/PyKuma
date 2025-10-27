"""Visual effects system for hit sparks and other game effects."""

import os
from typing import List, Tuple, Optional
import pygame


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


class VFXManager:
    """Manages all visual effects in the game."""

    def __init__(self):
        """Initialize VFX manager."""
        self.effects: List[VisualEffect] = []
        self.sprite_cache = {}  # Cache loaded sprites

        # Define hit spark sprite sequences
        self.hit_spark_sequences = {
            HitSparkType.LIGHT: list(range(29361, 29370)),  # 29361-29369 (9 frames)
            HitSparkType.MEDIUM: list(range(29383, 29389)),  # 29383-29388 (6 frames)
            HitSparkType.HEAVY: list(range(30102, 30123)),  # 30102-30122 (21 frames)
            HitSparkType.SPECIAL: list(range(29846, 29855)),  # 29846-29854 (9 frames)
        }

        # Preload hit spark sprites
        self._preload_hit_sparks()

    def _preload_hit_sparks(self):
        """Preload all hit spark sprites into cache."""
        effects_dir = "assets/vfx/ingame_effects/hitsparks"

        if not os.path.exists(effects_dir):
            print(f"Warning: Effects directory not found: {effects_dir}")
            return

        for spark_type, sprite_ids in self.hit_spark_sequences.items():
            for sprite_id in sprite_ids:
                sprite_path = os.path.join(effects_dir, f"{sprite_id}.png")

                if os.path.exists(sprite_path):
                    try:
                        sprite = pygame.image.load(sprite_path).convert_alpha()
                        self.sprite_cache[sprite_id] = sprite
                    except Exception as e:
                        print(f"Error loading sprite {sprite_path}: {e}")

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
        """Clear all active effects."""
        self.effects.clear()
