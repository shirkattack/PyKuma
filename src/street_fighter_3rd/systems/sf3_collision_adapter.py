"""
SF3 Collision System Adapter

This adapter bridges the authentic SF3CollisionSystem with our current Character class,
allowing us to use the authentic SF3 collision mechanics without rewriting the entire
character system.
"""

import logging
import pygame
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from street_fighter_3rd.util.logging_config import get_logger, log_once

log = get_logger(__name__)

from .sf3_collision import SF3CollisionSystem, SF3CollisionEvent, SF3CollisionResult
from .sf3_core import SF3PlayerWork, SF3WorkStructure
from .sf3_hitboxes import (
    SF3HitboxManager,
    SF3HitboxType,
    SF3Hitbox,
    SF3HitboxFrame,
    SF3HitboxAnimation,
    SF3HitLevel,
)
from .sf3_parry import SF3ParrySystem, SF3ParryResult, SF3ParryType
from .sf3_combo_system import SF3ComboSystem
from .hitbox_data import HitboxData
from ..data.enums import CharacterState, HitType, HitEffect
from ..data.constants import HITSTUN_BASE, BLOCKSTUN_MULTIPLIER, DEBUG_MODE
from ..data.akuma_hitboxes import get_akuma_hitboxes, get_akuma_hurtboxes, get_move_frame_data
from ..data.hitbox_repository import HitboxRepository
from ..characters.character import apply_reaction
from .vfx import HitSparkType

# Hit spark strength by the attacking state.
_LIGHT_STATES = {CharacterState.LIGHT_PUNCH, CharacterState.LIGHT_KICK,
                 CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_LIGHT_KICK,
                 CharacterState.JUMP_LIGHT_PUNCH, CharacterState.JUMP_LIGHT_KICK}
_MEDIUM_STATES = {CharacterState.MEDIUM_PUNCH, CharacterState.MEDIUM_KICK,
                  CharacterState.CROUCH_MEDIUM_PUNCH, CharacterState.CROUCH_MEDIUM_KICK,
                  CharacterState.JUMP_MEDIUM_PUNCH, CharacterState.JUMP_MEDIUM_KICK}
_HEAVY_STATES = {CharacterState.HEAVY_PUNCH, CharacterState.HEAVY_KICK,
                 CharacterState.CROUCH_HEAVY_PUNCH, CharacterState.CROUCH_HEAVY_KICK,
                 CharacterState.JUMP_HEAVY_PUNCH, CharacterState.JUMP_HEAVY_KICK}
_SPECIAL_STATES = {CharacterState.GOHADOKEN, CharacterState.GOSHORYUKEN, CharacterState.TATSUMAKI}

# Damage-scaled hitstop (deterministic, integer)
HITSTOP_BASE, HITSTOP_PER, HITSTOP_MAX = 6, 4, 16
SHAKE_INTENSITY = 4


def _knockback_for(hit_effect: HitEffect, damage: int) -> float:
    """Provisional knockback magnitude (px/frame, decays via hitstun friction).

    Used only when the move carries no explicit pushback. Magnitudes are a sane
    starting model scaled lightly by damage; calibrate against a ROM/decomp golden
    (see docs/DIAGNOSTIC_FRAMEWORK.md). Knockdown-class hits push harder.
    """
    base = 3.0
    if hit_effect in (HitEffect.KNOCKDOWN, HitEffect.CRUMPLE,
                      HitEffect.GROUND_BOUNCE, HitEffect.WALL_BOUNCE):
        base = 5.0
    return base + min(2.0, damage / 80.0)


def _spark_for_state(state) -> str:
    """Hit-spark type for the attacking state (heavier = bigger spark)."""
    if state in _SPECIAL_STATES:
        return HitSparkType.SPECIAL
    if state in _HEAVY_STATES:
        return HitSparkType.HEAVY
    if state in _MEDIUM_STATES:
        return HitSparkType.MEDIUM
    return HitSparkType.LIGHT


@dataclass
class CollisionResult:
    """Result of collision processing"""
    hit_occurred: bool = False
    mutual_hit: bool = False
    throw_occurred: bool = False
    attacker_id: int = 0
    defender_id: int = 0
    damage: int = 0
    hitstun: int = 0


