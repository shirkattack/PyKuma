"""Animation system for sprite sequence playback."""

import os
import pygame
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class AnimationFrame:
    """Single frame in an animation."""
    sprite_number: int  # Sprite file number (e.g., 18664)
    duration: int = 1   # How many game frames to display this sprite


@dataclass
class FolderAnimationFrame:
    """Single frame in a folder-based animation."""
    folder_path: str     # Path to folder containing frames
    frame_index: int     # Frame number (0, 1, 2, etc.)
    duration: int = 1    # How many game frames to display this sprite


class Animation:
    """Handles playback of a sprite sequence."""

    def __init__(self, frames: List[AnimationFrame], loop: bool = False):
        """Initialize animation.

        Args:
            frames: List of animation frames
            loop: Whether animation should loop
        """
        self.frames = frames
        self.loop = loop
        self.current_frame_index = 0
        self.frame_counter = 0
        self.is_playing = True
        self.is_finished = False

    def update(self):
        """Update animation (call once per game frame)."""
        if not self.is_playing or self.is_finished:
            return

        # Increment frame counter
        self.frame_counter += 1

        # Check if it's time to advance to next frame
        current_frame = self.frames[self.current_frame_index]
        if self.frame_counter >= current_frame.duration:
            self.frame_counter = 0
            self.current_frame_index += 1

            # Check if animation is complete
            if self.current_frame_index >= len(self.frames):
                if self.loop:
                    self.current_frame_index = 0
                else:
                    self.current_frame_index = len(self.frames) - 1
                    self.is_finished = True

    def get_current_sprite_number(self) -> int:
        """Get the current sprite number to display."""
        return self.frames[self.current_frame_index].sprite_number

    def reset(self):
        """Reset animation to beginning."""
        self.current_frame_index = 0
        self.frame_counter = 0
        self.is_finished = False
        self.is_playing = True

    def stop(self):
        """Stop animation playback."""
        self.is_playing = False

    def play(self):
        """Resume animation playback."""
        self.is_playing = True

    def is_complete(self) -> bool:
        """Check if animation has finished."""
        return self.is_finished

    def get_active_frames(self) -> List[int]:
        """Get frame indices where hitbox should be active (override in subclass)."""
        return []


class FolderAnimation:
    """Handles playback of a folder-based sprite sequence."""

    def __init__(self, frames: List[FolderAnimationFrame], loop: bool = False):
        """Initialize folder animation.

        Args:
            frames: List of folder animation frames
            loop: Whether animation should loop
        """
        self.frames = frames
        self.loop = loop
        self.current_frame_index = 0
        self.frame_counter = 0
        self.is_playing = True
        self.is_finished = False

    def update(self):
        """Update animation (call once per game frame)."""
        if not self.is_playing or self.is_finished:
            return

        # Increment frame counter
        self.frame_counter += 1

        # Check if it's time to advance to next frame
        current_frame = self.frames[self.current_frame_index]
        if self.frame_counter >= current_frame.duration:
            self.frame_counter = 0
            self.current_frame_index += 1

            # Check if animation is complete
            if self.current_frame_index >= len(self.frames):
                if self.loop:
                    self.current_frame_index = 0
                else:
                    self.current_frame_index = len(self.frames) - 1
                    self.is_finished = True

    def get_current_frame(self) -> FolderAnimationFrame:
        """Get the current frame to display."""
        return self.frames[self.current_frame_index]

    def reset(self):
        """Reset animation to beginning."""
        self.current_frame_index = 0
        self.frame_counter = 0
        self.is_finished = False
        self.is_playing = True

    def stop(self):
        """Stop animation playback."""
        self.is_playing = False

    def play(self):
        """Resume animation playback."""
        self.is_playing = True

    def is_complete(self) -> bool:
        """Check if animation has finished."""
        return self.is_finished


