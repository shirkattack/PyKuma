"""
SF3:3S Shoto Character Base Class

This module implements the base Shoto character archetype that Ryu, Ken, and Akuma
inherit from. It defines common moves, properties, and behaviors while allowing
for character-specific customization.

Key Features:
- Shared Shoto moveset (Hadoken, Shoryuken, Tatsumaki)
- Common frame data patterns
- Inheritance-based character customization
- AI personality templates
- Authentic SF3 Shoto mechanics
"""

from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# Import our schemas
from ..schemas.sf3_schemas import (
    CharacterData, CharacterStats, MoveData, FrameData, 
    HitboxData, MoveHitboxes, AIPersonality, CharacterArchetype
)


@dataclass
class ShotoMoveVariant:
    """Defines variations of Shoto moves between characters"""
    startup: int
    active: int
    recovery: int
    damage: int
    stun: int
    special_properties: Dict[str, Any] = field(default_factory=dict)


class ShotoArchetype(ABC):
    """
    Abstract base class for Shoto characters
    
    This defines the common interface and shared moves that all Shoto
    characters (Ryu, Ken, Akuma) inherit from.
    """
    
    def __init__(self, character_name: str):
        self.character_name = character_name
        self.base_health = 1000  # Standard Shoto health
        self.base_stun = 64      # Standard Shoto stun
        
        # Shoto move variants (overridden by subclasses)
        self.move_variants = self._get_move_variants()
        
        # Character-specific properties
        self.unique_moves = self._get_unique_moves()
        self.personality_template = self._get_personality_template()
    
    @abstractmethod
    def _get_move_variants(self) -> Dict[str, ShotoMoveVariant]:
        """Get character-specific variants of Shoto moves"""
        pass
    
    @abstractmethod
    def _get_unique_moves(self) -> Dict[str, MoveData]:
        """Get character-specific unique moves"""
        pass
    
    @abstractmethod
    def _get_personality_template(self) -> AIPersonality:
        """Get character-specific AI personality template"""
        pass
    
    def create_character_data(self) -> CharacterData:
        """Create complete character data using Shoto base + character variants"""
        
        # Create character stats
        character_stats = self._create_character_stats()
        
        # Create moveset
        normal_attacks = self._create_normal_attacks()
        special_moves = self._create_special_moves()
        super_arts = self._create_super_arts()
        throws = self._create_throws()
        
        # Create movement and system data
        movement = self._create_movement_data()
        parry = self._create_parry_data()
        
        # Combine everything
        character_data = CharacterData(
            character_info=character_stats,
            normal_attacks=normal_attacks,
            special_moves=special_moves,
            super_arts=super_arts,
            throws=throws,
            movement=movement,
            parry=parry,
            ai_personality=self.personality_template
        )
        
        return character_data
    
    def _create_character_stats(self) -> CharacterStats:
        """Create character statistics"""
        return CharacterStats(
            name=self.character_name,
            sf3_character_id=self._get_sf3_character_id(),
            archetype=CharacterArchetype.SHOTO,
            health=self.base_health,
            stun=self.base_stun,
            walk_speed=self._get_walk_speed(),
            walk_backward_speed=self._get_walk_speed() * 0.8,
            dash_distance=80,
            jump_startup=4,
            jump_duration=45,
            jump_height=120
        )
    
    def _create_normal_attacks(self) -> Dict[str, MoveData]:
        """Create standard Shoto normal attacks"""
        
        normals = {}
        
        # Standing normals
        normals["standing_light_punch"] = self._create_move(
            "standing_light_punch", "normal",
            FrameData(startup=4, active=2, recovery=6, total=12, special_cancelable=True, super_cancelable=True),
            self._create_standard_hitboxes(damage=60, stun=3)
        )
        
        normals["standing_medium_punch"] = self._create_move(
            "standing_medium_punch", "normal",
            self._get_variant_frame_data("standing_medium_punch", 
                                       FrameData(startup=5, active=3, recovery=10, total=18, special_cancelable=True, super_cancelable=True)),
            self._create_standard_hitboxes(damage=115, stun=7)
        )
        
        normals["standing_heavy_punch"] = self._create_move(
            "standing_heavy_punch", "normal",
            FrameData(startup=8, active=4, recovery=17, total=29, special_cancelable=True, super_cancelable=True),
            self._create_standard_hitboxes(damage=180, stun=12)
        )
        
        # Standing kicks
        normals["standing_light_kick"] = self._create_move(
            "standing_light_kick", "normal",
            FrameData(startup=4, active=3, recovery=7, total=14, special_cancelable=True, super_cancelable=True),
            self._create_standard_hitboxes(damage=70, stun=3)
        )
        
        normals["standing_medium_kick"] = self._create_move(
            "standing_medium_kick", "normal",
            FrameData(startup=6, active=3, recovery=12, total=21, special_cancelable=True, super_cancelable=True),
            self._create_standard_hitboxes(damage=130, stun=7)
        )
        
        normals["standing_heavy_kick"] = self._create_move(
            "standing_heavy_kick", "normal",
            FrameData(startup=10, active=4, recovery=21, total=35, special_cancelable=True, super_cancelable=True),
            self._create_standard_hitboxes(damage=200, stun=12)
        )
        
        # Crouching normals
        normals["crouching_light_punch"] = self._create_move(
            "crouching_light_punch", "normal",
            FrameData(startup=4, active=2, recovery=7, total=13, special_cancelable=True, super_cancelable=True),
            self._create_crouching_hitboxes(damage=60, stun=3)
        )
        
        normals["crouching_medium_punch"] = self._create_move(
            "crouching_medium_punch", "normal",
            FrameData(startup=5, active=3, recovery=11, total=19, special_cancelable=True, super_cancelable=True),
            self._create_crouching_hitboxes(damage=110, stun=7)
        )
        
        normals["crouching_heavy_punch"] = self._create_move(
            "crouching_heavy_punch", "normal",
            FrameData(startup=7, active=4, recovery=18, total=29, special_cancelable=True, super_cancelable=True),
            self._create_crouching_hitboxes(damage=170, stun=12)
        )
        
        normals["crouching_light_kick"] = self._create_move(
            "crouching_light_kick", "normal",
            FrameData(startup=4, active=2, recovery=8, total=14, special_cancelable=True, super_cancelable=True),
            self._create_low_hitboxes(damage=65, stun=3)
        )
        
        normals["crouching_medium_kick"] = self._create_move(
            "crouching_medium_kick", "normal",
            FrameData(startup=6, active=3, recovery=13, total=22, special_cancelable=True, super_cancelable=True),
            self._create_low_hitboxes(damage=125, stun=7)
        )
        
        normals["crouching_heavy_kick"] = self._create_move(
            "crouching_heavy_kick", "normal",
            FrameData(startup=8, active=4, recovery=19, total=31, special_cancelable=False, super_cancelable=False, knockdown=True),
            self._create_low_hitboxes(damage=190, stun=12)
        )
        
        return normals
    
    def _create_special_moves(self) -> Dict[str, MoveData]:
        """Create standard Shoto special moves"""
        
        specials = {}
        
        # Hadoken (Fireball)
        for strength in ["light", "medium", "heavy"]:
            move_name = f"hadoken_{strength}"
            variant = self.move_variants.get(move_name, ShotoMoveVariant(13, 2, 31, 100, 8))
            
            specials[move_name] = self._create_move(
                move_name, "special",
                FrameData(
                    startup=variant.startup,
                    active=variant.active,
                    recovery=variant.recovery,
                    total=variant.startup + variant.active + variant.recovery
                ),
                self._create_projectile_hitboxes(damage=variant.damage, stun=variant.stun),
                input_command="QCF+P",
                projectile_speed=3.0 + (0.5 if strength == "medium" else 1.0 if strength == "heavy" else 0.0),
                projectile_durability=1 + (1 if strength == "heavy" else 0)
            )
        
        # Shoryuken (Dragon Punch)
        for strength in ["light", "medium", "heavy"]:
            move_name = f"shoryuken_{strength}"
            variant = self.move_variants.get(move_name, ShotoMoveVariant(3, 12, 25, 180, 15))
            
            invincibility_frames = list(range(1, 9)) if strength == "light" else list(range(1, 11)) if strength == "medium" else list(range(1, 13))
            
            specials[move_name] = self._create_move(
                move_name, "special",
                FrameData(
                    startup=variant.startup,
                    active=variant.active,
                    recovery=variant.recovery,
                    total=variant.startup + variant.active + variant.recovery,
                    invincibility_frames=invincibility_frames
                ),
                self._create_uppercut_hitboxes(damage=variant.damage, stun=variant.stun),
                input_command="DP+P"
            )
        
        # Tatsumaki (Hurricane Kick)
        for strength in ["light", "medium", "heavy"]:
            move_name = f"tatsumaki_{strength}"
            variant = self.move_variants.get(move_name, ShotoMoveVariant(7, 18, 15, 150, 12))
            
            specials[move_name] = self._create_move(
                move_name, "special",
                FrameData(
                    startup=variant.startup,
                    active=variant.active,
                    recovery=variant.recovery,
                    total=variant.startup + variant.active + variant.recovery
                ),
                self._create_spinning_hitboxes(damage=variant.damage, stun=variant.stun),
                input_command="QCB+K",
                movement_distance=120 + (30 if strength == "medium" else 60 if strength == "heavy" else 0)
            )
        
        return specials
    
    def _create_super_arts(self) -> Dict[str, MoveData]:
        """Create character-specific super arts (implemented by subclasses)"""
        return {}
    
    def _create_throws(self) -> Dict[str, MoveData]:
        """Create standard Shoto throws"""
        
        throws = {}
        
        throws["forward_throw"] = self._create_move(
            "forward_throw", "throw",
            FrameData(startup=3, active=2, recovery=25, total=30),
            self._create_throw_hitboxes(damage=180, stun=15),
            input_command="F+LP+LK",
            range=50,
            unescapable_frames=15
        )
        
        throws["back_throw"] = self._create_move(
            "back_throw", "throw",
            FrameData(startup=3, active=2, recovery=25, total=30),
            self._create_throw_hitboxes(damage=180, stun=15),
            input_command="B+LP+LK",
            range=50,
            unescapable_frames=15
        )
        
        return throws
    
    def _create_movement_data(self) -> Dict[str, Any]:
        """Create movement properties"""
        return {
            "walk_forward_speed": self._get_walk_speed(),
            "walk_backward_speed": self._get_walk_speed() * 0.8,
            "dash_forward_distance": 80,
            "dash_forward_duration": 20,
            "dash_backward_distance": 60,
            "dash_backward_duration": 25,
            "jump_startup": 4,
            "jump_duration": 45,
            "jump_height": 120,
            "jump_forward_distance": 100
        }
    
    def _create_parry_data(self) -> Dict[str, Any]:
        """Create parry system data"""
        return {
            "window_frames": 7,
            "advantage_frames": 8,
            "guard_directions": ["high", "mid", "low"]
        }
    
    # Helper methods for creating moves and hitboxes
    def _create_move(self, name: str, move_type: str, frame_data: FrameData, 
                    hitboxes: MoveHitboxes, input_command: str = None, **kwargs) -> MoveData:
        """Create a move with all properties"""
        return MoveData(
            name=name,
            move_type=move_type,
            frame_data=frame_data,
            hitboxes=hitboxes,
            input_command=input_command,
            **kwargs
        )
    
    def _create_standard_hitboxes(self, damage: int, stun: int) -> MoveHitboxes:
        """Create standard standing attack hitboxes"""
        return MoveHitboxes(
            attack=[HitboxData(offset_x=50, offset_y=-65, width=60, height=40, damage=damage, stun=stun)],
            body=[HitboxData(offset_x=0, offset_y=-80, width=40, height=80)],
            hand=[HitboxData(offset_x=30, offset_y=-65, width=25, height=25)]
        )
    
    def _create_crouching_hitboxes(self, damage: int, stun: int) -> MoveHitboxes:
        """Create crouching attack hitboxes"""
        return MoveHitboxes(
            attack=[HitboxData(offset_x=45, offset_y=-40, width=55, height=25, damage=damage, stun=stun)],
            body=[HitboxData(offset_x=0, offset_y=-40, width=40, height=40)],
            hand=[HitboxData(offset_x=25, offset_y=-40, width=25, height=20)]
        )
    
    def _create_low_hitboxes(self, damage: int, stun: int) -> MoveHitboxes:
        """Create low attack hitboxes"""
        return MoveHitboxes(
            attack=[HitboxData(offset_x=55, offset_y=-20, width=60, height=20, damage=damage, stun=stun)],
            body=[HitboxData(offset_x=0, offset_y=-40, width=40, height=40)],
            hand=[HitboxData(offset_x=30, offset_y=-20, width=30, height=15)]
        )
    
    def _create_projectile_hitboxes(self, damage: int, stun: int) -> MoveHitboxes:
        """Create projectile attack hitboxes"""
        return MoveHitboxes(
            attack=[HitboxData(offset_x=45, offset_y=-50, width=50, height=35, damage=damage, stun=stun)],
            body=[HitboxData(offset_x=0, offset_y=-80, width=40, height=80)],
            projectile=[HitboxData(offset_x=0, offset_y=0, width=30, height=20)]
        )
    
    def _create_uppercut_hitboxes(self, damage: int, stun: int) -> MoveHitboxes:
        """Create uppercut attack hitboxes"""
        return MoveHitboxes(
            attack=[
                HitboxData(offset_x=30, offset_y=-60, width=45, height=80, damage=damage, stun=stun),
                HitboxData(offset_x=25, offset_y=-100, width=40, height=60, damage=damage, stun=stun)
            ],
            body=[HitboxData(offset_x=0, offset_y=-80, width=40, height=80)],
            hand=[HitboxData(offset_x=15, offset_y=-60, width=25, height=40)]
        )
    
    def _create_spinning_hitboxes(self, damage: int, stun: int) -> MoveHitboxes:
        """Create spinning attack hitboxes"""
        return MoveHitboxes(
            attack=[HitboxData(offset_x=35, offset_y=-50, width=60, height=50, damage=damage, stun=stun)],
            body=[HitboxData(offset_x=0, offset_y=-80, width=40, height=80)],
            hand=[HitboxData(offset_x=20, offset_y=-50, width=40, height=40)]
        )
    
    def _create_throw_hitboxes(self, damage: int, stun: int) -> MoveHitboxes:
        """Create throw hitboxes"""
        return MoveHitboxes(
            grab=[HitboxData(offset_x=25, offset_y=-60, width=50, height=60, damage=damage, stun=stun)],
            body=[HitboxData(offset_x=0, offset_y=-80, width=40, height=80)]
        )
    
    def _get_variant_frame_data(self, move_name: str, default: FrameData) -> FrameData:
        """Get character-specific variant of frame data"""
        if move_name in self.move_variants:
            variant = self.move_variants[move_name]
            return FrameData(
                startup=variant.startup,
                active=variant.active,
                recovery=variant.recovery,
                total=variant.startup + variant.active + variant.recovery,
                hit_advantage=default.hit_advantage,
                block_advantage=default.block_advantage,
                special_cancelable=default.special_cancelable,
                super_cancelable=default.super_cancelable
            )
        return default
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    def _get_sf3_character_id(self) -> int:
        """Get SF3 character ID"""
        pass
    
    @abstractmethod
    def _get_walk_speed(self) -> float:
        """Get character walk speed"""
        pass


if __name__ == "__main__":
    print("SF3 Shoto Base Class created! ✅")
    print("🎯 Features implemented:")
    print("   - Abstract Shoto archetype")
    print("   - Shared moveset (Hadoken, Shoryuken, Tatsumaki)")
    print("   - Character inheritance system")
    print("   - Move variant customization")
    print("   - Complete normal attack set")
    print("   - Standard throw system")
    print("🚀 Ready for Ken and Ryu implementation!")
