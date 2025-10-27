"""Projectile system for special moves (fireballs, etc.)."""

import pygame
from street_fighter_3rd.systems.animation import AnimationController, SpriteManager, create_simple_animation
from street_fighter_3rd.data.enums import FacingDirection


class Projectile:
    """Base projectile class for fireballs and other projectiles."""

    def __init__(self, x: float, y: float, velocity_x: float, owner_facing: FacingDirection,
                 damage: int, sprite_manager: SpriteManager = None):
        """Initialize a projectile.

        Args:
            x: Starting x position
            y: Starting y position (ground level)
            velocity_x: Horizontal velocity (pixels per frame, already accounts for facing)
            owner_facing: Direction the owner is facing
            damage: Damage dealt on hit
            sprite_manager: Sprite manager for animations (optional)
        """
        self.x = x
        self.y = y
        self.velocity_x = velocity_x
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

        # Update animation
        if self.animation_controller:
            self.animation_controller.update()

        # Remove if off screen (assuming 896px wide screen with some margin)
        if self.x < -100 or self.x > 1000:
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
                 strength: str = "light"):
        """Initialize a Gohadoken.

        Args:
            x: Starting x position
            y: Starting y position (ground level)
            velocity_x: Horizontal velocity (already accounts for facing)
            owner_facing: Direction the owner is facing
            strength: "light", "medium", or "heavy" (affects speed/damage)
        """
        # Damage based on strength
        damage_values = {"light": 60, "medium": 70, "heavy": 80}
        damage = damage_values.get(strength, 60)

        # Initialize sprite manager for Gohadoken
        sprite_directory = "assets/sprites/akuma/sprite_sheets"
        sprite_manager = SpriteManager(sprite_directory)

        super().__init__(x, y, velocity_x, owner_facing, damage, sprite_manager)

        # Hitbox for fireball
        self.hitbox_width = 60
        self.hitbox_height = 60

        # Setup animation
        self._setup_animation()

    def _setup_animation(self):
        """Setup Gohadoken animation."""
        self.animation_controller = AnimationController(self.sprite_manager)

        # Gohadoken projectile animation (spinning fireball)
        # Sprites 19201-19220 (20 frames of spinning fireball)
        gohadoken_projectile_anim = create_simple_animation(
            [19201, 19202, 19203, 19204, 19205, 19206, 19207, 19208, 19209, 19210,
             19211, 19212, 19213, 19214, 19215, 19216, 19217, 19218, 19219, 19220],
            frame_duration=2,  # Hold each frame for 2 game frames
            loop=True  # Loop the spinning animation
        )
        self.animation_controller.add_animation("projectile", gohadoken_projectile_anim)
        self.animation_controller.play_animation("projectile")
