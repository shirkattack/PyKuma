#!/usr/bin/env python3
"""
Main Game with Sprite Integration Demo

This demo integrates our working SF3 sprite system with the main game architecture.
It's a stepping stone between our working sprite demo and the full main game.

Features:
- Uses main game structure (Game class, proper systems)
- Integrates working SF3SpriteManager
- Akuma vs Akuma with authentic sprites
- Professional game loop with proper timing
"""

import pygame
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import working sprite system
try:
    from street_fighter_3rd.graphics.sprite_manager import SF3SpriteManager
    SPRITES_AVAILABLE = True
    print("✅ SF3SpriteManager imported successfully")
except ImportError as e:
    print(f"⚠️ SF3SpriteManager not available: {e}")
    SPRITES_AVAILABLE = False

# Import game constants
try:
    from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
except ImportError:
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS = 1280, 720, 60

# Import enums
try:
    from street_fighter_3rd.data.enums import CharacterState, FacingDirection
except ImportError:
    from enum import Enum
    
    class CharacterState(Enum):
        IDLE = "idle"
        WALK_FORWARD = "walk_forward"
        WALK_BACKWARD = "walk_backward"
        JUMP = "jump"
        CROUCH = "crouch"
        LIGHT_PUNCH = "light_punch"
        MEDIUM_PUNCH = "medium_punch"
        HEAVY_PUNCH = "heavy_punch"
    
    class FacingDirection(Enum):
        LEFT = -1
        RIGHT = 1


