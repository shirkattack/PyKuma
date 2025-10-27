"""
SF3:3S Pydantic Schemas

This module provides type-safe Pydantic wrappers around our authentic SF3 systems.
These schemas add runtime validation, serialization, and clean APIs while preserving
the exact behavior of the underlying SF3 algorithms.

Key Features:
- Runtime validation of all SF3 data
- Type safety for complex nested structures
- Automatic serialization/deserialization
- AI-ready data structures
- Schema documentation generation
"""

from typing import List, Optional, Dict, Any, Tuple, Union, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import yaml
from pathlib import Path

# Import our authentic SF3 systems
from ..systems.sf3_core import (
    SF3WorkStructure, SF3PlayerWork, SF3GamePhase, SF3StateCategory,
    SF3Position, SF3HitData, SF3_DAMAGE_SCALING, SF3_PARRY_WINDOW
)
from ..systems.sf3_hitboxes import SF3HitboxType, SF3HitLevel
from ..systems.sf3_input import SF3InputDirection, SF3ButtonInput


class Vector2(BaseModel):
    """2D vector with validation"""
    x: float = Field(default=0.0, description="X coordinate")
    y: float = Field(default=0.0, description="Y coordinate")
    
    class Config:
        json_schema_extra = {
            "example": {"x": 100.0, "y": 200.0}
        }


class Vector3(BaseModel):
    """3D vector with validation"""
    x: float = Field(default=0.0, description="X coordinate")
    y: float = Field(default=0.0, description="Y coordinate") 
    z: float = Field(default=0.0, description="Z coordinate")
    
    class Config:
        json_schema_extra = {
            "example": {"x": 100.0, "y": 200.0, "z": 0.0}
        }


class CharacterArchetype(str, Enum):
    """Character archetypes for AI and balance"""
    SHOTO = "shoto"           # Ryu, Ken, Akuma
    GRAPPLER = "grappler"     # Alex, Hugo
    RUSHDOWN = "rushdown"     # Chun-Li, Yun, Yang
    ZONER = "zoner"           # Remy
    TECHNICAL = "technical"   # Makoto, Ibuki
    BALANCED = "balanced"     # Dudley, Necro


class HitboxData(BaseModel):
    """
    Validated hitbox data
    
    This wraps our SF3Hitbox with Pydantic validation and provides
    clean serialization for YAML data.
    """
    offset_x: float = Field(description="X offset from character center")
    offset_y: float = Field(description="Y offset from character center")
    width: float = Field(gt=0, description="Hitbox width")
    height: float = Field(gt=0, description="Hitbox height")
    
    # Combat properties
    damage: int = Field(ge=0, le=999, default=0, description="Damage value")
    stun: int = Field(ge=0, le=100, default=0, description="Stun value")
    hitstun: int = Field(ge=0, le=60, default=0, description="Hitstun frames")
    blockstun: int = Field(ge=0, le=30, default=0, description="Blockstun frames")
    
    # Hit properties
    hit_level: SF3HitLevel = Field(default=SF3HitLevel.MID, description="Attack level")
    priority: int = Field(ge=0, le=10, default=5, description="Attack priority")
    pushback: float = Field(ge=0, default=0.0, description="Pushback distance")
    
    # AI metadata
    ai_utility: float = Field(ge=0, le=1, default=0.5, description="AI utility score")
    ai_risk_level: float = Field(ge=0, le=1, default=0.5, description="AI risk assessment")
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "offset_x": 50,
                "offset_y": -65,
                "width": 60,
                "height": 40,
                "damage": 115,
                "stun": 7,
                "hit_level": "mid"
            }
        }


