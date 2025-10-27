"""Game mode definitions and configuration."""

from enum import Enum, auto
from dataclasses import dataclass, replace
from typing import Optional


class GameMode(Enum):
    """Different game modes with different features enabled."""
    NORMAL = auto()      # Standard fighting game
    TRAINING = auto()    # Practice mode with infinite health
    DEV = auto()         # Full debug mode for development
    VERSUS = auto()      # 2-player versus mode
    DEMO = auto()        # AI vs AI demonstration


@dataclass
class GameModeConfig:
    """Configuration for different game modes."""
    
    # Visual debug features
    show_hitboxes: bool = False
    show_hurtboxes: bool = False
    show_frame_data: bool = False
    show_input_display: bool = False
    show_collision_info: bool = False
    show_performance_metrics: bool = False
    
    # Gameplay features
    infinite_health: bool = False
    no_rounds: bool = False
    no_timer: bool = False
    auto_reset_position: bool = False
    
    # Training mode features
    show_damage_numbers: bool = False
    show_frame_advantage: bool = False
    show_combo_counter: bool = False
    record_replay: bool = False
    
    # Dev mode features
    show_state_machine: bool = False
    show_memory_usage: bool = False
    show_fps_counter: bool = False
    enable_hot_reload: bool = False


# Predefined configurations for each mode
GAME_MODE_CONFIGS = {
    GameMode.NORMAL: GameModeConfig(
        # Clean gameplay experience
        show_combo_counter=True
    ),
    
    GameMode.TRAINING: GameModeConfig(
        # Training features
        show_hitboxes=True,
        show_hurtboxes=True,
        show_frame_data=True,
        show_damage_numbers=True,
        show_frame_advantage=True,
        show_combo_counter=True,
        infinite_health=True,
        no_rounds=True,
        no_timer=True,
        auto_reset_position=True,
        record_replay=True
    ),
    
    GameMode.DEV: GameModeConfig(
        # Full debug mode
        show_hitboxes=True,
        show_hurtboxes=True,
        show_frame_data=True,
        show_input_display=True,
        show_collision_info=True,
        show_performance_metrics=True,
        show_damage_numbers=True,
        show_frame_advantage=True,
        show_combo_counter=True,
        show_state_machine=True,
        show_memory_usage=True,
        show_fps_counter=True,
        infinite_health=True,
        no_rounds=True,
        no_timer=True,
        enable_hot_reload=True
    ),
    
    GameMode.VERSUS: GameModeConfig(
        # Standard versus with some visual aids
        show_combo_counter=True,
        show_damage_numbers=True
    ),
    
    GameMode.DEMO: GameModeConfig(
        # Demo mode for showcasing
        show_combo_counter=True,
        show_damage_numbers=True,
        no_timer=True
    )
}


class GameModeManager:
    """Manages current game mode and configuration."""
    
    def __init__(self, initial_mode: GameMode = GameMode.NORMAL):
        self.current_mode = initial_mode
        self.config = replace(GAME_MODE_CONFIGS[initial_mode])
        
    def set_mode(self, mode: GameMode):
        """Switch to a different game mode."""
        self.current_mode = mode
        self.config = GAME_MODE_CONFIGS[mode]
        
    def get_config(self) -> GameModeConfig:
        """Get current mode configuration."""
        return self.config
        
    def is_debug_mode(self) -> bool:
        """Check if any debug features are enabled."""
        return (self.config.show_hitboxes or 
                self.config.show_hurtboxes or 
                self.config.show_frame_data or
                self.config.show_collision_info)
                
    def is_training_mode(self) -> bool:
        """Check if in training mode."""
        return self.current_mode == GameMode.TRAINING
        
    def is_dev_mode(self) -> bool:
        """Check if in development mode."""
        return self.current_mode == GameMode.DEV
        
    def toggle_feature(self, feature_name: str):
        """Toggle a specific debug feature."""
        if hasattr(self.config, feature_name):
            current_value = getattr(self.config, feature_name)
            setattr(self.config, feature_name, not current_value)
            
    def get_mode_description(self) -> str:
        """Get human-readable description of current mode."""
        descriptions = {
            GameMode.NORMAL: "Standard fighting game experience",
            GameMode.TRAINING: "Practice mode with infinite health and debug tools",
            GameMode.DEV: "Full development mode with all debug features",
            GameMode.VERSUS: "Local 2-player versus matches",
            GameMode.DEMO: "AI demonstration mode"
        }
        return descriptions.get(self.current_mode, "Unknown mode")
