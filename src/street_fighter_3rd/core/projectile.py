"""Projectile system for special moves (fireballs, etc.)."""

import pygame
from street_fighter_3rd.systems.animation import (
    AnimationController, SpriteManager, create_simple_animation, create_folder_animation)
from street_fighter_3rd.data.enums import FacingDirection
from street_fighter_3rd.data.constants import STAGE_FLOOR


class Projectile:
    """Base projectile class for fireballs and other projectiles."""

    def __init__(self, x: float, y: float, velocity_x: float, owner_facing: FacingDirection,
                 damage: int, sprite_manager: SpriteManager = None, velocity_y: float = 0.0,
                 ground_y: float = STAGE_FLOOR):
        """Initialize a projectile.

        Args:
            x: Starting x position
            y: Starting y position (ground level)
            velocity_x: Horizontal velocity (pixels per frame, already accounts for facing)
            owner_facing: Direction the owner is facing
            damage: Damage dealt on hit
            sprite_manager: Sprite manager for animations (optional)
            velocity_y: Vertical velocity (positive = down); 0 for a flat ground
                fireball, positive for Akuma's down-forward air fireball.
            ground_y: Y at which a descending projectile dissipates (the visible
                feet/ground line, not necessarily STAGE_FLOOR).
        """
        self.x = x
        self.y = y
        self.velocity_x = velocity_x
        self.velocity_y = velocity_y
        self.ground_y = ground_y
        self.facing = owner_facing
        self.damage = damage
        self.active = True  # Becomes False when projectile should be removed

        # Animation
        self.sprite_manager = sprite_manager
        self.animation_controller = None

        # Hitbox (will be set by subclass)
        self.hitbox_width = 40
        self.hitbox_height = 40

    def update(self):
        """Update projectile position and animation."""
        if not self.active:
            return

        # Move projectile
        self.x += self.velocity_x
        self.y += self.velocity_y

        # Update animation
        if self.animation_controller:
            self.animation_controller.update()

        # Remove if off screen (assuming 896px wide screen with some margin)
        if self.x < -100 or self.x > 1000:
            self.active = False
        # A descending (air) fireball dissipates when it reaches the ground.
        if self.velocity_y > 0 and self.y >= self.ground_y:
            self.y = self.ground_y
            self.active = False

    def render(self, screen: pygame.Surface):
        """Render the projectile.

        Args:
            screen: Pygame surface to render to
        """
        if not self.active:
            return

        if self.animation_controller:
            # Get current sprite from animation
            sprite = self.animation_controller.get_current_sprite()
            if sprite:
                # Flip sprite based on facing direction
                if self.facing == FacingDirection.LEFT:
                    sprite = pygame.transform.flip(sprite, True, False)

                # Position sprite
                sprite_rect = sprite.get_rect()
                sprite_rect.centerx = int(self.x)
                sprite_rect.centery = int(self.y)

                screen.blit(sprite, sprite_rect)
        else:
            # Fallback: draw simple rectangle if no sprite
            pygame.draw.circle(screen, (255, 100, 0), (int(self.x), int(self.y)), 20)

    def get_hitbox(self) -> pygame.Rect:
        """Get the projectile's hitbox.

        Returns:
            Pygame rect representing hitbox
        """
        return pygame.Rect(
            int(self.x - self.hitbox_width / 2),
            int(self.y - self.hitbox_height / 2),
            self.hitbox_width,
            self.hitbox_height
        )

    def on_hit(self):
        """Called when projectile hits something."""
        self.active = False


class Gohadoken(Projectile):
    """Akuma's fireball projectile."""

    def __init__(self, x: float, y: float, velocity_x: float, owner_facing: FacingDirection,
                 strength: str = "light", velocity_y: float = 0.0, ground_y: float = STAGE_FLOOR):
        """Initialize a Gohadoken.

        Args:
            x: Starting x position
            y: Starting y position (ground level)
            velocity_x: Horizontal velocity (already accounts for facing)
            owner_facing: Direction the owner is facing
            strength: "light", "medium", or "heavy" (affects speed/damage)
            velocity_y: Vertical velocity (positive = down) for the air fireball.
        """
        # Damage based on strength
        damage_values = {"light": 60, "medium": 70, "heavy": 80}
        damage = damage_values.get(strength, 60)

        # Initialize sprite manager for Gohadoken (canonical character asset tree)
        sprite_directory = "assets/characters/akuma/sprite_sheets"
        sprite_manager = SpriteManager(sprite_directory)

        super().__init__(x, y, velocity_x, owner_facing, damage, sprite_manager,
                         velocity_y=velocity_y, ground_y=ground_y)

        # Hitbox for fireball
        self.hitbox_width = 60
        self.hitbox_height = 60

        # Gou Hadouken projectile sprite (ROM rip, ids 30660-30668), cropped to a
        # common bbox and vendored under the akuma animations tree. Authored
        # traveling LEFT (core leads left, tail trails right), so render() flips
        # it when facing right. Loops while in flight. If the assets are missing
        # (gitignored tree), get_current_sprite returns None and render() falls
        # back to the procedural energy ball.
        self.animation_controller = AnimationController(sprite_manager)
        self.animation_controller.add_animation(
            "proj", create_folder_animation(
                "assets/characters/akuma/animations/akuma-gohadoken-proj",
                frame_count=9, frame_duration=2, loop=True))
        self.animation_controller.play_animation("proj")
        self._anim_t = 0  # for the procedural-fallback pulse

    def update(self):
        super().update()
        self._anim_t += 1

    def render(self, screen: pygame.Surface):
        """Draw the Gou Hadouken: the real ROM projectile sprite if available
        (flipped to face travel), else the procedural energy ball."""
        if not self.active:
            return
        sprite = (self.animation_controller.get_current_sprite()
                  if self.animation_controller else None)
        if sprite is not None:
            # Sprite is authored traveling LEFT; flip for rightward travel.
            if self.facing == FacingDirection.RIGHT:
                sprite = pygame.transform.flip(sprite, True, False)
            rect = sprite.get_rect(center=(int(self.x), int(self.y)))
            screen.blit(sprite, rect)
            return

        # --- Procedural fallback (assets missing) ---
        d = 1 if self.facing == FacingDirection.RIGHT else -1
        pulse = 2 if (self._anim_t // 3) % 2 == 0 else 0
        w, h = 96, 56
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = 66, h // 2  # ball centered toward the front; trail to the left
        # trailing comet tail (behind travel)
        for i, tx in enumerate((48, 34, 22)):
            a = 70 - i * 20
            pygame.draw.circle(surf, (255, 110, 0, a), (tx, cy), 9 - i * 2)
        # outer glow -> mid -> bright core
        pygame.draw.circle(surf, (255, 120, 0, 110), (cx, cy), 18 + pulse)
        pygame.draw.circle(surf, (255, 180, 50, 180), (cx, cy), 13 + pulse)
        pygame.draw.circle(surf, (255, 235, 170, 255), (cx, cy), 8)
        pygame.draw.circle(surf, (255, 255, 255, 255), (cx, cy), 4)
        if d < 0:
            surf = pygame.transform.flip(surf, True, False)
        rect = surf.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(surf, rect)
