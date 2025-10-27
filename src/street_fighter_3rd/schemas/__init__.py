"""
SF3 Schemas Package

This package provides Pydantic schemas and validation for the SF3 fighting game engine.
It wraps our authentic SF3 systems with modern Python type safety and validation.
"""

from .sf3_schemas import (
    # Core data types
    Vector2,
    Vector3,
    CharacterArchetype,
    
    # Combat data
    HitboxData,
    FrameData,
    MoveHitboxes,
    MoveData,
    
    # Character data
    CharacterStats,
    AIPersonality,
    CharacterData,
    
    # Game configuration
    SF3GameConfig,
    
    # Utility functions
    load_character_data,
    save_character_data,
)

__all__ = [
    "Vector2",
    "Vector3", 
    "CharacterArchetype",
    "HitboxData",
    "FrameData",
    "MoveHitboxes",
    "MoveData",
    "CharacterStats",
    "AIPersonality",
    "CharacterData",
    "SF3GameConfig",
    "load_character_data",
    "save_character_data",
]