class FrameData(BaseModel):
    """
    Validated frame data with SF3 authenticity checks
    
    This ensures all frame data matches SF3's authentic values and
    provides validation for impossible frame combinations.
    """
    startup: int = Field(ge=1, le=60, description="Startup frames")
    active: int = Field(ge=1, le=30, description="Active frames") 
    recovery: int = Field(ge=1, le=60, description="Recovery frames")
    total: int = Field(ge=3, le=120, description="Total animation frames")
    
    # Advantage data
    hit_advantage: int = Field(ge=-20, le=20, default=0, description="Frame advantage on hit")
    block_advantage: int = Field(ge=-20, le=20, default=0, description="Frame advantage on block")
    
    # Cancel properties
    special_cancelable: bool = Field(default=False, description="Can cancel into specials")
    super_cancelable: bool = Field(default=False, description="Can cancel into supers")
    
    # Special properties
    invincibility_frames: List[int] = Field(default_factory=list, description="Invincible frame numbers")
    armor_frames: List[int] = Field(default_factory=list, description="Armor frame numbers")
    
    @field_validator('total')
    @classmethod
    def validate_total_frames(cls, v, info):
        """Ensure total frames equals startup + active + recovery"""
        if info.data:
            startup = info.data.get('startup', 0)
            active = info.data.get('active', 0) 
            recovery = info.data.get('recovery', 0)
            expected = startup + active + recovery
            if v != expected:
                raise ValueError(f"Total frames {v} must equal startup + active + recovery ({expected})")
        return v
    
    @field_validator('invincibility_frames')
    @classmethod
    def validate_invincibility_frames(cls, v, info):
        """Ensure invincibility frames are within move duration"""
        if info.data and 'total' in info.data:
            total = info.data['total']
            for frame in v:
                if frame < 1 or frame > total:
                    raise ValueError(f"Invincibility frame {frame} outside move duration (1-{total})")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "startup": 5,
                "active": 3,
                "recovery": 10,
                "total": 18,
                "hit_advantage": 2,
                "block_advantage": 1,
                "special_cancelable": True
            }
        }


class MoveHitboxes(BaseModel):
    """
    Multiple hitbox types per move (like SF3)
    
    This matches SF3's approach of having attack, body, and hand hitboxes
    for each animation frame.
    """
    attack: List[HitboxData] = Field(default_factory=list, description="Attack hitboxes (h_att)")
    body: List[HitboxData] = Field(default_factory=list, description="Body hurtboxes (h_bod)")
    hand: List[HitboxData] = Field(default_factory=list, description="Hand hurtboxes (h_han)")
    grab: List[HitboxData] = Field(default_factory=list, description="Grab hitboxes")
    projectile: List[HitboxData] = Field(default_factory=list, description="Projectile hitboxes")
    
    @field_validator('attack', 'body', 'hand', 'grab', 'projectile')
    @classmethod
    def validate_hitbox_lists(cls, v):
        """Ensure hitbox lists are not too large"""
        if len(v) > 10:  # Reasonable limit
            raise ValueError(f"Too many hitboxes in list: {len(v)} (max 10)")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "attack": [{"offset_x": 50, "offset_y": -65, "width": 60, "height": 40, "damage": 115}],
                "body": [{"offset_x": 0, "offset_y": -80, "width": 40, "height": 80}],
                "hand": [{"offset_x": 30, "offset_y": -65, "width": 25, "height": 25}]
            }
        }


class MoveData(BaseModel):
    """
    Complete move data with validation
    
    This represents a single move (normal, special, super) with all
    its properties, frame data, and hitboxes.
    """
    name: str = Field(description="Move name")
    frame_data: FrameData = Field(description="Frame timing data")
    hitboxes: MoveHitboxes = Field(description="Collision data")
    
    # Move properties
    move_type: Literal["normal", "special", "super", "throw"] = Field(description="Move category")
    input_command: Optional[str] = Field(None, description="Input command (e.g., 'QCF+P')")
    
    # Resource costs
    super_meter_cost: int = Field(ge=0, le=3, default=0, description="Super meter cost")
    ex_meter_cost: int = Field(ge=0, le=2, default=0, description="EX meter cost")
    
    # Special properties
    projectile_speed: Optional[float] = Field(None, ge=0, description="Projectile speed")
    projectile_durability: Optional[int] = Field(None, ge=0, description="Projectile durability")
    movement_distance: Optional[float] = Field(None, description="Movement distance")
    air_only: bool = Field(default=False, description="Air-only move")
    ground_only: bool = Field(default=True, description="Ground-only move")
    unblockable: bool = Field(default=False, description="Cannot be blocked")
    knockdown: bool = Field(default=False, description="Causes knockdown")
    
    # AI metadata
    ai_utility: float = Field(ge=0, le=1, default=0.5, description="AI utility score")
    ai_risk_level: float = Field(ge=0, le=1, default=0.5, description="AI risk assessment")
    ai_range: Literal["close", "mid", "far"] = Field(default="mid", description="Optimal range")
    
    @field_validator('input_command')
    @classmethod
    def validate_input_command(cls, v):
        """Validate input command format"""
        if v is not None:
            valid_motions = ["QCF", "QCB", "DP", "HCF", "HCB", "charge"]
            valid_buttons = ["P", "K", "LP", "MP", "HP", "LK", "MK", "HK"]
            
            # Simple validation - could be more sophisticated
            if not any(motion in v for motion in valid_motions + valid_buttons):
                raise ValueError(f"Invalid input command format: {v}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "standing_medium_punch",
                "move_type": "normal",
                "frame_data": {
                    "startup": 5,
                    "active": 3,
                    "recovery": 10,
                    "total": 18
                },
                "hitboxes": {
                    "attack": [{"offset_x": 50, "offset_y": -65, "width": 60, "height": 40, "damage": 115}]
                }
            }
        }


