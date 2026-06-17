"""Deterministic CPU opponent.

The AI does not bypass the character state machine -- it *feeds inputs* into the
normal pipeline, exactly like `tools/diagnostics/scenario.py:ScriptedPlayerInput`,
except it computes each frame's `(direction, buttons)` from the live game state
instead of replaying a fixed script. So motions, supers, throws, and blocking all
come out through the same code a human drives.

Determinism: the engine is fixed-timestep with no RNG (see tests/test_determinism),
and the AI must not break that. All decisions key off distance, the opponent's
state, and an internal frame counter -- variety comes from frame-based patterns,
never `random`. Directions are facing-relative (FORWARD = toward the opponent),
matching what the rest of the input system consumes.
"""

from __future__ import annotations

from collections import deque
from typing import List, Tuple

from street_fighter_3rd.systems.input_system import PlayerInput, InputState
from street_fighter_3rd.data.enums import InputDirection, Button

# Facing-relative direction shorthands.
_N = InputDirection.NEUTRAL
_F = InputDirection.FORWARD
_B = InputDirection.BACK
_D = InputDirection.DOWN
_DF = InputDirection.DOWN_FORWARD
_UF = InputDirection.UP_FORWARD

FrameInput = Tuple[InputDirection, List[Button]]

# Spacing thresholds (world units). Provisional game-feel; tune freely.
_THROW_RANGE = 70
_POKE_RANGE = 115
_BLOCK_RANGE = 120
_ANTIAIR_RANGE = 150


class AIController:
    """Pure decision logic: decide(me, opponent) -> (direction, [buttons]).

    Holds a short queue so multi-frame motions (QCF fireball, DP anti-air) play out
    over consecutive frames through the normal motion detector.
    """

    def __init__(self):
        self.frame = 0
        self._queue: deque[FrameInput] = deque()

    def reset(self):
        self.frame = 0
        self._queue.clear()

    def decide(self, me, opponent) -> FrameInput:
        self.frame += 1
        # Play out a queued motion (fireball / DP) first.
        if self._queue:
            return self._queue.popleft()

        dist = abs(getattr(me, "x", 0.0) - getattr(opponent, "x", 0.0))
        me_grounded = getattr(me, "is_grounded", True)
        opp_airborne = not getattr(opponent, "is_grounded", True)
        opp_attacking = opponent.is_attacking() if hasattr(opponent, "is_attacking") else False

        if not me_grounded:
            return (_N, [])  # no air logic yet; ride the arc out

        # 1) Anti-air a close, airborne opponent with a Shoryuken.
        if opp_airborne and dist < _ANTIAIR_RANGE:
            self._queue_motion([(_F, []), (_D, []), (_DF, [Button.MEDIUM_PUNCH])])
            return self._queue.popleft()

        # 2) Block an incoming attack at close range (hold back).
        if opp_attacking and dist < _BLOCK_RANGE:
            return (_B, [])

        # 3) Throw occasionally at point-blank.
        if dist < _THROW_RANGE and (self.frame // 26) % 4 == 0:
            return (_N, [Button.LIGHT_PUNCH, Button.LIGHT_KICK])

        # 4) Poke when in range, on a cadence (don't mash every frame).
        if dist < _POKE_RANGE:
            if self.frame % 24 < 2:
                return (_N, [self._poke()])
            return (_N, [])

        # 5) Far: approach, with an occasional fireball or jump-in.
        choice = (self.frame // 40) % 4
        if choice == 0:
            self._queue_motion([(_D, []), (_DF, []), (_F, [Button.MEDIUM_PUNCH])])  # QCF+P
            return self._queue.popleft()
        if choice == 2:
            return (_UF, [])  # jump-in approach
        return (_F, [])       # walk forward

    # --- helpers ---
    def _poke(self) -> Button:
        # Rotate light/medium pokes so it isn't one-note.
        return (Button.LIGHT_PUNCH, Button.MEDIUM_KICK, Button.MEDIUM_PUNCH)[(self.frame // 24) % 3]

    def _queue_motion(self, frames: List[FrameInput]):
        self._queue.extend(frames)


class AIPlayerInput(PlayerInput):
    """A PlayerInput whose per-frame state comes from an AIController instead of
    hardware. Wired in place of the keyboard input for a CPU-controlled player."""

    def __init__(self, player_number: int, me, opponent, controller: AIController = None):
        super().__init__(player_number)
        self.me = me
        self.opponent = opponent
        self.controller = controller or AIController()

    def update(self, facing_right: bool = True):
        self.frame_count += 1
        direction, buttons = self.controller.decide(self.me, self.opponent)
        direction = direction or InputDirection.NEUTRAL
        held = set(buttons)
        prev = self.buttons_held
        self.buttons_pressed_this_frame = held - prev
        self.buttons_released_this_frame = prev - held
        self.buttons_held = held
        self.current_direction = direction
        self.input_buffer.append(InputState(
            direction, set(held), set(self.buttons_pressed_this_frame),
            set(self.buttons_released_this_frame), self.frame_count))

    def reset(self):
        super().reset()
        self.controller.reset()
