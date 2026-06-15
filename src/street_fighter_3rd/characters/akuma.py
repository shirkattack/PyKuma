"""Akuma character implementation."""

import logging
import pygame
from street_fighter_3rd.util.logging_config import get_logger, log_once
from street_fighter_3rd.characters.character import Character, get_debug_font
from street_fighter_3rd.data.enums import CharacterState, Button, FacingDirection, InputDirection
from street_fighter_3rd.systems.animation import (
    SpriteManager,
    AnimationController,
    create_folder_animation,
)
from street_fighter_3rd.core.projectile import Gohadoken
from street_fighter_3rd.data.hitbox_repository import HitboxRepository

log = get_logger(__name__)

# Extracted per-move sprite folders (one PNG sequence per move), under the
# canonical asset tree (assets/characters/akuma/animations). Single source of
# truth for Akuma's animations. Resolved CWD-independently by the loader.
ANIM_BASE = "assets/characters/akuma/animations"

# States that must NOT auto-return to STANDING when their (non-looping) animation
# finishes — recovery is governed by physics/input/stun timers, not animation
# completion (movement states + hit/block reactions).
_HOLD_STATES = frozenset({
    CharacterState.STANDING, CharacterState.CROUCHING,
    CharacterState.WALKING_FORWARD, CharacterState.WALKING_BACKWARD,
    CharacterState.DASH_FORWARD, CharacterState.DASH_BACKWARD,
    CharacterState.JUMP_STARTUP, CharacterState.JUMPING,
    CharacterState.JUMPING_FORWARD, CharacterState.JUMPING_BACKWARD,
    CharacterState.HITSTUN_STANDING, CharacterState.HITSTUN_CROUCHING,
    CharacterState.HITSTUN_AIRBORNE, CharacterState.KNOCKDOWN,
    CharacterState.BLOCKSTUN_HIGH, CharacterState.BLOCKSTUN_LOW,
})


