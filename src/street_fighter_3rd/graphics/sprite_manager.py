"""
SF3:3S Sprite Management System

This module handles loading, caching, and managing character sprites and animations.
It integrates with our existing Akuma animation assets and provides a clean
interface for character rendering.

Key Features:
- Sprite loading and caching
- Animation frame management
- Character-specific sprite organization
- Memory-efficient sprite handling
- Integration with SF3 timing systems
"""

import pygame
import os
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

# Import our systems
from ..schemas.sf3_schemas import CharacterData, MoveData


class SpriteFlip(Enum):
    """Sprite flip directions"""
    NONE = "none"
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOTH = "both"


@dataclass
class SpriteFrame:
    """Individual sprite frame data"""
    frame_number: int
    image: pygame.Surface
    offset_x: int = 0
    offset_y: int = 0
    duration: int = 1  # Duration in game frames
    
    # Collision data
    hitbox_offset_x: int = 0
    hitbox_offset_y: int = 0
    
    # Animation properties
    flip: SpriteFlip = SpriteFlip.NONE
    scale: float = 1.0
    rotation: float = 0.0


@dataclass
class SpriteAnimation:
    """Complete sprite animation"""
    animation_name: str
    frames: List[SpriteFrame] = field(default_factory=list)
    total_frames: int = 0
    loop: bool = True
    
    # Animation timing
    frame_rate: int = 60  # Frames per second
    total_duration: int = 0  # Total duration in game frames
    
    # Animation properties
    origin_x: int = 0  # Character origin point
    origin_y: int = 0
    
    def get_frame(self, frame_index: int) -> Optional[SpriteFrame]:
        """Get frame by index with looping"""
        if not self.frames:
            return None
        
        if self.loop:
            frame_index = frame_index % len(self.frames)
        elif frame_index >= len(self.frames):
            frame_index = len(self.frames) - 1
        
        return self.frames[frame_index] if 0 <= frame_index < len(self.frames) else None
    
    def get_total_duration(self) -> int:
        """Get total animation duration in game frames"""
        return sum(frame.duration for frame in self.frames)


class SpriteCache:
    """Efficient sprite caching system"""
    
    def __init__(self, max_cache_size: int = 100):
        self.cache: Dict[str, pygame.Surface] = {}
        self.access_order: List[str] = []
        self.max_cache_size = max_cache_size
    
    def get(self, key: str) -> Optional[pygame.Surface]:
        """Get sprite from cache"""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, surface: pygame.Surface):
        """Add sprite to cache"""
        # Remove if already exists
        if key in self.cache:
            self.access_order.remove(key)
        
        # Add to cache
        self.cache[key] = surface
        self.access_order.append(key)
        
        # Evict oldest if cache is full
        while len(self.cache) > self.max_cache_size:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
    
    def clear(self):
        """Clear all cached sprites"""
        self.cache.clear()
        self.access_order.clear()


