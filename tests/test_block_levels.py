"""Block levels: holding back no longer blocks everything.

Guard posture is re-evaluated every frame from the held direction
(Character._update_guard): back = standing guard, down-back = crouching guard,
neither while attacking / jumping / in hitstun. The collision adapter checks
the hit's level against it: MID blocked either way, HIGH (jump-ins, UOH) only
standing, LOW (crouching kicks) only crouching. Parry gets the real level too,
so lows need a down parry.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold
from street_fighter_3rd.characters.character import guard_covers
from street_fighter_3rd.data.enums import Button, CharacterState, HitType, InputDirection as I


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


BLOCKSTUN = (CharacterState.BLOCKSTUN_HIGH, CharacterState.BLOCKSTUN_LOW)
HITSTUN = (CharacterState.HITSTUN_STANDING, CharacterState.HITSTUN_CROUCHING,
           CharacterState.HITSTUN_AIRBORNE, CharacterState.KNOCKDOWN)


def _exchange(p1_script, p2_dir, p2_dist=55, frames=70):
    """P1 runs a script; P2 holds one direction the whole time, pinned in the
    corner so holding back guards without walking out of range. Returns the
    set of P2 states seen plus the final game."""
    from street_fighter_3rd.data.constants import STAGE_RIGHT_BOUND
    g = new_game()
    p1, p2 = g.player1, g.player2
    p2.x = STAGE_RIGHT_BOUND
    p1.x = p2.x - p2_dist
    p1._prev_x, p2._prev_x = p1.x, p2.x
    g.input_system = ScriptedInputSystem(p1_script, hold(p2_dir, frames))
    p1.input, p2.input = g.input_system.player1, g.input_system.player2
    seen = set()
    for _ in range(frames):
        g.update()
        seen.add(p2.state)
    return seen, g


def _outcome(seen):
    if seen & set(HITSTUN):
        return "hit"
    if seen & set(BLOCKSTUN):
        return "blocked"
    return "whiff"


ST_MP = hold(I.NEUTRAL, 2) + [(None, [Button.MEDIUM_PUNCH])] + hold(None, 80)          # MID
CR_MK = hold(I.DOWN, 2) + [(I.DOWN, [Button.MEDIUM_KICK])] + hold(I.DOWN, 80)         # LOW
UOH = hold(I.NEUTRAL, 2) + [(None, [Button.MEDIUM_PUNCH, Button.MEDIUM_KICK])] + hold(None, 80)  # HIGH


@pytest.mark.parametrize("attack,guard,expected", [
    (ST_MP, I.BACK, "blocked"),        # mid vs standing guard
    (ST_MP, I.DOWN_BACK, "blocked"),   # mid vs crouching guard
    (CR_MK, I.DOWN_BACK, "blocked"),   # low vs crouching guard
    (CR_MK, I.BACK, "hit"),            # low vs standing guard -> hits
    (UOH, I.BACK, "blocked"),          # overhead vs standing guard
    (UOH, I.DOWN_BACK, "hit"),         # overhead vs crouching guard -> hits
    (ST_MP, I.NEUTRAL, "hit"),         # no guard at all
], ids=["mid-stand", "mid-crouch", "low-crouch", "low-stand", "high-stand", "high-crouch", "no-guard"])
def test_block_matrix(attack, guard, expected):
    seen, _ = _exchange(attack, guard)
    assert _outcome(seen) == expected, sorted(s.name for s in seen)


def test_guard_covers_table():
    assert guard_covers(HitType.MID, "high") and guard_covers(HitType.MID, "low")
    assert guard_covers(HitType.HIGH, "high") and not guard_covers(HitType.HIGH, "low")
    assert guard_covers(HitType.OVERHEAD, "high") and not guard_covers(HitType.OVERHEAD, "low")
    assert guard_covers(HitType.LOW, "low") and not guard_covers(HitType.LOW, "high")
    assert not guard_covers(HitType.THROW, "high")
    assert guard_covers(HitType.MID, None) and not guard_covers(HitType.LOW, None)  # None = standing


def test_guard_drops_while_attacking():
    """Holding back and pressing a button: the guard flag used to stay set
    (it was only refreshed by the input path) so the attacker 'blocked' during
    its own move."""
    g = new_game()
    p1, p2 = g.player1, g.player2
    p1.x, p2.x = 300, 600
    g.input_system = ScriptedInputSystem(hold(I.BACK, 5) + [(I.BACK, [Button.LIGHT_PUNCH])] + hold(I.BACK, 30), [])
    p1.input, p2.input = g.input_system.player1, g.input_system.player2
    for _ in range(5):
        g.update()
    assert p1.is_blocking and p1.guard_posture == "high"
    for _ in range(3):
        g.update()
    assert p1.state == CharacterState.LIGHT_PUNCH
    assert not p1.is_blocking and p1.guard_posture is None


def test_guard_height_can_switch_during_blockstun():
    """Crouch-block a low, then hold plain back: the posture must update while
    still in blockstun (3S lets you switch guard height mid-string)."""
    g = new_game()
    p1, p2 = g.player1, g.player2
    p1.x, p2.x = 300, 355
    p1._prev_x, p2._prev_x = p1.x, p2.x
    p2_script = hold(I.DOWN_BACK, 12) + hold(I.BACK, 60)
    g.input_system = ScriptedInputSystem(CR_MK, p2_script)
    p1.input, p2.input = g.input_system.player1, g.input_system.player2
    switched = False
    for _ in range(40):
        g.update()
        if p2.state == CharacterState.BLOCKSTUN_LOW and p2.guard_posture == "high":
            switched = True
    assert switched, "guard posture must follow the held direction during blockstun"


def test_no_guard_in_hitstun_or_in_the_air():
    g = new_game()
    p = g.player1
    p.x, g.player2.x = 300, 700
    g.input_system = ScriptedInputSystem(hold(I.UP_BACK, 4) + hold(I.BACK, 40), [])
    p.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    for _ in range(12):
        g.update()
    assert not p.is_grounded and not p.is_blocking, "no air blocking"


def test_low_needs_a_down_parry():
    """cr.MK is LOW: a down-forward tap (low parry) beats it, a forward tap
    (high parry) does not -- the parry check now sees the real hit level."""
    def parried(parry_dir, tap_frame):
        g = new_game()
        p1, p2 = g.player1, g.player2
        p1.x, p2.x = 300, 355
        p1._prev_x, p2._prev_x = p1.x, p2.x
        p2_script = hold(I.NEUTRAL, tap_frame) + [(parry_dir, [])] + hold(I.NEUTRAL, 60)
        g.input_system = ScriptedInputSystem(CR_MK, p2_script)
        p1.input, p2.input = g.input_system.player1, g.input_system.player2
        for _ in range(50):
            g.update()
        ps = g.collision_system.sf3_parry_system
        return ps.get_parry_counter(g.collision_system.player_works[2]) > 0
    low = [parried(I.DOWN_FORWARD, f) for f in range(2, 10)]
    high = [parried(I.FORWARD, f) for f in range(2, 10)]
    assert any(low), "a down-forward tap must be able to parry a low"
    assert not any(high), "a forward tap must never parry a low"
