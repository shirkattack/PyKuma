"""Phase 2.1: hit reactions + knockback (scenario-gated, decomp-aligned structure).

Locks the keystone fixes the diagnostics framework surfaced:
- the ATTACKER no longer enters hitstun on its own hit (correct attacker/defender
  attribution per the queued hit's ids),
- an attack connects ONCE (no re-hit every active frame),
- the defender takes a hit reaction + knockback and stays in bounds.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.scenario import run_scenario, jab_knockback
from street_fighter_3rd.data.constants import STAGE_LEFT_BOUND, STAGE_RIGHT_BOUND


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _hitstun(state):
    return state.startswith("HITSTUN") or state == "KNOCKDOWN"


def test_attacker_does_not_self_stun():
    tl = run_scenario(jab_knockback())
    assert not any(_hitstun(fr["players"][0]["state"]) for fr in tl), \
        "attacker must never enter a hit reaction from its own hit"


def test_attack_connects_exactly_once():
    tl = run_scenario(jab_knockback())
    hps = [fr["players"][1]["health"] for fr in tl]
    drops = sum(1 for i in range(1, len(hps)) if hps[i] < hps[i - 1])
    assert drops == 1, f"a single jab must deal damage once, not {drops} times"
    assert hps[0] - hps[-1] > 0, "the jab should deal some damage"


def test_defender_reacts_knocked_back_and_in_bounds():
    tl = run_scenario(jab_knockback())
    d_states = {fr["players"][1]["state"] for fr in tl}
    assert "HITSTUN_STANDING" in d_states, "defender should enter hitstun"
    xs = [fr["players"][1]["pos"][0] for fr in tl]
    assert xs[-1] > xs[0], "defender should be pushed away from the attacker"
    assert all(STAGE_LEFT_BOUND <= x <= STAGE_RIGHT_BOUND for x in xs), \
        "knockback must stay within the stage (no off-screen fling)"
