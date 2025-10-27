"""Animation loader that reads animation data from YAML configuration."""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass
from street_fighter_3rd.systems.animation import (
    Animation,
    FolderAnimation,
    AnimationFrame,
    FolderAnimationFrame,
    create_simple_animation,
    create_folder_animation
)
from street_fighter_3rd.data.enums import HitType


@dataclass
class HitboxConfig:
    """Hitbox configuration from YAML."""
    active_frames: list[int]  # Frames where hitbox is active (1-indexed)
    offset_x: int
    offset_y: int
    width: int
    height: int
    damage: int
    hitstun: int
    hit_type: HitType


@dataclass
class ProjectileConfig:
    """Projectile configuration from YAML."""
    spawn_frame: int
    offset_x: int
    offset_y: int
    speeds: dict[str, float]  # Speed by strength (light, medium, heavy)


@dataclass
class AnimationConfig:
    """Animation configuration from YAML."""
    name: str
    source: str  # "numbered_sprites" or "folder"
    sprites: Optional[list[int]] = None  # For numbered sprites
    path: Optional[str] = None  # For folder-based
    frames: Optional[int] = None  # For folder-based
    frame_duration: int = 1
    loop: bool = False
    hitbox: Optional[HitboxConfig] = None
    projectile: Optional[ProjectileConfig] = None


class AnimationLoadError(Exception):
    """Raised when animation loading fails."""
    pass


