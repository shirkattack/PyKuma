"""The simulation must be deterministic for replay/scenarios to be trustworthy:
the same scripted inputs from the same setup produce an identical state timeline.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.scenario import run_scenario, jump_arc, jab_knockback


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _key(timeline):
    """Reduce a timeline to the fields that must reproduce exactly."""
    out = []
    for fr in timeline:
        row = [fr["frame"]]
        for p in fr["players"]:
            row += [p["state"], tuple(p["pos"]), tuple(p["vel"]),
                    p["facing"], p["health"], p["grounded"]]
        out.append(tuple(row))
    return out


@pytest.mark.parametrize("make", [jump_arc, jab_knockback])
def test_scenario_runs_are_identical(make):
    a = run_scenario(make())
    b = run_scenario(make())
    assert _key(a) == _key(b), "same inputs must yield an identical timeline"
