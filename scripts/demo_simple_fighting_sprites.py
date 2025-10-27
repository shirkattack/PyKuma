#!/usr/bin/env python3
"""
Simple Fighting Game Demo - WITH SPRITES!

A playable fighting game showing ACTUAL Akuma sprites instead of rectangles.
This combines the simple fighting mechanics with authentic SF3 character visuals.

Controls:
- WASD: Move Player 1 (Akuma)
- UIOJKL: Attack buttons for Player 1
- Arrow Keys: Move Player 2 (Akuma) 
- Numpad: Attack buttons for Player 2

This is a REAL fighting game with REAL SF3 sprites!
"""

import pygame
import sys
import math
import os
from enum import Enum
from dataclasses import dataclass
from typing import Set, Tuple, List, Optional
from pathlib import Path

# Add src to path for sprite loading
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Try to import sprite system
SPRITES_AVAILABLE = False
try:
    from street_fighter_3rd.graphics.sprite_manager import SF3SpriteManager
    SPRITES_AVAILABLE = True
    print("✅ Sprite system available!")
except ImportError as e:
    print(f"⚠️ Sprite system not available: {e}")
    print("🎮 Using rectangle graphics as fallback")


class CharacterState(Enum):
    """Character states"""
    IDLE = "idle"
    WALKING = "walking"
    JUMPING = "jumping"
    CROUCHING = "crouching"
    ATTACKING = "attacking"
    HITSTUN = "hitstun"
    BLOCKING = "blocking"
    BLOCKSTUN = "blockstun"


class AttackType(Enum):
    """Attack types"""
    LIGHT_PUNCH = "light_punch"
    MEDIUM_PUNCH = "medium_punch"
    HEAVY_PUNCH = "heavy_punch"
    LIGHT_KICK = "light_kick"
    MEDIUM_KICK = "medium_kick"
    HEAVY_KICK = "heavy_kick"


@dataclass
class Hitbox:
    """Simple hitbox for attacks"""
    x: float
    y: float
    width: float
    height: float
    damage: int
    hitstun: int
    blockstun: int
    active: bool = True


@dataclass
class SpriteAnimation:
    """Simple sprite animation data"""
    frames: List[pygame.Surface]
    frame_durations: List[int]
    current_frame: int = 0
    frame_timer: int = 0
    loop: bool = True