class AnimationLoader:
    """Loads and validates animation data from YAML configuration."""

    def __init__(self, yaml_path: str):
        """Initialize animation loader.

        Args:
            yaml_path: Path to animations.yaml file
        """
        self.yaml_path = yaml_path
        self.config: Dict[str, Any] = {}
        self._load_yaml()

    def _load_yaml(self):
        """Load and parse the YAML configuration file."""
        if not os.path.exists(self.yaml_path):
            raise AnimationLoadError(f"Animation config not found: {self.yaml_path}")

        try:
            with open(self.yaml_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise AnimationLoadError(f"Failed to parse YAML: {e}")

        if not self.config or 'characters' not in self.config:
            raise AnimationLoadError("Invalid YAML: missing 'characters' section")

    def get_character_config(self, character_name: str) -> Dict[str, Any]:
        """Get configuration for a specific character.

        Args:
            character_name: Name of the character (e.g., "akuma")

        Returns:
            Character configuration dictionary

        Raises:
            AnimationLoadError: If character not found
        """
        if character_name not in self.config['characters']:
            raise AnimationLoadError(f"Character '{character_name}' not found in config")

        return self.config['characters'][character_name]

    def load_character_animations(self, character, character_name: str):
        """Load all animations for a character from YAML.

        Args:
            character: Character instance to load animations into
            character_name: Name of character in YAML (e.g., "akuma")

        Raises:
            AnimationLoadError: If loading fails
        """
        char_config = self.get_character_config(character_name)
        animations = char_config.get('animations', {})

        if not animations:
            raise AnimationLoadError(f"No animations defined for {character_name}")

        print(f"Loading {len(animations)} animations for {character_name}...")

        for anim_name, anim_data in animations.items():
            try:
                anim_config = self._parse_animation_config(anim_name, anim_data)
                animation = self._create_animation(anim_config)
                character.animation_controller.add_animation(anim_name, animation)

                # Store hitbox config if present (for collision system to use)
                if anim_config.hitbox:
                    if not hasattr(character, 'animation_hitboxes'):
                        character.animation_hitboxes = {}
                    character.animation_hitboxes[anim_name] = anim_config.hitbox

                # Store projectile config if present (for special moves)
                if anim_config.projectile:
                    if not hasattr(character, 'animation_projectiles'):
                        character.animation_projectiles = {}
                    character.animation_projectiles[anim_name] = anim_config.projectile

                print(f"  ✓ Loaded '{anim_name}' ({anim_config.source})")

            except Exception as e:
                # Validation: log error but continue loading other animations
                print(f"  ✗ Failed to load '{anim_name}': {e}")
                continue

        print(f"Animation loading complete for {character_name}")

    def _parse_animation_config(self, name: str, data: Dict[str, Any]) -> AnimationConfig:
        """Parse animation data from YAML into AnimationConfig.

        Args:
            name: Animation name
            data: Animation data from YAML

        Returns:
            AnimationConfig object

        Raises:
            AnimationLoadError: If data is invalid
        """
        source = data.get('source')
        if not source:
            raise AnimationLoadError(f"Animation '{name}': missing 'source' field")

        if source not in ['numbered_sprites', 'folder']:
            raise AnimationLoadError(f"Animation '{name}': invalid source '{source}'")

        # Parse hitbox if present
        hitbox = None
        if 'hitbox' in data:
            hitbox_data = data['hitbox']
            try:
                hit_type_str = hitbox_data.get('hit_type', 'MID')
                hit_type = HitType[hit_type_str]  # Convert string to enum

                hitbox = HitboxConfig(
                    active_frames=hitbox_data['active_frames'],
                    offset_x=hitbox_data['offset_x'],
                    offset_y=hitbox_data['offset_y'],
                    width=hitbox_data['width'],
                    height=hitbox_data['height'],
                    damage=hitbox_data['damage'],
                    hitstun=hitbox_data['hitstun'],
                    hit_type=hit_type
                )
            except (KeyError, ValueError) as e:
                raise AnimationLoadError(f"Animation '{name}': invalid hitbox data: {e}")

        # Parse projectile if present
        projectile = None
        if 'projectile' in data:
            proj_data = data['projectile']
            try:
                projectile = ProjectileConfig(
                    spawn_frame=proj_data['spawn_frame'],
                    offset_x=proj_data['offset_x'],
                    offset_y=proj_data['offset_y'],
                    speeds=proj_data['speeds']
                )
            except (KeyError, ValueError) as e:
                raise AnimationLoadError(f"Animation '{name}': invalid projectile data: {e}")

        config = AnimationConfig(
            name=name,
            source=source,
            sprites=data.get('sprites'),
            path=data.get('path'),
            frames=data.get('frames'),
            frame_duration=data.get('frame_duration', 1),
            loop=data.get('loop', False),
            hitbox=hitbox,
            projectile=projectile
        )

        # Validation
        if source == 'numbered_sprites' and not config.sprites:
            raise AnimationLoadError(f"Animation '{name}': missing 'sprites' list")
        if source == 'folder' and (not config.path or not config.frames):
            raise AnimationLoadError(f"Animation '{name}': missing 'path' or 'frames'")

        return config

    def _create_animation(self, config: AnimationConfig) -> Animation | FolderAnimation:
        """Create an Animation or FolderAnimation object from config.

        Args:
            config: Animation configuration

        Returns:
            Animation or FolderAnimation object

        Raises:
            AnimationLoadError: If animation creation fails
        """
        if config.source == 'numbered_sprites':
            return create_simple_animation(
                sprite_numbers=config.sprites,
                frame_duration=config.frame_duration,
                loop=config.loop
            )
        else:  # folder
            # Validate folder exists
            if not os.path.exists(config.path):
                raise AnimationLoadError(f"Animation folder not found: {config.path}")

            return create_folder_animation(
                folder_path=config.path,
                frame_count=config.frames,
                frame_duration=config.frame_duration,
                loop=config.loop
            )

    def get_character_settings(self, character_name: str) -> Dict[str, Any]:
        """Get character-specific settings (scale, ground_offset, etc.).

        Args:
            character_name: Name of character

        Returns:
            Dictionary of settings
        """
        char_config = self.get_character_config(character_name)
        return {
            'sprite_scale': char_config.get('sprite_scale', 2.0),
            'ground_offset': char_config.get('ground_offset', 136)
        }
