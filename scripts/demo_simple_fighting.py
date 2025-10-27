#!/usr/bin/env python3
"""
Simple Fighting Game Demo

A self-contained playable fighting game that doesn't depend on complex imports.
You can finally control characters and see them move and fight!

Controls:
- WASD: Move Player 1 (Blue)
- UIOJKL: Attack buttons for Player 1
- Arrow Keys: Move Player 2 (Red) 
- Numpad: Attack buttons for Player 2

This is a REAL fighting game you can play!
"""

import pygame
import sys
import math
from enum import Enum
from dataclasses import dataclass
from typing import Set, Tuple, List, Optional


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
    SPECIAL = "special"


class AttackHeight(Enum):
    """Attack height classification for blocking"""
    MID = "mid"        # Can be blocked standing or crouching
    LOW = "low"        # Must be blocked crouching
    OVERHEAD = "overhead"  # Must be blocked standing


@dataclass
class Attack:
    """Attack data"""
    name: str
    damage: int
    startup: int
    active: int
    recovery: int
    range: int
    height: AttackHeight = AttackHeight.MID  # Attack height for blocking
    blockstun: int = 10  # Frames of blockstun
    priority: int = 1  # Attack priority (higher = wins clashes)
    pushback: float = 5.0  # Pushback distance on block


