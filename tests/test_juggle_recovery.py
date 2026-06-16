"""Phase 2.2: juggle launch is consistent with gravity and recovers on landing.

Regression for the HITSTUN_AIRBORNE 'STATE TIMEOUT': the JUGGLE launch velocity
(-14) was tuned for the old gravity (0.8); after gravity dropped to 0.34 for the
ROM jump arc it flew ~288px off-screen for ~82 frames and blew past the 60-frame
airborne cap, snapping to STANDING mid-air. Launch is now -9 (apex ~119, airtime
~53) and the airborne reaction recovers on LANDING (cap raised to a stuck-only
safety net).
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.scenario import run_scenario, launch_recovery
from street_fighter_3rd.data.constants import STAGE_FLOOR, SCREEN_HEIGHT


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def test_heavy_punch_launches_to_sane_apex():
    tl = run_scenario(launch_recovery())
    ys = [fr["players"][1]["pos"][1] for fr in tl]
    apex = STAGE_FLOOR - min(ys)
    assert apex > 60, "heavy punch should pop the opponent up (juggle)"
    assert apex < 220, f"apex {apex} must not fly off-screen (was ~288 with the bug)"
    assert min(ys) > 0, "launched character must stay on screen"


def test_launched_character_lands_and_recovers():
    tl = run_scenario(launch_recovery())
    # the launched defender enters the airborne reaction...
    assert any(fr["players"][1]["state"] == "HITSTUN_AIRBORNE" for fr in tl)
    # ...and by the end it has landed and recovered to a neutral grounded state
    last = tl[-1]["players"][1]
    assert last["grounded"], "must land"
    assert last["state"] in ("STANDING", "CROUCHING"), \
        f"must recover, not stay stuck ({last['state']})"


def test_airborne_reaction_does_not_hit_the_timeout():
    tl = run_scenario(launch_recovery())
    # max consecutive frames in HITSTUN_AIRBORNE must stay under the 120 safety cap
    run = best = 0
    for fr in tl:
        if fr["players"][1]["state"] == "HITSTUN_AIRBORNE":
            run += 1; best = max(best, run)
        else:
            run = 0
    assert best < 120, f"airborne reaction ran {best}f -> would trip STATE TIMEOUT"
