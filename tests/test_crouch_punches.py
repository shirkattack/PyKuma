"""B7: crouching MP/HP must deal damage (they had no ROM move mapped -> no box).

Regression: CROUCH_MEDIUM_PUNCH / CROUCH_HEAVY_PUNCH were absent from move_names +
COMBAT_MAP, so they loaded no attack box and dealt 0 damage.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.scenario import run_scenario, crouch_hp
from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data
from street_fighter_3rd.data.enums import CharacterState


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


@pytest.mark.parametrize("state", [CharacterState.CROUCH_MEDIUM_PUNCH,
                                   CharacterState.CROUCH_HEAVY_PUNCH])
def test_crouch_punch_has_move_data_and_damage(state):
    fd = get_move_frame_data(state)
    assert fd is not None, f"{state.name} must be mapped to a ROM move"
    assert fd.active, "must have active frames"
    assert fd.hitboxes, "must have attack hitboxes"
    dmg = sum(hb.damage for _, hb in fd.hitboxes)
    assert dmg > 0, "crouch punch must deal damage"


def test_crouch_hp_connects_and_deals_damage():
    tl = run_scenario(crouch_hp())
    states = {fr["players"][0]["state"] for fr in tl}
    assert "CROUCH_HEAVY_PUNCH" in states, "P1 should perform cr.HP"
    hps = [fr["players"][1]["health"] for fr in tl]
    assert hps[-1] < hps[0], "cr.HP should deal damage to P2"
