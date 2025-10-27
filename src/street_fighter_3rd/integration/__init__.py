"""
SF3 Integration Package

This package provides integration between Pydantic schemas and authentic SF3 systems.
It maintains 100% SF3 accuracy while adding modern Python type safety and validation.
"""

from .sf3_integration import (
    SF3CharacterManager,
    SF3GameManager,
    load_sf3_game,
)

__all__ = [
    "SF3CharacterManager",
    "SF3GameManager", 
    "load_sf3_game",
]