class SpriteManager:
    """Manages loading and caching of sprite images."""

    def __init__(self, sprite_directory: str):
        """Initialize sprite manager.

        Args:
            sprite_directory: Path to directory containing sprite PNG files
        """
        self.sprite_directory = sprite_directory
        self.sprite_cache: Dict[int, pygame.Surface] = {}

    def load_sprite(self, sprite_number: int, scale: float = 2.0) -> Optional[pygame.Surface]:
        """Load a sprite by number.

        Args:
            sprite_number: Sprite file number (e.g., 18664)
            scale: Scale factor for sprite (default 2x for visibility)

        Returns:
            Pygame surface with sprite, or None if not found
        """
        # Check cache first
        cache_key = sprite_number
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        # Load from file
        sprite_path = os.path.join(self.sprite_directory, f"{sprite_number}.png")

        if not os.path.exists(sprite_path):
            print(f"Warning: Sprite {sprite_number}.png not found at {sprite_path}")
            return None

        try:
            sprite = pygame.image.load(sprite_path).convert_alpha()

            # Scale sprite
            if scale != 1.0:
                original_size = sprite.get_size()
                new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
                sprite = pygame.transform.scale(sprite, new_size)

            # Cache it
            self.sprite_cache[cache_key] = sprite
            return sprite

        except Exception as e:
            print(f"Error loading sprite {sprite_number}: {e}")
            return None

    def preload_sprites(self, sprite_numbers: List[int], scale: float = 2.0):
        """Preload a list of sprites into cache.

        Args:
            sprite_numbers: List of sprite numbers to preload
            scale: Scale factor for sprites
        """
        for sprite_num in sprite_numbers:
            if sprite_num not in self.sprite_cache:
                self.load_sprite(sprite_num, scale)

    def clear_cache(self):
        """Clear sprite cache to free memory."""
        self.sprite_cache.clear()

    def load_sprite_from_folder(self, folder_path: str, frame_index: int, scale: float = 2.0) -> Optional[pygame.Surface]:
        """Load a sprite from a folder with frame_NNN.png naming.

        Args:
            folder_path: Path to folder containing frame_000.png, frame_001.png, etc.
            frame_index: Frame number (0, 1, 2, etc.)
            scale: Scale factor for sprite (default 2x for visibility)

        Returns:
            Pygame surface with sprite, or None if not found
        """
        # Create a unique cache key using folder path and frame index
        cache_key = hash(f"{folder_path}_{frame_index}")
        if cache_key in self.sprite_cache:
            return self.sprite_cache[cache_key]

        # Load from file
        sprite_path = os.path.join(folder_path, f"frame_{frame_index:03d}.png")

        if not os.path.exists(sprite_path):
            print(f"Warning: Frame {frame_index} not found at {sprite_path}")
            return None

        try:
            sprite = pygame.image.load(sprite_path).convert_alpha()

            # Scale sprite
            if scale != 1.0:
                original_size = sprite.get_size()
                new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
                sprite = pygame.transform.scale(sprite, new_size)

            # Cache it
            self.sprite_cache[cache_key] = sprite
            return sprite

        except Exception as e:
            print(f"Error loading sprite from {sprite_path}: {e}")
            return None


class AnimationController:
    """Controls animation playback for a character."""

    def __init__(self, sprite_manager: SpriteManager):
        """Initialize animation controller.

        Args:
            sprite_manager: Sprite manager for loading sprites
        """
        self.sprite_manager = sprite_manager
        self.current_animation: Optional[Animation | FolderAnimation] = None
        self.animations: Dict[str, Animation | FolderAnimation] = {}

    def add_animation(self, name: str, animation: Animation | FolderAnimation):
        """Add a named animation.

        Args:
            name: Animation name (e.g., "standing_light_punch")
            animation: Animation or FolderAnimation object
        """
        self.animations[name] = animation

    def play_animation(self, name: str, force_restart: bool = False):
        """Play a named animation.

        Args:
            name: Animation name
            force_restart: If True, restart animation even if already playing
        """
        if name not in self.animations:
            print(f"Warning: Animation '{name}' not found")
            return

        # Check if we're already playing this animation
        if self.current_animation == self.animations[name] and not force_restart:
            return

        # Switch to new animation
        self.current_animation = self.animations[name]
        self.current_animation.reset()

    def update(self):
        """Update current animation."""
        if self.current_animation:
            self.current_animation.update()

    def get_current_sprite(self) -> Optional[pygame.Surface]:
        """Get current sprite surface to render."""
        if not self.current_animation:
            return None

        # Check if this is a FolderAnimation or regular Animation
        if isinstance(self.current_animation, FolderAnimation):
            frame = self.current_animation.get_current_frame()
            return self.sprite_manager.load_sprite_from_folder(frame.folder_path, frame.frame_index)
        else:
            sprite_number = self.current_animation.get_current_sprite_number()
            return self.sprite_manager.load_sprite(sprite_number)

    def is_animation_complete(self) -> bool:
        """Check if current animation has finished."""
        if not self.current_animation:
            return True
        return self.current_animation.is_complete()

    def get_current_animation_name(self) -> Optional[str]:
        """Get name of currently playing animation."""
        if not self.current_animation:
            return None

        for name, anim in self.animations.items():
            if anim == self.current_animation:
                return name
        return None


def create_simple_animation(sprite_numbers: List[int], frame_duration: int = 1,
                           loop: bool = False) -> Animation:
    """Helper function to create simple animation from sprite list.

    Args:
        sprite_numbers: List of sprite numbers
        frame_duration: How many game frames to hold each sprite
        loop: Whether to loop animation

    Returns:
        Animation object
    """
    frames = [AnimationFrame(sprite_num, frame_duration) for sprite_num in sprite_numbers]
    return Animation(frames, loop)


def create_folder_animation(folder_path: str, frame_count: int, frame_duration: int = 1,
                            loop: bool = False) -> FolderAnimation:
    """Helper function to create animation from folder with frame_NNN.png files.

    Args:
        folder_path: Path to folder containing frame_000.png, frame_001.png, etc.
        frame_count: Number of frames in the animation
        frame_duration: How many game frames to hold each sprite
        loop: Whether to loop animation

    Returns:
        FolderAnimation object
    """
    frames = [FolderAnimationFrame(folder_path, i, frame_duration) for i in range(frame_count)]
    return FolderAnimation(frames, loop)