class SimpleSpriteLoader:
    """Simple sprite loader for character animations"""
    
    def __init__(self):
        global SPRITES_AVAILABLE
        self.sprites = {}
        self.sprite_manager = None
        
        if SPRITES_AVAILABLE:
            try:
                self.sprite_manager = SF3SpriteManager("tools/sprite_extraction")
                print("🎨 Loading character sprites...")
                self._load_character_sprites()
            except Exception as e:
                print(f"⚠️ Could not load sprites: {e}")
                SPRITES_AVAILABLE = False
    
    def _load_character_sprites(self):
        """Load character animations for both Akuma and Ken"""
        try:
            # Load Akuma sprites
            self._load_akuma_sprites()
            
            # Try to load Ken sprites
            self._load_ken_sprites()
            
        except Exception as e:
            print(f"⚠️ Error loading character sprites: {e}")
    
    def _load_akuma_sprites(self):
        """Load key Akuma animations"""
        try:
            # Load essential animations
            animations_to_load = {
                'akuma_stance': 'akuma-stance',
                'akuma_walkf': 'akuma-walkf', 
                'akuma_walkb': 'akuma-walkb',
                'akuma_jump': 'akuma-jump',
                'akuma_crouch': 'akuma-crouch',
                'akuma_block': 'akuma-block',
                'akuma_mp': 'akuma-mp',  # Medium punch
                'akuma_mk': 'akuma-mk',  # Medium kick
                'akuma_hp': 'akuma-hp',  # Heavy punch
            }
            
            for anim_name, sprite_folder in animations_to_load.items():
                sprite_path = Path("tools/sprite_extraction/akuma_animations") / sprite_folder
                if sprite_path.exists():
                    frames = self._load_animation_frames(sprite_path)
                    if frames:
                        self.sprites[anim_name] = SpriteAnimation(
                            frames=frames,
                            frame_durations=[4] * len(frames)  # 4 frames per sprite frame
                        )
                        print(f"✅ Loaded {anim_name}: {len(frames)} frames")
            
            print(f"🎨 Loaded {len([k for k in self.sprites.keys() if k.startswith('akuma')])} Akuma animations")
            
        except Exception as e:
            print(f"⚠️ Error loading Akuma sprites: {e}")
    
    def _load_ken_sprites(self):
        """Load key Ken animations"""
        try:
            # Check if Ken animations folder exists
            ken_path = Path("tools/sprite_extraction/ken_animations")
            if not ken_path.exists():
                print("⚠️ Ken sprites not available - using Akuma sprites for both players")
                # Copy Akuma sprites as Ken sprites for now
                akuma_animations = {k: v for k, v in self.sprites.items() if k.startswith('akuma')}
                for akuma_key, animation in akuma_animations.items():
                    ken_key = akuma_key.replace('akuma', 'ken')
                    # Create a copy with different color tint for Ken
                    ken_frames = []
                    for frame in animation.frames:
                        # Create a slightly different colored version for Ken
                        ken_frame = frame.copy()
                        # Apply a slight red tint to distinguish Ken
                        red_overlay = pygame.Surface(ken_frame.get_size())
                        red_overlay.fill((255, 200, 200))
                        red_overlay.set_alpha(30)
                        ken_frame.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_MULT)
                        ken_frames.append(ken_frame)
                    
                    self.sprites[ken_key] = SpriteAnimation(
                        frames=ken_frames,
                        frame_durations=animation.frame_durations.copy()
                    )
                
                print(f"🎨 Created {len([k for k in self.sprites.keys() if k.startswith('ken')])} Ken animations (Akuma-based)")
                return
            
            # Load actual Ken animations if available
            animations_to_load = {
                'ken_stance': 'ken-stance',
                'ken_walkf': 'ken-walkf', 
                'ken_walkb': 'ken-walkb',
                'ken_jump': 'ken-jump',
                'ken_crouch': 'ken-crouch',
                'ken_block': 'ken-block',
                'ken_mp': 'ken-mp',  # Medium punch
                'ken_mk': 'ken-mk',  # Medium kick
                'ken_hp': 'ken-hp',  # Heavy punch
            }
            
            ken_loaded = 0
            for anim_name, sprite_folder in animations_to_load.items():
                sprite_path = ken_path / sprite_folder
                if sprite_path.exists():
                    frames = self._load_animation_frames(sprite_path)
                    if frames:
                        self.sprites[anim_name] = SpriteAnimation(
                            frames=frames,
                            frame_durations=[4] * len(frames)  # 4 frames per sprite frame
                        )
                        print(f"✅ Loaded {anim_name}: {len(frames)} frames")
                        ken_loaded += 1
            
            if ken_loaded > 0:
                print(f"🎨 Loaded {ken_loaded} authentic Ken animations")
            else:
                print("⚠️ No Ken sprite files found - using Akuma-based Ken")
            
        except Exception as e:
            print(f"⚠️ Error loading Ken sprites: {e}")
    
    def _load_animation_frames(self, sprite_folder: Path) -> List[pygame.Surface]:
        """Load all PNG frames from a sprite folder"""
        frames = []
        try:
            png_files = sorted(sprite_folder.glob("*.png"))
            for png_file in png_files:
                try:
                    surface = pygame.image.load(str(png_file)).convert_alpha()
                    # Scale up sprites for better visibility
                    scaled_surface = pygame.transform.scale(surface, (surface.get_width() * 2, surface.get_height() * 2))
                    frames.append(scaled_surface)
                except Exception as e:
                    print(f"⚠️ Could not load {png_file}: {e}")
        except Exception as e:
            print(f"⚠️ Error reading sprite folder {sprite_folder}: {e}")
        
        return frames
    
    def get_sprite_for_state(self, state: CharacterState, character: str = 'akuma', facing_right: bool = True) -> Optional[SpriteAnimation]:
        """Get sprite animation for character state"""
        sprite_map = {
            CharacterState.IDLE: 'stance',
            CharacterState.WALKING: 'walkf' if facing_right else 'walkb',
            CharacterState.JUMPING: 'jump',
            CharacterState.CROUCHING: 'crouch',
            CharacterState.BLOCKING: 'block',
            CharacterState.ATTACKING: 'mp',  # Default to medium punch
        }
        
        base_sprite_name = sprite_map.get(state, 'stance')
        sprite_name = f"{character}_{base_sprite_name}"
        
        if sprite_name in self.sprites:
            return self.sprites[sprite_name]
        
        # Fallback to character's stance
        fallback_name = f"{character}_stance"
        if fallback_name in self.sprites:
            return self.sprites[fallback_name]
        
        # Ultimate fallback to any stance
        for key in self.sprites.keys():
            if 'stance' in key:
                return self.sprites[key]
        
        return None