class SimpleSpriteCharacter:
    """Simple character using SF3 sprites"""
    
    def __init__(self, x: float, y: float, player_num: int, sprite_manager: Optional[object] = None):
        self.x = x
        self.y = y
        self.player_num = player_num
        self.sprite_manager = sprite_manager
        
        # Character properties
        self.health = 1000
        self.max_health = 1000
        self.facing = FacingDirection.RIGHT if player_num == 1 else FacingDirection.LEFT
        
        # State
        self.state = CharacterState.IDLE
        self.state_timer = 0
        
        # Animation
        self.animation_timer = 0
        self.current_animation = "stance"
        
        # Movement
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.walk_speed = 3.0
        self.jump_power = -15.0
        self.gravity = 0.8
        self.ground_y = y
        
        # Input
        self.inputs = set()
        
        # Visual
        self.color = (100, 150, 255) if player_num == 1 else (255, 100, 100)
        
    def update(self, opponent=None):
        """Update character"""
        self.state_timer += 1
        self.animation_timer += 1
        
        # Handle input
        self._handle_input()
        
        # Apply physics
        self._apply_physics()
        
        # Update facing
        if opponent:
            if opponent.x > self.x:
                self.facing = FacingDirection.RIGHT
            else:
                self.facing = FacingDirection.LEFT
    
    def _handle_input(self):
        """Handle character input"""
        # Movement
        if "left" in self.inputs:
            self.velocity_x = -self.walk_speed
            self.state = CharacterState.WALK_BACKWARD
        elif "right" in self.inputs:
            self.velocity_x = self.walk_speed
            self.state = CharacterState.WALK_FORWARD
        else:
            self.velocity_x = 0
            if self.state in [CharacterState.WALK_FORWARD, CharacterState.WALK_BACKWARD]:
                self.state = CharacterState.IDLE
        
        # Jump
        if "up" in self.inputs and self.y >= self.ground_y - 5:
            self.velocity_y = self.jump_power
            self.state = CharacterState.JUMP
        
        # Crouch
        if "down" in self.inputs and self.y >= self.ground_y - 5:
            self.state = CharacterState.CROUCH
        elif "down" not in self.inputs and self.state == CharacterState.CROUCH:
            self.state = CharacterState.IDLE
        
        # Attacks
        if "lp" in self.inputs:
            self.state = CharacterState.LIGHT_PUNCH
            self.state_timer = 0
        elif "mp" in self.inputs:
            self.state = CharacterState.MEDIUM_PUNCH
            self.state_timer = 0
        elif "hp" in self.inputs:
            self.state = CharacterState.HEAVY_PUNCH
            self.state_timer = 0
        
        # Return to idle after attack
        if self.state in [CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_PUNCH, CharacterState.HEAVY_PUNCH]:
            if self.state_timer > 20:  # Attack duration
                self.state = CharacterState.IDLE
    
    def _apply_physics(self):
        """Apply physics"""
        # Gravity
        if self.y < self.ground_y:
            self.velocity_y += self.gravity
        
        # Update position
        self.x += self.velocity_x
        self.y += self.velocity_y
        
        # Ground collision
        if self.y >= self.ground_y:
            self.y = self.ground_y
            if self.velocity_y > 0:
                self.velocity_y = 0
                if self.state == CharacterState.JUMP:
                    self.state = CharacterState.IDLE
        
        # Screen boundaries
        self.x = max(50, min(SCREEN_WIDTH - 50, self.x))
    
    def render(self, screen: pygame.Surface):
        """Render character"""
        if SPRITES_AVAILABLE and self.sprite_manager:
            self._render_sprites(screen)
        else:
            self._render_rectangle(screen)
    
    def _render_sprites(self, screen: pygame.Surface):
        """Render using SF3 sprites"""
        # Map state to animation
        animation_name = self._get_animation_name()
        
        # Get sprite
        sprite = None
        try:
            sprites = self.sprite_manager.get_character_sprites("akuma")
            if sprites and animation_name in sprites:
                animation_data = sprites[animation_name]
                if animation_data and len(animation_data) > 0:
                    # Cycle through frames
                    frame_index = (self.animation_timer // 4) % len(animation_data)
                    sprite_path = animation_data[frame_index]
                    sprite = pygame.image.load(sprite_path).convert_alpha()
                    # Scale up for visibility
                    sprite = pygame.transform.scale(sprite, (sprite.get_width() * 2, sprite.get_height() * 2))
        except Exception as e:
            print(f"⚠️ Sprite error: {e}")
        
        if sprite:
            # Flip sprite based on facing
            if self.facing == FacingDirection.RIGHT:
                sprite = pygame.transform.flip(sprite, True, False)
            
            # Position sprite
            sprite_rect = sprite.get_rect()
            sprite_rect.centerx = int(self.x)
            sprite_rect.bottom = int(self.y)
            
            screen.blit(sprite, sprite_rect)
        else:
            # Fallback to rectangle
            self._render_rectangle(screen)
    
    def _render_rectangle(self, screen: pygame.Surface):
        """Render as rectangle (fallback)"""
        rect = pygame.Rect(int(self.x - 30), int(self.y - 120), 60, 120)
        pygame.draw.rect(screen, self.color, rect)
        
        # Facing indicator
        eye_x = rect.centerx + (10 if self.facing == FacingDirection.RIGHT else -10)
        pygame.draw.circle(screen, (255, 255, 255), (eye_x, rect.y + 20), 5)
    
    def _get_animation_name(self) -> str:
        """Get animation name for current state"""
        state_map = {
            CharacterState.IDLE: "stance",
            CharacterState.WALK_FORWARD: "walkf",
            CharacterState.WALK_BACKWARD: "walkb",
            CharacterState.JUMP: "jump",
            CharacterState.CROUCH: "crouch",
            CharacterState.LIGHT_PUNCH: "standing_light_punch",
            CharacterState.MEDIUM_PUNCH: "standing_medium_punch", 
            CharacterState.HEAVY_PUNCH: "standing_heavy_punch",
        }
        return state_map.get(self.state, "stance")


class MainGameSpritesDemo:
    """Main game with sprite integration"""
    
    def __init__(self):
        pygame.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("SF3: Main Game with Sprites Integration")
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Initialize sprite system
        self.sprite_manager = None
        if SPRITES_AVAILABLE:
            try:
                self.sprite_manager = SF3SpriteManager("tools/sprite_extraction")
                print("🎨 SF3SpriteManager initialized successfully")
            except Exception as e:
                print(f"⚠️ Sprite manager failed: {e}")
        
        # Create characters
        ground_y = SCREEN_HEIGHT - 100
        self.player1 = SimpleSpriteCharacter(300, ground_y, 1, self.sprite_manager)
        self.player2 = SimpleSpriteCharacter(980, ground_y, 2, self.sprite_manager)
        
        # Fonts
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        print("🚀 Main Game with Sprites Demo ready!")
        print("✨ This integrates SF3 sprites with main game architecture")
    
    def handle_input(self):
        """Handle input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
        
        # Get key states
        keys = pygame.key.get_pressed()
        
        # Player 1 inputs (WASD + UIOJKL)
        self.player1.inputs.clear()
        if keys[pygame.K_a]: self.player1.inputs.add("left")
        if keys[pygame.K_d]: self.player1.inputs.add("right")
        if keys[pygame.K_w]: self.player1.inputs.add("up")
        if keys[pygame.K_s]: self.player1.inputs.add("down")
        if keys[pygame.K_u]: self.player1.inputs.add("lp")
        if keys[pygame.K_i]: self.player1.inputs.add("mp")
        if keys[pygame.K_o]: self.player1.inputs.add("hp")
        
        # Player 2 inputs (Arrows + Numpad)
        self.player2.inputs.clear()
        if keys[pygame.K_LEFT]: self.player2.inputs.add("left")
        if keys[pygame.K_RIGHT]: self.player2.inputs.add("right")
        if keys[pygame.K_UP]: self.player2.inputs.add("up")
        if keys[pygame.K_DOWN]: self.player2.inputs.add("down")
        if keys[pygame.K_KP4]: self.player2.inputs.add("lp")
        if keys[pygame.K_KP5]: self.player2.inputs.add("mp")
        if keys[pygame.K_KP6]: self.player2.inputs.add("hp")
    
    def update(self):
        """Update game"""
        self.player1.update(self.player2)
        self.player2.update(self.player1)
    
    def render(self):
        """Render game"""
        # Clear screen
        self.screen.fill((40, 50, 80))
        
        # Draw ground
        ground_y = SCREEN_HEIGHT - 100
        pygame.draw.line(self.screen, (100, 100, 100), (0, ground_y), (SCREEN_WIDTH, ground_y), 3)
        
        # Draw characters
        self.player1.render(self.screen)
        self.player2.render(self.screen)
        
        # Draw health bars
        self._draw_health_bar(self.player1, 50, 50)
        self._draw_health_bar(self.player2, SCREEN_WIDTH - 350, 50)
        
        # Draw status
        sprite_status = "✅ SF3 SPRITES ACTIVE" if SPRITES_AVAILABLE and self.sprite_manager else "⚠️ RECTANGLES (no sprites)"
        status_color = (0, 255, 0) if SPRITES_AVAILABLE and self.sprite_manager else (255, 255, 0)
        status_text = self.small_font.render(sprite_status, True, status_color)
        self.screen.blit(status_text, (10, 10))
        
        # Draw controls
        controls_text = "P1: WASD+UIO | P2: Arrows+456 | ESC: Exit"
        controls = self.small_font.render(controls_text, True, (200, 200, 200))
        controls_rect = controls.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30))
        self.screen.blit(controls, controls_rect)
        
        pygame.display.flip()
    
    def _draw_health_bar(self, player, x: int, y: int):
        """Draw health bar"""
        bar_width = 300
        bar_height = 20
        
        # Background
        pygame.draw.rect(self.screen, (100, 0, 0), (x, y, bar_width, bar_height))
        
        # Health
        health_width = int((player.health / player.max_health) * bar_width)
        pygame.draw.rect(self.screen, (0, 255, 0), (x, y, health_width, bar_height))
        
        # Border
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, bar_width, bar_height), 2)
        
        # Text
        player_text = f"P{player.player_num}: AKUMA"
        health_text = f"{player.health}/{player.max_health}"
        
        player_surface = self.font.render(player_text, True, (255, 255, 255))
        health_surface = self.small_font.render(health_text, True, (255, 255, 255))
        
        self.screen.blit(player_surface, (x, y - 30))
        self.screen.blit(health_surface, (x, y + 25))
    
    def run(self):
        """Run the game"""
        while self.running:
            self.handle_input()
            self.update()
            self.render()
            self.clock.tick(FPS)
        
        pygame.quit()


if __name__ == "__main__":
    print("🎮 Starting Main Game with Sprites Integration...")
    demo = MainGameSpritesDemo()
    demo.run()