class Character:
    """Simple fighting game character"""
    
    def __init__(self, player_number: int, x: float, y: float, color: tuple):
        self.player_number = player_number
        self.position = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.color = color

        # Character properties
        self.health = 1000
        self.max_health = 1000
        self.facing_right = player_number == 1

        # State
        self.state = CharacterState.IDLE
        self.on_ground = True

        # Movement
        self.walk_speed = 3.0
        self.jump_speed = 12.0
        self.gravity = 0.6
        self.ground_y = 500

        # Combat
        self.current_attack = None
        self.attack_timer = 0
        self.hitstun_timer = 0
        self.blockstun_timer = 0
        self.is_blocking = False
        self.is_low_blocking = False  # Track if blocking low (crouching)

        # Hit queue system - prevents multi-hitting
        self.attack_id = 0  # Unique ID for each attack activation
        self.last_hit_by_attack_id = None  # Track the last attack that hit this character

        # Input
        self.input_buffer = []

        # Reference to opponent (set by game)
        self.opponent = None
        
        # Attacks with detailed properties (standing versions)
        # Crouching attacks will automatically become LOW
        self.attacks = {
            AttackType.LIGHT_PUNCH: Attack(
                "Light Punch", 30, 5, 3, 8, 60,
                height=AttackHeight.MID, blockstun=8, priority=1, pushback=3.0
            ),
            AttackType.MEDIUM_PUNCH: Attack(
                "Medium Punch", 50, 8, 4, 12, 80,
                height=AttackHeight.MID, blockstun=12, priority=2, pushback=6.0
            ),
            AttackType.HEAVY_PUNCH: Attack(
                "Heavy Punch", 80, 12, 6, 18, 100,
                height=AttackHeight.OVERHEAD, blockstun=18, priority=3, pushback=10.0
            ),
            AttackType.LIGHT_KICK: Attack(
                "Light Kick", 35, 6, 4, 10, 70,
                height=AttackHeight.MID, blockstun=9, priority=1, pushback=4.0
            ),
            AttackType.MEDIUM_KICK: Attack(
                "Medium Kick", 55, 10, 5, 15, 90,
                height=AttackHeight.MID, blockstun=14, priority=2, pushback=7.0
            ),
            AttackType.HEAVY_KICK: Attack(
                "Heavy Kick", 85, 15, 8, 20, 110,
                height=AttackHeight.MID, blockstun=20, priority=3, pushback=12.0
            ),
        }
        
        print(f"Player {player_number} character created at ({x}, {y})")
    
    def update(self, keys_pressed, events: List[pygame.event.Event]):
        """Update character"""
        
        # Handle input based on state
        if self.state == CharacterState.HITSTUN:
            self._update_hitstun()
        elif self.state == CharacterState.BLOCKSTUN:
            self._update_blockstun()
        elif self.state == CharacterState.ATTACKING:
            self._update_attack()
        else:
            self._handle_input(keys_pressed, events)
        
        # Apply physics
        self._apply_physics()
        
        # Update timers
        if self.attack_timer > 0:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self._end_attack()
        
        if self.hitstun_timer > 0:
            self.hitstun_timer -= 1
            if self.hitstun_timer <= 0:
                self._end_hitstun()
        
        if self.blockstun_timer > 0:
            self.blockstun_timer -= 1
            if self.blockstun_timer <= 0:
                self._end_blockstun()
    
    def _handle_input(self, keys_pressed, events: List[pygame.event.Event]):
        """Handle player input"""
        
        # Get key mappings for this player
        if self.player_number == 1:
            # Player 1: WASD + UIOJKL
            left_key = pygame.K_a
            right_key = pygame.K_d
            up_key = pygame.K_w
            down_key = pygame.K_s
            attack_keys = {
                pygame.K_u: AttackType.LIGHT_PUNCH,
                pygame.K_i: AttackType.MEDIUM_PUNCH,
                pygame.K_o: AttackType.HEAVY_PUNCH,
                pygame.K_j: AttackType.LIGHT_KICK,
                pygame.K_k: AttackType.MEDIUM_KICK,
                pygame.K_l: AttackType.HEAVY_KICK,
            }
        else:
            # Player 2: Arrow Keys + Numpad
            left_key = pygame.K_LEFT
            right_key = pygame.K_RIGHT
            up_key = pygame.K_UP
            down_key = pygame.K_DOWN
            attack_keys = {
                pygame.K_KP4: AttackType.LIGHT_PUNCH,
                pygame.K_KP5: AttackType.MEDIUM_PUNCH,
                pygame.K_KP6: AttackType.HEAVY_PUNCH,
                pygame.K_KP1: AttackType.LIGHT_KICK,
                pygame.K_KP2: AttackType.MEDIUM_KICK,
                pygame.K_KP3: AttackType.HEAVY_KICK,
            }
        
        # Check for attack inputs (only on key press, not hold)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in attack_keys:
                    attack_type = attack_keys[event.key]
                    self._start_attack(attack_type)
                    return
        
        # Handle movement
        self.velocity.x = 0
        
        # Determine back direction (for blocking)
        back_key = left_key if self.facing_right else right_key
        forward_key = right_key if self.facing_right else left_key

        # Check holding states
        holding_back = keys_pressed[back_key]
        holding_down = keys_pressed[down_key]

        # CONTEXTUAL BLOCKING: Only block when opponent is close AND attacking
        # Otherwise allow free backward movement
        if holding_back and self.on_ground and self.opponent:
            # Check if opponent is actively attacking
            opponent_attacking = self.opponent.state == CharacterState.ATTACKING

            # Only block if opponent is actively attacking (not just nearby)
            # This prevents blocking when just trying to walk backward
            if opponent_attacking:
                # Additional proximity check - only block if opponent is reasonably close
                distance = abs(self.position.x - self.opponent.position.x)
                if distance < 300:  # Within attack range
                    low_block = holding_down
                    self._start_block(low_block=low_block)
                    return  # Exit early - blocking takes priority

        # Stop blocking if not holding back anymore
        if not holding_back and self.state == CharacterState.BLOCKING:
            self._stop_block()

        # Jumping
        if keys_pressed[up_key] and self.on_ground:
            self._start_jump()
            return

        # Crouching (only if not blocking)
        if keys_pressed[down_key] and not holding_back and self.state != CharacterState.BLOCKING:
            if self.state != CharacterState.CROUCHING:
                self._start_crouch()
        else:
            if self.state == CharacterState.CROUCHING:
                self._start_idle()
        
        # Walking
        if keys_pressed[back_key]:
            # Walking backward
            direction = -1 if self.facing_right else 1
            self.velocity.x = direction * self.walk_speed * 0.8  # Slower backward walk
            if self.state != CharacterState.CROUCHING:
                self._start_walk()
        elif keys_pressed[forward_key]:
            # Walking forward
            direction = 1 if self.facing_right else -1
            self.velocity.x = direction * self.walk_speed
            if self.state != CharacterState.CROUCHING:
                self._start_walk()
        else:
            if self.state == CharacterState.WALKING:
                self._start_idle()
    
    def _start_idle(self):
        """Start idle state"""
        self.state = CharacterState.IDLE
    
    def _start_walk(self):
        """Start walking"""
        self.state = CharacterState.WALKING
    
    def _start_jump(self):
        """Start jumping"""
        self.state = CharacterState.JUMPING
        self.velocity.y = -self.jump_speed
        self.on_ground = False
    
    def _start_crouch(self):
        """Start crouching"""
        self.state = CharacterState.CROUCHING
        self.velocity.x = 0
    
    def _start_block(self, low_block: bool = False):
        """Start blocking"""
        # Only print when transitioning into blocking (not already blocking)
        if self.state != CharacterState.BLOCKING:
            block_type = "low" if low_block else "high"
            print(f"Player {self.player_number} blocks {block_type}!")

        self.state = CharacterState.BLOCKING
        self.is_blocking = True
        self.is_low_blocking = low_block
        self.velocity.x = 0
    
    def _stop_block(self):
        """Stop blocking"""
        self.is_blocking = False
        self.is_low_blocking = False
        if self.on_ground:
            self._start_idle()
        else:
            self.state = CharacterState.JUMPING
    
    def _check_for_incoming_attack(self) -> bool:
        """Check if there's an incoming attack that should trigger blocking"""
        # This is a simple check - in a real game you'd check opponent's attack state
        # and distance. For now, we'll make blocking more manual/reactive.
        return False  # Always allow walking backward unless manually blocking
    
    def _start_attack(self, attack_type: AttackType):
        """Start an attack"""
        if self.state in [CharacterState.ATTACKING, CharacterState.HITSTUN]:
            return

        # Increment attack ID for this new attack (unique identifier)
        self.attack_id += 1

        # Get base attack properties
        base_attack = self.attacks[attack_type]

        # Modify attack based on stance (crouching = low attack)
        if self.state == CharacterState.CROUCHING:
            # Crouching attacks become LOW attacks
            self.current_attack = Attack(
                f"Crouching {base_attack.name}",
                base_attack.damage,
                base_attack.startup,
                base_attack.active,
                base_attack.recovery,
                base_attack.range,
                height=AttackHeight.LOW,  # Force LOW
                blockstun=base_attack.blockstun,
                priority=base_attack.priority,
                pushback=base_attack.pushback
            )
        else:
            # Standing attacks use default height
            self.current_attack = base_attack

        self.state = CharacterState.ATTACKING
        self.attack_timer = self.current_attack.startup + self.current_attack.active + self.current_attack.recovery
        self.velocity.x = 0

        print(f"Player {self.player_number} uses {self.current_attack.name}!")
    
    def _update_attack(self):
        """Update during attack state"""
        # Reduce movement during attacks
        self.velocity.x *= 0.5
    
    def _end_attack(self):
        """End current attack"""
        self.current_attack = None
        if self.on_ground:
            self._start_idle()
        else:
            self.state = CharacterState.JUMPING

    
    def check_character_collision(self, other_character) -> bool:
        """Check if this character is colliding with another character"""
        my_rect = self.get_hurtbox()
        other_rect = other_character.get_hurtbox()
        return my_rect.colliderect(other_rect)
    
    def resolve_character_collision(self, other_character):
        """Resolve collision with another character (push mechanics)"""
        
        # Don't resolve collision during certain states
        if (self.state in [CharacterState.HITSTUN, CharacterState.BLOCKSTUN] or 
            other_character.state in [CharacterState.HITSTUN, CharacterState.BLOCKSTUN]):
            return
        
        # Calculate push direction
        if self.position.x < other_character.position.x:
            # I'm on the left, other is on the right
            push_direction = -1  # Push me left
            other_push_direction = 1  # Push other right
        else:
            # I'm on the right, other is on the left
            push_direction = 1  # Push me right
            other_push_direction = -1  # Push other left
        
        # Determine who gets pushed based on movement and state
        my_moving = abs(self.velocity.x) > 0.1
        other_moving = abs(other_character.velocity.x) > 0.1
        
        push_strength = 2.0
        
        if my_moving and not other_moving:
            # I'm moving, other is stationary - push other
            other_character.position.x += other_push_direction * push_strength
            # Stop my movement
            self.velocity.x = 0
        elif other_moving and not my_moving:
            # Other is moving, I'm stationary - push me
            self.position.x += push_direction * push_strength
        elif my_moving and other_moving:
            # Both moving - push both away from each other
            self.position.x += push_direction * (push_strength * 0.5)
            other_character.position.x += other_push_direction * (push_strength * 0.5)
            # Reduce both velocities
            self.velocity.x *= 0.5
            other_character.velocity.x *= 0.5
        else:
            # Neither moving - push both away equally
            self.position.x += push_direction * (push_strength * 0.5)
            other_character.position.x += other_push_direction * (push_strength * 0.5)
        
        # Ensure characters stay within screen bounds after pushing
        self.position.x = max(50, min(1230, self.position.x))
        other_character.position.x = max(50, min(1230, other_character.position.x))
    
    def take_damage(self, damage: int):
        """Apply damage to character"""
        self.health = max(0, self.health - damage)
        self.hitstun_timer = 20
        self.state = CharacterState.HITSTUN
        
        # Knockback
        knockback_direction = -1 if self.facing_right else 1
        self.velocity.x = knockback_direction * 3
        
        print(f"Player {self.player_number} takes {damage} damage! Health: {self.health}")
    
    def _update_hitstun(self):
        """Update during hitstun"""
        # Reduce knockback
        self.velocity.x *= 0.9
    
    def _end_hitstun(self):
        """End hitstun"""
        if self.on_ground:
            self._start_idle()
        else:
            self.state = CharacterState.JUMPING
    
    def _update_blockstun(self):
        """Update during blockstun"""
        # Can't move during blockstun
        self.velocity.x = 0
    
    def _end_blockstun(self):
        """End blockstun"""
        if self.on_ground:
            self._start_idle()
        else:
            self.state = CharacterState.JUMPING
    
    def can_block_attack(self, attack: Attack) -> bool:
        """Check if current blocking stance can block the incoming attack"""
        if not self.is_blocking:
            return False

        # MID attacks can be blocked by any stance
        if attack.height == AttackHeight.MID:
            return True

        # LOW attacks must be blocked crouching
        if attack.height == AttackHeight.LOW:
            return self.is_low_blocking

        # OVERHEAD attacks must be blocked standing
        if attack.height == AttackHeight.OVERHEAD:
            return not self.is_low_blocking

        return False

    def take_blocked_damage(self, attack: Attack):
        """Take chip damage from blocked attack"""
        chip_damage = max(1, attack.damage // 10)  # 10% chip damage, minimum 1
        self.health = max(0, self.health - chip_damage)
        self.blockstun_timer = attack.blockstun  # Use attack's blockstun value
        self.state = CharacterState.BLOCKSTUN

        block_type = "low" if self.is_low_blocking else "high"
        print(f"Player {self.player_number} {block_type} blocks for {chip_damage} chip damage! Health: {self.health}")

    def _end_attack(self):
        """End current attack"""
        self.current_attack = None
        if self.on_ground:
            self._start_idle()
        else:
            self.state = CharacterState.JUMPING
    
    def _apply_physics(self):
        """Apply physics"""
        
        # Gravity
        if not self.on_ground:
            self.velocity.y += self.gravity
        
        # Update position
        self.position += self.velocity
        
        # Ground collision
        if self.position.y >= self.ground_y:
            self.position.y = self.ground_y
            self.velocity.y = 0
            if not self.on_ground:
                self.on_ground = True
                if self.state == CharacterState.JUMPING:
                    self._start_idle()
        
        # Screen boundaries
        self.position.x = max(50, min(1230, self.position.x))

    def get_hurtbox(self) -> pygame.Rect:
        """Get character hurtbox for collision detection"""
        return pygame.Rect(self.position.x - 20, self.position.y - 80, 40, 80)
    
    def get_attack_hitbox(self) -> Optional[pygame.Rect]:
        """Get attack hitbox if attacking"""
        if self.state != CharacterState.ATTACKING or not self.current_attack:
            return None
        
        # Only active during active frames
        frames_elapsed = (self.current_attack.startup + self.current_attack.active + self.current_attack.recovery) - self.attack_timer
        if frames_elapsed < self.current_attack.startup or frames_elapsed >= self.current_attack.startup + self.current_attack.active:
            return None
        
        # Create hitbox in front of character
        hitbox_x = self.position.x + (50 if self.facing_right else -50)
        hitbox_y = self.position.y - 40
        
        return pygame.Rect(hitbox_x - 25, hitbox_y - 25, 50, 50)
    
    def render(self, screen: pygame.Surface):
        """Render character"""
        
        # Character body
        char_rect = pygame.Rect(self.position.x - 20, self.position.y - 80, 40, 80)
        
        # Color based on state
        color = self.color
        if self.state == CharacterState.ATTACKING:
            color = tuple(min(255, c + 50) for c in self.color)
        elif self.state == CharacterState.HITSTUN:
            color = (255, 100, 100)
        elif self.state == CharacterState.BLOCKING:
            color = (200, 200, 255)  # Light blue for blocking
        elif self.state == CharacterState.BLOCKSTUN:
            color = (150, 150, 255)  # Darker blue for blockstun
        elif self.state == CharacterState.CROUCHING:
            char_rect.height = 60
            char_rect.y += 20
        
        pygame.draw.rect(screen, color, char_rect)
        
        # Facing indicator
        facing_x = self.position.x + (15 if self.facing_right else -25)
        facing_rect = pygame.Rect(facing_x, self.position.y - 85, 10, 5)
        pygame.draw.rect(screen, (255, 255, 255), facing_rect)
        
        # Attack hitbox
        hitbox = self.get_attack_hitbox()
        if hitbox:
            pygame.draw.rect(screen, (255, 255, 0), hitbox, 2)
        
        # Current action text
        if self.current_attack:
            font = pygame.font.Font(None, 18)
            text = font.render(self.current_attack.name, True, (255, 255, 255))
            screen.blit(text, (self.position.x - 40, self.position.y - 100))


class SimpleFightingGame:
    """Simple fighting game"""
    
    def __init__(self):
        pygame.init()
        self.screen_size = (1280, 720)
        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption("Simple Fighting Game - FIGHT!")
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.fps = 60
        
        # Create characters
        self.player1 = Character(1, 300, 500, (100, 150, 255))  # Blue
        self.player2 = Character(2, 900, 500, (255, 100, 100))  # Red

        # Set opponent references for contextual blocking
        self.player1.opponent = self.player2
        self.player2.opponent = self.player1

        # Game state
        self.round_timer = 99 * 60  # 99 seconds
        self.paused = False
        self.winner = None
        
        # UI
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 18)
        
        # Effects
        self.hit_effects = []
        
        print("🥋 Simple Fighting Game initialized!")
        print("🎮 CONTROLS:")
        print("   Player 1 (Blue): WASD (move) + UIOJKL (attacks)")
        print("   Player 2 (Red): Arrow Keys (move) + Numpad (attacks)")
        print("   BLOCKING: Hold BACK (away from opponent)")
        print("   P = Pause, ESC = Exit")
    
    def run(self):
        """Main game loop"""
        
        print("🚀 FIGHT!")
        
        while self.running:
            # Handle events
            events = pygame.event.get()
            keys_pressed = pygame.key.get_pressed()
            
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_p:
                        self.paused = not self.paused
                        print(f"Game {'paused' if self.paused else 'resumed'}")
                    elif event.key == pygame.K_r and self.winner:
                        self._reset_round()
            
            if not self.paused and not self.winner:
                # Update game
                self._update(keys_pressed, events)
            
            # Draw everything
            self._draw()
            
            self.clock.tick(self.fps)
        
        pygame.quit()
    
    def _update(self, keys_pressed, events):
        """Update game state"""
        
        # Update characters
        self.player1.update(keys_pressed, events)
        self.player2.update(keys_pressed, events)
        
        # Check character collision and resolve pushing (multiple times for better collision)
        for _ in range(3):  # Check collision multiple times per frame
            self._check_character_collision()
            # Break early if no collision
            if not self.player1.get_hurtbox().colliderect(self.player2.get_hurtbox()):
                break
        
        # Update character facing
        if self.player1.position.x < self.player2.position.x:
            self.player1.facing_right = True
            self.player2.facing_right = False
        else:
            self.player1.facing_right = False
            self.player2.facing_right = True
        
        # Check combat
        self._check_combat()
        
        # Check win conditions
        if self.player1.health <= 0:
            self.winner = 2
        elif self.player2.health <= 0:
            self.winner = 1
    
    def _check_character_collision(self):
        """Check and resolve character collision (push mechanics)"""
        
        # Get character hitboxes
        p1_rect = self.player1.get_hurtbox()
        p2_rect = self.player2.get_hurtbox()
        
        # Check if characters are colliding or overlapping
        if p1_rect.colliderect(p2_rect):
            # Calculate push directions based on position
            if self.player1.position.x < self.player2.position.x:
                p1_push_direction = -1
                p2_push_direction = 1
            else:
                p1_push_direction = 1
                p2_push_direction = -1

            # Check states
            p1_stunned = self.player1.state in [CharacterState.HITSTUN, CharacterState.BLOCKSTUN]
            p2_stunned = self.player2.state in [CharacterState.HITSTUN, CharacterState.BLOCKSTUN]
            p1_blocking = self.player1.state == CharacterState.BLOCKING
            p2_blocking = self.player2.state == CharacterState.BLOCKING

            # Don't push during stun
            if p1_stunned and p2_stunned:
                return

            # Calculate how much to push
            push_amount = 3.0

            # Who gets pushed?
            if p1_stunned:
                # P1 stunned, only push P2
                self.player2.position.x += p2_push_direction * push_amount
            elif p2_stunned:
                # P2 stunned, only push P1
                self.player1.position.x += p1_push_direction * push_amount
            elif p1_blocking and p2_blocking:
                # Both blocking - push both
                self.player1.position.x += p1_push_direction * push_amount
                self.player2.position.x += p2_push_direction * push_amount
            elif p1_blocking:
                # P1 blocking - push P2
                self.player2.position.x += p2_push_direction * push_amount
            elif p2_blocking:
                # P2 blocking - push P1
                self.player1.position.x += p1_push_direction * push_amount
            else:
                # Neither blocking/stunned - push both equally
                self.player1.position.x += p1_push_direction * push_amount
                self.player2.position.x += p2_push_direction * push_amount

            # Ensure characters stay within screen bounds
            self.player1.position.x = max(50, min(1230, self.player1.position.x))
            self.player2.position.x = max(50, min(1230, self.player2.position.x))
    
    def _check_combat(self):
        """Check for combat interactions with high/low blocking and pushback"""

        # Check if P1 hits P2
        p1_hitbox = self.player1.get_attack_hitbox()
        if p1_hitbox and p1_hitbox.colliderect(self.player2.get_hurtbox()):
            if self.player2.state not in [CharacterState.HITSTUN, CharacterState.BLOCKSTUN]:
                attack = self.player1.current_attack

                # HIT QUEUE: Check if this attack has already hit P2
                if self.player2.last_hit_by_attack_id == self.player1.attack_id:
                    # This attack already hit P2, skip
                    return

                # Mark that this attack has now hit P2
                self.player2.last_hit_by_attack_id = self.player1.attack_id

                # Check if P2 can block this attack
                if self.player2.can_block_attack(attack):
                    # Successful block
                    print(f"P2 blocks {attack.name} ({attack.height.value})!")
                    self.player2.take_blocked_damage(attack)

                    # Apply pushback on block
                    pushback_direction = 1 if self.player1.facing_right else -1
                    self.player2.position.x += pushback_direction * attack.pushback
                else:
                    # Failed to block or not blocking
                    if self.player2.is_blocking:
                        print(f"P2 failed to block! Wrong block type for {attack.height.value} attack!")
                    self.player2.take_damage(attack.damage)

        # Check if P2 hits P1
        p2_hitbox = self.player2.get_attack_hitbox()
        if p2_hitbox and p2_hitbox.colliderect(self.player1.get_hurtbox()):
            if self.player1.state not in [CharacterState.HITSTUN, CharacterState.BLOCKSTUN]:
                attack = self.player2.current_attack

                # HIT QUEUE: Check if this attack has already hit P1
                if self.player1.last_hit_by_attack_id == self.player2.attack_id:
                    # This attack already hit P1, skip
                    return

                # Mark that this attack has now hit P1
                self.player1.last_hit_by_attack_id = self.player2.attack_id

                # Check if P1 can block this attack
                if self.player1.can_block_attack(attack):
                    # Successful block
                    print(f"P1 blocks {attack.name} ({attack.height.value})!")
                    self.player1.take_blocked_damage(attack)

                    # Apply pushback on block
                    pushback_direction = 1 if self.player2.facing_right else -1
                    self.player1.position.x += pushback_direction * attack.pushback
                else:
                    # Failed to block or not blocking
                    if self.player1.is_blocking:
                        print(f"P1 failed to block! Wrong block type for {attack.height.value} attack!")
                    self.player1.take_damage(attack.damage)
    
    def _draw(self):
        """Draw everything"""
        
        # Clear screen
        self.screen.fill((20, 30, 50))
        
        # Draw characters
        self.player1.render(self.screen)
        self.player2.render(self.screen)
        
        # Draw UI
        self._draw_ui()
        
        pygame.display.flip()
    
    def _draw_ui(self):
        """Draw UI"""
        
        # Health bars
        self._draw_health_bar(1, self.player1.health, self.player1.max_health)
        self._draw_health_bar(2, self.player2.health, self.player2.max_health)
        
        # Winner announcement
        if self.winner:
            win_text = f"PLAYER {self.winner} WINS!"
            win_surface = self.big_font.render(win_text, True, (255, 255, 0))
            win_rect = win_surface.get_rect(center=(self.screen_size[0] // 2, self.screen_size[1] // 2))
            self.screen.blit(win_surface, win_rect)
        
        # Controls
        if not self.winner:
            controls_text = "P1: WASD+UIOJKL | P2: Arrows+Numpad | BLOCK: Hold BACK (away from opponent) | P=Pause | ESC=Exit"
            controls_surface = self.small_font.render(controls_text, True, (200, 200, 200))
            self.screen.blit(controls_surface, (10, self.screen_size[1] - 25))
    
    def _draw_health_bar(self, player_number: int, health: int, max_health: int):
        """Draw health bar"""
        
        bar_width = 400
        bar_height = 20
        
        if player_number == 1:
            bar_x = 50
        else:
            bar_x = self.screen_size[0] - bar_width - 50
        
        bar_y = 50
        
        # Background
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(self.screen, (100, 100, 100), bg_rect)
        
        # Health
        health_width = int((health / max_health) * bar_width)
        health_rect = pygame.Rect(bar_x, bar_y, health_width, bar_height)
        
        # Color based on health
        if health > max_health * 0.6:
            color = (0, 255, 0)
        elif health > max_health * 0.3:
            color = (255, 255, 0)
        else:
            color = (255, 0, 0)
        
        pygame.draw.rect(self.screen, color, health_rect)
        
        # Border
        pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, 2)
        
        # Player name
        name = f"P{player_number}"
        name_surface = self.font.render(name, True, (255, 255, 255))
        self.screen.blit(name_surface, (bar_x, bar_y - 25))
    
    def _reset_round(self):
        """Reset for new round"""
        self.player1.health = self.player1.max_health
        self.player2.health = self.player2.max_health
        self.player1.position = pygame.Vector2(300, 500)
        self.player2.position = pygame.Vector2(900, 500)
        self.player1.state = CharacterState.IDLE
        self.player2.state = CharacterState.IDLE
        self.winner = None


def main():
    """Main function"""
    print("🥋 SIMPLE FIGHTING GAME 🥋")
    print("=" * 40)
    print("A real playable fighting game!")
    print("Move, jump, crouch, and attack!")
    print("=" * 40)
    
    game = SimpleFightingGame()
    game.run()


if __name__ == "__main__":
    main()