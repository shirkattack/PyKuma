"""Input system with keyboard and joystick support, including input buffer for special moves."""

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Dict, Tuple
import pygame

from street_fighter_3rd.data.enums import InputDirection, Button
from street_fighter_3rd.data.constants import INPUT_BUFFER_SIZE, MOTION_INPUT_WINDOW


@dataclass
class InputState:
    """Represents the input state for a single frame."""
    direction: InputDirection
    buttons_pressed: set[Button]
    buttons_just_pressed: set[Button]  # New this frame
    buttons_just_released: set[Button]  # Released this frame
    frame_number: int


@dataclass
class MotionInput:
    """Defines a motion input pattern (like quarter-circle forward)."""
    name: str
    directions: List[InputDirection]
    button: Button
    max_frames: int = MOTION_INPUT_WINDOW  # Frames to complete the motion


class PlayerInput:
    """Manages input for a single player with keyboard and joystick support."""

    def __init__(self, player_number: int):
        """Initialize player input.

        Args:
            player_number: 1 or 2
        """
        self.player_number = player_number
        self.input_buffer: Deque[InputState] = deque(maxlen=INPUT_BUFFER_SIZE)
        self.frame_count = 0

        # Current state
        self.current_direction = InputDirection.NEUTRAL
        self.buttons_held: set[Button] = set()
        self.buttons_pressed_this_frame: set[Button] = set()
        self.buttons_released_this_frame: set[Button] = set()

        # Joystick
        self.joystick: Optional[pygame.joystick.Joystick] = None
        self.joystick_deadzone = 0.5  # For analog sticks

        # Configure key bindings
        self._setup_key_bindings()
        self._setup_joystick_bindings()

        # Define common motion inputs
        self._setup_motion_inputs()

    def _setup_key_bindings(self):
        """Set up keyboard key bindings based on player number."""
        if self.player_number == 1:
            # Player 1: WASD + JKLUIO
            self.key_map = {
                # Directions
                pygame.K_w: 'up',
                pygame.K_s: 'down',
                pygame.K_a: 'left',
                pygame.K_d: 'right',
                # Attacks
                pygame.K_j: Button.LIGHT_PUNCH,
                pygame.K_k: Button.MEDIUM_PUNCH,
                pygame.K_l: Button.HEAVY_PUNCH,
                pygame.K_u: Button.LIGHT_KICK,
                pygame.K_i: Button.MEDIUM_KICK,
                pygame.K_o: Button.HEAVY_KICK,
            }
        else:
            # Player 2: Arrow keys + NumPad
            self.key_map = {
                # Directions
                pygame.K_UP: 'up',
                pygame.K_DOWN: 'down',
                pygame.K_LEFT: 'left',
                pygame.K_RIGHT: 'right',
                # Attacks
                pygame.K_KP1: Button.LIGHT_PUNCH,
                pygame.K_KP2: Button.MEDIUM_PUNCH,
                pygame.K_KP3: Button.HEAVY_PUNCH,
                pygame.K_KP4: Button.LIGHT_KICK,
                pygame.K_KP5: Button.MEDIUM_KICK,
                pygame.K_KP6: Button.HEAVY_KICK,
            }

    def _setup_joystick_bindings(self):
        """Set up joystick button bindings for Brooks UFB / standard fight stick."""
        # Standard arcade button layout (modifiable)
        self.joystick_button_map = {
            0: Button.LIGHT_PUNCH,
            1: Button.MEDIUM_PUNCH,
            2: Button.HEAVY_PUNCH,
            3: Button.LIGHT_KICK,
            4: Button.MEDIUM_KICK,
            5: Button.HEAVY_KICK,
        }

        # For leverless (hitbox-style) directional buttons
        # These will be detected as buttons on Brooks UFB
        self.joystick_direction_buttons = {
            # Common leverless button assignments (may need adjustment)
            6: 'up',      # Try button 6 for up
            7: 'down',    # Try button 7 for down
            8: 'right',   # Swap: Try button 8 for right
            9: 'left',    # Swap: Try button 9 for left
            # Alternative mappings
            10: 'up',     # Alternative button 10 for up
            11: 'down',   # Alternative button 11 for down
            12: 'right',  # Swap: Alternative button 12 for right
            13: 'left',   # Swap: Alternative button 13 for left
            # More common hitbox mappings
            14: 'up',     # Some hitboxes use 14-17
            15: 'down',   
            16: 'left',   
            17: 'right',  
        }

    def _setup_motion_inputs(self):
        """Define common special move motion inputs."""
        self.motion_inputs = [
            # Quarter-circle forward (hadoken)
            MotionInput(
                name="QCF",  # 236
                directions=[InputDirection.DOWN, InputDirection.DOWN_FORWARD, InputDirection.FORWARD],
                button=Button.LIGHT_PUNCH
            ),
            # Quarter-circle back
            MotionInput(
                name="QCB",  # 214
                directions=[InputDirection.DOWN, InputDirection.DOWN_BACK, InputDirection.BACK],
                button=Button.LIGHT_PUNCH
            ),
            # Dragon punch (shoryuken)
            MotionInput(
                name="DP",  # 623
                directions=[InputDirection.FORWARD, InputDirection.DOWN, InputDirection.DOWN_FORWARD],
                button=Button.LIGHT_PUNCH
            ),
            # Half-circle forward
            MotionInput(
                name="HCF",  # 41236
                directions=[
                    InputDirection.BACK,
                    InputDirection.DOWN_BACK,
                    InputDirection.DOWN,
                    InputDirection.DOWN_FORWARD,
                    InputDirection.FORWARD
                ],
                button=Button.LIGHT_PUNCH
            ),
        ]

    def connect_joystick(self, joystick_index: int) -> bool:
        """Connect a joystick to this player.

        Args:
            joystick_index: Index of the joystick to connect

        Returns:
            True if successfully connected
        """
        try:
            self.joystick = pygame.joystick.Joystick(joystick_index)
            self.joystick.init()
            print(f"Player {self.player_number} connected to: {self.joystick.get_name()}")
            return True
        except pygame.error as e:
            print(f"Failed to connect joystick {joystick_index}: {e}")
            return False

    def update(self, facing_right: bool = True):
        """Update input state for this frame.

        Args:
            facing_right: Whether player is facing right (for input mirroring)
        """
        self.frame_count += 1
        self.buttons_pressed_this_frame.clear()
        self.buttons_released_this_frame.clear()

        # Read keyboard input
        keys = pygame.key.get_pressed()
        direction_input = self._read_keyboard_direction(keys, facing_right)

        # Read joystick input if connected
        if self.joystick:
            joy_direction = self._read_joystick_direction(facing_right)
            if joy_direction != InputDirection.NEUTRAL:
                direction_input = joy_direction

            joy_buttons = self._read_joystick_buttons()
            for button in joy_buttons:
                if button not in self.buttons_held:
                    self.buttons_pressed_this_frame.add(button)
                self.buttons_held.add(button)

        # Update button states from keyboard
        for key, action in self.key_map.items():
            if isinstance(action, Button):
                if keys[key]:
                    if action not in self.buttons_held:
                        self.buttons_pressed_this_frame.add(action)
                    self.buttons_held.add(action)
                else:
                    if action in self.buttons_held:
                        self.buttons_released_this_frame.add(action)
                        self.buttons_held.discard(action)

        self.current_direction = direction_input

        # Add to input buffer
        input_state = InputState(
            direction=self.current_direction,
            buttons_pressed=self.buttons_held.copy(),
            buttons_just_pressed=self.buttons_pressed_this_frame.copy(),
            buttons_just_released=self.buttons_released_this_frame.copy(),
            frame_number=self.frame_count
        )
        self.input_buffer.append(input_state)

    def _read_keyboard_direction(self, keys, facing_right: bool) -> InputDirection:
        """Read directional input from keyboard.

        Args:
            keys: Pygame key state
            facing_right: Whether player is facing right

        Returns:
            InputDirection enum value
        """
        up = down = left = right = False

        for key, action in self.key_map.items():
            if keys[key] and isinstance(action, str):
                if action == 'up':
                    up = True
                elif action == 'down':
                    down = True
                elif action == 'left':
                    left = True
                elif action == 'right':
                    right = True

        # Convert to absolute directions based on facing
        if not facing_right:
            # Mirror inputs when facing left
            left, right = right, left

        # Convert to numpad notation
        return self._directions_to_input(up, down, left, right)

    def _read_joystick_direction(self, facing_right: bool) -> InputDirection:
        """Read directional input from joystick.

        Args:
            facing_right: Whether player is facing right

        Returns:
            InputDirection enum value
        """
        if not self.joystick:
            return InputDirection.NEUTRAL

        try:
            up = down = left = right = False

            # Check for leverless (hitbox-style) button inputs first
            for button_num, direction in self.joystick_direction_buttons.items():
                try:
                    if button_num < self.joystick.get_numbuttons():
                        if self.joystick.get_button(button_num):
                            # Only print direction debug once per press
                            # Direction debug disabled for stability
                            # if not hasattr(self, '_last_direction_buttons'):
                            #     self._last_direction_buttons = set()
                            # if button_num not in self._last_direction_buttons:
                            #     print(f"Direction button {button_num} pressed ({direction})")
                            #     self._last_direction_buttons.add(button_num)
                            if direction == 'up':
                                up = True
                            elif direction == 'down':
                                down = True
                            elif direction == 'left':
                                left = True
                            elif direction == 'right':
                                right = True
                        else:
                            # Button released, remove from tracking
                            if hasattr(self, '_last_direction_buttons') and button_num in self._last_direction_buttons:
                                self._last_direction_buttons.remove(button_num)
                except (pygame.error, IndexError):
                    continue

            # If no button directions, check analog stick and hat
            if not (up or down or left or right):
                # Check analog stick
                try:
                    if self.joystick.get_numaxes() >= 2:
                        x_axis = self.joystick.get_axis(0)
                        y_axis = self.joystick.get_axis(1)
                        
                        # Analog debug disabled for stability
                        # if abs(x_axis) > 0.1 or abs(y_axis) > 0.1:
                        #     if not hasattr(self, '_last_analog_values'):
                        #         self._last_analog_values = (0.0, 0.0)
                        #     if abs(x_axis - self._last_analog_values[0]) > 0.2 or abs(y_axis - self._last_analog_values[1]) > 0.2:
                        #         print(f"Analog stick: X={x_axis:.2f}, Y={y_axis:.2f}")
                        #         self._last_analog_values = (x_axis, y_axis)

                        if abs(x_axis) > self.joystick_deadzone:
                            right = x_axis > 0
                            left = x_axis < 0
                        if abs(y_axis) > self.joystick_deadzone:
                            down = y_axis > 0
                            up = y_axis < 0
                except (pygame.error, IndexError):
                    pass

                # Check D-pad (hat)
                try:
                    if self.joystick.get_numhats() > 0:
                        hat = self.joystick.get_hat(0)
                        # D-pad debug disabled for stability
                        # if hat[0] != 0 or hat[1] != 0:
                        #     if not hasattr(self, '_last_hat_value'):
                        #         self._last_hat_value = (0, 0)
                        #     if hat != self._last_hat_value:
                        #         print(f"D-pad/Hat: {hat}")
                        #         self._last_hat_value = hat
                        if hat[0] != 0:
                            right = hat[0] > 0
                            left = hat[0] < 0
                        if hat[1] != 0:
                            up = hat[1] > 0
                            down = hat[1] < 0
                except (pygame.error, IndexError):
                    pass

            # Mirror if facing left
            if not facing_right:
                left, right = right, left

            return self._directions_to_input(up, down, left, right)

        except Exception as e:
            # If any unexpected error, fall back to neutral
            return InputDirection.NEUTRAL

    def _read_joystick_buttons(self) -> set[Button]:
        """Read button presses from joystick.

        Returns:
            Set of pressed buttons
        """
        if not self.joystick:
            return set()

        pressed = set()
        try:
            # Debug: Show all pressed buttons (only when changed)
            all_pressed = []
            for i in range(self.joystick.get_numbuttons()):
                if self.joystick.get_button(i):
                    all_pressed.append(i)
            
            # Only print if different from last frame (disabled for stability)
            # if not hasattr(self, '_last_pressed_buttons'):
            #     self._last_pressed_buttons = []
            # if all_pressed != self._last_pressed_buttons:
            #     print(f"Button change: {all_pressed}")
            #     self._last_pressed_buttons = all_pressed.copy()
            
            for button_num, button in self.joystick_button_map.items():
                try:
                    if button_num < self.joystick.get_numbuttons():
                        if self.joystick.get_button(button_num):
                            pressed.add(button)
                except (pygame.error, IndexError):
                    continue
        except Exception as e:
            # If any unexpected error, return empty set
            print(f"Warning: Error reading joystick buttons: {e}")
            return set()

        return pressed

    def _directions_to_input(self, up: bool, down: bool, left: bool, right: bool) -> InputDirection:
        """Convert directional bools to InputDirection enum.

        Args:
            up, down, left, right: Direction button states

        Returns:
            InputDirection enum value
        """
        # Handle SOCD (should be cleaned by Brooks UFB, but just in case)
        # Standard: left+right = neutral, up+down = up
        if left and right:
            left = right = False
        if up and down:
            down = False

        # Convert to numpad notation
        if up and left:
            return InputDirection.UP_BACK
        elif up and right:
            return InputDirection.UP_FORWARD
        elif down and left:
            return InputDirection.DOWN_BACK
        elif down and right:
            return InputDirection.DOWN_FORWARD
        elif up:
            return InputDirection.UP
        elif down:
            return InputDirection.DOWN
        elif left:
            return InputDirection.BACK
        elif right:
            return InputDirection.FORWARD
        else:
            return InputDirection.NEUTRAL

    def check_motion_input(self, motion_name: str, button: Button) -> bool:
        """Check if a motion input has been completed.

        Args:
            motion_name: Name of the motion (e.g., "QCF")
            button: Button that should be pressed

        Returns:
            True if motion was completed
        """
        # Find the motion definition
        motion = next((m for m in self.motion_inputs if m.name == motion_name), None)
        if not motion:
            return False

        # Check if button was just pressed
        if button not in self.buttons_pressed_this_frame:
            return False

        # Look for the motion pattern in the input buffer
        return self._search_buffer_for_motion(motion.directions, motion.max_frames)

    def _search_buffer_for_motion(self, directions: List[InputDirection], max_frames: int) -> bool:
        """Search the input buffer for a sequence of directions.

        Args:
            directions: Sequence of directions to find
            max_frames: Maximum frames to complete the motion

        Returns:
            True if motion found in buffer
        """
        if len(self.input_buffer) == 0:
            return False

        # Start from most recent input
        pattern_index = len(directions) - 1
        frames_searched = 0

        for input_state in reversed(self.input_buffer):
            if frames_searched > max_frames:
                return False

            if input_state.direction == directions[pattern_index]:
                pattern_index -= 1
                if pattern_index < 0:
                    return True  # Found complete pattern!

            frames_searched += 1

        return False

    def is_button_pressed(self, button: Button) -> bool:
        """Check if a button is currently held.

        Args:
            button: Button to check

        Returns:
            True if button is pressed
        """
        return button in self.buttons_held

    def is_button_just_pressed(self, button: Button) -> bool:
        """Check if a button was pressed this frame.

        Args:
            button: Button to check

        Returns:
            True if button was just pressed
        """
        return button in self.buttons_pressed_this_frame

    def get_direction(self) -> InputDirection:
        """Get current directional input.

        Returns:
            Current InputDirection
        """
        return self.current_direction

    def check_double_tap_forward(self, max_frames: int = 15) -> bool:
        """Check if forward was double-tapped (for dash).

        Args:
            max_frames: Maximum frames between taps (default 15 = 0.25 seconds at 60fps)

        Returns:
            True if forward was double-tapped
        """
        if len(self.input_buffer) < 2:
            return False

        # Must currently be pressing forward
        if self.current_direction not in [InputDirection.FORWARD, InputDirection.UP_FORWARD, InputDirection.DOWN_FORWARD]:
            return False

        # Look for: Forward -> Neutral -> Forward pattern within max_frames
        found_neutral = False
        found_first_forward = False
        frames_searched = 0

        for input_state in reversed(self.input_buffer):
            if frames_searched > max_frames:
                return False

            if not found_neutral:
                # Looking for neutral after current forward
                if input_state.direction == InputDirection.NEUTRAL:
                    found_neutral = True
            elif not found_first_forward:
                # Looking for first forward press
                if input_state.direction in [InputDirection.FORWARD, InputDirection.UP_FORWARD, InputDirection.DOWN_FORWARD]:
                    found_first_forward = True
                    return True  # Found the pattern!

            frames_searched += 1

        return False

    def check_double_tap_back(self, max_frames: int = 15) -> bool:
        """Check if back was double-tapped (for backdash).

        Args:
            max_frames: Maximum frames between taps (default 15 = 0.25 seconds at 60fps)

        Returns:
            True if back was double-tapped
        """
        if len(self.input_buffer) < 2:
            return False

        # Must currently be pressing back
        if self.current_direction not in [InputDirection.BACK, InputDirection.UP_BACK, InputDirection.DOWN_BACK]:
            return False

        # Look for: Back -> Neutral -> Back pattern within max_frames
        found_neutral = False
        found_first_back = False
        frames_searched = 0

        for input_state in reversed(self.input_buffer):
            if frames_searched > max_frames:
                return False

            if not found_neutral:
                # Looking for neutral after current back
                if input_state.direction == InputDirection.NEUTRAL:
                    found_neutral = True
            elif not found_first_back:
                # Looking for first back press
                if input_state.direction in [InputDirection.BACK, InputDirection.UP_BACK, InputDirection.DOWN_BACK]:
                    found_first_back = True
                    return True  # Found the pattern!

            frames_searched += 1

        return False


class InputSystem:
    """Manages input for all players."""

    def __init__(self):
        """Initialize the input system."""
        pygame.joystick.init()

        self.player1 = PlayerInput(1)
        self.player2 = PlayerInput(2)

        # Auto-connect joysticks
        self._auto_connect_joysticks()

    def _auto_connect_joysticks(self):
        """Automatically connect available joysticks to players."""
        try:
            joystick_count = pygame.joystick.get_count()
            print(f"Detected {joystick_count} joystick(s)")

            if joystick_count >= 1:
                self.player1.connect_joystick(0)
            if joystick_count >= 2:
                self.player2.connect_joystick(1)
        except Exception as e:
            print(f"Warning: Failed to auto-connect joysticks: {e}")
            print("Continuing with keyboard only...")

    def update(self, player1_facing_right: bool = True, player2_facing_right: bool = False):
        """Update input for all players.

        Args:
            player1_facing_right: Whether player 1 is facing right
            player2_facing_right: Whether player 2 is facing right
        """
        self.player1.update(player1_facing_right)
        self.player2.update(player2_facing_right)