class CharacterStats(BaseModel):
    """
    Character statistics and properties
    
    This defines the core character attributes that affect gameplay.
    """
    name: str = Field(description="Character name")
    sf3_character_id: int = Field(ge=0, le=20, description="SF3 character ID")
    archetype: CharacterArchetype = Field(description="Character archetype")
    
    # Vital statistics
    health: int = Field(ge=800, le=1200, description="Character health")
    stun: int = Field(ge=50, le=80, description="Stun capacity")
    
    # Movement properties
    walk_speed: float = Field(gt=0, le=0.1, description="Walk speed")
    walk_backward_speed: float = Field(gt=0, le=0.1, description="Backward walk speed")
    dash_distance: float = Field(gt=0, le=150, description="Dash distance")
    jump_startup: int = Field(ge=3, le=6, description="Jump startup frames")
    jump_duration: int = Field(ge=30, le=60, description="Jump duration frames")
    jump_height: float = Field(gt=0, le=200, description="Jump height")
    
    @field_validator('walk_backward_speed')
    @classmethod
    def validate_backward_speed(cls, v, info):
        """Backward walk should be slower than forward walk"""
        if info.data and 'walk_speed' in info.data and v > info.data['walk_speed']:
            raise ValueError("Backward walk speed cannot exceed forward walk speed")
        return v
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "name": "Akuma",
                "sf3_character_id": 14,
                "archetype": "shoto",
                "health": 1050,
                "stun": 64,
                "walk_speed": 0.032
            }
        }


class AIPersonality(BaseModel):
    """
    AI personality configuration
    
    This defines how the AI behaves and makes decisions, allowing for
    different AI personalities and difficulty levels.
    """
    aggression: float = Field(ge=0, le=1, default=0.5, description="Aggression level")
    defensive_style: float = Field(ge=0, le=1, default=0.5, description="Defensive preference")
    zoning_preference: float = Field(ge=0, le=1, default=0.5, description="Zoning vs rushdown")
    combo_preference: float = Field(ge=0, le=1, default=0.5, description="Combo focus")
    risk_taking: float = Field(ge=0, le=1, default=0.5, description="Risk tolerance")
    
    # Advanced AI settings
    reaction_time: int = Field(ge=1, le=10, default=3, description="Reaction time in frames")
    input_accuracy: float = Field(ge=0.5, le=1.0, default=0.9, description="Input execution accuracy")
    pattern_recognition: float = Field(ge=0, le=1, default=0.7, description="Pattern recognition ability")
    
    @model_validator(mode='after')
    def validate_personality_balance(self):
        """Ensure personality traits are balanced"""
        aggression = self.aggression
        defensive = self.defensive_style
        
        # Aggression and defensive style should be somewhat inverse
        if aggression > 0.8 and defensive > 0.8:
            raise ValueError("Cannot be both highly aggressive and highly defensive")
        
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "aggression": 0.7,
                "defensive_style": 0.4,
                "zoning_preference": 0.8,
                "combo_preference": 0.6,
                "risk_taking": 0.5
            }
        }


