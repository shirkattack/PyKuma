"""Base character class with state machine and physics."""

import logging
from typing import Optional, Dict, List
import pygame

from street_fighter_3rd.util.logging_config import get_logger, log_once
from street_fighter_3rd.data.enums import CharacterState, FacingDirection, InputDirection, Button, HitEffect
from street_fighter_3rd.data.constants import (
    GRAVITY,
    JUMP_VELOCITY,
    WALK_SPEED,
    STAGE_FLOOR,
    STAGE_LEFT_BOUND,
    STAGE_RIGHT_BOUND,
    MAX_HEALTH,
    MAX_SUPER_METER,
)
from street_fighter_3rd.data.frame_data import MoveData
from street_fighter_3rd.systems.input_system import PlayerInput

log = get_logger(__name__)

_ATTACK_STATES = frozenset({
    CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_PUNCH, CharacterState.HEAVY_PUNCH,
    CharacterState.LIGHT_KICK, CharacterState.MEDIUM_KICK, CharacterState.HEAVY_KICK,
    CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_MEDIUM_PUNCH, CharacterState.CROUCH_HEAVY_PUNCH,
    CharacterState.CROUCH_LIGHT_KICK, CharacterState.CROUCH_MEDIUM_KICK, CharacterState.CROUCH_HEAVY_KICK,
    CharacterState.JUMP_LIGHT_PUNCH, CharacterState.JUMP_MEDIUM_PUNCH, CharacterState.JUMP_HEAVY_PUNCH,
    CharacterState.JUMP_LIGHT_KICK, CharacterState.JUMP_MEDIUM_KICK, CharacterState.JUMP_HEAVY_KICK,
    CharacterState.GOHADOKEN, CharacterState.GOSHORYUKEN, CharacterState.TATSUMAKI,
})

_CROUCH_STATES = frozenset({
    CharacterState.CROUCHING,
    CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_MEDIUM_PUNCH, CharacterState.CROUCH_HEAVY_PUNCH,
    CharacterState.CROUCH_LIGHT_KICK, CharacterState.CROUCH_MEDIUM_KICK, CharacterState.CROUCH_HEAVY_KICK,
})

# Recovery for these reaction states is governed by hitstun_frames / physics,
# not by animation completion, so a character subclass should hold them.
LAUNCH_HITSTUN = 60     # generous; physics lands the character before it expires
KNOCKDOWN_HITSTUN = 40


def apply_reaction(character, hit_effect: HitEffect, hitstun: int):
    """Put `character` into the reaction state for a given hit effect.

    Shared by the collision adapter and Character.take_damage so direct callers
    (tests, projectiles) get the same reactions. Recovery is driven by
    hitstun_frames (decremented in update()), with the floor-land transition for
    airborne/launch.
    """
    character.in_hitstun = True
    if hit_effect == HitEffect.JUGGLE:
        character.velocity_y = -14.0
        character.is_grounded = False
        character.hitstun_frames = LAUNCH_HITSTUN
        character._transition_to_state(CharacterState.HITSTUN_AIRBORNE)
    elif hit_effect in (HitEffect.KNOCKDOWN, HitEffect.CRUMPLE,
                        HitEffect.GROUND_BOUNCE, HitEffect.WALL_BOUNCE):
        character.hitstun_frames = max(hitstun, KNOCKDOWN_HITSTUN)
        character._transition_to_state(CharacterState.KNOCKDOWN)
    else:  # NORMAL
        character.hitstun_frames = hitstun
        if not character.is_grounded:
            character._transition_to_state(CharacterState.HITSTUN_AIRBORNE)
        elif character.state in _CROUCH_STATES:
            character._transition_to_state(CharacterState.HITSTUN_CROUCHING)
        else:
            character._transition_to_state(CharacterState.HITSTUN_STANDING)


_debug_font: Optional[pygame.font.Font] = None


def get_debug_font() -> pygame.font.Font:
    """Shared lazily-created font for per-character debug text (Font construction is expensive)."""
    global _debug_font
    if _debug_font is None:
        _debug_font = pygame.font.Font(None, 16)
    return _debug_font


