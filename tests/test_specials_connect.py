"""Specials and the UOH actually hit (they had no hitboxes at all before).

Goshoryuken / Tatsumaki had no ROM pointer mapping -> no boxes -> 0 damage;
the UOH had ROM boxes but no combat row -> 0 damage and, with hitstun 0, a
defender stuck in HITSTUN_STANDING until the 60-frame state timeout.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold
from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.characters.character import apply_reaction
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import Button, CharacterState, HitEffect, InputDirection as I
from street_fighter_3rd.data.hitbox_repository import HitboxRepository


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _run(script, p2_dist=60, frames=130, p2_script=None):
    g = new_game()
    p1, p2 = g.player1, g.player2
    p1.x, p2.x = 620, 620 + p2_dist
    p1._prev_x, p2._prev_x = p1.x, p2.x
    g.input_system = ScriptedInputSystem(script, p2_script or [])
    p1.input, p2.input = g.input_system.player1, g.input_system.player2
    hp, hits, p2_states, x0 = p2.health, 0, [], p1.x
    for _ in range(frames):
        g.update()
        if p2.health < hp:
            hits += 1
        hp = p2.health
        p2_states.append(p2.state)
    return g, hits, p2_states, p1.x - x0


TATSU = lambda b: hold(I.NEUTRAL, 2) + hold(I.DOWN, 2) + hold(I.DOWN_BACK, 2) + [(I.BACK, [b])] + hold(None, 150)


@pytest.mark.parametrize("button,travel", [(Button.LIGHT_KICK, 92), (Button.MEDIUM_KICK, 130), (Button.HEAVY_KICK, 173)])
def test_tatsumaki_travels_rom_distance_and_ends_standing(button, travel):
    g, _, _, dx = _run(TATSU(button), p2_dist=600)
    assert abs(dx - travel) <= 2, f"{button.name} tatsu travelled {dx:.0f}px, ROM {travel}"
    assert g.player1.state == CharacterState.STANDING and g.player1.is_grounded
    assert g.player1.y == STAGE_FLOOR


@pytest.mark.parametrize("button", [Button.LIGHT_KICK, Button.MEDIUM_KICK, Button.HEAVY_KICK])
def test_tatsumaki_connects(button):
    g, hits, p2_states, _ = _run(TATSU(button), p2_dist=90)
    assert hits >= 1, "tatsu must connect"
    assert CharacterState.HITSTUN_AIRBORNE in p2_states, "ground tatsu launches (JUGGLE)"


def test_tatsumaki_multi_hit_connects_more_than_once():
    _, hits, _, _ = _run(TATSU(Button.MEDIUM_KICK), p2_dist=90)
    assert hits >= 2


def test_uoh_does_damage_and_does_not_lock_the_defender():
    g, hits, p2_states, _ = _run(hold(I.NEUTRAL, 2) + [(None, [Button.MEDIUM_PUNCH, Button.MEDIUM_KICK])] + hold(None, 120))
    assert hits == 1
    stunned = sum(1 for s in p2_states if s == CharacterState.HITSTUN_STANDING)
    assert 0 < stunned < 45, f"UOH left the defender in hitstun for {stunned} frames"


def test_zero_hitstun_hit_still_recovers_quickly():
    a, b = Akuma(520, STAGE_FLOOR, 1), Akuma(620, STAGE_FLOOR, 2)
    apply_reaction(b, HitEffect.NORMAL, 0)
    n = 0
    while b.state == CharacterState.HITSTUN_STANDING and n < 100:
        b.update(a)
        n += 1
    assert n <= 2, f"a 0-hitstun hit locked the defender for {n} frames"


def test_close_hk_connects_on_both_rom_hit_windows():
    _, hits, _, _ = _run(hold(I.NEUTRAL, 2) + [(None, [Button.HEAVY_KICK])] + hold(None, 100), p2_dist=50)
    assert hits == 2


def test_frames_between_rom_hit_windows_do_not_connect():
    """MP Goshoryuken draws boxes on frames 3-9 but the ROM registers hits on
    3 and 5-9 only: frame 4 must not land a third hit."""
    m = HitboxRepository.instance().get_move_by_state("GOSHORYUKEN", "medium")
    assert m.hit_windows == [[3, 3], [5, 9]]
    dp = hold(I.NEUTRAL, 2) + hold(I.FORWARD, 2) + hold(I.DOWN, 2) + [(I.DOWN_FORWARD, [Button.MEDIUM_PUNCH])] + hold(None, 150)
    _, hits, _, _ = _run(dp, p2_dist=60, frames=160)
    assert hits == 2


def test_standing_normals_are_mid_and_jump_ins_high():
    from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data
    from street_fighter_3rd.data.enums import HitType
    for st in (CharacterState.LIGHT_PUNCH, CharacterState.HEAVY_PUNCH, CharacterState.MEDIUM_KICK,
               CharacterState.HEAVY_KICK, CharacterState.CROUCH_HEAVY_PUNCH):
        assert get_move_frame_data(st).hitboxes[0][1].hit_type == HitType.MID, st
    for st in (CharacterState.JUMP_HEAVY_KICK, CharacterState.OVERHEAD):
        assert get_move_frame_data(st).hitboxes[0][1].hit_type == HitType.HIGH, st
    for st in (CharacterState.CROUCH_LIGHT_KICK, CharacterState.CROUCH_HEAVY_KICK):
        assert get_move_frame_data(st).hitboxes[0][1].hit_type == HitType.LOW, st
