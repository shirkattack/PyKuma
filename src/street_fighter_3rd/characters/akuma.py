"""Akuma character implementation."""

import logging
import pygame
from street_fighter_3rd.util.logging_config import get_logger, log_once
from street_fighter_3rd.characters.character import (
    Character, get_debug_font, apply_reaction, SUPER_FREEZE_FRAMES)
from street_fighter_3rd.data.enums import (
    CharacterState, Button, FacingDirection, InputDirection, HitEffect)
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

# Animations authored on an oversized canvas with the body's horizontal travel
# baked into the frames (Akuma's forward/back somersault jumps). These are
# anchored by their opaque-pixel body center, not the canvas center, so physics
# owns the horizontal travel and the body doesn't lurch. See Akuma.render().
_BODY_ANCHORED_ANIMS = frozenset({"jump_forward", "jump_backward"})

# Ashura Senku (teleport). Strike-invulnerable reposition; no hitbox/damage.
# Distances/durations are provisional (game-feel), tagged pending ROM calibration.
TELEPORT_SPEED = 12.0          # px/frame during the travel window
TELEPORT_TRAVEL_FRAMES = 15    # -> ~180px of displacement
TELEPORT_TOTAL_FRAMES = 40     # state duration incl. recovery

# Demon Flip (Hyakkishu): an arcing forward jump toward the opponent. The flip
# itself has no hitbox -- the dive/throw/palm followups do (deferred until their
# hitbox data exists). Arc values are provisional game-feel, flagged.
DEMON_FLIP_RISE = -8.0         # initial vertical velocity (up)
DEMON_FLIP_FORWARD = 6.5       # forward velocity toward the opponent