class SF3CollisionAdapter:
    """
    Adapter that makes SF3CollisionSystem compatible with our current game loop.
    
    This allows us to use authentic SF3 collision mechanics while keeping our
    existing Character class interface.
    """
    
    def __init__(self):
        self.sf3_system = SF3CollisionSystem()
        self.sf3_parry_system = SF3ParrySystem()
        self.sf3_combo_system = SF3ComboSystem()
        self.frame_counter = 0

        # Debug rendering (compatible with old CollisionSystem)
        self.debug_hitboxes: List[pygame.Rect] = []
        self.debug_hurtboxes: List[pygame.Rect] = []

        # Persistent player work structures and hitbox managers, keyed by
        # player_number. Updated in place every frame instead of being
        # reallocated per collision check.
        self.player_works: Dict[int, SF3PlayerWork] = {}
        self.hitbox_managers: Dict[int, SF3HitboxManager] = {}
        for player_id in (1, 2):
            work = SF3PlayerWork()
            work.work.player_number = player_id
            self.player_works[player_id] = work
            self.hitbox_managers[player_id] = SF3HitboxManager(f"player_{player_id}")

        # Results from last collision check
        self.last_results: List[CollisionResult] = []

    def tick(self, *characters):
        """Advance the SF3 core by exactly one game frame.

        Must be called once per game frame, before any check_attack_collision
        calls that frame. Frame advancement used to happen inside
        check_attack_collision, which runs twice per frame (P1->P2, P2->P1) and
        made every frame-windowed mechanic inside the SF3 core half as long as
        specified.

        Pass the live characters so combos can be expired deterministically when
        their defender recovers from hitstun (see below).
        """
        self.frame_counter += 1
        self.sf3_system.update_frame(self.frame_counter)

        # End any active combo whose defender has recovered from hitstun. A combo
        # is a hitstun chain, so it ends the frame the defender leaves hitstun --
        # this is what stops mashed jabs (recovery gaps between them) from racking
        # up a fake multi-hit combo. Deterministic; replaces the old wall-clock
        # timeout in the combo system.
        if characters:
            in_hitstun_by_id = {
                getattr(c, "player_number", i + 1): bool(
                    getattr(c, "in_hitstun", False)
                    or getattr(c, "hitstun_frames", 0) > 0
                )
                for i, c in enumerate(characters)
            }
            self.sf3_combo_system.update(in_hitstun_by_id)

    def update_parry_inputs(self, character, input_state: Dict[str, bool]):
        """Update parry input tracking for a character.

        Must be called once per game frame per player: it both registers new
        parry attempts and counts down the active parry window.
        """
        player_id = getattr(character, 'player_number', 1)
        self.sf3_parry_system.update_parry_inputs(self.player_works[player_id], input_state)

    def check_attack_collision(self, attacker, defender, vfx_manager=None) -> bool:
        """
        Main collision check interface - compatible with old CollisionSystem.

        This method:
        1. Syncs Character objects into the persistent SF3 data structures
        2. Runs authentic SF3 collision detection
        3. Applies results back to Character objects
        4. Maintains compatibility with existing VFX system

        Frame advancement happens in tick(), not here.
        """
        att_id = getattr(attacker, 'player_number', 1)
        def_id = getattr(defender, 'player_number', 2)

        # Sync characters into persistent SF3 structures
        att_work = self.player_works[att_id]
        def_work = self.player_works[def_id]
        self._sync_sf3_work(att_work, attacker)
        self._sync_sf3_work(def_work, defender)

        # Rebuild current-frame hitboxes in the persistent managers
        att_hitbox_mgr = self.hitbox_managers[att_id]
        def_hitbox_mgr = self.hitbox_managers[def_id]
        self._sync_hitbox_manager(att_hitbox_mgr, attacker)
        self._sync_hitbox_manager(def_hitbox_mgr, defender)

        # Enable throw checking if either player is attempting a throw
        self.sf3_system.enable_throw_checking(
            self._is_throwing(attacker) or self._is_throwing(defender)
        )

        # Run SF3 collision detection
        self.sf3_system.check_collision_between_players(
            att_work, def_work, att_hitbox_mgr, def_hitbox_mgr
        )

        # TODO: Integrate full SF3 hit_check_main_process
        # Currently using direct damage application from hit_status
        hit_occurred = False
        if self.sf3_system.hit_queue_input > 0:
            # (Combo expiry is handled deterministically in tick(), driven by the
            # defender's hitstun state -- not here, and not on a wall clock.)

            # Apply results back to characters directly from hit_status
            hit_occurred = self._apply_collision_results(attacker, defender, vfx_manager)

            # Clear the hit queue for next frame
            self.sf3_system.hit_queue_input = 0

        return hit_occurred
    
    def _sync_sf3_work(self, work: SF3PlayerWork, character):
        """Update a persistent SF3PlayerWork in place from our Character object"""
        # Basic positioning - MUST set work.work.position for SF3 collision system
        work.work.position.x = float(character.x)
        work.work.position.y = float(character.y)
        work.work.position.z = 0.0

        # Also set velocity in work structure
        work.velocity_x = int(character.velocity_x) if hasattr(character, 'velocity_x') else 0
        work.velocity_y = int(character.velocity_y) if hasattr(character, 'velocity_y') else 0

        # Set facing direction in work structure
        work.work.face = 1 if character.is_facing_right() else -1

        # Feet offset for the debug overlay's scaled-box anchoring (view-only).
        work.feet_offset = float(getattr(character, "feet_offset", 0))

        # Player identification (legacy fields, kept for compatibility)
        work.player_id = work.work.player_number
        work.facing_right = character.is_facing_right()

        # State mapping
        work.current_state = self._map_character_state(character.state)
        work.previous_state = work.current_state  # Simplified for now
        
        # Frame data
        work.animation_frame = character.animation_frame if hasattr(character, 'animation_frame') else 0
        work.state_timer = character.state_frame if hasattr(character, 'state_frame') else 0
        
        # Combat status
        work.health = character.health
        work.meter = character.meter if hasattr(character, 'meter') else 0
        work.hitstun_timer = character.hitstun_frames if hasattr(character, 'hitstun_frames') else 0
        work.blockstun_timer = character.blockstun_frames if hasattr(character, 'blockstun_frames') else 0
        work.hitfreeze_timer = character.hitfreeze_frames if hasattr(character, 'hitfreeze_frames') else 0
        
        # Flags
        work.is_attacking = character.state in [
            CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_PUNCH, 
            CharacterState.HEAVY_PUNCH, CharacterState.LIGHT_KICK,
            CharacterState.MEDIUM_KICK, CharacterState.HEAVY_KICK
        ]
        work.is_blocking = character.state in [CharacterState.BLOCKING_HIGH, CharacterState.BLOCKING_LOW]
        work.is_crouching = character.state in [CharacterState.CROUCHING, CharacterState.BLOCKING_LOW]

    def _sync_hitbox_manager(self, manager: SF3HitboxManager, character):
        """Rebuild a persistent SF3HitboxManager's current frame from the character"""
        # Get current frame number (1-indexed for frame data)
        frame_number = (character.state_frame if hasattr(character, 'state_frame') else 0) + 1

        # Try to get hitboxes from akuma_hitboxes.py
        akuma_attack_hitboxes = get_akuma_hitboxes(character.state, frame_number)
        akuma_hurtboxes = get_akuma_hurtboxes(character.state, frame_number)

        # Attack-box provenance: geometry is ROM-verified, but if the move's
        # NAME is only inferred, surface that as the box status so the debug
        # viewer can flag it (PENDING/INFERRED). Hurtboxes are always verified.
        repo_move = HitboxRepository.instance().get_move_by_state(character.state.name)
        attack_status = "verified"
        if repo_move is not None and repo_move.name_status == "inferred":
            attack_status = "inferred"

        # Create a frame with the hitboxes
        sf3_frame = SF3HitboxFrame(frame_number=frame_number)

        # Add attack hitboxes (offensive boxes)
        if akuma_attack_hitboxes:
            if DEBUG_MODE:
                log.debug("Character %s state=%s, frame=%s, has %s attack hitbox(es)", character.name if hasattr(character, 'name') else '?', character.state.name, frame_number, len(akuma_attack_hitboxes))
            for hitbox_data in akuma_attack_hitboxes:
                # Map HitType to SF3HitLevel
                hit_level_map = {
                    HitType.HIGH: SF3HitLevel.HIGH,
                    HitType.MID: SF3HitLevel.MID,
                    HitType.LOW: SF3HitLevel.LOW,
                    HitType.OVERHEAD: SF3HitLevel.HIGH,
                }
                hit_level = hit_level_map.get(hitbox_data.hit_type, SF3HitLevel.MID)

                sf3_hitbox = SF3Hitbox(
                    offset_x=float(hitbox_data.offset_x),
                    offset_y=float(hitbox_data.offset_y),
                    width=float(hitbox_data.width),
                    height=float(hitbox_data.height),
                    damage=hitbox_data.damage,
                    hitstun=hitbox_data.hitstun,
                    blockstun=hitbox_data.blockstun,
                    hit_level=hit_level,
                    status=attack_status,
                    anchor="edge",  # attack offset_x = forward-positive near edge
                )
                sf3_frame.add_hitbox(SF3HitboxType.ATTACK, sf3_hitbox)

        # Add hurtboxes (vulnerable areas - these are BODY boxes in SF3)
        if akuma_hurtboxes:
            for hurtbox_data in akuma_hurtboxes:
                sf3_hurtbox = SF3Hitbox(
                    offset_x=float(hurtbox_data.offset_x),
                    offset_y=float(hurtbox_data.offset_y),
                    width=float(hurtbox_data.width),
                    height=float(hurtbox_data.height),
                    damage=0,  # Hurtboxes don't deal damage
                    hitstun=0,
                    blockstun=0,
                    status="verified",
                    anchor="center",  # hurtbox offset_x = center of the box
                )
                sf3_frame.add_hitbox(SF3HitboxType.BODY, sf3_hurtbox)

        # Set the current frame in the manager
        # Create a temporary animation name based on the state
        anim_name = f"state_{character.state.value}" if hasattr(character.state, 'value') else "unknown"
        manager.current_animation = anim_name
        manager.current_frame = frame_number

        # Replace the manager's animations with just the current frame
        animation = SF3HitboxAnimation(animation_name=anim_name, total_frames=100)
        animation.add_frame(frame_number, sf3_frame)
        manager.animations.clear()
        manager.animations[anim_name] = animation
    
    def _get_character_hitboxes(self, character) -> List[Tuple[HitboxData, pygame.Rect]]:
        """Get hitboxes from character using frame data"""
        hitboxes = []

        # Get current frame number (1-indexed for frame data)
        frame_number = (character.state_frame if hasattr(character, 'state_frame') else 0) + 1

        # Try to get hitboxes from akuma_hitboxes.py
        akuma_hitboxes = get_akuma_hitboxes(character.state, frame_number)
        if akuma_hitboxes:
            for hitbox_frame in akuma_hitboxes:
                # Convert HitboxFrame to HitboxData and pygame.Rect
                hitbox_data = HitboxData(
                    x=hitbox_frame.offset_x,
                    y=hitbox_frame.offset_y,
                    width=hitbox_frame.width,
                    height=hitbox_frame.height,
                    damage=hitbox_frame.damage,
                    hitstun=hitbox_frame.hitstun,
                    hit_type=hitbox_frame.hit_type
                )

                # Create rectangle in world coordinates
                offset_x = hitbox_frame.offset_x
                offset_y = hitbox_frame.offset_y

                # Apply facing direction
                if character.is_facing_right():
                    rect = pygame.Rect(
                        character.x + offset_x,
                        character.y + offset_y,
                        hitbox_frame.width,
                        hitbox_frame.height
                    )
                else:
                    rect = pygame.Rect(
                        character.x - offset_x - hitbox_frame.width,
                        character.y + offset_y,
                        hitbox_frame.width,
                        hitbox_frame.height
                    )

                hitboxes.append((hitbox_data, rect))

            return hitboxes

        # No ROM-verified frame data for this state/frame. Never fabricate
        # boxes -- return empty and note it once.
        log_once(
            log, ("no_attack_hitboxes", getattr(character.state, "name", character.state)),
            logging.INFO,
            "No frame-data attack hitboxes for state %s; returning none.",
            getattr(character.state, "name", character.state),
        )
        return hitboxes

    def _get_character_hurtboxes(self, character) -> List[pygame.Rect]:
        """Get hurtboxes from character using frame data"""
        hurtboxes = []

        # Try to get hurtboxes from akuma_hitboxes.py (base + per-frame v_hb)
        frame_number = (character.state_frame if hasattr(character, 'state_frame') else 0) + 1
        akuma_hurtboxes = get_akuma_hurtboxes(character.state, frame_number)
        if akuma_hurtboxes:
            for hurtbox_frame in akuma_hurtboxes:
                # Create rectangle in world coordinates
                offset_x = hurtbox_frame.offset_x
                offset_y = hurtbox_frame.offset_y

                # Hurtboxes are centered on character (offset_x is from center)
                rect = pygame.Rect(
                    character.x + offset_x - hurtbox_frame.width // 2,
                    character.y + offset_y,
                    hurtbox_frame.width,
                    hurtbox_frame.height
                )
                hurtboxes.append(rect)

            return hurtboxes

        # Fallback hurtboxes if no data available
        if character.state == CharacterState.CROUCHING:
            # Smaller hurtbox when crouching
            hurtbox = pygame.Rect(character.x - 30, character.y - 60, 60, 60)
        else:
            # Standing hurtbox
            hurtbox = pygame.Rect(character.x - 30, character.y - 120, 60, 120)

        hurtboxes.append(hurtbox)
        return hurtboxes
    
    def _map_character_state(self, state: CharacterState) -> int:
        """Map our CharacterState to SF3 state values"""
        # Simplified mapping - could be more sophisticated
        state_map = {
            CharacterState.STANDING: 0,
            CharacterState.WALKING_FORWARD: 1,
            CharacterState.WALKING_BACKWARD: 2,
            CharacterState.CROUCHING: 3,
            CharacterState.JUMPING: 4,
            CharacterState.LIGHT_PUNCH: 100,
            CharacterState.MEDIUM_PUNCH: 101,
            CharacterState.HEAVY_PUNCH: 102,
            CharacterState.LIGHT_KICK: 103,
            CharacterState.MEDIUM_KICK: 104,
            CharacterState.HEAVY_KICK: 105,
            CharacterState.BLOCKING_HIGH: 200,
            CharacterState.BLOCKING_LOW: 201,
            CharacterState.HITSTUN_STANDING: 300,
            CharacterState.HITSTUN_CROUCHING: 301,
            CharacterState.HITSTUN_AIRBORNE: 302,
            CharacterState.BLOCKSTUN_HIGH: 310,
            CharacterState.BLOCKSTUN_LOW: 311,
        }
        return state_map.get(state, 0)
    
    def _is_throwing(self, character) -> bool:
        """Check if character is attempting a throw"""
        # For now, no throw states defined - could add later
        return False
    
    def _apply_collision_results(self, attacker, defender, vfx_manager) -> bool:
        """Apply SF3 collision results back to our Character objects.

        Each queued hit carries its own attacker/defender ids, so we apply it to
        the REAL attacker/defender (resolved by player_number), not whichever pair
        this call happened to be invoked with. This is what stops an attacker from
        eating its own hit and makes trades attribute correctly.
        """
        hit_occurred = False
        by_id = {getattr(attacker, "player_number", 1): attacker,
                 getattr(defender, "player_number", 2): defender}

        for i in range(self.sf3_system.hit_queue_input):
            hit_status = self.sf3_system.hit_status[i]
            real_att = by_id.get(hit_status.attacker_id, attacker)
            real_def = by_id.get(hit_status.defender_id, defender)

            if hit_status.result_flags & SF3CollisionResult.HIT_CONFIRMED:
                self._apply_hit_to_character(real_att, real_def, hit_status, vfx_manager)
                hit_occurred = True

            elif hit_status.result_flags & SF3CollisionResult.CATCH_CONFIRMED:
                self._apply_throw_to_character(real_att, real_def, hit_status, vfx_manager)
                hit_occurred = True
        
        # Handle mutual hits
        if self.sf3_system.aiuchi_flag:
            # TODO: Implement mutual hit (aiuchi) effects
            # Both characters should take damage/hitstun
            pass

        return hit_occurred
    
    def _apply_hit_to_character(self, attacker, defender, hit_status, vfx_manager):
        """Apply hit effects to defender character with parry checking"""
        from ..data.enums import CharacterState

        # One connect per attack: an active hitbox must not re-hit every frame.
        if getattr(attacker, "attack_connected", False):
            return

        attacker_id = getattr(attacker, 'player_number', 1)
        defender_id = getattr(defender, 'player_number', 2)

        # Create SF3Hitbox for parry system
        # TODO: carry the real hit level through SF3HitStatus; MID is parryable
        # by both high and low parry rules' high path, which matches most normals.
        attack_box = SF3Hitbox(
            offset_x=0, offset_y=0,
            width=10, height=10,
            hit_level=SF3HitLevel.MID,
            damage=hit_status.damage,
            hitstun=hit_status.hitstun
        )

        # Defense check: parry first (highest priority), then guard, then hit.
        att_work = self.player_works[attacker_id]
        def_work = self.player_works[defender_id]
        if defender.is_grounded:
            defense = self.sf3_parry_system.defense_ground(att_work, def_work, attack_box, "mid")
        else:
            defense = self.sf3_parry_system.defense_sky(att_work, def_work, attack_box, "mid")

        if defense == SF3ParryResult.PARRY_SUCCESS:
            self._apply_parry_effects(attacker, defender, vfx_manager)
            return

        # The parry system's guard check is still simplified; honor the
        # defender's own guard signal (holding back, see _check_movement).
        if defense == SF3ParryResult.GUARD_SUCCESS or getattr(defender, 'is_blocking', False):
            self._apply_block_effects(attacker, defender, hit_status, vfx_manager)
            return

        # Register hit with combo system and get scaled damage. Capture whether
        # the defender is STILL reacting to a prior hit BEFORE we apply the new
        # reaction below -- that's what tells the combo system this hit links into
        # an ongoing combo vs. starts a fresh one (mashed jabs on a recovered
        # defender must not rack up a fake combo count).
        defender_in_hitstun = bool(
            getattr(defender, "in_hitstun", False)
            or getattr(defender, "hitstun_frames", 0) > 0
        )
        scaled_damage = self.sf3_combo_system.register_hit(
            attacker_id, defender_id, hit_status.damage, "normal",
            defender_in_hitstun=defender_in_hitstun,
        )

        # Apply clamped damage and the reaction the attacking move causes
        # (knockdown / launch / normal), selected from the attacker's move data.
        defender.health = max(0, defender.health - scaled_damage)
        move = get_move_frame_data(getattr(attacker, 'state', None))
        hit_effect = move.hit_effect if move else HitEffect.NORMAL
        # Knockback: shove the defender away from the attacker. Magnitude is
        # provisional (calibrate vs ROM/decomp golden); direction is away from the
        # attacker; _update_state friction decays it and _clamp_to_stage bounds it.
        kb = getattr(hit_status, "pushback", 0.0) or _knockback_for(hit_effect, scaled_damage)
        kb_dir = 1.0 if attacker.x <= defender.x else -1.0
        apply_reaction(defender, hit_effect, hit_status.hitstun, knockback_vx=kb * kb_dir)
        attacker.attack_connected = True  # this attack has now connected

        # Hitstop scales with damage so heavy hits land harder (deterministic).
        hitstop = min(HITSTOP_MAX, HITSTOP_BASE + scaled_damage // HITSTOP_PER)
        attacker.hitfreeze_frames = hitstop
        defender.hitfreeze_frames = hitstop

        # Spawn a strength-appropriate spark + request a screen shake on heavy
        # / knockdown-class hits.
        spark = _spark_for_state(getattr(attacker, 'state', None))
        if vfx_manager:
            vfx_manager.spawn_hit_spark(hit_status.hit_position_x, hit_status.hit_position_y, spark)
            heavy_class = spark in (HitSparkType.HEAVY, HitSparkType.SPECIAL)
            knockdown_class = hit_effect in (HitEffect.KNOCKDOWN, HitEffect.JUGGLE,
                                             HitEffect.CRUMPLE, HitEffect.GROUND_BOUNCE,
                                             HitEffect.WALL_BOUNCE)
            if heavy_class or knockdown_class:
                vfx_manager.request_shake(SHAKE_INTENSITY)
        
        # Display combo info in debug mode
        if DEBUG_MODE:
            combo_count = self.sf3_combo_system.get_combo_count(defender_id)
            if combo_count > 1:
                log.debug("SF3 Hit Applied: %s -> %s damage, %s hitstun (Combo: %s)", hit_status.damage, scaled_damage, hit_status.hitstun, combo_count)
            else:
                log.debug("SF3 Hit Applied: %s damage, %s hitstun", scaled_damage, hit_status.hitstun)
    
    def _apply_parry_effects(self, attacker, defender, vfx_manager):
        """Apply effects when a parry is successful"""
        from ..data.enums import CharacterState
        
        # Defender gets parry advantage (frame advantage)
        defender.hitfreeze_frames = 0  # No hitfreeze for defender
        attacker.hitfreeze_frames = 16  # Extended freeze for attacker
        
        # Defender can act immediately (parry advantage)
        defender._transition_to_state(CharacterState.STANDING)
        
        # Spawn parry VFX
        if vfx_manager:
            parry_x = defender.x
            parry_y = defender.y - 60
            vfx_manager.spawn_hit_spark(parry_x, parry_y, HitSparkType.PARRY)

        if DEBUG_MODE:
            log.debug("PARRY! Defender has frame advantage")
    
    def _apply_block_effects(self, attacker, defender, hit_status, vfx_manager):
        """Apply effects when an attack is blocked"""
        from ..data.enums import CharacterState
        
        # Apply chip damage (small amount), clamped at zero
        chip_damage = max(1, hit_status.damage // 8)
        defender.health = max(0, defender.health - chip_damage)

        # Apply blockstun (low block if crouching) + small pushback
        blockstun = max(4, hit_status.hitstun // 2)
        defender.blockstun_frames = blockstun
        crouching = defender.state in (CharacterState.CROUCHING, CharacterState.BLOCKSTUN_LOW)
        defender._transition_to_state(
            CharacterState.BLOCKSTUN_LOW if crouching else CharacterState.BLOCKSTUN_HIGH)
        push = 3.0 if attacker.x < defender.x else -3.0
        defender.x += push

        # Both characters get hitfreeze
        attacker.hitfreeze_frames = 6
        defender.hitfreeze_frames = 6
        
        # Spawn block VFX
        if vfx_manager:
            block_x = defender.x
            block_y = defender.y - 60
            vfx_manager.spawn_hit_spark(block_x, block_y, HitSparkType.BLOCK)

        if DEBUG_MODE:
            log.debug("BLOCKED! Chip damage: %s, Blockstun: %s", chip_damage, blockstun)
    
    def _apply_throw_to_character(self, attacker, defender, hit_status, vfx_manager):
        """Apply throw effects to defender character"""
        from ..data.enums import CharacterState
        
        # Apply throw damage (usually higher than normal attacks), clamped
        defender.health = max(0, defender.health - hit_status.damage)

        # Apply throw hitstun (usually longer)
        defender.hitstun_frames = hit_status.hitstun
        defender._transition_to_state(CharacterState.HITSTUN_STANDING)
        
        # Position adjustment (basic throw positioning)
        if attacker.is_facing_right():
            defender.x = attacker.x + 100
        else:
            defender.x = attacker.x - 100

        if DEBUG_MODE:
            log.debug("SF3 Throw Applied: %s damage", hit_status.damage)
    
    @staticmethod
    def _draw_dashed_rect(screen, color, rect, dash=4, width=2):
        """Draw a rectangle outline as a dashed line (for non-verified boxes)."""
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        corners = [((x, y), (x + w, y)), ((x + w, y), (x + w, y + h)),
                   ((x + w, y + h), (x, y + h)), ((x, y + h), (x, y))]
        for (x0, y0), (x1, y1) in corners:
            length = max(abs(x1 - x0), abs(y1 - y0))
            if length == 0:
                continue
            steps = int(length // (dash * 2)) + 1
            for i in range(steps):
                t0 = (i * dash * 2) / length
                t1 = min(1.0, (i * dash * 2 + dash) / length)
                sx = x0 + (x1 - x0) * t0
                sy = y0 + (y1 - y0) * t0
                ex = x0 + (x1 - x0) * t1
                ey = y0 + (y1 - y0) * t1
                pygame.draw.line(screen, color, (sx, sy), (ex, ey), width)

    def render_debug(self, screen: pygame.Surface, show_hitboxes: bool = None, show_hurtboxes: bool = None):
        """Render debug visualization - compatible with old CollisionSystem.

        Verified boxes are drawn solid (hitboxes red, hurtboxes blue). Any box
        whose provenance status is not ``verified`` (inferred / community /
        pending) is drawn DASHED in yellow, with a one-time "PENDING/INFERRED
        DATA" legend so the operator knows it is not ROM-verified.
        """
        if not (show_hitboxes or show_hurtboxes):
            return

        YELLOW = (255, 255, 0)
        # (rect, status) pairs so we can choose solid vs dashed per box.
        self.debug_hitboxes.clear()
        self.debug_hurtboxes.clear()
        hit_pairs = []
        hurt_pairs = []

        for player_id, manager in self.hitbox_managers.items():
            work = self.player_works.get(player_id)
            if not work:
                continue

            # Draw with get_screen_rect: same facing-mirror + per-box anchor as
            # the live collision get_rect, but scaled (SPRITE_SCALE) and anchored
            # at the on-screen feet line (position.y + feet_offset) so the boxes
            # line up with the scaled sprite. (Collision math still uses get_rect.)
            px, face = work.work.position.x, work.work.face
            feet_y = work.work.position.y + getattr(work, "feet_offset", 0.0)

            for hitbox in manager.get_current_hitboxes(SF3HitboxType.ATTACK):
                rect = hitbox.get_screen_rect(px, feet_y, face)
                hit_pairs.append((rect, getattr(hitbox, "status", "verified")))
                self.debug_hitboxes.append(rect)

            for hitbox in manager.get_current_hitboxes(SF3HitboxType.BODY):
                rect = hitbox.get_screen_rect(px, feet_y, face)
                hurt_pairs.append((rect, getattr(hitbox, "status", "verified")))
                self.debug_hurtboxes.append(rect)

        has_pending = False

        if show_hitboxes:
            for rect, status in hit_pairs:
                if status == "verified":
                    pygame.draw.rect(screen, (255, 0, 0), rect, 2)
                else:
                    self._draw_dashed_rect(screen, YELLOW, rect)
                    has_pending = True

        if show_hurtboxes:
            for rect, status in hurt_pairs:
                if status == "verified":
                    pygame.draw.rect(screen, (0, 0, 255), rect, 2)
                else:
                    self._draw_dashed_rect(screen, YELLOW, rect)
                    has_pending = True

        if has_pending:
            if not hasattr(self, "_pending_legend_font"):
                self._pending_legend_font = pygame.font.Font(None, 18)
            label = self._pending_legend_font.render("PENDING/INFERRED DATA", True, YELLOW)
            screen.blit(label, (8, 8))
    
    def get_combo_info(self, player_id: int) -> Dict[str, Any]:
        """Get combo information for a player (for UI display)"""
        return self.sf3_combo_system.get_combo_display_info(player_id)

    def reset_combos(self):
        """Reset all combo states"""
        self.sf3_combo_system.reset_all_combos()

    def reset(self):
        """Reset all per-round state: frame counter, hit queue, combos, parry."""
        self.frame_counter = 0
        self.sf3_system.update_frame(0)
        self.sf3_system.clear_hit_queue()
        self.sf3_combo_system.reset_all_combos()
        for work in self.player_works.values():
            self.sf3_parry_system.reset_parry_state(work)
        self.debug_hitboxes.clear()
        self.debug_hurtboxes.clear()
        self.last_results.clear()