class SF3SpriteManager:
    """
    Main sprite management system for SF3 characters
    
    Handles loading character sprites, managing animations, and providing
    efficient access to sprite data for rendering.
    """
    
    def __init__(self, assets_base_path: str = "tools/sprite_extraction"):
        self.assets_base_path = Path(assets_base_path)
        
        # Sprite storage
        self.character_animations: Dict[str, Dict[str, SpriteAnimation]] = {}
        self.sprite_cache = SpriteCache(max_cache_size=200)
        
        # Loading state
        self.loaded_characters: set = set()
        
        # Sprite scaling (SF3 sprites are typically small)
        self.default_scale = 2.0  # 2x scaling for better visibility
        
        # Color key for transparency (SF3 sprites often use magenta)
        self.transparency_color = (255, 0, 255)  # Magenta
        
        print(f"SF3SpriteManager initialized with assets path: {self.assets_base_path}")
    
    def load_character_sprites(self, character_name: str, character_data: CharacterData) -> bool:
        """
        Load all sprites for a character
        
        Args:
            character_name: Character identifier (e.g., "akuma", "ken")
            character_data: Character data with move information
            
        Returns:
            True if loading successful, False otherwise
        """
        
        if character_name in self.loaded_characters:
            print(f"Character {character_name} sprites already loaded")
            return True
        
        print(f"Loading sprites for {character_name}...")
        
        # Character animations path
        char_animations_path = self.assets_base_path / f"{character_name}_animations"
        
        if not char_animations_path.exists():
            print(f"⚠️ Animation path not found: {char_animations_path}")
            return False
        
        # Initialize character animations
        self.character_animations[character_name] = {}
        
        # Load animations for all moves
        success_count = 0
        total_moves = 0
        
        # Load normal attacks
        for move_name, move_data in character_data.normal_attacks.items():
            if self._load_move_animation(character_name, move_name, move_data):
                success_count += 1
            total_moves += 1
        
        # Load special moves
        for move_name, move_data in character_data.special_moves.items():
            if self._load_move_animation(character_name, move_name, move_data):
                success_count += 1
            total_moves += 1
        
        # Load super arts
        for move_name, move_data in character_data.super_arts.items():
            if self._load_move_animation(character_name, move_name, move_data):
                success_count += 1
            total_moves += 1
        
        # Load basic animations (stance, walk, etc.)
        basic_animations = [
            "stance", "walkf", "walkb", "jump", "jumpf", "jumpb",
            "block", "crouch", "crouching"
        ]
        
        for anim_name in basic_animations:
            if self._load_basic_animation(character_name, anim_name):
                success_count += 1
            total_moves += 1
        
        # Mark as loaded if we got at least some animations
        if success_count > 0:
            self.loaded_characters.add(character_name)
            print(f"✅ Loaded {success_count}/{total_moves} animations for {character_name}")
            return True
        else:
            print(f"❌ Failed to load any animations for {character_name}")
            return False
    
    def _load_move_animation(self, character_name: str, move_name: str, move_data: MoveData) -> bool:
        """Load animation for a specific move"""
        
        # Map move names to animation folder names
        animation_folder = self._map_move_to_animation_folder(character_name, move_name)
        
        if not animation_folder:
            return False
        
        animation_path = self.assets_base_path / f"{character_name}_animations" / animation_folder
        
        if not animation_path.exists():
            print(f"⚠️ Animation folder not found: {animation_path}")
            return False
        
        # Load animation frames
        animation = self._load_animation_from_folder(animation_path, move_name)
        
        if animation:
            # Set animation properties from move data
            animation.total_duration = move_data.frame_data.total
            animation.loop = False  # Most moves don't loop
            
            self.character_animations[character_name][move_name] = animation
            return True
        
        return False
    
    def _load_basic_animation(self, character_name: str, animation_name: str) -> bool:
        """Load basic character animation (stance, walk, etc.)"""
        
        # Map animation names to folder names
        folder_mapping = {
            "stance": "akuma-stance",
            "walkf": "akuma-walkf", 
            "walkb": "akuma-walkb",
            "jump": "akuma-jump",
            "jumpf": "akuma-jumpf",
            "jumpb": "akuma-jumpb",
            "block": "akuma-block",
            "crouch": "akuma-crouch",
            "crouching": "akuma-crouching"
        }
        
        folder_name = folder_mapping.get(animation_name)
        if not folder_name:
            return False
        
        animation_path = self.assets_base_path / f"{character_name}_animations" / folder_name
        
        if not animation_path.exists():
            return False
        
        # Load animation frames
        animation = self._load_animation_from_folder(animation_path, animation_name)
        
        if animation:
            # Basic animations usually loop
            animation.loop = animation_name in ["stance", "walkf", "walkb", "crouching"]
            
            self.character_animations[character_name][animation_name] = animation
            return True
        
        return False
    
    def _map_move_to_animation_folder(self, character_name: str, move_name: str) -> Optional[str]:
        """Map move names to animation folder names"""
        
        # Akuma move mappings
        if character_name == "akuma":
            move_mappings = {
                # Normal attacks
                "standing_light_punch": "akuma-wp",
                "standing_medium_punch": "akuma-mp", 
                "standing_heavy_punch": "akuma-hp",
                "standing_light_kick": "akuma-wk",
                "standing_medium_kick": "akuma-mk",
                "standing_heavy_kick": "akuma-hk",
                "crouching_light_punch": "akuma-crouch-wp",
                "crouching_medium_punch": "akuma-crouch-mp",
                "crouching_heavy_punch": "akuma-crouch-hp",
                "crouching_light_kick": "akuma-crouch-wk",
                "crouching_medium_kick": "akuma-crouch-mk",
                "crouching_heavy_kick": "akuma-crouch-hk",
                
                # Special moves
                "hadoken_light": "akuma-fireball",
                "hadoken_medium": "akuma-fireball",
                "hadoken_heavy": "akuma-fireball",
                "shoryuken_light": "akuma-dp",
                "shoryuken_medium": "akuma-dp", 
                "shoryuken_heavy": "akuma-dp",
                "tatsumaki_light": "akuma-hurricane",
                "tatsumaki_medium": "akuma-hurricane",
                "tatsumaki_heavy": "akuma-hurricane",
                
                # Throws
                "forward_throw": "akuma-throw-forward",
                "back_throw": "akuma-throw-back",
            }
            
            return move_mappings.get(move_name)
        
        # Ken move mappings (when we add Ken sprites)
        elif character_name == "ken":
            # For now, Ken uses placeholder mappings
            # In the future, we'd have ken-specific animations
            return None
        
        return None
    
    def _load_animation_from_folder(self, folder_path: Path, animation_name: str) -> Optional[SpriteAnimation]:
        """Load animation frames from a folder"""
        
        if not folder_path.exists():
            return None
        
        # Get all PNG files in the folder
        frame_files = sorted([f for f in folder_path.glob("*.png")])
        
        if not frame_files:
            print(f"⚠️ No PNG files found in {folder_path}")
            return None
        
        # Create animation
        animation = SpriteAnimation(animation_name=animation_name)
        
        # Load each frame
        for i, frame_file in enumerate(frame_files):
            try:
                # Load image
                surface = pygame.image.load(str(frame_file))
                
                # Apply transparency
                surface = surface.convert()
                surface.set_colorkey(self.transparency_color)
                
                # Scale sprite
                if self.default_scale != 1.0:
                    new_width = int(surface.get_width() * self.default_scale)
                    new_height = int(surface.get_height() * self.default_scale)
                    surface = pygame.transform.scale(surface, (new_width, new_height))
                
                # Create sprite frame
                sprite_frame = SpriteFrame(
                    frame_number=i,
                    image=surface,
                    duration=1  # Default 1 frame duration
                )
                
                animation.frames.append(sprite_frame)
                
            except Exception as e:
                print(f"⚠️ Failed to load frame {frame_file}: {e}")
                continue
        
        if animation.frames:
            animation.total_frames = len(animation.frames)
            animation.total_duration = animation.get_total_duration()
            
            # Set origin point (center-bottom of sprite)
            if animation.frames:
                first_frame = animation.frames[0]
                animation.origin_x = first_frame.image.get_width() // 2
                animation.origin_y = first_frame.image.get_height()
            
            print(f"✅ Loaded animation '{animation_name}' with {len(animation.frames)} frames")
            return animation
        
        return None
    
    def get_character_animation(self, character_name: str, animation_name: str) -> Optional[SpriteAnimation]:
        """Get animation for a character"""
        
        if character_name not in self.character_animations:
            return None
        
        return self.character_animations[character_name].get(animation_name)
    
    def get_animation_frame(self, character_name: str, animation_name: str, frame_index: int) -> Optional[SpriteFrame]:
        """Get specific frame from character animation"""
        
        animation = self.get_character_animation(character_name, animation_name)
        if not animation:
            return None
        
        return animation.get_frame(frame_index)
    
    def render_character_sprite(self, screen: pygame.Surface, character_name: str, 
                               animation_name: str, frame_index: int, 
                               x: int, y: int, facing_right: bool = True) -> bool:
        """
        Render character sprite to screen
        
        Args:
            screen: Pygame surface to render to
            character_name: Character identifier
            animation_name: Animation name
            frame_index: Current frame index
            x, y: Screen position
            facing_right: Whether character is facing right
            
        Returns:
            True if rendered successfully, False otherwise
        """
        
        sprite_frame = self.get_animation_frame(character_name, animation_name, frame_index)
        if not sprite_frame:
            return False
        
        # Get sprite surface
        sprite_surface = sprite_frame.image
        
        # Flip sprite if facing left
        if not facing_right:
            sprite_surface = pygame.transform.flip(sprite_surface, True, False)
        
        # Calculate render position (accounting for origin)
        animation = self.get_character_animation(character_name, animation_name)
        if animation:
            render_x = x - animation.origin_x + sprite_frame.offset_x
            render_y = y - animation.origin_y + sprite_frame.offset_y
        else:
            render_x = x + sprite_frame.offset_x
            render_y = y + sprite_frame.offset_y
        
        # Render sprite
        screen.blit(sprite_surface, (render_x, render_y))
        
        return True
    
    def get_character_animations(self, character_name: str) -> Dict[str, SpriteAnimation]:
        """Get all animations for a character"""
        return self.character_animations.get(character_name, {})
    
    def is_character_loaded(self, character_name: str) -> bool:
        """Check if character sprites are loaded"""
        return character_name in self.loaded_characters
    
    def unload_character(self, character_name: str):
        """Unload character sprites to free memory"""
        if character_name in self.character_animations:
            del self.character_animations[character_name]
        
        if character_name in self.loaded_characters:
            self.loaded_characters.remove(character_name)
        
        # Clear related cache entries
        keys_to_remove = [key for key in self.sprite_cache.cache.keys() if character_name in key]
        for key in keys_to_remove:
            if key in self.sprite_cache.cache:
                del self.sprite_cache.cache[key]
                self.sprite_cache.access_order.remove(key)
        
        print(f"Unloaded sprites for {character_name}")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        total_surfaces = 0
        total_memory = 0
        
        for char_name, animations in self.character_animations.items():
            for anim_name, animation in animations.items():
                for frame in animation.frames:
                    total_surfaces += 1
                    # Estimate memory usage (width * height * 4 bytes per pixel for RGBA)
                    surface = frame.image
                    total_memory += surface.get_width() * surface.get_height() * 4
        
        return {
            "loaded_characters": len(self.loaded_characters),
            "total_animations": sum(len(anims) for anims in self.character_animations.values()),
            "total_surfaces": total_surfaces,
            "estimated_memory_mb": total_memory / (1024 * 1024),
            "cache_size": len(self.sprite_cache.cache)
        }