class Fighter:
    """Simple fighter character"""
    
    def __init__(self, x: float, y: float, player_num: int, sprite_loader: SimpleSpriteLoader, character: str = 'akuma'):
        # Position
        self.x = x
        self.y = y
        self.ground_y = y
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        
        # Character properties
        self.player_num = player_num
        self.character = character
        self.health = 1000
        self.max_health = 1000
        self.facing_right = player_num == 1
        
        # Dimensions
        self.width = 60
        self.height = 120
        
        # State
        self.state = CharacterState.IDLE
        self.state_timer = 0
        
        # Combat
        self.hitboxes: List[Hitbox] = []
        self.invulnerable = False
        self.invuln_timer = 0
        
        # Movement
        self.walk_speed = 3.0
        self.jump_power = -15.0
        self.gravity = 0.8
        
        # Input
        self.inputs: Set[str] = set()
        
        # Sprites
        self.sprite_loader = sprite_loader
        self.current_animation = None
        self.animation_timer = 0
        
        # Colors for fallback
        self.color = (100, 150, 255) if player_num == 1 else (255, 100, 100)
    
    def update(self):
        """Update fighter"""
        self.state_timer += 1
        self.animation_timer += 1
        
        # Handle invulnerability
        if self.invulnerable:
            self.invuln_timer -= 1
            if self.invuln_timer <= 0:
                self.invulnerable = False
        
        # Update based on state
        if self.state == CharacterState.IDLE:
            self._handle_idle()
        elif self.state == CharacterState.WALKING:
            self._handle_walking()
        elif self.state == CharacterState.JUMPING:
            self._handle_jumping()
        elif self.state == CharacterState.CROUCHING:
            self._handle_crouching()
        elif self.state == CharacterState.ATTACKING:
            self._handle_attacking()
        elif self.state == CharacterState.HITSTUN:
            self._handle_hitstun()
        elif self.state == CharacterState.BLOCKING:
            self._handle_blocking()
        elif self.state == CharacterState.BLOCKSTUN:
            self._handle_blockstun()
        
        # Apply physics
        self._apply_physics()
        
        # Update animation
        self._update_animation()
    
    def _handle_idle(self):
        """Handle idle state"""
        # Check for movement
        if "left" in self.inputs or "right" in self.inputs:
            self.state = CharacterState.WALKING
            self.state_timer = 0
        elif "down" in self.inputs:
            self.state = CharacterState.CROUCHING
            self.state_timer = 0
        elif "up" in self.inputs and self.y >= self.ground_y - 5:
            self.state = CharacterState.JUMPING
            self.velocity_y = self.jump_power
            self.state_timer = 0
        
        # Check for attacks
        for attack_input in ["lp", "mp", "hp", "lk", "mk", "hk"]:
            if attack_input in self.inputs:
                self._start_attack(attack_input)
                break
    
    def _handle_walking(self):
        """Handle walking state"""
        moving = False
        
        if "left" in self.inputs:
            self.velocity_x = -self.walk_speed
            self.facing_right = False
            moving = True
        elif "right" in self.inputs:
            self.velocity_x = self.walk_speed
            self.facing_right = True
            moving = True
        
        if not moving:
            self.velocity_x = 0
            self.state = CharacterState.IDLE
            self.state_timer = 0
        
        # Check for other actions
        if "down" in self.inputs:
            self.state = CharacterState.CROUCHING
            self.state_timer = 0
        elif "up" in self.inputs and self.y >= self.ground_y - 5:
            self.state = CharacterState.JUMPING
            self.velocity_y = self.jump_power
            self.state_timer = 0
    
    def _handle_jumping(self):
        """Handle jumping state"""
        # Air control
        if "left" in self.inputs:
            self.velocity_x = -self.walk_speed * 0.7
            self.facing_right = False
        elif "right" in self.inputs:
            self.velocity_x = self.walk_speed * 0.7
            self.facing_right = True
        else:
            self.velocity_x *= 0.95  # Air friction
        
        # Land
        if self.y >= self.ground_y and self.velocity_y >= 0:
            self.y = self.ground_y
            self.velocity_y = 0
            self.state = CharacterState.IDLE
            self.state_timer = 0
    
    def _handle_crouching(self):
        """Handle crouching state"""
        if "down" not in self.inputs:
            self.state = CharacterState.IDLE
            self.state_timer = 0
    
    def _handle_attacking(self):
        """Handle attacking state"""
        if self.state_timer >= 20:  # Attack duration
            self.state = CharacterState.IDLE
            self.state_timer = 0
            self.hitboxes.clear()
    
    def _handle_hitstun(self):
        """Handle hitstun state"""
        if self.state_timer >= 15:
            self.state = CharacterState.IDLE
            self.state_timer = 0
    
    def _handle_blocking(self):
        """Handle blocking state"""
        if "back" not in self.inputs:
            self.state = CharacterState.IDLE
            self.state_timer = 0
    
    def _handle_blockstun(self):
        """Handle blockstun state"""
        if self.state_timer >= 10:
            self.state = CharacterState.IDLE
            self.state_timer = 0
    
    def _start_attack(self, attack_type: str):
        """Start an attack"""
        self.state = CharacterState.ATTACKING
        self.state_timer = 0
        
        # Create hitbox
        hitbox_x = self.x + (40 if self.facing_right else -40)
        hitbox = Hitbox(
            x=hitbox_x,
            y=self.y - 60,
            width=50,
            height=40,
            damage=50 if attack_type.startswith('h') else 30,
            hitstun=15,
            blockstun=10
        )
        self.hitboxes = [hitbox]
    
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
        
        # Screen boundaries
        self.x = max(50, min(1230, self.x))
    
    def _update_animation(self):
        """Update sprite animation"""
        if not SPRITES_AVAILABLE:
            return
        
        # Get appropriate animation for current state
        target_animation = self.sprite_loader.get_sprite_for_state(self.state, self.character, self.facing_right)
        
        if target_animation != self.current_animation:
            self.current_animation = target_animation
            if self.current_animation:
                self.current_animation.current_frame = 0
                self.current_animation.frame_timer = 0
        
        # Update animation frame
        if self.current_animation and self.current_animation.frames:
            self.current_animation.frame_timer += 1
            frame_duration = self.current_animation.frame_durations[self.current_animation.current_frame]
            
            if self.current_animation.frame_timer >= frame_duration:
                self.current_animation.frame_timer = 0
                self.current_animation.current_frame += 1
                
                if self.current_animation.current_frame >= len(self.current_animation.frames):
                    if self.current_animation.loop:
                        self.current_animation.current_frame = 0
                    else:
                        self.current_animation.current_frame = len(self.current_animation.frames) - 1
    
    def take_damage(self, damage: int, hitstun: int):
        """Take damage"""
        if self.invulnerable:
            return
        
        self.health -= damage
        self.health = max(0, self.health)
        self.state = CharacterState.HITSTUN
        self.state_timer = 0
        self.invulnerable = True
        self.invuln_timer = hitstun
        self.hitboxes.clear()
    
    def block_attack(self, blockstun: int):
        """Block an attack"""
        self.state = CharacterState.BLOCKSTUN
        self.state_timer = 0
        self.hitboxes.clear()
    
    def get_rect(self) -> pygame.Rect:
        """Get character rectangle"""
        return pygame.Rect(self.x - self.width//2, self.y - self.height, self.width, self.height)
    
    def render(self, screen: pygame.Surface):
        """Render the fighter"""
        if SPRITES_AVAILABLE and self.current_animation and self.current_animation.frames:
            # Render sprite
            sprite = self.current_animation.frames[self.current_animation.current_frame]
            
            # Flip sprite if facing left
            if not self.facing_right:
                sprite = pygame.transform.flip(sprite, True, False)
            
            # Center sprite on character position
            sprite_rect = sprite.get_rect()
            sprite_rect.centerx = int(self.x)
            sprite_rect.bottom = int(self.y)
            
            screen.blit(sprite, sprite_rect)
            
            # Add a small indicator for the character center
            pygame.draw.circle(screen, (255, 255, 0), (int(self.x), int(self.y)), 3)
            
        else:
            # Fallback rectangle rendering
            rect = self.get_rect()
            color = self.color
            
            # Flash when invulnerable
            if self.invulnerable and (self.invuln_timer // 3) % 2:
                color = (255, 255, 255)
            
            pygame.draw.rect(screen, color, rect)
            
            # Draw facing direction
            eye_x = rect.centerx + (10 if self.facing_right else -10)
            pygame.draw.circle(screen, (255, 255, 255), (eye_x, rect.y + 20), 5)
        
        # Draw hitboxes (debug)
        for hitbox in self.hitboxes:
            if hitbox.active:
                hitbox_rect = pygame.Rect(hitbox.x - hitbox.width//2, hitbox.y - hitbox.height//2, hitbox.width, hitbox.height)
                pygame.draw.rect(screen, (255, 0, 0), hitbox_rect, 2)


class SimpleFightingGame:
    """Simple fighting game with sprites"""
    
    def __init__(self):
        pygame.init()
        
        self.screen_width = 1280
        self.screen_height = 720
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("SF3: Akuma vs Ken - WITH SPRITES!")
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load sprites
        print("🎨 Initializing sprite system...")
        self.sprite_loader = SimpleSpriteLoader()
        
        # Create fighters
        ground_y = self.screen_height - 100
        self.fighter1 = Fighter(300, ground_y, 1, self.sprite_loader, 'akuma')  # Player 1: Akuma
        self.fighter2 = Fighter(980, ground_y, 2, self.sprite_loader, 'ken')    # Player 2: Ken
        
        # Fonts
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        print("🚀 Akuma vs Ken Fighting Game ready!")
        print("✨ Player 1: Akuma (Blue) | Player 2: Ken (Red)")
        print("🥋 Classic Shoto vs Shoto matchup!")
    
    def handle_input(self):
        """Handle input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
        
        # Get current key states
        keys = pygame.key.get_pressed()
        
        # Player 1 inputs (WASD + UIOJKL)
        self.fighter1.inputs.clear()
        if keys[pygame.K_a]: self.fighter1.inputs.add("left")
        if keys[pygame.K_d]: self.fighter1.inputs.add("right")
        if keys[pygame.K_w]: self.fighter1.inputs.add("up")
        if keys[pygame.K_s]: self.fighter1.inputs.add("down")
        if keys[pygame.K_u]: self.fighter1.inputs.add("lp")
        if keys[pygame.K_i]: self.fighter1.inputs.add("mp")
        if keys[pygame.K_o]: self.fighter1.inputs.add("hp")
        if keys[pygame.K_j]: self.fighter1.inputs.add("lk")
        if keys[pygame.K_k]: self.fighter1.inputs.add("mk")
        if keys[pygame.K_l]: self.fighter1.inputs.add("hk")
        
        # Player 2 inputs (Arrows + Numpad)
        self.fighter2.inputs.clear()
        if keys[pygame.K_LEFT]: self.fighter2.inputs.add("left")
        if keys[pygame.K_RIGHT]: self.fighter2.inputs.add("right")
        if keys[pygame.K_UP]: self.fighter2.inputs.add("up")
        if keys[pygame.K_DOWN]: self.fighter2.inputs.add("down")
        if keys[pygame.K_KP4]: self.fighter2.inputs.add("lp")
        if keys[pygame.K_KP5]: self.fighter2.inputs.add("mp")
        if keys[pygame.K_KP6]: self.fighter2.inputs.add("hp")
        if keys[pygame.K_KP1]: self.fighter2.inputs.add("lk")
        if keys[pygame.K_KP2]: self.fighter2.inputs.add("mk")
        if keys[pygame.K_KP3]: self.fighter2.inputs.add("hk")
    
    def update(self):
        """Update game"""
        self.fighter1.update()
        self.fighter2.update()
        
        # Check collisions
        self._check_collisions()
    
    def _check_collisions(self):
        """Check attack collisions"""
        # Fighter 1 attacks Fighter 2
        for hitbox in self.fighter1.hitboxes:
            if hitbox.active and self._hitbox_collision(hitbox, self.fighter2):
                if self._is_blocking(self.fighter2, self.fighter1):
                    self.fighter2.block_attack(hitbox.blockstun)
                else:
                    self.fighter2.take_damage(hitbox.damage, hitbox.hitstun)
                hitbox.active = False
        
        # Fighter 2 attacks Fighter 1
        for hitbox in self.fighter2.hitboxes:
            if hitbox.active and self._hitbox_collision(hitbox, self.fighter1):
                if self._is_blocking(self.fighter1, self.fighter2):
                    self.fighter1.block_attack(hitbox.blockstun)
                else:
                    self.fighter1.take_damage(hitbox.damage, hitbox.hitstun)
                hitbox.active = False
    
    def _hitbox_collision(self, hitbox: Hitbox, fighter: Fighter) -> bool:
        """Check if hitbox collides with fighter"""
        hitbox_rect = pygame.Rect(hitbox.x - hitbox.width//2, hitbox.y - hitbox.height//2, hitbox.width, hitbox.height)
        fighter_rect = fighter.get_rect()
        return hitbox_rect.colliderect(fighter_rect)
    
    def _is_blocking(self, defender: Fighter, attacker: Fighter) -> bool:
        """Check if defender is blocking the attack"""
        if defender.state not in [CharacterState.BLOCKING, CharacterState.IDLE]:
            return False
        
        # Check if blocking in correct direction
        if attacker.x < defender.x:  # Attack from left
            return not defender.facing_right and "left" in defender.inputs
        else:  # Attack from right
            return defender.facing_right and "right" in defender.inputs
    
    def render(self):
        """Render game"""
        # Clear screen
        self.screen.fill((40, 50, 80))
        
        # Draw ground
        ground_y = self.screen_height - 100
        pygame.draw.line(self.screen, (100, 100, 100), (0, ground_y), (self.screen_width, ground_y), 3)
        
        # Draw fighters
        self.fighter1.render(self.screen)
        self.fighter2.render(self.screen)
        
        # Draw health bars
        self._draw_health_bar(self.fighter1, 50, 50)
        self._draw_health_bar(self.fighter2, self.screen_width - 350, 50)
        
        # Draw controls
        self._draw_controls()
        
        # Draw sprite status
        sprite_status = "✅ SPRITES LOADED" if SPRITES_AVAILABLE else "⚠️ RECTANGLES (sprites not loaded)"
        status_color = (0, 255, 0) if SPRITES_AVAILABLE else (255, 255, 0)
        status_text = self.small_font.render(sprite_status, True, status_color)
        self.screen.blit(status_text, (10, 10))
        
        pygame.display.flip()
    
    def _draw_health_bar(self, fighter: Fighter, x: int, y: int):
        """Draw health bar"""
        bar_width = 300
        bar_height = 20
        
        # Background
        pygame.draw.rect(self.screen, (100, 0, 0), (x, y, bar_width, bar_height))
        
        # Health
        health_width = int((fighter.health / fighter.max_health) * bar_width)
        pygame.draw.rect(self.screen, (0, 255, 0), (x, y, health_width, bar_height))
        
        # Border
        pygame.draw.rect(self.screen, (255, 255, 255), (x, y, bar_width, bar_height), 2)
        
        # Text
        character_name = fighter.character.upper()
        player_text = f"P{fighter.player_num}: {character_name}"
        health_text = f"{fighter.health}/{fighter.max_health}"
        
        player_surface = self.font.render(player_text, True, (255, 255, 255))
        health_surface = self.small_font.render(health_text, True, (255, 255, 255))
        
        self.screen.blit(player_surface, (x, y - 30))
        self.screen.blit(health_surface, (x, y + 25))
    
    def _draw_controls(self):
        """Draw control instructions"""
        controls = [
            "P1: WASD+UIOJKL | P2: Arrows+Numpad | ESC: Exit"
        ]
        
        y_offset = self.screen_height - 30
        for i, control in enumerate(controls):
            text = self.small_font.render(control, True, (200, 200, 200))
            text_rect = text.get_rect(center=(self.screen_width // 2, y_offset + i * 25))
            self.screen.blit(text, text_rect)
    
    def run(self):
        """Run the game"""
        while self.running:
            self.handle_input()
            self.update()
            self.render()
            self.clock.tick(60)
        
        pygame.quit()


if __name__ == "__main__":
    print("🎮 Starting Simple Fighting Game with Sprites...")
    game = SimpleFightingGame()
    game.run()
