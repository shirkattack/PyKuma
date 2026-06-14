"""Gameplay diagnostics: per-frame invariant checks + a frame recorder.

Turns "this feels wrong" into quantified, shareable data:
  - InvariantChecker flags anomalies (off-floor, out-of-bounds, NaN, stuck
    state, missing sprite) once per signature, with frame numbers + values.
  - FrameRecorder keeps a ring buffer of recent per-frame state so a dynamic
    issue can be dumped as a timeline ("clip") for an assistant to read.

Both are cheap (arithmetic + a deque append) and gated by the caller so release
builds pay ~nothing.
"""

import collections
import logging
import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

from street_fighter_3rd.data.constants import (
    STAGE_FLOOR, STAGE_LEFT_BOUND, STAGE_RIGHT_BOUND,
)
from street_fighter_3rd.util.logging_config import get_logger, log_once

log = get_logger(__name__)

# how close to the floor a grounded character must be (logical y)
FLOOR_TOL = 2
RING_FRAMES = 300  # ~5s at 60fps


@dataclass
class Violation:
    frame: int
    type: str
    severity: str           # "warn" | "error"
    player: int
    values: Dict[str, Any] = field(default_factory=dict)
    context: str = ""

    def as_dict(self):
        return asdict(self)


class InvariantChecker:
    """Runs once per frame; records anomalies without throwing."""

    def __init__(self, ring=120):
        self.ring: collections.deque = collections.deque(maxlen=ring)
        self._last = None  # most recent Violation, for the overlay

    def recent(self, n):
        return list(self.ring)[-n:]

    def last_status(self):
        """(ok, last_violation_or_None) for the debug overlay."""
        return (self._last is None, self._last)

    def _flag(self, frame, vtype, severity, player, values, context=""):
        v = Violation(frame, vtype, severity, player, values, context)
        self.ring.append(v)
        self._last = v
        log_once(log, (vtype, player), logging.WARNING,
                 "INVARIANT %s p%s @f%s %s", vtype, player, frame, values)

    def check(self, game) -> List[Violation]:
        frame = game.frame_count
        before = len(self.ring)
        for player in (game.player1, game.player2):
            s = player.get_debug_state()
            pid = s["player"]
            x, y = s["pos"]
            vx, vy = s["vel"]

            # NaN / inf
            if not all(math.isfinite(v) for v in (x, y, vx, vy)):
                self._flag(frame, "nan_inf", "error", pid,
                           {"pos": s["pos"], "vel": s["vel"]})
                continue  # other checks meaningless once non-finite

            # health bounds
            if not (0 <= s["health"] <= s["max_health"]):
                self._flag(frame, "health_oob", "error", pid,
                           {"health": s["health"], "max": s["max_health"]})

            # horizontal stage bounds
            if not (STAGE_LEFT_BOUND <= x <= STAGE_RIGHT_BOUND):
                self._flag(frame, "pos_oob", "warn", pid,
                           {"x": x, "bounds": [STAGE_LEFT_BOUND, STAGE_RIGHT_BOUND]})

            # floor: grounded characters should sit at the floor line
            if s["grounded"] and abs(y - STAGE_FLOOR) > FLOOR_TOL:
                self._flag(frame, "feet_off_floor", "warn", pid,
                           {"y": y, "floor": STAGE_FLOOR}, context=s["state"])

            # stuck state: state_frame past the safety cap for that state
            max_frames = player.max_state_frames.get(player.state, 60)
            if s["state_frame"] > max_frames:
                self._flag(frame, "state_stuck", "warn", pid,
                           {"state": s["state"], "state_frame": s["state_frame"],
                            "max": max_frames})

            # rendering fallback = missing art (drew a rectangle, not a sprite)
            if s.get("rendering_fallback"):
                self._flag(frame, "sprite_fallback", "warn", pid,
                           {"state": s["state"], "anim": s.get("anim", {}).get("animation")})

        # characters fully overlapping (push/separation bug)
        dx = abs(game.player1.x - game.player2.x)
        if dx < 1:
            self._flag(frame, "overlap", "warn", 0, {"distance": round(dx, 2)})

        return list(self.ring)[before - len(self.ring):] if len(self.ring) > before else []


class FrameRecorder:
    """Ring buffer of recent per-frame state for clip dumps."""

    def __init__(self, ring=RING_FRAMES):
        self.ring: collections.deque = collections.deque(maxlen=ring)

    def record(self, game):
        combo = None
        cs = game.collision_system
        if hasattr(cs, "get_combo_info"):
            combo = [cs.get_combo_info(1), cs.get_combo_info(2)]
        self.ring.append({
            "frame": game.frame_count,
            "game_state": game.round_manager.game_state.name,
            "players": [game.player1.get_debug_state(), game.player2.get_debug_state()],
            "combo": combo,
        })

    def recent(self, n):
        return list(self.ring)[-n:]