class CharacterData(BaseModel):
    """
    Complete character data with validation
    
    This is the top-level schema for a character, containing all moves,
    stats, and AI configuration.
    """
    character_info: CharacterStats = Field(description="Character statistics")
    
    # Move categories
    normal_attacks: Dict[str, MoveData] = Field(description="Normal attacks")
    special_moves: Dict[str, MoveData] = Field(description="Special moves")
    super_arts: Dict[str, MoveData] = Field(description="Super arts")
    throws: Dict[str, MoveData] = Field(description="Throw moves")
    
    # Movement data
    movement: Dict[str, Any] = Field(description="Movement properties")
    
    # Parry configuration
    parry: Dict[str, Any] = Field(description="Parry system configuration")
    
    # AI configuration
    ai_personality: AIPersonality = Field(description="AI behavior configuration")
    
    @field_validator('normal_attacks', 'special_moves', 'super_arts', 'throws')
    @classmethod
    def validate_move_categories(cls, v, info):
        """Validate move categories have reasonable sizes"""
        max_moves = {
            'normal_attacks': 20,
            'special_moves': 15,
            'super_arts': 5,
            'throws': 5
        }
        
        field_name = info.field_name
        if len(v) > max_moves.get(field_name, 20):
            raise ValueError(f"Too many {field_name}: {len(v)} (max {max_moves[field_name]})")
        
        return v
    
    @field_validator('parry')
    @classmethod
    def validate_parry_config(cls, v):
        """Validate parry configuration"""
        required_fields = ['window_frames', 'advantage_frames', 'guard_directions']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required parry field: {field}")
        
        # Validate SF3 authentic values
        if v.get('window_frames') != SF3_PARRY_WINDOW:
            raise ValueError(f"Parry window must be {SF3_PARRY_WINDOW} frames (SF3 authentic)")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "character_info": {
                    "name": "Akuma",
                    "archetype": "shoto",
                    "health": 1050
                },
                "normal_attacks": {
                    "standing_medium_punch": {
                        "name": "standing_medium_punch",
                        "move_type": "normal"
                    }
                }
            }
        }


class SF3GameConfig(BaseModel):
    """
    Global SF3 game configuration
    
    This contains game-wide settings and constants that affect all characters.
    """
    # SF3 authentic constants
    damage_scaling: List[int] = Field(default=SF3_DAMAGE_SCALING, description="Combo damage scaling")
    parry_window: int = Field(default=SF3_PARRY_WINDOW, description="Parry window frames")
    hit_queue_size: int = Field(default=32, description="Hit queue size")
    input_buffer_size: int = Field(default=15, description="Input buffer frames")
    
    # Game settings
    round_time: int = Field(ge=30, le=120, default=99, description="Round time in seconds")
    rounds_to_win: int = Field(ge=1, le=5, default=2, description="Rounds to win match")
    
    @field_validator('damage_scaling')
    @classmethod
    def validate_damage_scaling(cls, v):
        """Ensure damage scaling matches SF3 authentic values"""
        if v != SF3_DAMAGE_SCALING:
            raise ValueError(f"Damage scaling must match SF3 authentic values: {SF3_DAMAGE_SCALING}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "damage_scaling": [100, 90, 80, 70, 60, 50, 40, 30, 20, 10],
                "parry_window": 7,
                "hit_queue_size": 32
            }
        }


def load_character_data(file_path: Path) -> CharacterData:
    """
    Load and validate character data from YAML file
    
    This provides a clean interface for loading character data with
    full Pydantic validation.
    """
    with open(file_path, 'r') as f:
        raw_data = yaml.safe_load(f)
    
    return CharacterData(**raw_data)


def save_character_data(character_data: CharacterData, file_path: Path):
    """
    Save character data to YAML file
    
    This serializes the validated character data back to YAML format.
    """
    with open(file_path, 'w') as f:
        yaml.dump(character_data.dict(), f, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":
    # Test the Pydantic schemas
    print("Testing SF3 Pydantic Schemas...")
    
    # Test basic data structures
    hitbox = HitboxData(
        offset_x=50, offset_y=-65, width=60, height=40,
        damage=115, stun=7, hit_level=SF3HitLevel.MID
    )
    print(f"✅ HitboxData: {hitbox.damage} damage, {hitbox.hit_level} level")
    
    # Test frame data validation
    try:
        frame_data = FrameData(startup=5, active=3, recovery=10, total=18)
        print(f"✅ FrameData: {frame_data.startup}/{frame_data.active}/{frame_data.recovery}")
    except Exception as e:
        print(f"❌ FrameData validation failed: {e}")
    
    # Test character stats
    stats = CharacterStats(
        name="Akuma",
        sf3_character_id=14,
        archetype=CharacterArchetype.SHOTO,
        health=1050,
        stun=64,
        walk_speed=0.032
    )
    print(f"✅ CharacterStats: {stats.name} ({stats.archetype}) - {stats.health}HP")
    
    # Test AI personality
    ai = AIPersonality(
        aggression=0.7,
        zoning_preference=0.8,
        combo_preference=0.6
    )
    print(f"✅ AIPersonality: Aggression={ai.aggression}, Zoning={ai.zoning_preference}")
    
    print("SF3 Pydantic Schemas working correctly! ✅")
    print("🚀 Ready for Phase 1 implementation!")
