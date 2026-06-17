"""Deterministic CPU opponent, parameterized by an AIProfile (the boss ladder).

The AI does not bypass the character state machine -- it *feeds inputs* into the
normal pipeline, exactly like `tools/diagnostics/scenario.py:ScriptedPlayerInput`,
except it computes each frame's `(direction, buttons)` from the live game state.

Difficulty comes from the profile (`systems/ai_profiles.py`): a reaction-delay
buffer (the AI perceives the opponent from `reaction_frames` ago), a fixed-seed
PRNG for variety + input "fumbles" (low `input_accuracy`), capability gating
(which tactics are available), and spacing/cadence scaling. Everything stays
deterministic: same profile + seed + inputs => identical timeline (no wall-clock,
no unseeded random). Directions are facing-relative (FORWARD = toward opponent).
"""

from __future__ import annotations

import random
from collections import deque
from typing import List, Tuple

from street_fighter_3rd.systems.input_system import PlayerInput, InputState
from street_fighter_3rd.systems.ai_profiles import AIProfile, get_profile, DEFAULT_AI_SEED
from street_fighter_3rd.data.enums import InputDirection, Button

# Facing-relative direction shorthands.
_N = InputDirection.NEUTRAL
_F = InputDirection.FORWARD
_B = InputDirection.BACK
_D = InputDirection.DOWN
_DF = InputDirection.DOWN_FORWARD
_DB = InputDirection.DOWN_BACK
_UF = InputDirection.UP_FORWARD

FrameInput = Tuple[InputDirection, List[Button]]

# Base spacing thresholds (world units); scaled per-profile by spacing_scale.
_THROW_RANGE = 70
_POKE_RANGE = 115
_BLOCK_RANGE = 120
_ANTIAIR_RANGE = 150
_SUPER_RANGE = 320

# Opponent perception snapshot: (x, is_grounded, is_attacking).
_Snap = Tuple[float, bool, bool]


class AIController:
    """Profile-driven decision logic: decide(me, opponent) -> (direction, [buttons])."""

    def __init__(self, profile: AIProfile = None, rng_seed: int = DEFAULT_AI_SEED):
        self.profile = profile or get_profile("brawler")
        self.rng_seed = rng_seed
        self.frame = 0
        self._queue: deque[FrameInput] = deque()
        self._perception: deque[_Snap] = deque(maxlen=max(2, self.profile.reaction_frames + 1))
        self.rng = random.Random(rng_seed)

    def reset(self):
        self.frame = 0
        self._queue.clear()
        self._perception.clear()
        self.rng = random.Random(self.rng_seed)

    # --- perception (reaction delay) ---
    def _perceive(self, opponent) -> _Snap:
        snap: _Snap = (
            float(getattr(opponent, "x", 0.0)),
            bool(getattr(opponent, "is_grounded", True)),
            opponent.is_attacking() if hasattr(opponent, "is_attacking") else False,
        )
        self._perception.append(snap)
        # The opponent as the AI "sees" it `reaction_frames` ago (clamped to history).
        idx = max(0, len(self._perception) - 1 - self.profile.reaction_frames)
        return self._perception[idx]

    def decide(self, me, opponent) -> FrameInput:
        self.frame += 1
        # A queued motion (DP / fireball / super) plays out cleanly, ignoring fumbles.
        if self._queue:
            return self._queue.popleft()

        opp_x, opp_grounded, opp_attacking = self._perceive(opponent)
        if not getattr(me, "is_grounded", True):
            return (_N, [])  # no air logic yet

        p = self.profile
        dist = abs(getattr(me, "x", 0.0) - opp_x)
        opp_airborne = not opp_grounded

        # 1) Anti-air a close, airborne opponent (Shoryuken).
        if p.anti_air and opp_airborne and dist < _ANTIAIR_RANGE * p.spacing_scale:
            self._queue_motion([(_F, []), (_D, []), (_DF, [Button.MEDIUM_PUNCH])])
            return self._queue.popleft()

        # 2) Block an incoming attack at close range (hold back).
        if p.block and opp_attacking and dist < _BLOCK_RANGE * p.spacing_scale:
            return (_B, [])

        # 3) Spend a full meter on a Super Art when in range (Messatsu Gou Hadou).
        if p.use_super and dist < _SUPER_RANGE * p.spacing_scale and \
                getattr(me, "has_full_super", lambda: False)():
            self._queue_motion([(_D, []), (_DF, []), (_F, []),
                                (_D, []), (_DF, []), (_F, [Button.MEDIUM_PUNCH])])
            return self._queue.popleft()

        # 4) Throw occasionally at point-blank.
        if p.throw and dist < _THROW_RANGE * p.spacing_scale and (self.frame // 26) % 4 == 0:
            return self._fuzz((_N, [Button.LIGHT_PUNCH, Button.LIGHT_KICK]))

        # 5) Poke when in range, on the profile's cadence.
        if dist < _POKE_RANGE * p.spacing_scale:
            if self.frame % max(4, p.act_period) < 2:
                return self._fuzz((_N, [self._poke()]))
            return (_N, [])

        # 6) Far: approach, with an occasional fireball (zoning) or jump-in.
        choice = (self.frame // 40) % 4
        if p.zoning and choice == 0:
            self._queue_motion([(_D, []), (_DF, []), (_F, [Button.MEDIUM_PUNCH])])  # QCF+P
            return self._queue.popleft()
        if choice == 2:
            return (_UF, [])   # jump-in approach
        return (_F, [])        # walk forward

    # --- helpers ---
    def _poke(self) -> Button:
        return (Button.LIGHT_PUNCH, Button.MEDIUM_KICK, Button.MEDIUM_PUNCH)[(self.frame // 24) % 3]

    def _queue_motion(self, frames: List[FrameInput]):
        self._queue.extend(frames)

    def _fuzz(self, action: FrameInput) -> FrameInput:
        """Apply input_accuracy: a less-than-perfect bot occasionally drops the
        attack button (still deterministic via the seeded PRNG)."""
        direction, buttons = action
        if buttons and self.profile.input_accuracy < 1.0 and \
                self.rng.random() > self.profile.input_accuracy:
            return (direction, [])
        return action


class AIPlayerInput(PlayerInput):
    """A PlayerInput whose per-frame state comes from an AIController instead of
    hardware. Wired in place of the keyboard input for a CPU-controlled player."""

    def __init__(self, player_number: int, me, opponent,
                 profile: AIProfile = None, rng_seed: int = DEFAULT_AI_SEED,
                 controller: AIController = None):
        super().__init__(player_number)
        self.me = me
        self.opponent = opponent
        self.controller = controller or AIController(profile, rng_seed)

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
