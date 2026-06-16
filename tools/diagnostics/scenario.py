"""Scripted, repeatable scenarios — the regression-proof half of the framework.

A scenario sets up a starting position/state, drives SCRIPTED per-frame inputs
through the real simulation (so it exercises the actual game logic), and returns
the resulting per-frame timeline. Assertions compare that timeline against
expected values (decomp-derived or a ROM `data/golden/*.jsonl` capture).

Inputs are injected via `ScriptedPlayerInput`, a `PlayerInput` whose `update()`
applies the next scripted frame instead of reading hardware -- so every other
input method (motion buffer, history) keeps working. Directions are
facing-relative (FORWARD = toward the opponent), matching what the game logic
consumes. Re-simulation is deterministic (fixed timestep, no RNG); see
tests/test_determinism.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from street_fighter_3rd.systems.input_system import PlayerInput, InputState, InputSystem
from street_fighter_3rd.data.enums import (
    CharacterState, FacingDirection, InputDirection, Button)
from street_fighter_3rd.data.constants import STAGE_FLOOR

from tools.diagnostics.harness import new_game, build_montage

# One scripted frame of input: (direction, list-of-Button). None dir -> NEUTRAL.
FrameInput = Tuple[Optional[InputDirection], List[Button]]


class ScriptedPlayerInput(PlayerInput):
    """PlayerInput driven by a fixed list of per-frame (direction, buttons)."""

    def __init__(self, player_number: int, script: List[FrameInput]):
        super().__init__(player_number)
        self._script = script
        self._i = 0

    def update(self, facing_right: bool = True):
        self.frame_count += 1
        if self._i < len(self._script):
            direction, buttons = self._script[self._i]
        else:
            direction, buttons = None, []          # hold NEUTRAL after the script
        self._i += 1
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


class ScriptedInputSystem:
    """Drop-in for InputSystem that feeds two scripted players."""

    def __init__(self, p1: List[FrameInput], p2: Optional[List[FrameInput]] = None):
        self.player1 = ScriptedPlayerInput(1, p1)
        self.player2 = ScriptedPlayerInput(2, p2 or [])

    def update(self, player1_facing_right=True, player2_facing_right=False):
        self.player1.update(player1_facing_right)
        self.player2.update(player2_facing_right)

    def reset(self):
        self.player1.reset()
        self.player2.reset()


@dataclass
class Scenario:
    name: str
    frames: int
    p1: Dict = field(default_factory=dict)          # setup: x,y,state,facing
    p2: Dict = field(default_factory=dict)
    p1_inputs: List[FrameInput] = field(default_factory=list)
    p2_inputs: List[FrameInput] = field(default_factory=list)


def _setup(player, spec: Dict):
    if "x" in spec:
        player.x = float(spec["x"])
    player.y = float(spec.get("y", STAGE_FLOOR))
    if "facing" in spec:
        player.facing = (FacingDirection.RIGHT if spec["facing"] == "R"
                         else FacingDirection.LEFT)
    if "state" in spec:
        player._transition_to_state(CharacterState[spec["state"]])


def run_scenario(scn: Scenario, montage_path: Optional[str] = None, every: int = 4) -> List[dict]:
    """Run a scenario through the real sim; return the per-frame state timeline.

    If montage_path is given, also render a contact sheet of the run.
    """
    game = new_game()
    _setup(game.player1, scn.p1)
    _setup(game.player2, scn.p2)
    game.input_system = ScriptedInputSystem(scn.p1_inputs, scn.p2_inputs)
    # Characters read their OWN .input; point them at the scripted players too
    # (Game wired the originals in __init__).
    game.player1.input = game.input_system.player1
    game.player2.input = game.input_system.player2

    timeline, tiles = [], []
    for i in range(scn.frames):
        game.update()
        snap = {
            "frame": i,
            "players": [game.player1.get_debug_state(), game.player2.get_debug_state()],
        }
        timeline.append(snap)
        if montage_path and (i % every == 0 or i == scn.frames - 1):
            game.render()
            p1, p2 = snap["players"]
            tiles.append({"surface": game.screen.copy(),
                          "label": f"f{i} P1 {p1['state']} {p1['pos']} P2 {p2['state']} {p2['pos']}"})
    if montage_path and tiles:
        build_montage(tiles, montage_path)
    return timeline


# ---- helpers + a few seed scenarios ----------------------------------------

def hold(direction: Optional[InputDirection], n: int, buttons: List[Button] = ()) -> List[FrameInput]:
    return [(direction, list(buttons)) for _ in range(n)]


def tap(button: Button) -> List[FrameInput]:
    return [(None, [button])]


def jump_arc() -> Scenario:
    """P1 forward jump from neutral (verify a clean rising/falling arc)."""
    return Scenario(
        name="jump_arc", frames=60,
        p1={"x": 300, "facing": "R"}, p2={"x": 560, "facing": "L"},
        # tap up-forward (held briefly), then neutral so it jumps once and lands
        p1_inputs=hold(InputDirection.UP_FORWARD, 4) + hold(InputDirection.NEUTRAL, 56))


def jab_knockback() -> Scenario:
    """P1 standing LP point-blank into P2 (verify P2's hit reaction + knockback)."""
    return Scenario(
        name="jab_knockback", frames=40,
        p1={"x": 300, "facing": "R"}, p2={"x": 360, "facing": "L"},
        p1_inputs=hold(InputDirection.NEUTRAL, 2) + tap(Button.LIGHT_PUNCH) + hold(None, 37))


def launch_recovery() -> Scenario:
    """P1 heavy punch (JUGGLE) point-blank into P2: P2 should pop up, fall, land,
    and recover -- without getting stuck airborne / hitting the safety timeout."""
    return Scenario(
        name="launch_recovery", frames=110,
        p1={"x": 300, "facing": "R"}, p2={"x": 360, "facing": "L"},
        p1_inputs=hold(InputDirection.NEUTRAL, 2) + tap(Button.HEAVY_PUNCH) + hold(None, 107))


def qcf(button: Button) -> List[FrameInput]:
    """A quarter-circle-forward motion ending in `button` (236+btn)."""
    return (hold(InputDirection.DOWN, 2) + hold(InputDirection.DOWN_FORWARD, 2)
            + [(InputDirection.FORWARD, [button])])


def crouch_hp() -> Scenario:
    """P1 crouching HP point-blank into P2 (regression: cr.HP used to do 0 damage
    because CROUCH_HEAVY_PUNCH had no ROM move mapped)."""
    return Scenario(
        name="crouch_hp", frames=40,
        p1={"x": 320, "facing": "R"}, p2={"x": 380, "facing": "L"},
        p1_inputs=hold(InputDirection.DOWN, 4) + [(InputDirection.DOWN, [Button.HEAVY_PUNCH])]
                  + hold(InputDirection.DOWN, 35))


def fireball() -> Scenario:
    """P1 throws a Gohadoken (QCF+LP); the projectile should travel forward."""
    return Scenario(
        name="fireball", frames=55,
        p1={"x": 250, "facing": "R"}, p2={"x": 640, "facing": "L"},
        p1_inputs=qcf(Button.LIGHT_PUNCH) + hold(None, 50))


SEED_SCENARIOS = {s.name: s for s in
                  (jump_arc(), jab_knockback(), launch_recovery(), fireball(), crouch_hp())}