class Character:
    """Base class for all playable characters."""

    def __init__(self, x: float, y: float, player_number: int):
        """Initialize character.

        Args:
            x: Starting x position
            y: Starting y position
            player_number: 1 or 2
        """
        # Position and physics
        self.x = x
        self.y = y
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.facing = FacingDirection.RIGHT if player_number == 1 else FacingDirection.LEFT
        self.facing_lock_frames = 0  # Prevent rapid facing changes (crossup protection)

        # Dimensions (will be overridden by actual sprites)
        self.width = 50
        self.height = 80
        self.hitbox_width = 40
        self.hitbox_height = 75

        # Game state
        self.player_number = player_number
        self.state = CharacterState.STANDING
        self.previous_state = CharacterState.STANDING
        self.state_frame = 0  # Current frame in the current state
        self.animation_frame = 0  # Current animation frame
        self.total_frames = 0  # Total frames since game start

        # Combat stats
        # max_health is the single source of truth for this character's health.
        # Subclasses override it (e.g. Akuma's 145) and health bars normalize against it.
        self.max_health = MAX_HEALTH
        self.health = self.max_health
        self.super_meter = 0
        self.stun_meter = 0
        self.combo_counter = 0
        self.hitstun_frames = 0
        self.blockstun_frames = 0
        self.hitfreeze_frames = 0  # Frames of hit freeze (hitstop)
        self.hitflash_frames = 0  # Frames of white flash on hit

        # State flags
        self.is_grounded = True
        self.can_act = True
        self.in_hitstun = False
        self.in_blockstun = False
        self.is_blocking = False
        self.is_invincible = False  # Invincibility frames (DP, etc.)
        self.invincibility_frames = []  # List of frames with invincibility

        # Jump tracking
        self.jump_direction = InputDirection.NEUTRAL  # Track jump direction for animations

        # Input reference (will be set externally)
        self.input: Optional[PlayerInput] = None

        # Move data (to be defined by subclasses)
        self.move_data: Dict[CharacterState, MoveData] = {}

        # STATE SAFETY GUARDS - Prevent soft-locks and infinite loops
        self.max_state_frames = self._get_max_state_frames()  # Maximum frames allowed per state
        self.non_cancelable_states = self._get_non_cancelable_states()  # States that can't be interrupted
        self.last_special_frame = -999  # Frame when last special was executed (prevents spam)
        self.special_cooldown_frames = 15  # Minimum frames between special moves

        # Colors for placeholder rendering
        self.color = (255, 50, 50) if player_number == 1 else (50, 50, 255)
        self.outline_color = (255, 255, 255)

        # True when the last render drew the rectangle placeholder (missing art)
        self._rendered_fallback = False

    def _get_max_state_frames(self) -> Dict[CharacterState, int]:
        """Define maximum frames allowed for each state to prevent infinite loops.

        Returns:
            Dictionary mapping states to their maximum allowed frames
        """
        return {
            # Movement states - can stay indefinitely
            CharacterState.STANDING: 9999,
            CharacterState.WALKING_FORWARD: 9999,
            CharacterState.WALKING_BACKWARD: 9999,
            CharacterState.CROUCHING: 9999,

            # Jump states
            CharacterState.JUMP_STARTUP: 10,
            CharacterState.JUMPING: 60,
            CharacterState.JUMPING_FORWARD: 60,
            CharacterState.JUMPING_BACKWARD: 60,

            # Dash states
            CharacterState.DASH_FORWARD: 20,
            CharacterState.DASH_BACKWARD: 15,

            # Normal attacks (generous safety limits - actual transitions handled by frame data)
            CharacterState.LIGHT_PUNCH: 30,
            CharacterState.MEDIUM_PUNCH: 40,
            CharacterState.HEAVY_PUNCH: 50,
            CharacterState.LIGHT_KICK: 30,
            CharacterState.MEDIUM_KICK: 40,
            CharacterState.HEAVY_KICK: 60,

            # Crouching attacks
            CharacterState.CROUCH_LIGHT_PUNCH: 30,
            CharacterState.CROUCH_MEDIUM_PUNCH: 40,
            CharacterState.CROUCH_HEAVY_PUNCH: 50,
            CharacterState.CROUCH_LIGHT_KICK: 30,
            CharacterState.CROUCH_MEDIUM_KICK: 40,
            CharacterState.CROUCH_HEAVY_KICK: 60,

            # Jumping attacks
            CharacterState.JUMP_LIGHT_PUNCH: 30,
            CharacterState.JUMP_MEDIUM_PUNCH: 30,
            CharacterState.JUMP_HEAVY_PUNCH: 40,
            CharacterState.JUMP_LIGHT_KICK: 30,
            CharacterState.JUMP_MEDIUM_KICK: 30,
            CharacterState.JUMP_HEAVY_KICK: 40,

            # Special moves (generous limits)
            CharacterState.GOHADOKEN: 45,
            CharacterState.GOSHORYUKEN: 60,
            CharacterState.TATSUMAKI: 60,

            # Hit reactions
            CharacterState.HITSTUN_STANDING: 60,
            CharacterState.HITSTUN_CROUCHING: 60,
            CharacterState.HITSTUN_AIRBORNE: 60,
            CharacterState.BLOCKSTUN_HIGH: 60,
            CharacterState.BLOCKSTUN_LOW: 60,
            CharacterState.KNOCKDOWN: 120,
        }

    def _get_non_cancelable_states(self) -> set:
        """Define states that cannot be interrupted/canceled.

        Returns:
            Set of states that must complete before allowing new actions
        """
        return {
            # Can't cancel attacks mid-swing (except with specials via special cancel)
            CharacterState.MEDIUM_PUNCH,
            CharacterState.HEAVY_PUNCH,
            CharacterState.MEDIUM_KICK,
            CharacterState.HEAVY_KICK,
            CharacterState.CROUCH_MEDIUM_PUNCH,
            CharacterState.CROUCH_HEAVY_PUNCH,
            CharacterState.CROUCH_MEDIUM_KICK,
            CharacterState.CROUCH_HEAVY_KICK,

            # Can't cancel jump startup
            CharacterState.JUMP_STARTUP,

            # Can't cancel special moves
            CharacterState.GOHADOKEN,
            CharacterState.GOSHORYUKEN,
            CharacterState.TATSUMAKI,

            # Can't cancel hit reactions
            CharacterState.HITSTUN_STANDING,
            CharacterState.HITSTUN_CROUCHING,
            CharacterState.HITSTUN_AIRBORNE,
            CharacterState.BLOCKSTUN_HIGH,
            CharacterState.BLOCKSTUN_LOW,
            CharacterState.KNOCKDOWN,
        }

    def update(self, opponent: 'Character'):
        """Update character state and physics.

        Args:
            opponent: The opposing character
        """
        self.total_frames += 1

        # Update invincibility status based on current frame
        self._update_invincibility()

        # Handle hit freeze (hitstop) - character freezes in place
        if self.hitfreeze_frames > 0:
            self.hitfreeze_frames -= 1
            # During hit freeze, only update animation, nothing else
            return

        # Decrement hit flash timer
        if self.hitflash_frames > 0:
            self.hitflash_frames -= 1

        self.state_frame += 1

        # STATE SAFETY CHECK: Force state reset if we exceed maximum frames
        # This prevents infinite loops/soft-locks from rapid inputs or bugs
        max_frames = self.max_state_frames.get(self.state, 60)  # Default 60 frames (1 second)
        if self.state_frame > max_frames:
            log_once(log, ("state_timeout", self.state.name), logging.WARNING, "STATE TIMEOUT: %s exceeded %s frames, forcing STANDING", self.state.name, max_frames)
            self._transition_to_state(CharacterState.STANDING)

        # Update facing direction
        self._update_facing(opponent)

        # Handle stun
        if self.hitstun_frames > 0:
            self.hitstun_frames -= 1
            self.can_act = False
            # Recover only on the ground — a launched character stays in its
            # airborne reaction until physics lands it (which transitions us).
            if self.hitstun_frames == 0 and self.is_grounded:
                self.in_hitstun = False
                self._transition_to_state(CharacterState.STANDING)
        elif self.blockstun_frames > 0:
            self.blockstun_frames -= 1
            self.can_act = False
            if self.blockstun_frames == 0:
                self._transition_to_state(CharacterState.STANDING)
        else:
            self.can_act = True

        # Process input and update state machine
        if self.can_act and self.input:
            self._process_input()

        # Update based on current state
        self._update_state()

        # Apply physics
        self._apply_physics()

        # Resolve character collision (prevent walking through each other)
        self._resolve_character_collision(opponent)

        # Keep in bounds
        self._clamp_to_stage()

    def _update_invincibility(self):
        """Update invincibility status based on current state and frame."""
        # Check if current state_frame is in the invincibility frame list
        # Frame list is 1-indexed (frame 1, 2, 3...) but state_frame is 0-indexed
        if self.invincibility_frames and (self.state_frame + 1) in self.invincibility_frames:
            self.is_invincible = True
        else:
            self.is_invincible = False

    def _update_facing(self, opponent: 'Character'):
        """Update which direction the character is facing.

        Args:
            opponent: The opposing character
        """
        # Decrement facing lock timer
        if self.facing_lock_frames > 0:
            self.facing_lock_frames -= 1
            return  # Don't change facing while locked

        # Determine what facing should be
        new_facing = FacingDirection.RIGHT if self.x < opponent.x else FacingDirection.LEFT

        # If facing would change, add a small lock period (crossup protection)
        if new_facing != self.facing:
            self.facing = new_facing
            self.facing_lock_frames = 3  # Lock for 3 frames (5% of a second at 60fps)

    def _process_input(self):
        """Process player input and trigger state transitions."""
        if not self.input:
            return

        # STATE SAFETY: Don't allow input during non-cancelable states
        # This prevents stacking multiple special moves or canceling attacks mid-swing
        if self.state in self.non_cancelable_states:
            # Exception: Light attacks can be canceled (SF3 mechanic)
            if self.state not in [CharacterState.LIGHT_PUNCH, CharacterState.LIGHT_KICK,
                                   CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_LIGHT_KICK]:
                return

        direction = self.input.get_direction()

        # Check for special moves first (highest priority)
        if self._check_special_moves():
            return

        # Check for normal attacks
        if self._check_normal_attacks():
            return

        # Check for movement
        self._check_movement(direction)

    def _check_special_moves(self) -> bool:
        """Check for special move inputs.

        Returns:
            True if a special move was triggered
        """
        if not self.input:
            return False

        # STATE SAFETY: Prevent special move spam
        # Require minimum frames between special moves to prevent infinite loops
        frames_since_last_special = self.total_frames - self.last_special_frame
        if frames_since_last_special < self.special_cooldown_frames:
            return False

        # This will be overridden by character-specific implementations
        # For now, just a placeholder
        return False

    def _check_normal_attacks(self) -> bool:
        """Check for normal attack inputs.

        Returns:
            True if an attack was triggered
        """
        if not self.input:
            return False

        # Standing attacks (also available while walking -- a walking normal is
        # just a standing normal; you can attack out of forward/back movement).
        if self.state in (CharacterState.STANDING,
                          CharacterState.WALKING_FORWARD,
                          CharacterState.WALKING_BACKWARD):
            if self.input.is_button_just_pressed(Button.LIGHT_PUNCH):
                self._transition_to_state(CharacterState.LIGHT_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.MEDIUM_PUNCH):
                self._transition_to_state(CharacterState.MEDIUM_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.HEAVY_PUNCH):
                self._transition_to_state(CharacterState.HEAVY_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.LIGHT_KICK):
                self._transition_to_state(CharacterState.LIGHT_KICK)
                return True
            elif self.input.is_button_just_pressed(Button.MEDIUM_KICK):
                self._transition_to_state(CharacterState.MEDIUM_KICK)
                return True
            elif self.input.is_button_just_pressed(Button.HEAVY_KICK):
                self._transition_to_state(CharacterState.HEAVY_KICK)
                return True

        # Crouching attacks
        elif self.state == CharacterState.CROUCHING:
            if self.input.is_button_just_pressed(Button.LIGHT_PUNCH):
                self._transition_to_state(CharacterState.CROUCH_LIGHT_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.MEDIUM_PUNCH):
                self._transition_to_state(CharacterState.CROUCH_MEDIUM_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.HEAVY_PUNCH):
                self._transition_to_state(CharacterState.CROUCH_HEAVY_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.LIGHT_KICK):
                self._transition_to_state(CharacterState.CROUCH_LIGHT_KICK)
                return True
            elif self.input.is_button_just_pressed(Button.MEDIUM_KICK):
                self._transition_to_state(CharacterState.CROUCH_MEDIUM_KICK)
                return True
            elif self.input.is_button_just_pressed(Button.HEAVY_KICK):
                self._transition_to_state(CharacterState.CROUCH_HEAVY_KICK)
                return True

        # Jumping attacks (while airborne)
        elif self.state in [CharacterState.JUMPING, CharacterState.JUMPING_FORWARD, CharacterState.JUMPING_BACKWARD]:
            if self.input.is_button_just_pressed(Button.LIGHT_PUNCH):
                self._transition_to_state(CharacterState.JUMP_LIGHT_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.MEDIUM_PUNCH):
                self._transition_to_state(CharacterState.JUMP_MEDIUM_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.HEAVY_PUNCH):
                self._transition_to_state(CharacterState.JUMP_HEAVY_PUNCH)
                return True
            elif self.input.is_button_just_pressed(Button.LIGHT_KICK):
                self._transition_to_state(CharacterState.JUMP_LIGHT_KICK)
                return True
            elif self.input.is_button_just_pressed(Button.MEDIUM_KICK):
                self._transition_to_state(CharacterState.JUMP_MEDIUM_KICK)
                return True
            elif self.input.is_button_just_pressed(Button.HEAVY_KICK):
                self._transition_to_state(CharacterState.JUMP_HEAVY_KICK)
                return True

        return False

    def _check_movement(self, direction: InputDirection):
        """Check for movement inputs.

        Args:
            direction: Current input direction
        """
        # Holding back (or down-back) on the ground = guarding. The collision
        # adapter routes an incoming hit to block effects while this is set.
        # (Block direction high/low is derived from posture at block time.)
        self.is_blocking = self.is_grounded and direction in (
            InputDirection.BACK, InputDirection.DOWN_BACK)

        # Check for dashes first (highest priority for movement)
        if self.input.check_double_tap_forward():
            if self.is_grounded and self.state == CharacterState.STANDING:
                self._transition_to_state(CharacterState.DASH_FORWARD)
                return

        if self.input.check_double_tap_back():
            if self.is_grounded and self.state == CharacterState.STANDING:
                self._transition_to_state(CharacterState.DASH_BACKWARD)
                return

        # Jump. Must be jumpable out of walking too: to jump forward/back on a
        # pad you hold the direction first (-> WALKING_*), then press up. Gating
        # jump to STANDING/CROUCHING only made forward/back jumps impossible.
        if direction in [InputDirection.UP, InputDirection.UP_FORWARD, InputDirection.UP_BACK]:
            if self.is_grounded and self.state in [
                CharacterState.STANDING, CharacterState.CROUCHING,
                CharacterState.WALKING_FORWARD, CharacterState.WALKING_BACKWARD,
            ]:
                self.jump_direction = direction  # Store jump direction for animation
                self._transition_to_state(CharacterState.JUMP_STARTUP)
                return

        # Crouch - enter or stay in crouch state
        if direction in [InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.DOWN_BACK]:
            if self.is_grounded:
                if self.state == CharacterState.STANDING:
                    self._transition_to_state(CharacterState.CROUCHING)
                # Stay in crouch if already crouching
                return

        # Walk - allow immediate direction changes for responsive movement
        if direction == InputDirection.FORWARD:
            if self.is_grounded and self.state in [CharacterState.STANDING, CharacterState.WALKING_BACKWARD]:
                self._transition_to_state(CharacterState.WALKING_FORWARD)
                # Immediately set velocity for instant response
                walk_dir = 1 if self.facing == FacingDirection.RIGHT else -1
                self.velocity_x = WALK_SPEED * walk_dir
                return

        if direction == InputDirection.BACK:
            if self.is_grounded and self.state in [CharacterState.STANDING, CharacterState.WALKING_FORWARD]:
                self._transition_to_state(CharacterState.WALKING_BACKWARD)
                # Immediately set velocity for instant response
                walk_dir = -1 if self.facing == FacingDirection.RIGHT else 1
                self.velocity_x = WALK_SPEED * walk_dir
                return

        # Return to standing if neutral (but not during dash states)
        if direction == InputDirection.NEUTRAL:
            if self.state in [CharacterState.WALKING_FORWARD, CharacterState.WALKING_BACKWARD]:
                # Immediately stop movement and return to standing
                self.velocity_x = 0
                self._transition_to_state(CharacterState.STANDING)
            elif self.state == CharacterState.CROUCHING:
                # Only stand up if not holding down
                self._transition_to_state(CharacterState.STANDING)

    def _update_state(self):
        """Update behavior based on current state."""
        if self.state == CharacterState.STANDING:
            self.velocity_x = 0

        elif self.state == CharacterState.WALKING_FORWARD:
            walk_dir = 1 if self.facing == FacingDirection.RIGHT else -1
            self.velocity_x = WALK_SPEED * walk_dir

        elif self.state == CharacterState.WALKING_BACKWARD:
            walk_dir = -1 if self.facing == FacingDirection.RIGHT else 1
            self.velocity_x = WALK_SPEED * walk_dir

        elif self.state == CharacterState.CROUCHING:
            self.velocity_x = 0

        elif self.state == CharacterState.JUMP_STARTUP:
            # Prejump frames (usually 3-4 frames)
            if self.state_frame >= 3:
                self.velocity_y = JUMP_VELOCITY

                # Set horizontal velocity based on jump direction
                if self.jump_direction == InputDirection.UP_FORWARD:
                    # Forward jump
                    jump_h_speed = 4.0
                    self.velocity_x = jump_h_speed if self.is_facing_right() else -jump_h_speed
                elif self.jump_direction == InputDirection.UP_BACK:
                    # Backward jump
                    jump_h_speed = 4.0
                    self.velocity_x = -jump_h_speed if self.is_facing_right() else jump_h_speed
                else:
                    # Neutral jump - no horizontal movement
                    self.velocity_x = 0

                self._transition_to_state(CharacterState.JUMPING)

        elif self.state == CharacterState.JUMPING:
            # Maintain horizontal velocity during jump (no air control for now)
            pass

        elif self.state == CharacterState.DASH_FORWARD:
            # Forward dash - fast forward movement (14 frames total)
            # Akuma's forward dash covers good distance
            dash_speed = 9.0  # pixels per frame
            move_dir = 1 if self.is_facing_right() else -1
            self.velocity_x = dash_speed * move_dir

            # Return to standing after dash animation completes (14 frames)
            if self.state_frame >= 14:
                self._transition_to_state(CharacterState.STANDING)

        elif self.state == CharacterState.DASH_BACKWARD:
            # Backward dash - fast backward movement (9 frames total)
            # Backdash is slightly slower than forward dash
            dash_speed = 7.0  # pixels per frame
            move_dir = -1 if self.is_facing_right() else 1
            self.velocity_x = dash_speed * move_dir

            # Return to standing after dash animation completes (9 frames)
            if self.state_frame >= 9:
                self._transition_to_state(CharacterState.STANDING)

        # Attack states - handle recovery.
        # Placeholder timing until per-move frame data drives this (see the
        # animation-controller consolidation phase). Standing/crouch normals
        # recover to STANDING; crouch normals return to CROUCHING so a held
        # down-input keeps crouching. Without this, crouch/jump attacks linger
        # until the state-safety timeout (the CROUCH_HEAVY_PUNCH spam).
        elif self.state in [CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_PUNCH, CharacterState.HEAVY_PUNCH,
                           CharacterState.LIGHT_KICK, CharacterState.MEDIUM_KICK, CharacterState.HEAVY_KICK,
                           CharacterState.JUMP_LIGHT_PUNCH, CharacterState.JUMP_MEDIUM_PUNCH, CharacterState.JUMP_HEAVY_PUNCH,
                           CharacterState.JUMP_LIGHT_KICK, CharacterState.JUMP_MEDIUM_KICK, CharacterState.JUMP_HEAVY_KICK]:
            if self.state_frame >= 20:
                self._transition_to_state(CharacterState.STANDING)

        elif self.state in [CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_MEDIUM_PUNCH,
                           CharacterState.CROUCH_HEAVY_PUNCH, CharacterState.CROUCH_LIGHT_KICK,
                           CharacterState.CROUCH_MEDIUM_KICK, CharacterState.CROUCH_HEAVY_KICK]:
            self.velocity_x = 0
            if self.state_frame >= 20:
                self._transition_to_state(CharacterState.CROUCHING)

    def _apply_physics(self):
        """Apply gravity and update position."""
        # Apply gravity
        if not self.is_grounded:
            self.velocity_y += GRAVITY

        # Update position
        self.x += self.velocity_x
        self.y += self.velocity_y

        # Ground collision
        if self.y >= STAGE_FLOOR:
            self.y = STAGE_FLOOR
            self.velocity_y = 0
            if not self.is_grounded:
                self.is_grounded = True
                self._transition_to_state(CharacterState.STANDING)
        else:
            self.is_grounded = False

    def _clamp_to_stage(self):
        """Keep character within stage boundaries."""
        if self.x < STAGE_LEFT_BOUND:
            self.x = STAGE_LEFT_BOUND
            self.velocity_x = 0
        elif self.x > STAGE_RIGHT_BOUND:
            self.x = STAGE_RIGHT_BOUND
            self.velocity_x = 0

    def _resolve_character_collision(self, opponent: 'Character'):
        """Prevent characters from overlapping.

        When characters collide, push them apart based on who is moving.
        This prevents players from walking through each other.

        Args:
            opponent: The opposing character
        """
        # Pushboxes are ground-only: an airborne character passes over/through the
        # other so you can jump over opponents (and cross up). Only separate when
        # BOTH are grounded.
        if not self.is_grounded or not opponent.is_grounded:
            return

        # Calculate distance between characters
        distance = abs(self.x - opponent.x)
        min_distance = (self.hitbox_width + opponent.hitbox_width) / 2

        # Check if characters are overlapping
        if distance < min_distance:
            overlap = min_distance - distance

            # Determine push behavior based on movement
            self_moving_forward = False
            opponent_moving_forward = False

            # Check if self is moving toward opponent
            if abs(self.velocity_x) > 0.1:
                if (self.x < opponent.x and self.velocity_x > 0) or \
                   (self.x > opponent.x and self.velocity_x < 0):
                    self_moving_forward = True

            # Check if opponent is moving toward self
            if abs(opponent.velocity_x) > 0.1:
                if (opponent.x < self.x and opponent.velocity_x > 0) or \
                   (opponent.x > self.x and opponent.velocity_x < 0):
                    opponent_moving_forward = True

            if self_moving_forward and opponent_moving_forward:
                # Both moving toward each other - split the push 50/50
                push_amount = overlap / 2
                if self.x < opponent.x:
                    self.x -= push_amount
                    opponent.x += push_amount
                else:
                    self.x += push_amount
                    opponent.x -= push_amount

                # Stop forward momentum when colliding
                self.velocity_x = 0
                opponent.velocity_x = 0

            elif self_moving_forward:
                # Only self is moving forward - push opponent back
                if self.x < opponent.x:
                    opponent.x += overlap
                else:
                    opponent.x -= overlap
                # Self stops at collision point
                self.velocity_x = 0

            elif opponent_moving_forward:
                # Only opponent is moving forward - push self back
                if opponent.x < self.x:
                    self.x += overlap
                else:
                    self.x -= overlap
                # Opponent stops at collision point
                opponent.velocity_x = 0

            else:
                # Neither moving forward (e.g., both backing up into each other)
                # Just separate them equally
                push_amount = overlap / 2
                if self.x < opponent.x:
                    self.x -= push_amount
                    opponent.x += push_amount
                else:
                    self.x += push_amount
                    opponent.x -= push_amount

    def _transition_to_state(self, new_state: CharacterState):
        """Transition to a new state.

        Args:
            new_state: The state to transition to
        """
        if new_state != self.state:
            self.previous_state = self.state
            self.state = new_state
            self.state_frame = 0
            self.animation_frame = 0

            # State entry logic
            if new_state == CharacterState.JUMP_STARTUP:
                self.velocity_x = 0

    def take_damage(self, damage: int, hitstun: int, hit_effect: HitEffect = HitEffect.NORMAL):
        """Take damage from an attack and enter the matching reaction state."""
        self.health = max(0, self.health - damage)
        apply_reaction(self, hit_effect, hitstun)

    def render(self, screen: pygame.Surface):
        """Render the character.

        Args:
            screen: Pygame surface to render to
        """
        # Check if character has a sprite
        self._rendered_fallback = not (hasattr(self, 'sprite') and self.sprite is not None)
        if hasattr(self, 'sprite') and self.sprite is not None:
            # Flip sprite based on facing direction
            sprite_to_draw = self.sprite
            if self.facing == FacingDirection.LEFT:
                sprite_to_draw = pygame.transform.flip(self.sprite, True, False)

            # Center sprite at character position
            sprite_rect = sprite_to_draw.get_rect()
            sprite_rect.centerx = int(self.x)
            # Use per-animation ground offset if available, otherwise default
            default_offset = getattr(self, 'ground_offset', 0)
            if hasattr(self, 'animation_ground_offsets') and hasattr(self, 'animation_controller'):
                anim_name = getattr(self.animation_controller, 'get_current_animation_name', lambda: None)()
                ground_offset = self.animation_ground_offsets.get(anim_name, default_offset) if anim_name else default_offset
            else:
                ground_offset = default_offset
            sprite_rect.bottom = int(self.y) + ground_offset

            # Draw sprite
            screen.blit(sprite_to_draw, sprite_rect)

            # Draw state text (debug) above sprite
            font = get_debug_font()
            state_text = font.render(self.state.name, True, (255, 255, 255))
            screen.blit(state_text, (int(self.x - 30), sprite_rect.top - 20))
        else:
            # Fallback to rectangle placeholder
            rect = pygame.Rect(
                int(self.x - self.width // 2),
                int(self.y - self.height),
                self.width,
                self.height
            )
            pygame.draw.rect(screen, self.color, rect)
            pygame.draw.rect(screen, self.outline_color, rect, 2)

            # Draw facing indicator (small triangle)
            indicator_x = int(self.x + (20 if self.facing == FacingDirection.RIGHT else -20))
            indicator_y = int(self.y - self.height // 2)
            pygame.draw.circle(screen, (255, 255, 0), (indicator_x, indicator_y), 5)

            # Draw state text (debug)
            font = get_debug_font()
            state_text = font.render(self.state.name, True, (255, 255, 255))
            screen.blit(state_text, (int(self.x - 30), int(self.y - self.height - 20)))

    def get_rect(self) -> pygame.Rect:
        """Get character's collision rectangle.

        Returns:
            Pygame Rect representing character bounds
        """
        return pygame.Rect(
            int(self.x - self.hitbox_width // 2),
            int(self.y - self.hitbox_height),
            self.hitbox_width,
            self.hitbox_height
        )

    def screen_feet_y(self) -> float:
        """On-screen Y of the feet line, where the sprite bottom AND the debug
        boxes both anchor. Uses ``feet_offset`` when the character defines one
        (Akuma), else the base ``ground_offset``. Single source for the vertical
        anchor so boxes line up with the scaled sprite."""
        return self.y + getattr(self, "feet_offset", self.ground_offset)

    def is_facing_right(self) -> bool:
        """Check if character is facing right.

        Returns:
            True if facing right
        """
        return self.facing == FacingDirection.RIGHT

    def is_attacking(self) -> bool:
        """True while in any attacking state (normals, crouch/jump attacks, specials).

        Used for render z-order so an extended limb isn't hidden behind the
        opponent's body.
        """
        return self.state in _ATTACK_STATES

    def get_debug_state(self) -> Dict:
        """Full numerical state for the debug overlay and snapshot dumps.

        Subclasses extend this (e.g. Akuma adds the live animation/sprite info).
        """
        return {
            "player": self.player_number,
            "state": self.state.name,
            "state_frame": self.state_frame,
            "pos": [round(self.x, 1), round(self.y, 1)],
            "vel": [round(self.velocity_x, 2), round(self.velocity_y, 2)],
            "facing": "R" if self.is_facing_right() else "L",
            "health": self.health,
            "max_health": self.max_health,
            "hitstun": self.hitstun_frames,
            "blockstun": self.blockstun_frames,
            "hitfreeze": self.hitfreeze_frames,
            "grounded": self.is_grounded,
            "can_act": self.can_act,
            "invincible": self.is_invincible,
            "rendering_fallback": self._rendered_fallback,
        }

    def reset(self, x: float, y: float):
        """Reset to a clean round-start state at the given position.

        Every transient combat value must be cleared here so a new round
        is provably a clean slate. Subclasses override to clear their own
        state (projectiles, pending moves) and must call super().reset().

        Args:
            x: Round-start x position
            y: Round-start y position
        """
        self.x = x
        self.y = y
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.facing = FacingDirection.RIGHT if self.player_number == 1 else FacingDirection.LEFT
        self.facing_lock_frames = 0

        self.health = self.max_health
        self.super_meter = 0
        self.stun_meter = 0
        self.combo_counter = 0
        self.hitstun_frames = 0
        self.blockstun_frames = 0
        self.hitfreeze_frames = 0
        self.hitflash_frames = 0

        self.is_grounded = True
        self.can_act = True
        self.in_hitstun = False
        self.in_blockstun = False
        self.is_blocking = False
        self.is_invincible = False
        self.invincibility_frames = []
        self.jump_direction = InputDirection.NEUTRAL

        self.state = CharacterState.STANDING
        self.previous_state = CharacterState.STANDING
        self.state_frame = 0
        self.animation_frame = 0