# Super Arts (provisional damage/reach, flagged for ROM/community backfill).
SA2_DAMAGE = 180               # Messatsu Gou Shoryu (rising launcher)
SA2_REACH = 130
SA3_DAMAGE = 220               # Kongou Kokuretsu Zan (heavy ground hit)
SA3_REACH = 150
RAGING_DEMON_DAMAGE = 500      # Shun Goku Satsu (near-fatal command grab)
RAGING_DEMON_REACH = 84        # close unblockable grab range


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
        CharacterState.ASHURA_SENKU: "teleport",
        CharacterState.DEMON_FLIP: "hyakkishuu",
        CharacterState.SUPER_ART_1: "sa1",
        CharacterState.SUPER_ART_2: "sa2",
        CharacterState.SUPER_ART_3: "sa3",
        CharacterState.RAGING_DEMON: "raging_demon",
        # command actions
        CharacterState.OVERHEAD: "overhead",
        CharacterState.TAUNT: "taunt",
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
        # (STAGE_FLOOR), in world-buffer px. The sprite bottom sits here so the
        # feet land on the stage ground line; the view camera then zooms the whole
        # buffer. Nudge this if the character sits too high/low on the stage.
        self.feet_offset = 86

        # Cache of opaque-pixel padding-below-feet per cached sprite surface,
        # keyed by id(); get_bounding_rect scans pixels and would otherwise run
        # twice per frame per character.
        self._feet_pad_cache = {}
        # Same idea for horizontal body-center anchoring (somersault jump clips).
        self._body_center_cache = {}

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
        self._teleport_dir = 0          # +1/-1 travel direction during Ashura Senku
        self._teleport_frames_left = 0  # remaining travel frames
        self._super_freeze_pending = False  # apply super-freeze to opponent next update
        self._super_hit_done = False        # SA2/SA3 single-hit guard
        self.pending_projectile_strength = None  # Store strength for spawning
        self.pending_projectile_air = False       # was the fireball started airborne?
    
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
            # throws
            ("throw_forward",      "akuma-throw-forward", 17, 2, False),
            ("throw_back",         "akuma-throw-back",    14, 2, False),
            ("throw_miss",         "akuma-throw-miss",     6, 2, False),
            # command actions
            ("overhead",           "akuma-overhead",      23, 2, False),  # UOH (MP+MK)
            ("taunt",              "akuma-taunt",         39, 2, False),  # personal action (HP+HK)
            # round-flow poses (driven by the round manager, not the state machine)
            ("teleport",           "akuma-teleport",      63, 1, False),  # Ashura Senku
            ("hyakkishuu",         "akuma-hyakkishuu",    54, 1, False),  # Demon Flip
            # super arts
            ("sa1",                "akuma-sa1-air",       66, 1, False),  # Messatsu Gou Hadou
            ("sa2",                "akuma-sa2",           40, 1, False),  # Messatsu Gou Shoryu
            ("sa3",                "akuma-sa3",           92, 1, False),  # Kongou Kokuretsu Zan
            ("raging_demon",       "akuma-flame",         30, 2, False),  # Shun Goku Satsu
            ("intro1",             "akuma-intro1",        23, 3, False),  # round start
            ("win1",               "akuma-win1",          28, 3, False),  # round won
            ("win2",               "akuma-win2",          38, 3, False),
            ("win3",               "akuma-win3",           9, 3, False),
            ("timeout",            "akuma-timeout",        6, 4, False),  # time over
            ("chipdeath",          "akuma-chipdeath",     17, 3, False),  # KO by chip
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
        self.pending_projectile_air = False
        self.animation_controller.play_animation("stance", force_restart=True)

    def _check_special_moves(self) -> bool:
        """Check for Akuma's special moves.

        Returns:
            True if a special move was triggered
        """
        if not self.input:
            return False

        # Super Arts -- need a full meter, and are checked BEFORE the normal
        # specials because the doubled motions (236236/214214) contain the single
        # ones. Without meter they fall through (236236P just yields a Gohadoken).
        # SA1 = 236236P, SA2 = 236236K, SA3 = 214214P.
        if self.has_full_super():
            # Raging Demon (Shun Goku Satsu): LP, LP, F, LK, HP. Discrete button
            # sequence, checked first.
            if self._check_raging_demon():
                self._execute_raging_demon()
                return True
            P = (Button.LIGHT_PUNCH, Button.MEDIUM_PUNCH, Button.HEAVY_PUNCH)
            K = (Button.LIGHT_KICK, Button.MEDIUM_KICK, Button.HEAVY_KICK)
            if any(self.input.check_motion_input("QCF2", b) for b in P):
                self._execute_super(1)
                return True
            if any(self.input.check_motion_input("QCF2", b) for b in K):
                self._execute_super(2)
                return True
            if any(self.input.check_motion_input("QCB2", b) for b in P):
                self._execute_super(3)
                return True

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

        # Teleport (Ashura Senku): 623/421 + PPP or KKK. Checked BEFORE Goshoryuken
        # (also 623+P) so the 3-button version wins; single-punch falls through to DP.
        if self.input.check_motion_with_punches("DP") or self.input.check_motion_with_kicks("DP"):
            self._execute_teleport(forward=True)
            return True
        if self.input.check_motion_with_punches("RDP") or self.input.check_motion_with_kicks("RDP"):
            self._execute_teleport(forward=False)
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

        # Demon Flip / Hyakkishu (236K - Quarter Circle Forward + Kick)
        if (self.input.check_motion_input("QCF", Button.LIGHT_KICK)
                or self.input.check_motion_input("QCF", Button.MEDIUM_KICK)
                or self.input.check_motion_input("QCF", Button.HEAVY_KICK)):
            self._execute_demon_flip()
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
        # Airborne -> Akuma's air fireball (Zanku Hadou): down-forward trajectory.
        self.pending_projectile_air = not self.is_grounded

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

    def _execute_teleport(self, forward: bool):
        """Ashura Senku: a strike-invulnerable reposition forward (623) or back
        (421). No hitbox/damage; movement + invuln handled in _update_state."""
        log.debug("ASHURA SENKU (%s)", "forward" if forward else "back")
        self.last_special_frame = self.total_frames
        face = 1 if self.is_facing_right() else -1
        self._teleport_dir = face if forward else -face
        self._teleport_frames_left = TELEPORT_TRAVEL_FRAMES
        self.velocity_y = 0
        self._transition_to_state(CharacterState.ASHURA_SENKU)

    def _execute_demon_flip(self):
        """Hyakkishu: an arcing forward jump toward the opponent. The flip has no
        hitbox; physics handles the arc and the landing recovers to STANDING.
        (Dive/throw/palm followups are deferred until their hitbox data exists.)"""
        log.debug("HYAKKISHU (demon flip)")
        self.last_special_frame = self.total_frames
        face = 1 if self.is_facing_right() else -1
        self.velocity_y = DEMON_FLIP_RISE
        self.velocity_x = DEMON_FLIP_FORWARD * face
        self.is_grounded = False
        self._transition_to_state(CharacterState.DEMON_FLIP)

    def _spawn_gohadoken(self, strength: str, air: bool):
        """Create a Gou Hadouken projectile at hand height (shared by the normal
        fireball and the SA1 super-fireball burst)."""
        speed_map = {"light": 7.0, "medium": 9.0, "heavy": 11.0}
        speed = speed_map.get(strength, 7.0)
        fwd = 1 if self.facing == FacingDirection.RIGHT else -1
        feet_y = self.y + self.feet_offset
        spawn_y = feet_y - 70
        if air:
            velocity_y = speed * 0.6
            spawn_x = self.x + 30 * fwd
        else:
            velocity_y = 0.0
            spawn_x = self.x + 40 * fwd
        self.projectiles.append(
            Gohadoken(spawn_x, spawn_y, speed * fwd, self.facing, strength,
                      velocity_y=velocity_y, ground_y=feet_y))

    def _check_raging_demon(self) -> bool:
        """Detect the LP, LP, F, LK, HP sequence ending with HP this frame.

        Scans the recent input buffer for the four lead-in steps in order; the HP
        press is the trigger. Lenient on spacing (within a ~40-frame window)."""
        if Button.HEAVY_PUNCH not in self.input.buttons_pressed_this_frame:
            return False
        steps = (
            lambda s: Button.LIGHT_PUNCH in s.buttons_just_pressed,
            lambda s: Button.LIGHT_PUNCH in s.buttons_just_pressed,
            lambda s: s.direction == InputDirection.FORWARD,
            lambda s: Button.LIGHT_KICK in s.buttons_just_pressed,
        )
        idx = 0
        for s in list(self.input.input_buffer)[-40:]:
            if idx < len(steps) and steps[idx](s):
                idx += 1
        return idx == len(steps)

    def _execute_raging_demon(self):
        """Shun Goku Satsu: consume the bar, super-freeze, and (in _resolve_super)
        land an unblockable close grab for near-fatal damage."""
        log.debug("SHUN GOKU SATSU!")
        self.super_meter = 0
        self.last_special_frame = self.total_frames
        self._super_freeze_pending = True
        self._super_hit_done = False
        self.velocity_x = 0
        self._transition_to_state(CharacterState.RAGING_DEMON)

    def _execute_super(self, sa: int):
        """Activate a Super Art: consume the full meter, super-freeze the
        opponent, and play the SA. SA1 spawns a super-fireball burst (in
        _update_state); SA2/SA3 land a big direct hit (in _resolve_super)."""
        log.debug("SUPER ART %s!", sa)
        self.super_meter = 0
        self.last_special_frame = self.total_frames
        self._super_freeze_pending = True
        self._super_hit_done = False
        self.velocity_x = 0
        self._transition_to_state(
            {1: CharacterState.SUPER_ART_1, 2: CharacterState.SUPER_ART_2,
             3: CharacterState.SUPER_ART_3}[sa])

    def _resolve_super(self, opponent: 'Character'):
        """Per-frame super effects that need the opponent: the one-time
        super-freeze and the SA2/SA3 direct hits on their active frame."""
        if self._super_freeze_pending:
            opponent.hitfreeze_frames = max(opponent.hitfreeze_frames, SUPER_FREEZE_FRAMES)
            self._super_freeze_pending = False
        if self._super_hit_done:
            return
        if self.state == CharacterState.SUPER_ART_2 and self.state_frame >= 6:
            self._super_hit_done = True
            self._apply_super_hit(opponent, SA2_DAMAGE, HitEffect.JUGGLE, SA2_REACH)
        elif self.state == CharacterState.SUPER_ART_3 and self.state_frame >= 12:
            self._super_hit_done = True
            self._apply_super_hit(opponent, SA3_DAMAGE, HitEffect.KNOCKDOWN, SA3_REACH)
        elif self.state == CharacterState.RAGING_DEMON and self.state_frame >= 4:
            self._super_hit_done = True
            self._apply_super_hit(opponent, RAGING_DEMON_DAMAGE, HitEffect.KNOCKDOWN,
                                  RAGING_DEMON_REACH)

    def _apply_super_hit(self, opponent, damage, effect, reach):
        if abs(self.x - opponent.x) <= reach and not getattr(opponent, "is_invincible", False):
            opponent.health = max(0, opponent.health - damage)
            face = 1 if self.is_facing_right() else -1
            apply_reaction(opponent, effect, 30, knockback_vx=4.0 * face)

    def update(self, opponent: 'Character'):
        """Update Akuma with animation system.

        Args:
            opponent: The opposing character
        """
        # Raging Demon completes from its lead-in jabs (LP,LP,...). If one of those
        # jabs connected, its hitstop would make the base update() early-return and
        # eat the HP that finishes the sequence -- so detect+fire it here, clearing
        # that hitstop, before deferring to the base update. (Non-hitstop activation
        # still goes through _check_special_moves normally.)
        if (self.hitfreeze_frames > 0 and self.is_grounded
                and self.has_full_super() and self._check_raging_demon()):
            self.hitfreeze_frames = 0
            self._execute_raging_demon()

        # Call parent update FIRST (this updates facing direction)
        super().update(opponent)

        # Super Art per-frame effects (freeze + SA2/SA3/Raging-Demon hit) need
        # the opponent.
        if self.state in (CharacterState.SUPER_ART_1, CharacterState.SUPER_ART_2,
                          CharacterState.SUPER_ART_3, CharacterState.RAGING_DEMON):
            self._resolve_super(opponent)

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
        elif new_state == CharacterState.THROWING:
            # Forward/back grab clip; if it whiffs, _on_throw_whiff swaps in the
            # miss animation the same frame (the grab resolves in update()).
            play("throw_back" if self.throw_is_back else "throw_forward", force_restart=True)
        else:
            name = self._STATE_ANIM.get(new_state)
            if name:
                play(name, force_restart=True)

    def _on_throw_whiff(self):
        """A throw missed: play the whiff recovery clip."""
        self.animation_controller.play_animation("throw_miss", force_restart=True)

    def get_debug_state(self) -> dict:
        """Extend the base debug state with live animation/sprite info."""
        state = super().get_debug_state()
        state["name"] = self.name
        state["anim"] = self.animation_controller.get_current_frame_info()
        # On-screen feet line (constant by design — see _render).
        state["feet_y"] = round(self.y + self.feet_offset, 1)
        state["projectiles"] = len(self.projectiles)
        return state

    def _body_center_offset(self, sprite: pygame.Surface) -> int:
        """Signed px from the canvas center to the body's opaque-pixel center.

        Used to anchor baked-travel somersault clips by their body instead of
        their (oversized) canvas. Cached per sprite surface; 0 for an empty frame.
        Measured on the unflipped sprite; the caller negates it when flipped.
        """
        key = id(sprite)
        off = self._body_center_cache.get(key)
        if off is None:
            bbox = sprite.get_bounding_rect()
            off = (bbox.centerx - sprite.get_width() / 2) if bbox.width else 0
            self._body_center_cache[key] = off
        return off

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
            self._render_projectiles(screen)
            return

        # Align the character's ACTUAL feet (bottom of opaque pixels) to the
        # floor line, independent of each frame's transparent padding. Padding is
        # measured on the unflipped sprite (vertical extent is flip-invariant).
        pad_below_feet = self._padding_below_feet(sprite)

        # The somersault jump clips (akuma-jumpf/jumpb) are authored on an
        # oversized canvas with the body's horizontal travel BAKED into the frames
        # (the body sweeps ~70px across a ~220px canvas). Re-centering that canvas
        # on self.x every frame made the body lurch ~70px toward the opponent on
        # the first airborne frame, then drift back -- the "weird forward movement
        # before moving the right way". For those clips, anchor the body's actual
        # opaque-pixel center to self.x so physics (velocity_x) owns the horizontal
        # travel and the pose is lurch-free. Other clips keep canvas-center so
        # intentional offsets (an extended punch arm) are preserved.
        body_anchored = self.animation_controller.current_name in _BODY_ANCHORED_ANIMS
        body_off = self._body_center_offset(sprite) if body_anchored else 0

        # Folder sprites face RIGHT, so flip when facing LEFT.
        if self.facing == FacingDirection.LEFT:
            sprite = pygame.transform.flip(sprite, True, False)
            body_off = -body_off  # the body center mirrors with the sprite

        sprite_rect = sprite.get_rect()
        sprite_rect.centerx = int(self.x - body_off)
        # Feet line shared with the debug box overlay (screen_feet_y); pad seats
        # the opaque pixels on the line regardless of transparent canvas.
        sprite_rect.bottom = int(self.screen_feet_y()) + pad_below_feet

        if self.hitflash_frames > 0:
            flash_sprite = sprite.copy()
            flash_sprite.fill((30, 30, 30), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(flash_sprite, sprite_rect)
        else:
            screen.blit(sprite, sprite_rect)

        # Fireballs etc. render on top, in the same world buffer as the character.
        # (This MUST live in render() -- it used to sit only in the never-called
        # _render_fallback_rectangle, so projectiles spawned but never drew.)
        self._render_projectiles(screen)

    def _render_projectiles(self, screen: pygame.Surface):
        for projectile in self.projectiles:
            projectile.render(screen)

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

    def _update_state(self):
        """Update Akuma-specific state behavior."""
        # Call parent update first
        super()._update_state()

        # Ashura Senku teleport: strike-invulnerable; glide the travel distance,
        # then recover. No hitbox.
        if self.state == CharacterState.ASHURA_SENKU:
            self.is_invincible = True
            if self._teleport_frames_left > 0:
                self.velocity_x = TELEPORT_SPEED * self._teleport_dir
                self._teleport_frames_left -= 1
            else:
                self.velocity_x = 0
            if self.state_frame >= TELEPORT_TOTAL_FRAMES:
                self._transition_to_state(CharacterState.STANDING)
            return

        # Akuma-specific state handling
        if self.state == CharacterState.GOHADOKEN:
            # Spawn the fireball on the active frame.
            if self.state_frame == 14 and self.pending_projectile_strength:
                self._spawn_gohadoken(self.pending_projectile_strength, self.pending_projectile_air)
                self.pending_projectile_strength = None
                self.pending_projectile_air = False

        elif self.state == CharacterState.SUPER_ART_1:
            # Messatsu Gou Hadou: a burst of three super fireballs (multi-hit).
            if self.state_frame in (10, 16, 22):
                self._spawn_gohadoken("heavy", air=False)

        # GOHADOKEN/GOSHORYUKEN/TATSUMAKI now recover when their animation
        # completes (see update()); the per-state safety timeout still guards
        # against any soft-lock. No hardcoded state_frame returns here.
