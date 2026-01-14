"""
SF3 Collision System Adapter

This adapter bridges the authentic SF3CollisionSystem with our current Character class,
allowing us to use the authentic SF3 collision mechanics without rewriting the entire
character system.
"""

import pygame
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

from .sf3_collision import SF3CollisionSystem, SF3CollisionEvent, SF3CollisionResult
from .sf3_core import SF3PlayerWork, SF3WorkStructure
from .sf3_hitboxes import SF3HitboxManager, SF3HitboxType, SF3Hitbox
from .sf3_parry import SF3ParrySystem, SF3ParryResult, SF3ParryType
from .sf3_combo_system import SF3ComboSystem
from .collision import HitboxData  # For compatibility
from ..data.enums import CharacterState, HitType
from ..data.constants import HITSTUN_BASE, BLOCKSTUN_MULTIPLIER, DEBUG_MODE
from ..data.akuma_hitboxes import get_akuma_hitboxes, get_akuma_hurtboxes, get_move_frame_data


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
        
        # Player work structures for SF3 system
        self.player_works: Dict[int, SF3PlayerWork] = {}
        self.hitbox_managers: Dict[int, SF3HitboxManager] = {}
        
        # Results from last collision check
        self.last_results: List[CollisionResult] = []
    
    def update_parry_inputs(self, character, input_state: Dict[str, bool]):
        """Update parry input tracking for a character"""
        # Determine player_id based on player_number attribute if available
        player_id = character.player_number if hasattr(character, 'player_number') else 1

        # Only update if we have a player work structure for this player
        if player_id in self.player_works:
            player_work = self.player_works[player_id]
            
            # Ensure the player_work has the required structure for parry system
            if not hasattr(player_work, 'work'):
                # Create a simple work structure for compatibility
                class WorkStruct:
                    def __init__(self, player_number):
                        self.player_number = player_number
                player_work.work = WorkStruct(player_id)
            
            self.sf3_parry_system.update_parry_inputs(player_work, input_state)
    
    def check_attack_collision(self, attacker, defender, vfx_manager=None) -> bool:
        """
        Main collision check interface - compatible with old CollisionSystem.

        This method:
        1. Converts Character objects to SF3 data structures
        2. Runs authentic SF3 collision detection
        3. Applies results back to Character objects
        4. Maintains compatibility with existing VFX system
        """
        # Update frame counter
        self.frame_counter += 1
        self.sf3_system.update_frame(self.frame_counter)

        # Convert characters to SF3 structures
        att_work = self._character_to_sf3_work(attacker, player_id=1)
        def_work = self._character_to_sf3_work(defender, player_id=2)
        
        # Create hitbox managers
        att_hitbox_mgr = self._create_hitbox_manager(attacker)
        def_hitbox_mgr = self._create_hitbox_manager(defender)
        
        # Store for SF3 system
        self.player_works[1] = att_work
        self.player_works[2] = def_work
        self.hitbox_managers[1] = att_hitbox_mgr
        self.hitbox_managers[2] = def_hitbox_mgr
        
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
            # Update combo system
            self.sf3_combo_system.update()

            # Apply results back to characters directly from hit_status
            hit_occurred = self._apply_collision_results(attacker, defender, vfx_manager)

            # Clear the hit queue for next frame
            self.sf3_system.hit_queue_input = 0

        return hit_occurred
    
    def _character_to_sf3_work(self, character, player_id: int) -> SF3PlayerWork:
        """Convert our Character object to SF3PlayerWork structure"""
        work = SF3PlayerWork()

        # Ensure work.work exists and has player_number for parry system
        if not hasattr(work.work, 'player_number'):
            work.work.player_number = player_id

        # Basic positioning - MUST set work.work.position for SF3 collision system
        work.work.position.x = float(character.x)
        work.work.position.y = float(character.y)
        work.work.position.z = 0.0

        # Also set velocity in work structure
        work.velocity_x = int(character.velocity_x) if hasattr(character, 'velocity_x') else 0
        work.velocity_y = int(character.velocity_y) if hasattr(character, 'velocity_y') else 0

        # Set facing direction in work structure
        work.work.face = 1 if character.is_facing_right() else -1

        # Player identification (legacy fields, kept for compatibility)
        work.player_id = player_id
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
        
        return work
    
    def _create_hitbox_manager(self, character) -> SF3HitboxManager:
        """Create SF3HitboxManager from character's current hitboxes"""
        from .sf3_hitboxes import SF3Hitbox, SF3HitboxFrame, SF3HitLevel

        manager = SF3HitboxManager(character.name if hasattr(character, 'name') else "Unknown")

        # Get current frame number (1-indexed for frame data)
        frame_number = (character.state_frame if hasattr(character, 'state_frame') else 0) + 1

        # Try to get hitboxes from akuma_hitboxes.py
        akuma_attack_hitboxes = get_akuma_hitboxes(character.state, frame_number)
        akuma_hurtboxes = get_akuma_hurtboxes(character.state)

        # Create a frame with the hitboxes
        sf3_frame = SF3HitboxFrame(frame_number=frame_number)

        # Add attack hitboxes (offensive boxes)
        if akuma_attack_hitboxes:
            if DEBUG_MODE:
                print(f"DEBUG: Character {character.name if hasattr(character, 'name') else '?'} state={character.state.name}, frame={frame_number}, has {len(akuma_attack_hitboxes)} attack hitbox(es)")
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
                    hit_level=hit_level
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
                    blockstun=0
                )
                sf3_frame.add_hitbox(SF3HitboxType.BODY, sf3_hurtbox)

        # Set the current frame in the manager
        # Create a temporary animation name based on the state
        anim_name = f"state_{character.state.value}" if hasattr(character.state, 'value') else "unknown"
        manager.current_animation = anim_name
        manager.current_frame = frame_number

        # Add the frame to the manager's animations
        from .sf3_hitboxes import SF3HitboxAnimation
        animation = SF3HitboxAnimation(animation_name=anim_name, total_frames=100)
        animation.add_frame(frame_number, sf3_frame)
        manager.animations[anim_name] = animation

        return manager
    
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

        # Try YAML animation data as fallback
        yaml_hitbox = self._get_yaml_hitbox(character)
        if yaml_hitbox:
            hitboxes.append(yaml_hitbox)
            return hitboxes

        # Final fallback to basic hardcoded hitboxes
        return self._get_fallback_hitboxes(character)
    
    def _get_yaml_hitbox(self, character) -> Tuple[HitboxData, pygame.Rect] | None:
        """Get hitbox from YAML animation data if available"""
        try:
            import yaml
            from pathlib import Path

            # Load animation data (relative to this file)
            data_dir = Path(__file__).parent.parent / 'data'
            animations_file = data_dir / 'animations.yaml'
            with open(animations_file, 'r') as f:
                anim_data = yaml.safe_load(f)
            
            # Map character states to animation names
            state_to_anim = {
                CharacterState.LIGHT_PUNCH: 'light_punch',
                CharacterState.MEDIUM_PUNCH: 'medium_punch', 
                CharacterState.HEAVY_PUNCH: 'heavy_punch',
                CharacterState.LIGHT_KICK: 'light_kick',
                CharacterState.MEDIUM_KICK: 'medium_kick',
                CharacterState.HEAVY_KICK: 'heavy_kick',
                CharacterState.CROUCHING: 'crouch_light_punch'  # Example for crouching attacks
            }
            
            anim_name = state_to_anim.get(character.state)
            if not anim_name:
                return None
            
            # Get character animation data
            char_data = anim_data.get('characters', {}).get('akuma', {})
            animations = char_data.get('animations', {})
            anim = animations.get(anim_name, {})
            
            if 'hitbox' not in anim:
                return None
            
            hitbox_data_yaml = anim['hitbox']
            frame_data = anim.get('frame_data', {})
            
            # Check if we're in active frames
            active_frames = hitbox_data_yaml.get('active_frames', [])
            current_anim_frame = character.current_frame + 1  # Convert to 1-indexed
            
            if current_anim_frame not in active_frames:
                return None  # Not in active frames
            
            # Convert hit type string to enum
            hit_type_str = hitbox_data_yaml.get('hit_type', 'MID')
            hit_type_map = {
                'HIGH': HitType.HIGH,
                'MID': HitType.MID, 
                'LOW': HitType.LOW,
                'OVERHEAD': HitType.OVERHEAD
            }
            hit_type = hit_type_map.get(hit_type_str, HitType.MID)
            
            # Create hitbox data from YAML
            hitbox_data = HitboxData(
                x=hitbox_data_yaml.get('offset_x', 0),
                y=hitbox_data_yaml.get('offset_y', 0),
                width=hitbox_data_yaml.get('width', 50),
                height=hitbox_data_yaml.get('height', 50),
                damage=hitbox_data_yaml.get('damage', 10),
                hitstun=hitbox_data_yaml.get('hitstun', 10),
                hit_type=hit_type
            )
            
            # Create rectangle in world coordinates
            offset_x = hitbox_data.x
            offset_y = hitbox_data.y
            
            # Apply facing direction
            if character.is_facing_right():
                rect = pygame.Rect(
                    character.x + offset_x,
                    character.y + offset_y,
                    hitbox_data.width,
                    hitbox_data.height
                )
            else:
                rect = pygame.Rect(
                    character.x - offset_x - hitbox_data.width,
                    character.y + offset_y,
                    hitbox_data.width,
                    hitbox_data.height
                )
            
            return (hitbox_data, rect)
            
        except Exception as e:
            print(f"Warning: Could not load YAML hitbox data: {e}")
            return None
    
    def _get_fallback_hitboxes(self, character) -> List[Tuple[HitboxData, pygame.Rect]]:
        """Fallback hardcoded hitboxes if YAML data unavailable"""
        hitboxes = []
        
        # Basic attack hitboxes based on state (simplified versions)
        if character.state == CharacterState.LIGHT_PUNCH:
            hitbox_data = HitboxData(45, -70, 50, 35, 12, 12, HitType.HIGH)
            rect = pygame.Rect(character.x + 45, character.y - 70, 50, 35)
            if not character.is_facing_right():
                rect.x = character.x - 95
            hitboxes.append((hitbox_data, rect))
            
        elif character.state == CharacterState.MEDIUM_PUNCH:
            hitbox_data = HitboxData(50, -65, 60, 40, 18, 15, HitType.HIGH)
            rect = pygame.Rect(character.x + 50, character.y - 65, 60, 40)
            if not character.is_facing_right():
                rect.x = character.x - 110
            hitboxes.append((hitbox_data, rect))
            
        elif character.state == CharacterState.HEAVY_PUNCH:
            hitbox_data = HitboxData(35, -85, 55, 50, 25, 18, HitType.HIGH)
            rect = pygame.Rect(character.x + 35, character.y - 85, 55, 50)
            if not character.is_facing_right():
                rect.x = character.x - 90
            hitboxes.append((hitbox_data, rect))
        
        return hitboxes
    
    def _get_character_hurtboxes(self, character) -> List[pygame.Rect]:
        """Get hurtboxes from character using frame data"""
        hurtboxes = []

        # Try to get hurtboxes from akuma_hitboxes.py
        akuma_hurtboxes = get_akuma_hurtboxes(character.state)
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
        """Apply SF3 collision results back to our Character objects"""
        hit_occurred = False

        # Check if SF3 system detected any hits
        for i in range(self.sf3_system.hit_queue_input):
            hit_status = self.sf3_system.hit_status[i]

            if hit_status.result_flags & SF3CollisionResult.HIT_CONFIRMED:
                # Apply hit effects
                self._apply_hit_to_character(
                    attacker, defender, hit_status, vfx_manager
                )
                hit_occurred = True
                
            elif hit_status.result_flags & SF3CollisionResult.CATCH_CONFIRMED:
                # Apply throw effects
                self._apply_throw_to_character(
                    attacker, defender, hit_status, vfx_manager
                )
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
        from .sf3_hitboxes import SF3Hitbox, SF3HitLevel
        
        # Create SF3Hitbox for parry system
        attack_box = SF3Hitbox(
            offset_x=0, offset_y=0, 
            width=hit_status.damage, height=hit_status.hitstun,  # Using damage/hitstun as placeholder
            hit_level=SF3HitLevel.MID,  # Default to mid
            damage=hit_status.damage,
            hitstun=hit_status.hitstun
        )
        
        # WORKAROUND: Skip parry/block check for now to get basic hits working
        # TODO: Fix player_works mapping to enable parry system
        # att_work = self.player_works.get(1 if attacker == self.player_works.get(1) else 2)
        # def_work = self.player_works.get(1 if defender == self.player_works.get(1) else 2)

        # Determine attacker/defender IDs by player_number attribute
        attacker_id = getattr(attacker, 'player_number', 1)
        defender_id = getattr(defender, 'player_number', 2)

        # Register hit with combo system and get scaled damage
        scaled_damage = self.sf3_combo_system.register_hit(
            attacker_id, defender_id, hit_status.damage, "normal"
        )

        # Apply scaled damage and hitstun
        defender.health -= scaled_damage
        defender.hitstun_frames = hit_status.hitstun
        defender._transition_to_state(CharacterState.HITSTUN_STANDING)

        # Apply hitfreeze to both characters
        attacker.hitfreeze_frames = 8  # Standard hitfreeze
        defender.hitfreeze_frames = 8
        
        # Spawn VFX if available
        if vfx_manager:
            hit_x = hit_status.hit_position_x
            hit_y = hit_status.hit_position_y
            vfx_manager.spawn_hit_spark(hit_x, hit_y, "normal")
        
        # Display combo info in debug mode
        if DEBUG_MODE:
            combo_count = self.sf3_combo_system.get_combo_count(defender_id)
            if combo_count > 1:
                print(f"🥊 SF3 Hit Applied: {hit_status.damage} → {scaled_damage} damage, {hit_status.hitstun} hitstun (Combo: {combo_count})")
            else:
                print(f"SF3 Hit Applied: {scaled_damage} damage, {hit_status.hitstun} hitstun")
    
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
            vfx_manager.spawn_hit_spark(parry_x, parry_y, "parry")

        if DEBUG_MODE:
            print("🛡️ PARRY! Defender has frame advantage")
    
    def _apply_block_effects(self, attacker, defender, hit_status, vfx_manager):
        """Apply effects when an attack is blocked"""
        from ..data.enums import CharacterState
        
        # Apply chip damage (small amount)
        chip_damage = max(1, hit_status.damage // 8)
        defender.health -= chip_damage
        
        # Apply blockstun instead of hitstun
        blockstun = max(4, hit_status.hitstun // 2)
        defender.blockstun_frames = blockstun
        defender._transition_to_state(CharacterState.BLOCKSTUN_HIGH)

        # Both characters get hitfreeze
        attacker.hitfreeze_frames = 6
        defender.hitfreeze_frames = 6
        
        # Spawn block VFX
        if vfx_manager:
            block_x = defender.x
            block_y = defender.y - 60
            vfx_manager.spawn_hit_spark(block_x, block_y, "block")

        if DEBUG_MODE:
            print(f"🛡️ BLOCKED! Chip damage: {chip_damage}, Blockstun: {blockstun}")
    
    def _apply_throw_to_character(self, attacker, defender, hit_status, vfx_manager):
        """Apply throw effects to defender character"""
        from ..data.enums import CharacterState
        
        # Apply throw damage (usually higher than normal attacks)
        defender.health -= hit_status.damage

        # Apply throw hitstun (usually longer)
        defender.hitstun_frames = hit_status.hitstun
        defender._transition_to_state(CharacterState.HITSTUN_STANDING)
        
        # Position adjustment (basic throw positioning)
        if attacker.is_facing_right():
            defender.x = attacker.x + 100
        else:
            defender.x = attacker.x - 100

        if DEBUG_MODE:
            print(f"SF3 Throw Applied: {hit_status.damage} damage")
    
    def render_debug(self, screen: pygame.Surface, show_hitboxes: bool = None, show_hurtboxes: bool = None):
        """Render debug visualization - compatible with old CollisionSystem"""
        if not (show_hitboxes or show_hurtboxes):
            return
        
        # Update debug rectangles from current hitbox managers
        self.debug_hitboxes.clear()
        self.debug_hurtboxes.clear()
        
        for player_id, manager in self.hitbox_managers.items():
            work = self.player_works.get(player_id)
            if not work:
                continue
                
            # Get attack hitboxes
            attack_hitboxes = manager.get_current_hitboxes(SF3HitboxType.ATTACK)
            for hitbox in attack_hitboxes:
                screen_x = work.position_x + hitbox.offset_x
                screen_y = work.position_y + hitbox.offset_y
                rect = pygame.Rect(screen_x, screen_y, hitbox.width, hitbox.height)
                self.debug_hitboxes.append(rect)
            
            # Get body hurtboxes
            body_hitboxes = manager.get_current_hitboxes(SF3HitboxType.BODY)
            for hitbox in body_hitboxes:
                screen_x = work.position_x + hitbox.offset_x
                screen_y = work.position_y + hitbox.offset_y
                rect = pygame.Rect(screen_x, screen_y, hitbox.width, hitbox.height)
                self.debug_hurtboxes.append(rect)
        
        # Render hitboxes in red
        if show_hitboxes:
            for rect in self.debug_hitboxes:
                pygame.draw.rect(screen, (255, 0, 0), rect, 2)
        
        # Render hurtboxes in blue
        if show_hurtboxes:
            for rect in self.debug_hurtboxes:
                pygame.draw.rect(screen, (0, 0, 255), rect, 2)
    
    def get_combo_info(self, player_id: int) -> Dict[str, Any]:
        """Get combo information for a player (for UI display)"""
        return self.sf3_combo_system.get_combo_display_info(player_id)
    
    def reset_combos(self):
        """Reset all combo states"""
        self.sf3_combo_system.reset_all_combos()
