"""Collision detection system for hitboxes and hurtboxes."""

import pygame
from typing import List, Tuple, Optional
from street_fighter_3rd.data.enums import CharacterState, HitType
from street_fighter_3rd.data.constants import (
    HITSTUN_BASE,
    BLOCKSTUN_MULTIPLIER,
    DEBUG_MODE,
    SHOW_HITBOXES
)


class HitboxData:
    """Runtime hitbox data for an active attack."""

    def __init__(self, x: int, y: int, width: int, height: int, damage: int,
                 hitstun: int, hit_type: HitType = HitType.MID):
        """Initialize hitbox.

        Args:
            x, y: Position relative to character
            width, height: Hitbox dimensions
            damage: Damage dealt
            hitstun: Frames of hitstun on hit
            hit_type: Type of hit (high/mid/low)
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.damage = damage
        self.hitstun = hitstun
        self.hit_type = hit_type
        self.has_hit = False  # Track if this hitbox already connected


class CollisionSystem:
    """Handles all collision detection between characters."""

    def __init__(self):
        """Initialize collision system."""
        self.debug_hitboxes: List[pygame.Rect] = []  # For debug rendering
        self.debug_hurtboxes: List[pygame.Rect] = []

    def check_attack_collision(self, attacker, defender, vfx_manager=None) -> bool:
        """Check if attacker's hitbox hits defender's hurtbox.

        Args:
            attacker: Attacking character
            defender: Defending character
            vfx_manager: VFX manager to spawn hit effects (optional)

        Returns:
            True if hit connected
        """
        # Get active hitboxes from attacker
        hitboxes = self._get_hitboxes(attacker)

        # Get hurtboxes from defender
        hurtboxes = self._get_hurtboxes(defender)

        # Clear debug data
        self.debug_hitboxes.clear()
        self.debug_hurtboxes.clear()

        # Check each hitbox against each hurtbox
        for hitbox, hitbox_rect in hitboxes:
            self.debug_hitboxes.append(hitbox_rect)

            for hurtbox_rect in hurtboxes:
                self.debug_hurtboxes.append(hurtbox_rect)

                # Check collision
                if hitbox_rect.colliderect(hurtbox_rect):
                    # Only hit once per attack
                    if not hitbox.has_hit:
                        hitbox.has_hit = True
                        self._apply_hit(attacker, defender, hitbox, hurtbox_rect, vfx_manager)
                        return True

        return False

    def _get_hitboxes(self, character) -> List[Tuple[HitboxData, pygame.Rect]]:
        """Get active hitboxes for a character based on current state and frame.

        Args:
            character: Character to get hitboxes for

        Returns:
            List of (HitboxData, pygame.Rect) tuples for active hitboxes
        """
        hitboxes = []

        # First try to get hitbox from YAML animation data
        yaml_hitbox = self._get_yaml_hitbox(character)
        if yaml_hitbox:
            hitboxes.append(yaml_hitbox)
            return hitboxes

        # Fallback to hardcoded hitboxes for animations not yet in YAML
        # Standing attacks
        if character.state == CharacterState.LIGHT_PUNCH:
            # Light punch - 3f startup, 3f active → state_frame 3-5
            if 3 <= character.state_frame <= 5:
                offset_x = 45 if character.is_facing_right() else -45
                hitbox_data = HitboxData(
                    x=offset_x, y=-70, width=50, height=35,
                    damage=12, hitstun=12, hit_type=HitType.HIGH
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.MEDIUM_PUNCH:
            # Active frames 5-8 (frame data), which is state_frame 4-7 (0-indexed)
            if 4 <= character.state_frame <= 7:
                offset_x = 50 if character.is_facing_right() else -50
                hitbox_data = HitboxData(
                    x=offset_x, y=-65, width=60, height=40,
                    damage=18, hitstun=15, hit_type=HitType.HIGH
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.HEAVY_PUNCH:
            # Close s.HP - Active frames 5-8 (frame data), which is state_frame 4-7 (0-indexed)
            if 4 <= character.state_frame <= 7:
                offset_x = 50 if character.is_facing_right() else -50
                hitbox_data = HitboxData(
                    x=offset_x, y=-70, width=65, height=50,
                    damage=24, hitstun=20, hit_type=HitType.HIGH
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.LIGHT_KICK:
            # Active frames 5-8 (frame data), which is state_frame 4-7 (0-indexed)
            if 4 <= character.state_frame <= 7:
                offset_x = 45 if character.is_facing_right() else -45
                hitbox_data = HitboxData(
                    x=offset_x, y=-40, width=50, height=30,
                    damage=7, hitstun=12, hit_type=HitType.HIGH
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.MEDIUM_KICK:
            # Active frames 5-9 (frame data), which is state_frame 4-8 (0-indexed)
            if 4 <= character.state_frame <= 8:
                offset_x = 55 if character.is_facing_right() else -55
                hitbox_data = HitboxData(
                    x=offset_x, y=-50, width=65, height=35,
                    damage=20, hitstun=16, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.HEAVY_KICK:
            # Active frames 10-17 (frame data), which is state_frame 9-16 (0-indexed)
            if 9 <= character.state_frame <= 16:
                offset_x = 70 if character.is_facing_right() else -70
                hitbox_data = HitboxData(
                    x=offset_x, y=-55, width=75, height=40,
                    damage=33, hitstun=22, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        # Crouching attacks (all LOW hit type)
        elif character.state == CharacterState.CROUCH_LIGHT_PUNCH:
            # cr.LP - 4f startup, 2f active → state_frame 3-4
            if 3 <= character.state_frame <= 4:
                offset_x = 35 if character.is_facing_right() else -35
                hitbox_data = HitboxData(
                    x=offset_x, y=-35, width=40, height=25,
                    damage=8, hitstun=10, hit_type=HitType.LOW
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.CROUCH_MEDIUM_PUNCH:
            # cr.MP - 5f startup, 3f active → state_frame 4-6
            if 4 <= character.state_frame <= 6:
                offset_x = 40 if character.is_facing_right() else -40
                hitbox_data = HitboxData(
                    x=offset_x, y=-40, width=50, height=30,
                    damage=15, hitstun=13, hit_type=HitType.LOW
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.CROUCH_HEAVY_PUNCH:
            # cr.HP - 5f startup, 4f active → state_frame 4-7
            if 4 <= character.state_frame <= 7:
                offset_x = 45 if character.is_facing_right() else -45
                hitbox_data = HitboxData(
                    x=offset_x, y=-45, width=55, height=35,
                    damage=22, hitstun=18, hit_type=HitType.LOW
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.CROUCH_LIGHT_KICK:
            # cr.LK - 4f startup, 2f active → state_frame 3-4
            if 3 <= character.state_frame <= 4:
                offset_x = 40 if character.is_facing_right() else -40
                hitbox_data = HitboxData(
                    x=offset_x, y=-20, width=45, height=20,
                    damage=6, hitstun=10, hit_type=HitType.LOW
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.CROUCH_MEDIUM_KICK:
            # cr.MK - 6f startup, 3f active → state_frame 5-7
            if 5 <= character.state_frame <= 7:
                offset_x = 50 if character.is_facing_right() else -50
                hitbox_data = HitboxData(
                    x=offset_x, y=-25, width=60, height=25,
                    damage=18, hitstun=14, hit_type=HitType.LOW
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.CROUCH_HEAVY_KICK:
            # cr.HK (Sweep) - 7f startup, 5f active → state_frame 6-10
            if 6 <= character.state_frame <= 10:
                offset_x = 60 if character.is_facing_right() else -60
                hitbox_data = HitboxData(
                    x=offset_x, y=-15, width=70, height=20,
                    damage=28, hitstun=20, hit_type=HitType.LOW
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        # Jumping attacks (all MID hit type)
        elif character.state == CharacterState.JUMP_LIGHT_PUNCH:
            # j.LP - 4f startup, 5f active → state_frame 3-7
            if 3 <= character.state_frame <= 7:
                offset_x = 40 if character.is_facing_right() else -40
                hitbox_data = HitboxData(
                    x=offset_x, y=-50, width=40, height=30,
                    damage=10, hitstun=12, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.JUMP_MEDIUM_PUNCH:
            # j.MP - 5f startup, 6f active → state_frame 4-9
            if 4 <= character.state_frame <= 9:
                offset_x = 45 if character.is_facing_right() else -45
                hitbox_data = HitboxData(
                    x=offset_x, y=-55, width=50, height=35,
                    damage=17, hitstun=16, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.JUMP_HEAVY_PUNCH:
            # j.HP - 7f startup, 5f active → state_frame 6-10
            if 6 <= character.state_frame <= 10:
                offset_x = 50 if character.is_facing_right() else -50
                hitbox_data = HitboxData(
                    x=offset_x, y=-60, width=55, height=40,
                    damage=25, hitstun=20, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.JUMP_LIGHT_KICK:
            # j.LK - 4f startup, 8f active → state_frame 3-10 (crossup potential)
            if 3 <= character.state_frame <= 10:
                offset_x = 35 if character.is_facing_right() else -35
                hitbox_data = HitboxData(
                    x=offset_x, y=-45, width=45, height=35,
                    damage=11, hitstun=13, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.JUMP_MEDIUM_KICK:
            # j.MK - 6f startup, 6f active → state_frame 5-10
            if 5 <= character.state_frame <= 10:
                offset_x = 50 if character.is_facing_right() else -50
                hitbox_data = HitboxData(
                    x=offset_x, y=-50, width=55, height=30,
                    damage=19, hitstun=17, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        elif character.state == CharacterState.JUMP_HEAVY_KICK:
            # j.HK - 8f startup, 4f active → state_frame 7-10
            if 7 <= character.state_frame <= 10:
                offset_x = 55 if character.is_facing_right() else -55
                hitbox_data = HitboxData(
                    x=offset_x, y=-55, width=60, height=35,
                    damage=27, hitstun=22, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        # Goshoryuken (Dragon Punch) - Multi-hit rising uppercut
        elif character.state == CharacterState.GOSHORYUKEN:
            # Get DP strength for damage calculation
            dp_strength = getattr(character, 'dp_strength', Button.LIGHT_PUNCH)

            # First hit: 3f startup, hits on frames 3-8
            if 2 <= character.state_frame <= 7:
                offset_x = 30 if character.is_facing_right() else -30
                # Damage varies by strength
                if dp_strength == Button.HEAVY_PUNCH:
                    damage = 35
                elif dp_strength == Button.MEDIUM_PUNCH:
                    damage = 30
                else:  # LIGHT_PUNCH
                    damage = 25

                hitbox_data = HitboxData(
                    x=offset_x, y=-60, width=45, height=80,
                    damage=damage, hitstun=22, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

            # Second hit: Upper hitbox, frames 8-12
            if 7 <= character.state_frame <= 11:
                offset_x = 25 if character.is_facing_right() else -25
                # Second hit does more damage
                if dp_strength == Button.HEAVY_PUNCH:
                    damage = 45
                elif dp_strength == Button.MEDIUM_PUNCH:
                    damage = 40
                else:
                    damage = 35

                hitbox_data = HitboxData(
                    x=offset_x, y=-100, width=40, height=60,
                    damage=damage, hitstun=25, hit_type=HitType.MID
                )
                world_x = int(character.x + hitbox_data.x)
                world_y = int(character.y + hitbox_data.y)
                rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                hitboxes.append((hitbox_data, rect))

        # Tatsumaki (Hurricane Kick) - Multi-hit spinning kick with forward movement
        elif character.state == CharacterState.TATSUMAKI:
            # Get tatsu strength for damage calculation
            tatsu_strength = getattr(character, 'tatsu_strength', Button.LIGHT_KICK)

            # Determine number of hits and damage per hit
            if tatsu_strength == Button.HEAVY_KICK:
                total_hits = 5
                damage_per_hit = 32  # 160 total damage / 5 hits
                hit_spacing = 5  # Frames between hits
            elif tatsu_strength == Button.MEDIUM_KICK:
                total_hits = 4
                damage_per_hit = 35  # 140 total damage / 4 hits
                hit_spacing = 5
            else:  # LIGHT_KICK
                total_hits = 3
                damage_per_hit = 40  # 120 total damage / 3 hits
                hit_spacing = 6

            # Multi-hit during active frames (4f startup, active starts frame 5)
            # Calculate which hit this should be based on frame
            if character.state_frame >= 3:  # After startup
                active_frame = character.state_frame - 3
                hit_number = active_frame // hit_spacing

                # Only create hitbox on the frame each hit starts
                if hit_number < total_hits and active_frame % hit_spacing == 0:
                    offset_x = 40 if character.is_facing_right() else -40

                    hitbox_data = HitboxData(
                        x=offset_x, y=-55, width=50, height=45,
                        damage=damage_per_hit, hitstun=18, hit_type=HitType.MID
                    )
                    world_x = int(character.x + hitbox_data.x)
                    world_y = int(character.y + hitbox_data.y)
                    rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
                    hitboxes.append((hitbox_data, rect))

        return hitboxes

    def _get_yaml_hitbox(self, character) -> Tuple[HitboxData, pygame.Rect] | None:
        """Get hitbox from YAML animation data if available.
        
        Args:
            character: Character to get hitbox for
            
        Returns:
            Tuple of (HitboxData, pygame.Rect) if hitbox is active, None otherwise
        """
        # Check if character has YAML animation hitboxes
        if not hasattr(character, 'animation_hitboxes'):
            return None
            
        # Get current animation name
        current_anim = character.animation_controller.get_current_animation_name()
        if not current_anim or current_anim not in character.animation_hitboxes:
            return None
            
        hitbox_config = character.animation_hitboxes[current_anim]
        
        # Check if current frame is in active frames
        current_frame = character.state_frame + 1  # Convert to 1-indexed for frame data
        if current_frame not in hitbox_config.active_frames:
            return None
            
        # Create hitbox data from YAML config
        offset_x = hitbox_config.offset_x if character.is_facing_right() else -hitbox_config.offset_x
        hitbox_data = HitboxData(
            x=offset_x,
            y=hitbox_config.offset_y,
            width=hitbox_config.width,
            height=hitbox_config.height,
            damage=hitbox_config.damage,
            hitstun=hitbox_config.hitstun,
            hit_type=hitbox_config.hit_type
        )
        
        # Create world-space rectangle
        world_x = int(character.x + hitbox_data.x)
        world_y = int(character.y + hitbox_data.y)
        rect = pygame.Rect(world_x, world_y, hitbox_data.width, hitbox_data.height)
        
        return (hitbox_data, rect)

    def _get_hurtboxes(self, character) -> List[pygame.Rect]:
        """Get hurtboxes (vulnerable areas) for a character.

        Args:
            character: Character to get hurtboxes from

        Returns:
            List of pygame.Rect hurtboxes
        """
        hurtboxes = []

        # Main body hurtbox (always active unless invincible)
        if character.state != CharacterState.HITSTUN_STANDING:  # Can't hit during hitstun
            # Standing hurtbox
            if character.state in [CharacterState.STANDING, CharacterState.WALKING_FORWARD,
                                  CharacterState.WALKING_BACKWARD]:
                hurtbox = pygame.Rect(
                    int(character.x - 25),  # Center around character
                    int(character.y - 80),  # Top of character
                    50,  # Width
                    80   # Height
                )
                hurtboxes.append(hurtbox)

            # Crouching hurtbox (smaller)
            elif character.state == CharacterState.CROUCHING:
                hurtbox = pygame.Rect(
                    int(character.x - 25),
                    int(character.y - 50),
                    50,
                    50
                )
                hurtboxes.append(hurtbox)

            # Attacking hurtbox (extends forward)
            elif character.state in [CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_PUNCH,
                                    CharacterState.HEAVY_PUNCH, CharacterState.LIGHT_KICK,
                                    CharacterState.MEDIUM_KICK, CharacterState.HEAVY_KICK]:
                hurtbox = pygame.Rect(
                    int(character.x - 25),
                    int(character.y - 80),
                    50,
                    80
                )
                hurtboxes.append(hurtbox)

            # Crouching attack hurtbox (smaller, lower)
            elif character.state in [CharacterState.CROUCH_LIGHT_PUNCH, CharacterState.CROUCH_MEDIUM_PUNCH,
                                    CharacterState.CROUCH_HEAVY_PUNCH, CharacterState.CROUCH_LIGHT_KICK,
                                    CharacterState.CROUCH_MEDIUM_KICK, CharacterState.CROUCH_HEAVY_KICK]:
                hurtbox = pygame.Rect(
                    int(character.x - 25),
                    int(character.y - 50),
                    50,
                    50
                )
                hurtboxes.append(hurtbox)

            # Jumping hurtbox (airborne)
            elif character.state in [CharacterState.JUMPING, CharacterState.JUMPING_FORWARD,
                                    CharacterState.JUMPING_BACKWARD, CharacterState.JUMP_LIGHT_PUNCH,
                                    CharacterState.JUMP_MEDIUM_PUNCH, CharacterState.JUMP_HEAVY_PUNCH,
                                    CharacterState.JUMP_LIGHT_KICK, CharacterState.JUMP_MEDIUM_KICK,
                                    CharacterState.JUMP_HEAVY_KICK]:
                hurtbox = pygame.Rect(
                    int(character.x - 20),  # Slightly smaller than standing
                    int(character.y - 60),  # Airborne height
                    40,  # Width
                    60   # Height
                )
                hurtboxes.append(hurtbox)

            # Special move hurtboxes
            elif character.state in [CharacterState.GOSHORYUKEN, CharacterState.TATSUMAKI]:
                # Dragon Punch and Hurricane Kick have compact hurtbox during motion
                hurtbox = pygame.Rect(
                    int(character.x - 20),
                    int(character.y - 60),
                    40,
                    60
                )
                hurtboxes.append(hurtbox)

        return hurtboxes

    def _apply_hit(self, attacker, defender, hitbox: HitboxData, hurtbox_rect: pygame.Rect, vfx_manager=None):
        """Apply hit effects to defender.

        Args:
            attacker: Character that landed the hit
            defender: Character that got hit
            hitbox: Hitbox data with damage/hitstun info
            hurtbox_rect: The hurtbox that was hit
            vfx_manager: VFX manager to spawn effects
        """
        # Check if defender is invincible (e.g., during Dragon Punch)
        if hasattr(defender, 'is_invincible') and defender.is_invincible:
            print(f"⚡ {defender.name if hasattr(defender, 'name') else 'Defender'} is INVINCIBLE!")
            return  # No hit applied

        # Calculate hit position (center of collision)
        hit_x = hurtbox_rect.centerx
        hit_y = hurtbox_rect.centery

        # Calculate hit freeze duration based on damage (heavier hits = more freeze)
        from street_fighter_3rd.data.constants import HIT_FREEZE_FRAMES
        if hitbox.damage >= 35:
            hitfreeze = HIT_FREEZE_FRAMES + 4  # Heavy: 12 frames
        elif hitbox.damage >= 20:
            hitfreeze = HIT_FREEZE_FRAMES + 2  # Medium: 10 frames
        else:
            hitfreeze = HIT_FREEZE_FRAMES  # Light: 8 frames

        # Check if defender is blocking
        if self._is_blocking(defender, hitbox):
            # Apply chip damage (10% of normal damage)
            from street_fighter_3rd.data.constants import CHIP_DAMAGE_MULTIPLIER
            chip_damage = int(hitbox.damage * CHIP_DAMAGE_MULTIPLIER)
            defender.health -= chip_damage

            # Apply blockstun
            blockstun = int(hitbox.hitstun * BLOCKSTUN_MULTIPLIER)
            defender.blockstun_frames = blockstun
            defender._transition_to_state(CharacterState.BLOCKSTUN_HIGH)
            print(f"BLOCKED! Chip: {chip_damage}, Blockstun: {blockstun}f")

            # Apply hit freeze to both players (shorter on block)
            attacker.hitfreeze_frames = hitfreeze // 2
            defender.hitfreeze_frames = hitfreeze // 2

            # Apply pushback on block (less than on hit)
            if hitbox.damage >= 35:
                pushback = 4.0  # Heavy block pushback
            elif hitbox.damage >= 20:
                pushback = 2.5  # Medium block pushback
            else:
                pushback = 1.5  # Light block pushback

            # Push defender away from attacker
            if attacker.x < defender.x:
                defender.x += pushback
            else:
                defender.x -= pushback

            # Spawn block spark (use light spark for now)
            if vfx_manager:
                from street_fighter_3rd.systems.vfx import HitSparkType
                vfx_manager.spawn_hit_spark(hit_x, hit_y, HitSparkType.SPECIAL)
        else:
            # Apply damage and hitstun
            defender.take_damage(hitbox.damage, hitbox.hitstun)
            print(f"HIT! Damage: {hitbox.damage}, Hitstun: {hitbox.hitstun}")

            # Apply hit freeze to both players (full duration on hit)
            attacker.hitfreeze_frames = hitfreeze
            defender.hitfreeze_frames = hitfreeze

            # Apply hit flash effect (1 frame for authentic SF3 look)
            defender.hitflash_frames = 1

            # Apply pushback based on damage
            # Determine pushback distance based on hit strength
            if hitbox.damage >= 35:
                pushback = 8.0  # Heavy hit pushback
            elif hitbox.damage >= 20:
                pushback = 5.0  # Medium hit pushback
            else:
                pushback = 3.0  # Light hit pushback

            # Push defender away from attacker
            if attacker.x < defender.x:
                # Attacker on left, push defender right
                defender.x += pushback
            else:
                # Attacker on right, push defender left
                defender.x -= pushback

            # Spawn hit spark based on damage
            if vfx_manager:
                from street_fighter_3rd.systems.vfx import HitSparkType
                # Determine spark type based on damage
                if hitbox.damage >= 35:
                    spark_type = HitSparkType.HEAVY
                elif hitbox.damage >= 20:
                    spark_type = HitSparkType.MEDIUM
                else:
                    spark_type = HitSparkType.LIGHT

                vfx_manager.spawn_hit_spark(hit_x, hit_y, spark_type)

    def _is_blocking(self, defender, hitbox: HitboxData) -> bool:
        """Check if defender is blocking the attack.

        High/Low Blocking Rules:
        - Standing block: Blocks HIGH, MID, OVERHEAD attacks. Cannot block LOW.
        - Crouching block: Blocks LOW, MID attacks. Cannot block HIGH or OVERHEAD.
        - Throws cannot be blocked.

        Args:
            defender: Defending character
            hitbox: Incoming hitbox

        Returns:
            True if successfully blocking
        """
        if not defender.input:
            if DEBUG_MODE:
                print("DEBUG: No input system on defender")
            return False

        # Throws cannot be blocked
        if hitbox.hit_type == HitType.THROW:
            return False

        direction = defender.input.get_direction()
        from street_fighter_3rd.data.enums import InputDirection

        # Check if holding back
        # Input system already mirrors directions based on facing, so BACK is always "away from opponent"
        holding_back = direction in [InputDirection.BACK, InputDirection.DOWN_BACK]

        if DEBUG_MODE:
            print(f"DEBUG: Defender facing={'RIGHT' if defender.is_facing_right() else 'LEFT'}, direction={direction.name}, holding_back={holding_back}, state={defender.state.name}")

        if not holding_back:
            return False

        # Check block type vs attack type
        defender_state = defender.state
        attack_type = hitbox.hit_type

        # Standing block (includes standing, walking backward while blocking)
        if defender_state in [CharacterState.STANDING, CharacterState.WALKING_BACKWARD, CharacterState.WALKING_FORWARD]:
            # Can block: HIGH, MID, OVERHEAD
            # Cannot block: LOW
            if attack_type == HitType.LOW:
                if DEBUG_MODE:
                    print(f"DEBUG: Standing block cannot block LOW attack!")
                return False  # Low attack hits standing block!
            if DEBUG_MODE:
                print(f"DEBUG: Standing block SUCCESS against {attack_type.name}")
            return attack_type in [HitType.HIGH, HitType.MID, HitType.OVERHEAD, HitType.PROJECTILE]

        # Crouching block
        elif defender_state == CharacterState.CROUCHING:
            # Can block: LOW, MID
            # Cannot block: HIGH, OVERHEAD
            if attack_type in [HitType.HIGH, HitType.OVERHEAD]:
                if DEBUG_MODE:
                    print(f"DEBUG: Crouching block cannot block {attack_type.name} attack!")
                return False  # Overhead/high hits crouching block!
            if DEBUG_MODE:
                print(f"DEBUG: Crouching block SUCCESS against {attack_type.name}")
            return attack_type in [HitType.LOW, HitType.MID, HitType.PROJECTILE]

        if DEBUG_MODE:
            print(f"DEBUG: No valid blocking state (defender in {defender_state.name})")
        return False

    def render_debug(self, screen: pygame.Surface, show_hitboxes: bool = None, show_hurtboxes: bool = None):
        """Render debug hitbox/hurtbox visualization.

        Args:
            screen: Surface to render to
            show_hitboxes: Override for showing hitboxes
            show_hurtboxes: Override for showing hurtboxes
        """
        # Use parameters if provided, otherwise fall back to constants
        should_show_hitboxes = show_hitboxes if show_hitboxes is not None else (DEBUG_MODE and SHOW_HITBOXES)
        should_show_hurtboxes = show_hurtboxes if show_hurtboxes is not None else (DEBUG_MODE and SHOW_HITBOXES)
        
        if not (should_show_hitboxes or should_show_hurtboxes):
            return

        # Draw hitboxes (red) if enabled
        if should_show_hitboxes:
            for hitbox in self.debug_hitboxes:
                pygame.draw.rect(screen, (255, 0, 0), hitbox, 2)

        # Draw hurtboxes (blue) if enabled
        if should_show_hurtboxes:
            for hurtbox in self.debug_hurtboxes:
                pygame.draw.rect(screen, (0, 0, 255), hurtbox, 2)
