"""Goshoryuken: a ROM-driven arc, not a moon launch.

History: ``_execute_goshoryuken`` launched at a hard-coded vy=-18 that predated
the ROM gravity rescale (0.8 -> 0.34). That sent Akuma 467px up (off a 512px
screen) for 104 frames; the DP clip ended mid-air, the state fell to JUMPING,
its 60-frame safety cap forced STANDING while airborne, and the character
floated down in the idle pose. It also inherited walk/dash momentum.

Now the arc is the ROM's own per-frame movement (hitboxes.yaml 84f8/85c8/8658,
rising 56/87/124px) with physics taking over when the script ends, then a
landing recovery so the whole move lasts the Baston total (43/50/59 frames).
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import Button, CharacterState, InputDirection as I
from street_fighter_3rd.data.hitbox_repository import HitboxRepository


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


# Baston (revised) full-move totals; ROM script apex (the MP/HP scripts end
# mid-rise, physics adds a few px on top).
EXPECTED = {
    Button.LIGHT_PUNCH:  {"variant": "light",  "total": 43, "rom_apex": 56},
    Button.MEDIUM_PUNCH: {"variant": "medium", "total": 50, "rom_apex": 87},
    Button.HEAVY_PUNCH:  {"variant": "heavy",  "total": 59, "rom_apex": 124},
}


def _dp_script(button):
    return hold(I.NEUTRAL, 2) + hold(I.FORWARD, 2) + hold(I.DOWN, 2) + [(I.DOWN_FORWARD, [button])] + hold(None, 150)


def _run_dp(button, p2_x=700):
    g = new_game()
    p1, p2 = g.player1, g.player2
    p1.x, p2.x = 300, p2_x
    g.input_system = ScriptedInputSystem(_dp_script(button), [])
    p1.input, p2.input = g.input_system.player1, g.input_system.player2
    timeline = []
    for _ in range(160):
        g.update()
        timeline.append((p1.state, p1.y, p1.is_grounded, p1.velocity_x, p1.move_variant, p2.health))
    return timeline


@pytest.mark.parametrize("button", list(EXPECTED))
def test_dp_follows_rom_arc_and_lasts_baston_total(button):
    exp = EXPECTED[button]
    tl = _run_dp(button)
    dp = [(i, s, y, g, v) for i, (s, y, g, _, v, _) in enumerate(tl) if s == CharacterState.GOSHORYUKEN]
    assert dp, "the DP motion must produce a Goshoryuken"
    assert {v for *_, v in dp} == {exp["variant"]}, "move_variant must follow the button"

    # Whole move (whiff): exactly the Baston total, ending in STANDING.
    assert len(dp) == exp["total"], f"{button.name}: DP lasted {len(dp)} frames, Baston total {exp['total']}"
    assert tl[dp[-1][0] + 1][0] == CharacterState.STANDING

    # Arc: ROM apex (+ a few px of physics after the script ends), on screen.
    apex = STAGE_FLOOR - min(y for _, _, y, _, _ in dp)
    assert exp["rom_apex"] - 1 <= apex <= exp["rom_apex"] + 8, f"{button.name}: apex {apex:.1f}"
    assert min(y for _, _, y, _, _ in dp) > 0

    # Never a grounded-only pose while in the air (the old float-down-in-stance).
    assert all(s == CharacterState.GOSHORYUKEN for _, s, _, _, _ in dp)
    # Lands BEFORE the state ends: the tail is real landing recovery.
    landed_at = next(i for i, _, _, g, _ in dp[5:] if g)
    assert landed_at < dp[-1][0], "DP must land and then recover on the ground"


@pytest.mark.parametrize("button,hits", [(Button.LIGHT_PUNCH, 1), (Button.MEDIUM_PUNCH, 2), (Button.HEAVY_PUNCH, 3)])
def test_dp_connects_with_rom_hit_count(button, hits):
    """LP/MP/HP Goshoryuken hit 1/2/3 times (ROM hit_frames), point-blank."""
    tl = _run_dp(button, p2_x=360)
    drops = sum(1 for a, b in zip(tl, tl[1:]) if b[5] < a[5])
    assert drops == hits, f"{button.name}: {drops} hits, ROM says {hits}"


def test_dp_does_not_inherit_dash_momentum():
    g = new_game()
    p1 = g.player1
    p1.x, g.player2.x = 300, 700
    p1._transition_to_state(CharacterState.DASH_FORWARD)
    p1.velocity_x = 6.8
    p1._execute_goshoryuken(Button.MEDIUM_PUNCH)
    assert p1.velocity_x == 0.0
    x0 = p1.x
    for _ in range(70):
        g.update()
    rom_dx = sum(dx for dx, _ in HitboxRepository.instance().get_move_by_state("GOSHORYUKEN", "medium").movement)
    assert abs((p1.x - x0) - rom_dx) < 3, f"DP travelled {p1.x - x0:.0f}px, ROM script says {rom_dx}"


def test_repository_variant_lookup():
    repo = HitboxRepository.instance()
    for v, rom in (("light", "84f8"), ("medium", "85c8"), ("heavy", "8658")):
        m = repo.get_move_by_state("GOSHORYUKEN", v)
        assert m.rom_id == rom and m.variant == v and m.timing_scope == "segment"
        assert m.movement and m.hit_windows
    assert repo.get_move_by_state("GOSHORYUKEN").variant == "light"      # no variant -> lightest
    assert repo.get_move_by_state("HEAVY_PUNCH", "medium").rom_id == "1818"  # ignored for un-varianted moves
    assert repo.get_move_by_state("TATSUMAKI", "air_heavy").rom_id == "9818"