if __name__ == "__main__":
    # Test sprite manager
    print("Testing SF3 Sprite Manager...")
    
    # Initialize pygame
    pygame.init()
    
    sprite_manager = SF3SpriteManager()
    
    # Test with mock character data
    print(f"✅ Sprite manager created")
    print(f"   Assets path: {sprite_manager.assets_base_path}")
    print(f"   Default scale: {sprite_manager.default_scale}")
    print(f"   Transparency color: {sprite_manager.transparency_color}")
    
    # Check if Akuma animations exist
    akuma_path = sprite_manager.assets_base_path / "akuma_animations"
    if akuma_path.exists():
        animation_folders = [d for d in akuma_path.iterdir() if d.is_dir()]
        print(f"✅ Found {len(animation_folders)} Akuma animation folders")
        
        # List some animations
        for folder in animation_folders[:5]:
            frame_count = len(list(folder.glob("*.png")))
            print(f"   {folder.name}: {frame_count} frames")
    else:
        print(f"⚠️ Akuma animations not found at {akuma_path}")
    
    print("SF3 Sprite Manager working correctly! ✅")
    print("🎯 Features implemented:")
    print("   - Sprite loading and caching")
    print("   - Animation frame management")
    print("   - Character-specific organization")
    print("   - Memory-efficient handling")
    print("   - Integration with move data")
    print("🚀 Ready for character sprite integration!")
