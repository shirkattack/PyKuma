"""Regression tests for the neverending-juggle and corner-shove bugs.

Both are gameplay bugs the user reported that had cross-cutting root causes:

  1. "Akuma's HP gets opponent in neverending juggle." Root cause: on landing
     from HITSTUN_AIRBORNE / KNOCKDOWN the character was returned straight to
     STANDING with no wakeup window. The launched defender became immediately
     re-launchable, so mash HP would juggle -> land -> hit on the ground ->
     relaunch, forever. Fix: land into KNOCKDOWN, and defender is invulnerable
     to hurtboxes during KNOCKDOWN (no OTG on normals -- matches 3S).

  2. "If you jump over opponent in the corner it causes a bug where Akuma
     just moves back and forth." Root cause: the pushbox pair resolver's
     50/50 split shoved a cornered defender inward when the attacker landed
     on top of them; combined with the corner clamp, some frames produced a
     shove-and-reclamp oscillation. Fix: pre-detect the cornered case and
     give the full separation correction to the non-cornered character.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from street_fighter_3rd.data.enums import CharacterState, FacingDirection, HitEffect
from street_fighter_3rd.data.constants import STAGE_RIGHT_BOUND, STAGE_LEFT_BOUND
from street_fighter_3rd.characters.character import apply_reaction


@pytest.fixture
def game():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.core.game import Game
    g = Game(screen, GameModeManager(GameMode.TRAINING))
    return g


# ---------------------------------------------------------------- juggle ----

def test_landing_from_air_hitstun_goes_to_knockdown(game):
    """The core mechanic that closes the infinite juggle: air hitstun does
    NOT return the defender straight to STANDING (immediately re-launchable)."""
    p2 = game.player2
    apply_reaction(p2, HitEffect.JUGGLE, 20)
    assert not p2.is_grounded, "JUGGLE reaction must launch airborne"
    # Simulate falling to the floor
    for _ in range(120):
        game.update()
        if p2.is_grounded:
            break
    assert p2.is_grounded, "must land within a reasonable time"
    assert p2.state == CharacterState.KNOCKDOWN, \
        f"must land in KNOCKDOWN with a wakeup window, not {p2.state.name}"


def test_knocked_down_defender_is_invulnerable_to_normals(game):
    """No OTG on normals: a KNOCKDOWN defender has no hurtboxes, so mashed
    heavy punches from a standing attacker cannot connect."""
    p1, p2 = game.player1, game.player2
    p2.x = p1.x + 55
    apply_reaction(p2, HitEffect.KNOCKDOWN, 40)
    assert p2.state == CharacterState.KNOCKDOWN

    otg_hits = 0
    for _ in range(50):  # well within the KNOCKDOWN duration
        if p1.state == CharacterState.STANDING:
            p1._transition_to_state(CharacterState.HEAVY_PUNCH)
            p1.state_frame = -1
        game.update()
        for ev in game.collision_system.drain_hit_events():
            if not ev.get("blocked") and p2.state == CharacterState.KNOCKDOWN:
                otg_hits += 1
    assert otg_hits == 0, f"got {otg_hits} OTG hits — knockdown must be invulnerable"


def test_mashed_hp_does_not_produce_infinite_juggle(game):
    """The end-to-end scenario the user reported. Approach + mash HP for a
    reasonable window and confirm the defender is not stuck bouncing between
    HITSTUN_AIRBORNE and hittable-on-landing forever. (st.HP is now a NORMAL
    hit, as in 3S, so the defender never leaves the ground at all; an idle
    dummy still takes every hit, so damage is not bounded here.)"""
    p1, p2 = game.player1, game.player2
    p2.x = p1.x + 60
    hp0 = p2.health
    airborne_streak = max_airborne_streak = 0
    for _ in range(600):
        if p1.state == CharacterState.STANDING:
            if abs(p2.x - p1.x) > 75:
                p1.x += 4
            p1._transition_to_state(CharacterState.HEAVY_PUNCH)
            p1.state_frame = -1
        game.update()
        if not p2.is_grounded:
            airborne_streak += 1
            max_airborne_streak = max(airborne_streak, max_airborne_streak)
        else:
            airborne_streak = 0
    # An infinite juggle would leave p2 airborne for most of the run; with the
    # fix, the launched state resolves to knockdown quickly.
    assert max_airborne_streak == 0, \
        f"defender was airborne for {max_airborne_streak} consecutive frames — st.HP must not launch"
    assert p2.health < hp0, "the mashed HP must be connecting"


# ---------------------------------------------------------------- corner ----

def test_cornered_defender_does_not_get_shoved_when_landed_on(game):
    """The 'moves back and forth' bug: crossup landing must not push a
    cornered defender significantly off their corner."""
    p1, p2 = game.player1, game.player2
    p2.x = STAGE_RIGHT_BOUND
    p2.facing = FacingDirection.LEFT
    p1.x = p2.x - 60

    # p1 jumps forward, arcs over p2, lands on the far side
    p1.velocity_y = -13; p1.velocity_x = 7; p1.is_grounded = False
    p1._transition_to_state(CharacterState.JUMPING)

    for _ in range(90):
        game.update()

    # p2 will be pushed off the corner because p1 landed at STAGE_RIGHT_BOUND
    # (someone has to move — they can't overlap), but the shove is a single
    # min-distance separation, not repeated oscillation. Sample the last 30
    # frames to catch any wobble.
    samples = []
    for _ in range(30):
        game.update()
        samples.append(int(p2.x))
    assert max(samples) - min(samples) < 2, \
        f"cornered defender oscillated: p2 range {min(samples)}..{max(samples)}"


def test_walking_into_cornered_opponent_does_not_shove_them(game):
    """The simpler case: cornered defender, attacker walks toward them.
    The cornered defender must not slide into their own corner further."""
    p1, p2 = game.player1, game.player2
    p2.x = STAGE_RIGHT_BOUND
    p2._prev_x = STAGE_RIGHT_BOUND  # prime the "was cornered" signal
    p2.facing = FacingDirection.LEFT
    p1.x = p2.x - 60

    # p1 walks forward (into p2)
    positions = []
    for _ in range(60):
        p1._transition_to_state(CharacterState.WALKING_FORWARD)
        p1.velocity_x = 2
        game.update()
        positions.append(int(p2.x))

    assert max(positions) - min(positions) < 3, \
        f"cornered defender oscillated under walk pressure: {min(positions)}..{max(positions)}"
    assert p2.x >= STAGE_RIGHT_BOUND - 3, "cornered defender must stay at the corner"


# ------------------------------------------------- corner crossup / wall ----

def _prime_grounded(*players):
    """Make the prior-frame signals reflect 'standing here' (as after a frame)."""
    for p in players:
        p._prev_x = p.x
        p._prev_grounded = True


def _forward_jump(p, direction):
    from street_fighter_3rd.data.constants import JUMP_VELOCITY
    p.velocity_y = JUMP_VELOCITY
    p.velocity_x = 2.0 * direction
    p.is_grounded = False
    p._transition_to_state(CharacterState.JUMPING)


@pytest.mark.parametrize("wall,direction", [(STAGE_RIGHT_BOUND, +1), (STAGE_LEFT_BOUND, -1)])
def test_jumping_over_cornered_opponent_lands_in_front(game, wall, direction):
    """You cannot cross up a cornered opponent: the defender AT the wall keeps
    the corner and the jumper lands on the open side. Previously the jumper,
    clamped to the wall mid-air (x == wall == defender.x), won the prev_x
    tie-break, stole the corner, and both facings flipped -- with two identical
    Akuma sprites that looked like P1 and P2 swapping controls."""
    p1, p2 = game.player1, game.player2
    p2.x = wall
    p2.facing = FacingDirection.LEFT if direction > 0 else FacingDirection.RIGHT
    p1.x = wall - 116 * direction
    p1.facing = FacingDirection.RIGHT if direction > 0 else FacingDirection.LEFT
    _prime_grounded(p1, p2)
    _forward_jump(p1, direction)

    for _ in range(120):
        game.update()
        if p1.is_grounded:
            break
    assert p1.is_grounded, "jumper must land"
    for _ in range(10):
        game.update()

    assert p2.x == wall, f"cornered defender lost the wall: {p2.x}"
    assert (p2.x - p1.x) * direction > 0, "jumper must land on the open side of the defender"
    assert abs(p2.x - p1.x) >= (p1.pushbox_width + p2.pushbox_width) / 2 - 0.01
    assert p1.facing == (FacingDirection.RIGHT if direction > 0 else FacingDirection.LEFT)
    assert p2.facing == (FacingDirection.LEFT if direction > 0 else FacingDirection.RIGHT)


def test_block_pushback_keeps_cornered_defender_inside_stage(game):
    """Block pushback wrote defender.x directly and the defender then sat in
    hitfreeze, during which Character.update() skips the stage clamp -- so a
    cornered defender was parked past the wall for the whole freeze."""
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from tools.diagnostics.scenario import ScriptedInputSystem, hold, tap
    from street_fighter_3rd.data.enums import InputDirection, Button

    p1, p2 = game.player1, game.player2
    p2.x = STAGE_RIGHT_BOUND
    p2.facing = FacingDirection.LEFT
    p1.x = p2.x - 52
    p1.facing = FacingDirection.RIGHT
    _prime_grounded(p1, p2)
    game.input_system = ScriptedInputSystem(
        hold(None, 2) + tap(Button.LIGHT_PUNCH) + hold(None, 40),
        hold(InputDirection.BACK, 45))
    p1.input, p2.input = game.input_system.player1, game.input_system.player2

    blocked = False
    for _ in range(45):
        game.update()
        assert p2.x <= STAGE_RIGHT_BOUND, f"defender pushed through the wall to {p2.x}"
        if p2.state in (CharacterState.BLOCKSTUN_HIGH, CharacterState.BLOCKSTUN_LOW):
            blocked = True
    assert blocked, "scenario must actually produce a blocked hit"


def test_mashed_standing_hp_never_launches(game):
    """st.HP through the real input path: the defender is hit but never leaves
    the ground (it is a NORMAL hit in 3S, not a launcher)."""
    import sys, os as _os
    sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from tools.diagnostics.scenario import ScriptedInputSystem, hold, tap
    from street_fighter_3rd.data.enums import Button

    p1, p2 = game.player1, game.player2
    p2.x = p1.x + 60
    _prime_grounded(p1, p2)
    game.input_system = ScriptedInputSystem((tap(Button.HEAVY_PUNCH) + hold(None, 3)) * 100, [])
    p1.input, p2.input = game.input_system.player1, game.input_system.player2
    hp_prev, hits = p2.health, 0
    for _ in range(400):
        game.update()
        assert p2.is_grounded, "st.HP must not launch"
        assert p2.state != CharacterState.HITSTUN_AIRBORNE
        if p2.health < hp_prev:
            hits += 1
        hp_prev = p2.health
    assert hits >= 3, "the HP must actually be connecting"
