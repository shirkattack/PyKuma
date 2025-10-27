"""
SF3:3S Keyboard Input System

Maps keyboard inputs to authentic SF3 fighting game controls.
Supports both single-player and 2-player local play.

Controls:
Player 1: WASD + UIOJKL
Player 2: Arrow Keys + Numpad

Key Features:
- Motion inputs (QCF, DP, etc.)
- Button combinations
- Input buffering
- Special move detection
"""

import pygame
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

# Import our SF3 systems
from ..systems.sf3_core import SF3InputDirection
from ..systems.sf3_inputs import SF3ButtonInput


class InputState(Enum):
    """Input button states"""
    RELEASED = 0
    PRESSED = 1
    HELD = 2


@dataclass
class InputFrame:
    """Single frame of input data"""
    direction: SF3InputDirection = SF3InputDirection.NEUTRAL
    buttons: Set[SF3ButtonInput] = field(default_factory=set)
    frame_number: int = 0


@dataclass 
class MotionInput:
    """Motion input pattern (like QCF, DP)"""
    name: str
    directions: List[SF3InputDirection]
    max_frames: int = 20  # Maximum frames to complete motion
    

class SF3KeyboardInput:
    """
    SF3 Keyboard Input Handler
    
    Handles keyboard input for fighting game controls with motion detection,
    input buffering, and special move recognition.
    """
    
    def __init__(self):
        # Input history for motion detection
        self.input_buffer_size = 30
        self.input_history: deque[InputFrame] = deque(maxlen=self.input_buffer_size)
        
        # Current frame counter
        self.frame_counter = 0
        
        # Key mappings
        self.setup_key_mappings()
        
        # Motion inputs
        self.setup_motion_inputs()
        
        # Current input state
        self.current_direction = SF3InputDirection.NEUTRAL
        self.current_buttons: Set[SF3ButtonInput] = set()
        self.held_keys: Set[int] = set()
        
        print("SF3 Keyboard Input System initialized")
    
    def setup_key_mappings(self):
        """Setup keyboard mappings for players"""
        
        # Player 1 Controls (WASD + UIOJKL)
        self.p1_keys = {
            # Movement
            pygame.K_a: 'left',
            pygame.K_d: 'right', 
            pygame.K_w: 'up',
            pygame.K_s: 'down',
            
            # Attacks
            pygame.K_u: SF3ButtonInput.LIGHT_PUNCH,
            pygame.K_i: SF3ButtonInput.MEDIUM_PUNCH,
            pygame.K_o: SF3ButtonInput.HEAVY_PUNCH,
            pygame.K_j: SF3ButtonInput.LIGHT_KICK,
            pygame.K_k: SF3ButtonInput.MEDIUM_KICK,
            pygame.K_l: SF3ButtonInput.HEAVY_KICK,
        }
        
        # Player 2 Controls (Arrow Keys + Numpad)
        self.p2_keys = {
            # Movement
            pygame.K_LEFT: 'left',
            pygame.K_RIGHT: 'right',
            pygame.K_UP: 'up', 
            pygame.K_DOWN: 'down',
            
            # Attacks
            pygame.K_KP4: SF3ButtonInput.LIGHT_PUNCH,
            pygame.K_KP5: SF3ButtonInput.MEDIUM_PUNCH,
            pygame.K_KP6: SF3ButtonInput.HEAVY_PUNCH,
            pygame.K_KP1: SF3ButtonInput.LIGHT_KICK,
            pygame.K_KP2: SF3ButtonInput.MEDIUM_KICK,
            pygame.K_KP3: SF3ButtonInput.HEAVY_KICK,
        }
    
    def setup_motion_inputs(self):
        """Setup special move motion inputs"""
        
        self.motion_inputs = {
            # Quarter Circle Forward (Hadoken)
            "QCF": MotionInput(
                name="QCF",
                directions=[
                    SF3InputDirection.DOWN,
                    SF3InputDirection.DOWN_FORWARD,
                    SF3InputDirection.FORWARD
                ],
                max_frames=15
            ),
            
            # Quarter Circle Back (Tatsumaki)
            "QCB": MotionInput(
                name="QCB", 
                directions=[
                    SF3InputDirection.DOWN,
                    SF3InputDirection.DOWN_BACK,
                    SF3InputDirection.BACK
                ],
                max_frames=15
            ),
            
            # Dragon Punch (Shoryuken)
            "DP": MotionInput(
                name="DP",
                directions=[
                    SF3InputDirection.FORWARD,
                    SF3InputDirection.DOWN,
                    SF3InputDirection.DOWN_FORWARD
                ],
                max_frames=12
            ),
            
            # Half Circle Forward
            "HCF": MotionInput(
                name="HCF",
                directions=[
                    SF3InputDirection.BACK,
                    SF3InputDirection.DOWN_BACK,
                    SF3InputDirection.DOWN,
                    SF3InputDirection.DOWN_FORWARD,
                    SF3InputDirection.FORWARD
                ],
                max_frames=20
            ),
            
            # Half Circle Back  
            "HCB": MotionInput(
                name="HCB",
                directions=[
                    SF3InputDirection.FORWARD,
                    SF3InputDirection.DOWN_FORWARD,
                    SF3InputDirection.DOWN,
                    SF3InputDirection.DOWN_BACK,
                    SF3InputDirection.BACK
                ],
                max_frames=20
            )
        }
    
    def update(self, events: List[pygame.event.Event], player_number: int = 1) -> Tuple[SF3InputDirection, Set[SF3ButtonInput]]:
        """
        Update input state and return current inputs
        
        Args:
            events: Pygame events from this frame
            player_number: Which player's inputs to process (1 or 2)
            
        Returns:
            Tuple of (direction, buttons) for this frame
        """
        
        self.frame_counter += 1
        
        # Get key mappings for this player
        key_map = self.p1_keys if player_number == 1 else self.p2_keys
        
        # Process events
        for event in events:
            if event.type == pygame.KEYDOWN:
                self.held_keys.add(event.key)
            elif event.type == pygame.KEYUP:
                self.held_keys.discard(event.key)
        
        # Determine current direction
        direction = self._get_direction_from_keys(key_map, player_number)
        
        # Determine current buttons
        buttons = self._get_buttons_from_keys(key_map)
        
        # Store in input history
        input_frame = InputFrame(
            direction=direction,
            buttons=buttons.copy(),
            frame_number=self.frame_counter
        )
        self.input_history.append(input_frame)
        
        # Update current state
        self.current_direction = direction
        self.current_buttons = buttons
        
        return direction, buttons
    
    def _get_direction_from_keys(self, key_map: Dict, player_number: int) -> SF3InputDirection:
        """Convert held keys to SF3 direction"""
        
        # Check directional keys
        left = any(key in self.held_keys for key, action in key_map.items() if action == 'left')
        right = any(key in self.held_keys for key, action in key_map.items() if action == 'right')
        up = any(key in self.held_keys for key, action in key_map.items() if action == 'up')
        down = any(key in self.held_keys for key, action in key_map.items() if action == 'down')
        
        # Handle facing direction (Player 1 faces right, Player 2 faces left by default)
        if player_number == 1:
            forward = right
            back = left
        else:
            forward = left  # P2 faces left, so left is forward
            back = right
        
        # Convert to SF3 directions
        if up and forward:
            return SF3InputDirection.UP_FORWARD
        elif up and back:
            return SF3InputDirection.UP_BACK
        elif down and forward:
            return SF3InputDirection.DOWN_FORWARD
        elif down and back:
            return SF3InputDirection.DOWN_BACK
        elif up:
            return SF3InputDirection.UP
        elif down:
            return SF3InputDirection.DOWN
        elif forward:
            return SF3InputDirection.FORWARD
        elif back:
            return SF3InputDirection.BACK
        else:
            return SF3InputDirection.NEUTRAL
    
    def _get_buttons_from_keys(self, key_map: Dict) -> Set[SF3ButtonInput]:
        """Convert held keys to SF3 buttons"""
        
        buttons = set()
        
        for key in self.held_keys:
            if key in key_map:
                action = key_map[key]
                if isinstance(action, SF3ButtonInput):
                    buttons.add(action)
        
        return buttons
    
    def check_motion_input(self, motion_name: str, button: SF3ButtonInput) -> bool:
        """
        Check if a motion input was performed with the given button
        
        Args:
            motion_name: Name of motion (QCF, DP, etc.)
            button: Button that should be pressed with motion
            
        Returns:
            True if motion + button was detected
        """
        
        if motion_name not in self.motion_inputs:
            return False
        
        motion = self.motion_inputs[motion_name]
        
        # Check if button is currently pressed
        if button not in self.current_buttons:
            return False
        
        # Check motion in input history
        return self._check_motion_in_history(motion)
    
    def _check_motion_in_history(self, motion: MotionInput) -> bool:
        """Check if motion pattern exists in recent input history"""
        
        if len(self.input_history) < len(motion.directions):
            return False
        
        # Look for motion pattern in recent frames
        recent_frames = list(self.input_history)[-motion.max_frames:]
        
        # Extract just the directions
        recent_directions = [frame.direction for frame in recent_frames]
        
        # Look for the motion pattern
        return self._find_motion_pattern(recent_directions, motion.directions)
    
    def _find_motion_pattern(self, history: List[SF3InputDirection], pattern: List[SF3InputDirection]) -> bool:
        """Find motion pattern in direction history"""
        
        if len(pattern) > len(history):
            return False
        
        # Look for pattern at end of history (most recent)
        pattern_index = 0
        
        # Work backwards through history
        for i in range(len(history) - 1, -1, -1):
            if history[i] == pattern[len(pattern) - 1 - pattern_index]:
                pattern_index += 1
                if pattern_index == len(pattern):
                    return True
            elif pattern_index > 0:
                # Reset if we break the pattern
                pattern_index = 0
                if history[i] == pattern[len(pattern) - 1]:
                    pattern_index = 1
        
        return False
    
    def get_special_move_input(self) -> Optional[str]:
        """
        Check for special move inputs and return the move name
        
        Returns:
            Move name if special input detected, None otherwise
        """
        
        # Check for common special moves
        if self.check_motion_input("QCF", SF3ButtonInput.LIGHT_PUNCH):
            return "hadoken_light"
        elif self.check_motion_input("QCF", SF3ButtonInput.MEDIUM_PUNCH):
            return "hadoken_medium"
        elif self.check_motion_input("QCF", SF3ButtonInput.HEAVY_PUNCH):
            return "hadoken_heavy"
        
        elif self.check_motion_input("DP", SF3ButtonInput.LIGHT_PUNCH):
            return "shoryuken_light"
        elif self.check_motion_input("DP", SF3ButtonInput.MEDIUM_PUNCH):
            return "shoryuken_medium"
        elif self.check_motion_input("DP", SF3ButtonInput.HEAVY_PUNCH):
            return "shoryuken_heavy"
        
        elif self.check_motion_input("QCB", SF3ButtonInput.LIGHT_KICK):
            return "tatsumaki_light"
        elif self.check_motion_input("QCB", SF3ButtonInput.MEDIUM_KICK):
            return "tatsumaki_medium"
        elif self.check_motion_input("QCB", SF3ButtonInput.HEAVY_KICK):
            return "tatsumaki_heavy"
        
        return None
    
    def get_normal_attack_input(self) -> Optional[str]:
        """
        Check for normal attack inputs
        
        Returns:
            Attack name if normal attack detected, None otherwise
        """
        
        # Check current direction for standing/crouching
        is_crouching = self.current_direction in [
            SF3InputDirection.DOWN,
            SF3InputDirection.DOWN_FORWARD,
            SF3InputDirection.DOWN_BACK
        ]
        
        prefix = "crouching" if is_crouching else "standing"
        
        # Check button presses (only newly pressed, not held)
        if SF3ButtonInput.LIGHT_PUNCH in self.current_buttons:
            return f"{prefix}_light_punch"
        elif SF3ButtonInput.MEDIUM_PUNCH in self.current_buttons:
            return f"{prefix}_medium_punch"
        elif SF3ButtonInput.HEAVY_PUNCH in self.current_buttons:
            return f"{prefix}_heavy_punch"
        elif SF3ButtonInput.LIGHT_KICK in self.current_buttons:
            return f"{prefix}_light_kick"
        elif SF3ButtonInput.MEDIUM_KICK in self.current_buttons:
            return f"{prefix}_medium_kick"
        elif SF3ButtonInput.HEAVY_KICK in self.current_buttons:
            return f"{prefix}_heavy_kick"
        
        return None
    
    def get_input_display_string(self) -> str:
        """Get string representation of current inputs for debugging"""
        
        direction_names = {
            SF3InputDirection.NEUTRAL: "5",
            SF3InputDirection.FORWARD: "6",
            SF3InputDirection.BACK: "4", 
            SF3InputDirection.UP: "8",
            SF3InputDirection.DOWN: "2",
            SF3InputDirection.UP_FORWARD: "9",
            SF3InputDirection.UP_BACK: "7",
            SF3InputDirection.DOWN_FORWARD: "3",
            SF3InputDirection.DOWN_BACK: "1"
        }
        
        button_names = {
            SF3ButtonInput.LIGHT_PUNCH: "LP",
            SF3ButtonInput.MEDIUM_PUNCH: "MP",
            SF3ButtonInput.HEAVY_PUNCH: "HP",
            SF3ButtonInput.LIGHT_KICK: "LK",
            SF3ButtonInput.MEDIUM_KICK: "MK", 
            SF3ButtonInput.HEAVY_KICK: "HK"
        }
        
        direction_str = direction_names.get(self.current_direction, "?")
        button_strs = [button_names.get(btn, "?") for btn in self.current_buttons]
        
        if button_strs:
            return f"{direction_str}+{'+'.join(button_strs)}"
        else:
            return direction_str
    
    def clear_input_history(self):
        """Clear input history (useful for round resets)"""
        self.input_history.clear()
        self.frame_counter = 0


if __name__ == "__main__":
    # Test input system
    print("Testing SF3 Keyboard Input System...")
    
    pygame.init()
    
    input_system = SF3KeyboardInput()
    
    print("✅ Input system created")
    print("🎮 Key mappings:")
    print("   Player 1: WASD (movement) + UIOJKL (attacks)")
    print("   Player 2: Arrow Keys (movement) + Numpad (attacks)")
    print("🥋 Special moves:")
    print("   QCF+P = Hadoken")
    print("   DP+P = Shoryuken") 
    print("   QCB+K = Tatsumaki")
    print("🚀 Input system ready for fighting game!")