class Akuma(Character):
    """Akuma (Gouki) - The Master of the Fist."""

    # state -> animation name for one-shot states (movement states handled inline)
    _STATE_ANIM = {
        CharacterState.LIGHT_PUNCH: "light_punch",
        CharacterState.MEDIUM_PUNCH: "medium_punch",
        CharacterState.HEAVY_PUNCH: "heavy_punch",
        CharacterState.LIGHT_KICK: "light_kick",
        CharacterState.MEDIUM_KICK: "medium_kick",
        CharacterState.HEAVY_KICK: "heavy_kick",
        CharacterState.CROUCH_LIGHT_PUNCH: "crouch_light_punch",
        CharacterState.CROUCH_MEDIUM_PUNCH: "crouch_medium_punch",
        CharacterState.CROUCH_HEAVY_PUNCH: "crouch_heavy_punch",
        CharacterState.CROUCH_LIGHT_KICK: "crouch_light_kick",
        CharacterState.CROUCH_MEDIUM_KICK: "crouch_medium_kick",
        CharacterState.CROUCH_HEAVY_KICK: "crouch_heavy_kick",
        CharacterState.JUMP_LIGHT_PUNCH: "jump_light_punch",
        CharacterState.JUMP_MEDIUM_PUNCH: "jump_medium_punch",
        CharacterState.JUMP_HEAVY_PUNCH: "jump_heavy_punch",
        CharacterState.JUMP_LIGHT_KICK: "jump_light_kick",
        CharacterState.JUMP_MEDIUM_KICK: "jump_medium_kick",
        CharacterState.JUMP_HEAVY_KICK: "jump_heavy_kick",
        CharacterState.DASH_FORWARD: "dash_forward",
        CharacterState.DASH_BACKWARD: "dash_backward",
        CharacterState.GOHADOKEN: "gohadoken",
        CharacterState.GOSHORYUKEN: "goshoryuken",
        CharacterState.TATSUMAKI: "tatsumaki",
        # hit / block reactions
        CharacterState.HITSTUN_STANDING: "hit_medium",
        CharacterState.HITSTUN_CROUCHING: "crouch_hit",
        CharacterState.HITSTUN_AIRBORNE: "launch_spin",
        CharacterState.KNOCKDOWN: "knockdown",
        CharacterState.BLOCKSTUN_HIGH: "block_high",
        CharacterState.BLOCKSTUN_LOW: "block_crouch",
    }

    def __init__(self, x: float, y: float, player_number: int):
        """Initialize Akuma.

        Args:
            x: Starting x position
            y: Starting y position
            player_number: 1 or 2
        """
        super().__init__(x, y, player_number)

        # Akuma-specific stats (from SF3). Vitality is on the Baston scale that
        # the community damage values are authored against (sf3_authentic_frame_data
        # .yaml character_info.health=1050); a medium punch (115) is ~11%, not 80%.
        # The absolute pool is tunable; the damage:health RATIO is what matters.
        self.max_health = 1050
        self.health = self.max_health
        self.walk_speed = 3.2  # Slightly faster than average

        # Character-vs-character separation uses the ROM pushbox width (50), not
        # the generic hitbox_width, so spacing/no-cross matches the game.
        _pb = HitboxRepository.instance().get_pushbox()
        if _pb is not None:
            self.pushbox_width = _pb.width

        # Single animation path: folder-based sprites through the AnimationController.
        # sprite_directory is only used by SpriteManager's numbered loader (unused
        # by Akuma now); folder animations resolve their own paths.
        self.sprite_manager = SpriteManager("assets/characters/akuma/sprite_sheets")
        self.animation_controller = AnimationController(self.sprite_manager)

        # Set ground offset for consistent positioning
        self.ground_offset = 190  # From YAML configuration (base-class fallback)

        # feet_offset positions the character's actual feet relative to self.y
        # (STAGE_FLOOR). Tuned so standing height matches the previous look while
        # every animation now plants its feet on the same line. This is the one
        # knob to nudge if the whole character sits too high/low on the stage.
        self.feet_offset = 86

        # Cache of opaque-pixel padding-below-feet per cached sprite surface,
        # keyed by id(); get_bounding_rect scans pixels and would otherwise run
        # twice per frame per character.
        self._feet_pad_cache = {}

        # Per-animation ground offsets for sprites with different layouts
        self.animation_ground_offsets = {
            # Dash animations use different sprite range (19xxx) with different layout
            "dash_forward": 190,   # Set to default
            "dash_backward": 190,  # Set to default
            # Crouch might need adjustment if it's still shifting
            "crouch_hold": 190,    # Keep same as default for now
            "crouch_transition": 190,
        }

        # Register all folder animations and start idle
        self._setup_animations()
        self.animation_controller.play_animation("stance")

        # Visual (placeholder - will use sprites later)
        self.color = (128, 0, 128) if player_number == 1 else (75, 0, 130)  # Purple/dark purple
        self.name = "Akuma"

        # Projectile management
        self.projectiles = []  # List of active projectiles
        self.pending_projectile_strength = None  # Store strength for spawning
    
    def _setup_animations(self):
        """Register every animation as a folder clip (single source of truth).

        Looping clips (stance/walk/crouch idle) never self-complete; one-shot
        clips (attacks/specials/reactions) drive their own recovery via the
        completion check in update(). frame_duration values are tuned per move
        and are the knob for move speed. Folder frame counts are fixed by the
        extracted assets.
        """
        f = create_folder_animation
        base = ANIM_BASE
        specs = [
            # name,                folder,              frames, dur, loop
            ("stance",             "akuma-stance",      10,  6, True),
            ("walk_forward",       "akuma-walkf",       11,  3, True),
            ("walk_backward",      "akuma-walkb",       11,  3, True),
            ("crouch_hold",        "akuma-crouch",       5,  4, True),
            ("jump_up",            "akuma-jump",        34,  2, False),
            ("dash_forward",       "akuma-dashf",       14,  1, False),
            ("dash_backward",      "akuma-dashb",        9,  1, False),
            # standing normals
            ("light_punch",        "akuma-wp",           6,  2, False),
            ("medium_punch",       "akuma-mp",           8,  2, False),
            ("heavy_punch",        "akuma-hp",          14,  2, False),
            ("light_kick",         "akuma-wk",           7,  2, False),
            ("medium_kick",        "akuma-mk",          11,  2, False),
            ("heavy_kick",         "akuma-hk",          15,  2, False),
            # crouch normals
            ("crouch_light_punch", "akuma-crouch-wp",    7,  2, False),
            ("crouch_medium_punch","akuma-crouch-mp",    7,  2, False),
            ("crouch_heavy_punch", "akuma-crouch-hp",   11,  2, False),
            ("crouch_light_kick",  "akuma-crouch-wk",    7,  2, False),
            ("crouch_medium_kick", "akuma-crouch-mk",   11,  2, False),
            ("crouch_heavy_kick",  "akuma-crouch-hk",   13,  2, False),
            # jump normals
            ("jump_light_punch",   "akuma-jump-wp",      6,  2, False),
            ("jump_medium_punch",  "akuma-jump-mp",      8,  2, False),
            ("jump_heavy_punch",   "akuma-jump-hp",      8,  2, False),
            ("jump_light_kick",    "akuma-jump-wk",     10,  1, False),
            ("jump_medium_kick",   "akuma-jump-mk",      6,  2, False),
            ("jump_heavy_kick",    "akuma-jump-hk",      6,  2, False),
            # specials
            ("gohadoken",          "akuma-fireball",    14,  2, False),
            ("goshoryuken",        "akuma-dp",          20,  2, False),
            ("tatsumaki",          "akuma-hurricane",   30,  2, False),
        ]
        for name, folder, frames, dur, loop in specs:
            self.animation_controller.add_animation(
                name, f(f"{base}/{folder}", frames, frame_duration=dur, loop=loop))

        # Hit/block reactions. Recovery is driven by hitstun/blockstun timers,
        # not animation completion, so airborne/block clips loop while held.
        reactions = [
            # name,          folder,             frames, dur, loop, start
            ("hit_medium",   "akuma-stand-hit",  10,  2, False, 8),   # stand flinch (mid of stand-hit)
            ("crouch_hit",   "akuma-crouch-hit", 11,  2, False, 0),
            ("knockdown",    "akuma-slam",       25,  2, False, 0),
            ("launch_spin",  "akuma-twist",      27,  2, True,  0),   # juggle spin (loops while airborne)
            ("crumble",      "akuma-shocked",     3,  6, False, 0),
            ("block_high",   "akuma-block-high",  6,  3, True,  0),
            ("block_crouch", "akuma-block-crouch",5,  3, True,  0),
        ]
        for name, folder, frames, dur, loop, start in reactions:
            self.animation_controller.add_animation(
                name, f(f"{base}/{folder}", frames, frame_duration=dur, loop=loop, start_index=start))

        # Forward/back jumps use Akuma's flip/somersault clips (distinct from the
        # neutral jump). frame_duration=1 so the ~37-frame flip spans the airborne
        # window; JUMPING is a hold state so the last pose holds until landing.
        # (Provisional duration; retuned to the ROM airborne frame count in Phase 5.)
        self.animation_controller.add_animation(
            "jump_forward", f(f"{base}/akuma-jumpf", 37, frame_duration=1, loop=False))
        self.animation_controller.add_animation(
            "jump_backward", f(f"{base}/akuma-jumpb", 38, frame_duration=1, loop=False))

    def reset(self, x: float, y: float):
        """Reset Akuma to a clean round-start state.

        Args:
            x: Round-start x position
            y: Round-start y position
        """
        super().reset(x, y)

        self.projectiles.clear()
        self.pending_projectile_strength = None
        self.animation_controller.play_animation("stance", force_restart=True)

    def _check_special_moves(self) -> bool:
        """Check for Akuma's special moves.

        Returns:
            True if a special move was triggered
        """
        if not self.input:
            return False

        # Gohadoken (236P - Quarter Circle Forward + Punch)
        if self.input.check_motion_input("QCF", Button.LIGHT_PUNCH):
            self._execute_gohadoken(Button.LIGHT_PUNCH)
            return True
        elif self.input.check_motion_input("QCF", Button.MEDIUM_PUNCH):
            self._execute_gohadoken(Button.MEDIUM_PUNCH)
            return True
        elif self.input.check_motion_input("QCF", Button.HEAVY_PUNCH):
            self._execute_gohadoken(Button.HEAVY_PUNCH)
            return True

        # Goshoryuken (623P - Dragon Punch + Punch)
        if self.input.check_motion_input("DP", Button.LIGHT_PUNCH):
            self._execute_goshoryuken(Button.LIGHT_PUNCH)
            return True
        elif self.input.check_motion_input("DP", Button.MEDIUM_PUNCH):
            self._execute_goshoryuken(Button.MEDIUM_PUNCH)
            return True
        elif self.input.check_motion_input("DP", Button.HEAVY_PUNCH):
            self._execute_goshoryuken(Button.HEAVY_PUNCH)
            return True

        # Tatsumaki Zankukyaku (214K - Quarter Circle Back + Kick)
        if self.input.check_motion_input("QCB", Button.LIGHT_KICK):
            self._execute_tatsumaki(Button.LIGHT_KICK)
            return True
        elif self.input.check_motion_input("QCB", Button.MEDIUM_KICK):
            self._execute_tatsumaki(Button.MEDIUM_KICK)
            return True
        elif self.input.check_motion_input("QCB", Button.HEAVY_KICK):
            self._execute_tatsumaki(Button.HEAVY_KICK)
            return True

        return False

    def _execute_gohadoken(self, strength: Button):
        """Execute Gohadoken (fireball).

        Args:
            strength: Punch button used (determines speed/damage)
        """
        log.debug("GOHADOKEN! (%s)", strength.name)

        # Mark special move executed (for cooldown tracking)
        self.last_special_frame = self.total_frames

        # Map button to strength string
        strength_map = {
            Button.LIGHT_PUNCH: "light",
            Button.MEDIUM_PUNCH: "medium",
            Button.HEAVY_PUNCH: "heavy"
        }
        self.pending_projectile_strength = strength_map.get(strength, "light")

        self._transition_to_state(CharacterState.GOHADOKEN)

    def _execute_goshoryuken(self, strength: Button):
        """Execute Goshoryuken (dragon punch).

        Args:
            strength: Punch button used (determines height/damage)
        """
        log.debug("GOSHORYUKEN! (%s)", strength.name)

        # Mark special move executed (for cooldown tracking)
        self.last_special_frame = self.total_frames

        # Set invincibility frames based on strength
        if strength == Button.LIGHT_PUNCH:
            self.invincibility_frames = [1, 2, 3, 4, 5, 6, 7, 8]  # 8 frames
        elif strength == Button.MEDIUM_PUNCH:
            self.invincibility_frames = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # 10 frames
        else:  # HEAVY_PUNCH
            self.invincibility_frames = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # 12 frames

        # Launch character upward (DP rises into the air)
        self.velocity_y = -18.0  # Strong upward velocity
        self.is_grounded = False

        # Store which strength was used for hitbox generation
        self.dp_strength = strength

        self._transition_to_state(CharacterState.GOSHORYUKEN)

    def _execute_tatsumaki(self, strength: Button):
        """Execute Tatsumaki Zankukyaku (hurricane kick).

        Args:
            strength: Kick button used (determines distance/hits)
        """
        log.debug("TATSUMAKI! (%s)", strength.name)

        # Mark special move executed (for cooldown tracking)
        self.last_special_frame = self.total_frames

        # Set horizontal speed based on strength
        if strength == Button.LIGHT_KICK:
            horizontal_speed = 5.0
            self.tatsu_hits = 3
        elif strength == Button.MEDIUM_KICK:
            horizontal_speed = 6.5
            self.tatsu_hits = 4
        else:  # HEAVY_KICK
            horizontal_speed = 8.0
            self.tatsu_hits = 5

        # Apply horizontal velocity (moves in facing direction)
        direction = 1 if self.facing == FacingDirection.RIGHT else -1
        self.velocity_x = horizontal_speed * direction

        # If in air, this is air tatsumaki (slightly different)
        if not self.is_grounded:
            log.debug("  (AIR VERSION)")
            horizontal_speed *= 0.8  # Air version moves slower
            self.velocity_x = horizontal_speed * direction

        # Store which strength was used for hitbox generation
        self.tatsu_strength = strength
        self.tatsu_hit_count = 0  # Track how many hits have connected

        self._transition_to_state(CharacterState.TATSUMAKI)

    def update(self, opponent: 'Character'):
        """Update Akuma with animation system.

        Args:
            opponent: The opposing character
        """
        # Call parent update FIRST (this updates facing direction)
        super().update(opponent)

        # Advance the animation, then recover one-shot moves on completion.
        self.animation_controller.update()
        if self.animation_controller.is_animation_complete() and self.state not in _HOLD_STATES:
            # A one-shot move (attack/special/reaction) finished. If we finished
            # mid-air, resume the airborne pose and let physics land us. On the
            # ground, recover to the posture the player is still holding: crouch
            # if down is held (so a crouch normal doesn't briefly stand the
            # character up between presses), otherwise stand.
            held = self.input.get_direction() if self.input else InputDirection.NEUTRAL
            if not self.is_grounded:
                self._transition_to_state(CharacterState.JUMPING)
            elif held in (InputDirection.DOWN, InputDirection.DOWN_FORWARD,
                          InputDirection.DOWN_BACK):
                self._transition_to_state(CharacterState.CROUCHING)
            else:
                self._transition_to_state(CharacterState.STANDING)

        # Update projectiles
        for projectile in self.projectiles:
            projectile.update()

        # Remove inactive projectiles
        self.projectiles = [p for p in self.projectiles if p.active]

    def _transition_to_state(self, new_state: CharacterState):
        """Transition to a new state and play appropriate animation.

        Args:
            new_state: The state to transition to
        """
        # Call parent transition
        super()._transition_to_state(new_state)

        # Play the animation for this state. Looping idles play without restart
        # (so re-entering STANDING doesn't stutter); one-shots force-restart.
        play = self.animation_controller.play_animation
        if new_state == CharacterState.STANDING:
            play("stance")
        elif new_state == CharacterState.WALKING_FORWARD:
            play("walk_forward")
        elif new_state == CharacterState.WALKING_BACKWARD:
            play("walk_backward")
        elif new_state == CharacterState.CROUCHING:
            play("crouch_hold")
        elif new_state == CharacterState.JUMPING:
            # jump_direction is relative to facing (handled by the input system)
            if self.jump_direction == InputDirection.UP_FORWARD:
                play("jump_forward", force_restart=True)
            elif self.jump_direction == InputDirection.UP_BACK:
                play("jump_backward", force_restart=True)
            else:
                play("jump_up", force_restart=True)
        else:
            name = self._STATE_ANIM.get(new_state)
            if name:
                play(name, force_restart=True)

    def get_debug_state(self) -> dict:
        """Extend the base debug state with live animation/sprite info."""
        state = super().get_debug_state()
        state["name"] = self.name
        state["anim"] = self.animation_controller.get_current_frame_info()
        # On-screen feet line (constant by design — see _render).
        state["feet_y"] = round(self.y + self.feet_offset, 1)
        state["projectiles"] = len(self.projectiles)
        return state

    def _padding_below_feet(self, sprite: pygame.Surface) -> int:
        """Transparent pixels between the character's feet and the canvas bottom.

        Cached per sprite surface (get_bounding_rect scans every pixel).
        Returns 0 for a fully transparent frame.
        """
        key = id(sprite)
        pad = self._feet_pad_cache.get(key)
        if pad is None:
            bbox = sprite.get_bounding_rect()
            pad = sprite.get_height() - bbox.bottom if bbox.height else 0
            self._feet_pad_cache[key] = pad
        return pad

    def render(self, screen: pygame.Surface):
        """Render Akuma's current animation frame, feet aligned to the floor."""
        sprite = self.animation_controller.get_current_sprite()
        self._rendered_fallback = sprite is None
        if sprite is None:
            super().render(screen)  # rectangle placeholder
            return

        # Align the character's ACTUAL feet (bottom of opaque pixels) to the
        # floor line, independent of each frame's transparent padding. Padding is
        # measured on the unflipped sprite (vertical extent is flip-invariant).
        pad_below_feet = self._padding_below_feet(sprite)

        # Folder sprites face RIGHT, so flip when facing LEFT.
        if self.facing == FacingDirection.LEFT:
            sprite = pygame.transform.flip(sprite, True, False)

        sprite_rect = sprite.get_rect()
        sprite_rect.centerx = int(self.x)
        # Feet line shared with the debug box overlay (screen_feet_y); pad seats
        # the opaque pixels on the line regardless of transparent canvas.
        sprite_rect.bottom = int(self.screen_feet_y()) + pad_below_feet

        if self.hitflash_frames > 0:
            flash_sprite = sprite.copy()
            flash_sprite.fill((30, 30, 30), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(flash_sprite, sprite_rect)
        else:
            screen.blit(sprite, sprite_rect)

    def _render_fallback_rectangle(self, screen: pygame.Surface):
        """Render fallback rectangle when sprites fail."""
        # Draw character as colored rectangle (fallback)
        rect = pygame.Rect(int(self.x - 30), int(self.y - 120), 60, 120)
        pygame.draw.rect(screen, self.color, rect)
        
        # Draw facing direction indicator
        from street_fighter_3rd.data.enums import FacingDirection
        eye_x = rect.centerx + (10 if self.facing == FacingDirection.RIGHT else -10)
        pygame.draw.circle(screen, (255, 255, 255), (eye_x, rect.y + 20), 5)
        
        # Draw state text
        font = get_debug_font()
        facing_str = "RIGHT" if self.facing == FacingDirection.RIGHT else "LEFT"
        state_text = font.render(f"{self.state.name} [{facing_str}]", True, (255, 255, 255))
        screen.blit(state_text, (int(self.x - 30), rect.top - 20))

        # Render projectiles
        for projectile in self.projectiles:
            projectile.render(screen)

    def _update_state(self):
        """Update Akuma-specific state behavior."""
        # Call parent update first
        super()._update_state()

        # Akuma-specific state handling
        if self.state == CharacterState.GOHADOKEN:
            # Fireball animation - 24 frames total
            # Spawn projectile on frame 14 (when animation reaches active frames)
            if self.state_frame == 14 and self.pending_projectile_strength:
                # Spawn the fireball projectile
                # Speed based on strength: light=7, medium=9, heavy=11 pixels/frame
                speed_map = {"light": 7.0, "medium": 9.0, "heavy": 11.0}
                speed = speed_map.get(self.pending_projectile_strength, 7.0)

                # Adjust velocity based on facing direction
                velocity_x = speed if self.facing == FacingDirection.RIGHT else -speed

                # Spawn at character position (slightly in front, at chest height)
                spawn_x = self.x + (40 if self.facing == FacingDirection.RIGHT else -40)
                spawn_y = self.y - 60  # Chest height

                projectile = Gohadoken(spawn_x, spawn_y, velocity_x, self.facing, self.pending_projectile_strength)
                self.projectiles.append(projectile)
                self.pending_projectile_strength = None  # Clear after spawning

        # GOHADOKEN/GOSHORYUKEN/TATSUMAKI now recover when their animation
        # completes (see update()); the per-state safety timeout still guards
        # against any soft-lock. No hardcoded state_frame returns here.
