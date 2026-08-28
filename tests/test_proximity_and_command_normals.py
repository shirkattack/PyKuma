"""Close/far proximity normals, neutral-jump normals, f+MP and the dive kick.

The last unnamed ROM scripts (bar the Demon Flip followups) are now mapped:
close Jab 13a8 / far Strong 1598 / close Fierce 1728 / far Forward 1a38 / far
Roundhouse 1bf8 (Baston startup/active frame-exact), the five 'Straight Air'
normals (meta names), Forward MP 1638 and Air Down MK 2aa0 (meta names).
One CharacterState per family; `Character.move_variant` picks the record.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold
from street_fighter_3rd.characters.akuma import CLOSE_NORMAL_RANGE
from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import Button, CharacterState, HitType, InputDirection as I
from street_fighter_3rd.data.hitbox_repository import HitboxRepository


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def _run(script, dist, p2_script=None, frames=90):
    g = new_game()
    p1, p2 = g.player1, g.player2
    p1.x, p2.x = 300, 300 + dist
    p1._prev_x, p2._prev_x = p1.x, p2.x
    g.input_system = ScriptedInputSystem(script, p2_script or [])
    p1.input, p2.input = g.input_system.player1, g.input_system.player2
    hp, hits, seen, anims, x0, ymin = p2.health, 0, [], set(), p1.x, STAGE_FLOOR
    for _ in range(frames):
        g.update()
        if p2.health < hp:
            hits += 1
        hp = p2.health
        if p1.is_attacking():
            seen.append((p1.state, p1.move_variant))
            anims.add(p1.animation_controller.get_current_animation_name())
        ymin = min(ymin, p1.y)
    return dict(g=g, p1=p1, p2=p2, hits=hits, seen=seen, anims=anims, dx=p1.x - x0, apex=STAGE_FLOOR - ymin,
                attack_frames=len(seen))


def _tap(button, direction=None, pre=2):
    return hold(direction or I.NEUTRAL, pre) + [(direction, [button])] + hold(None, 80)


# ------------------------------------------------------------- close / far --

@pytest.mark.parametrize("button,state,close_rom,far_rom", [
    (Button.LIGHT_PUNCH, CharacterState.LIGHT_PUNCH, "13a8", "1438"),
    (Button.MEDIUM_PUNCH, CharacterState.MEDIUM_PUNCH, "14e8", "1598"),
    (Button.HEAVY_PUNCH, CharacterState.HEAVY_PUNCH, "1728", "1818"),
    (Button.MEDIUM_KICK, CharacterState.MEDIUM_KICK, "1988", "1a38"),
    (Button.HEAVY_KICK, CharacterState.HEAVY_KICK, "1b08", "1bf8"),
])
def test_standing_normal_picks_close_or_far_by_distance(button, state, close_rom, far_rom):
    repo = HitboxRepository.instance()
    near = _run(_tap(button), CLOSE_NORMAL_RANGE - 20)
    far = _run(_tap(button), CLOSE_NORMAL_RANGE + 20)
    assert {v for s, v in near["seen"] if s == state} == {"close"}
    assert {v for s, v in far["seen"] if s == state} == {"far"}
    assert repo.get_move_by_state(state.name, "close").rom_id == close_rom
    assert repo.get_move_by_state(state.name, "far").rom_id == far_rom
    # The move runs for ITS variant's ROM total.
    assert near["attack_frames"] >= repo.get_move_by_state(state.name, "close").timing["total"]
    assert far["attack_frames"] >= repo.get_move_by_state(state.name, "far").timing["total"]


def test_close_normals_play_their_own_clips():
    # (a ROM cel clip registers the base clip under its variant name too, so
    # the far version may be "far_heavy_punch"; either way close != far)
    hp = _run(_tap(Button.HEAVY_PUNCH), 60)
    assert hp["anims"] == {"close_heavy_punch"}
    hp_far = _run(_tap(Button.HEAVY_PUNCH), 100)
    assert hp_far["anims"] <= {"heavy_punch", "far_heavy_punch"} and hp_far["anims"]
    for button, clip in ((Button.MEDIUM_PUNCH, "close_medium_punch"), (Button.MEDIUM_KICK, "close_medium_kick"),
                         (Button.HEAVY_KICK, "close_heavy_kick")):
        assert _run(_tap(button), 60)["anims"] == {clip}
    # st.LP has no separate close clip: the base clip is fitted to the close total.
    assert _run(_tap(Button.LIGHT_PUNCH), 60)["anims"] <= {"light_punch", "close_light_punch"}


def test_close_fierce_is_the_fast_uppercut():
    """Close HP: 4f startup (Baston 'Fierce'), far HP: 8f ('Far Fierce')."""
    assert get_move_frame_data(CharacterState.HEAVY_PUNCH, "close").startup == 4
    assert get_move_frame_data(CharacterState.HEAVY_PUNCH, "far").startup == 8
    assert get_move_frame_data(CharacterState.HEAVY_PUNCH).startup == 8   # base = far


def test_lookup_without_variant_is_unchanged():
    """Callers that don't know the strength still get what they always got."""
    repo = HitboxRepository.instance()
    for state, rom in (("LIGHT_PUNCH", "1438"), ("MEDIUM_PUNCH", "14e8"), ("HEAVY_PUNCH", "1818"),
                       ("LIGHT_KICK", "1908"), ("MEDIUM_KICK", "1988"), ("HEAVY_KICK", "1b08")):
        assert repo.get_move_by_state(state).rom_id == rom
    assert repo.get_move_by_state("LIGHT_KICK", "close").rom_id == "1908"   # single version


# -------------------------------------------------------------- neutral jump --

def test_neutral_jump_normals_use_the_straight_air_scripts():
    neutral = _run(hold(I.UP, 4) + hold(None, 12) + _tap(Button.HEAVY_PUNCH, pre=0), 60)
    forward = _run(hold(I.UP_FORWARD, 4) + hold(None, 12) + _tap(Button.HEAVY_PUNCH, pre=0), 60)
    assert {v for s, v in neutral["seen"] if s == CharacterState.JUMP_HEAVY_PUNCH} == {"neutral"}
    assert {v for s, v in forward["seen"] if s == CharacterState.JUMP_HEAVY_PUNCH} == {None}
    repo = HitboxRepository.instance()
    assert repo.get_move_by_state("JUMP_HEAVY_PUNCH", "neutral").rom_id == "2388"
    assert repo.get_move_by_state("JUMP_HEAVY_PUNCH").rom_id == "2800"
    for st, rom in (("JUMP_LIGHT_PUNCH", "21c8"), ("JUMP_LIGHT_KICK", "2448"),
                    ("JUMP_MEDIUM_KICK", "2558"), ("JUMP_HEAVY_KICK", "2628")):
        assert repo.get_move_by_state(st, "neutral").rom_id == rom
    # no straight-air MP script exists: falls back to the base Air MP
    assert repo.get_move_by_state("JUMP_MEDIUM_PUNCH", "neutral").rom_id == "22a8"


# ---------------------------------------------------------------- f+MP -------

def test_forward_mp_is_a_two_hit_overhead():
    script = hold(I.FORWARD, 2) + [(I.FORWARD, [Button.MEDIUM_PUNCH])] + hold(None, 80)
    vs_crouch = _run(script, 60, p2_script=hold(I.DOWN_BACK, 90))
    vs_stand = _run(script, 60, p2_script=hold(I.BACK, 90))
    assert {s for s, _ in vs_crouch["seen"]} == {CharacterState.FORWARD_MP}
    assert vs_crouch["hits"] == 2, "f+MP registers two ROM hits"
    full = vs_crouch["p2"].max_health
    assert vs_crouch["p2"].health < full - 6, "an overhead beats a crouching guard"
    assert vs_stand["hits"] == 2 and full - vs_stand["p2"].health < 6, "standing guard blocks it (chip only)"
    mfd = get_move_frame_data(CharacterState.FORWARD_MP)
    assert mfd.hitboxes[0][1].hit_type == HitType.HIGH and mfd.total == 42 and mfd.hit_windows == [[15, 15], [16, 16]]


# ------------------------------------------------------------- dive kick -----

def test_dive_kick_dives_lands_and_recovers():
    script = hold(I.UP_FORWARD, 4) + hold(None, 14) + [(I.DOWN, [Button.MEDIUM_KICK])] + hold(None, 90)
    r = _run(script, 500, frames=110)
    states = [s for s, _ in r["seen"]]
    assert set(states) == {CharacterState.DIVE_KICK}
    assert r["dx"] > 120, "the dive carries the jump's momentum plus the ROM's 92px forward"
    assert r["p1"].state == CharacterState.STANDING and r["p1"].is_grounded, "lands and recovers to neutral"
    assert r["p1"].y == STAGE_FLOOR
    hit = _run(script, 120, frames=110)
    assert hit["hits"] == 1 and get_move_frame_data(CharacterState.DIVE_KICK).hitboxes[0][1].hit_type == HitType.HIGH


def test_dive_kick_needs_a_forward_jump_and_down():
    neutral = _run(hold(I.UP, 4) + hold(None, 14) + [(I.DOWN, [Button.MEDIUM_KICK])] + hold(None, 60), 500)
    assert CharacterState.DIVE_KICK not in {s for s, _ in neutral["seen"]}
    assert CharacterState.JUMP_MEDIUM_KICK in {s for s, _ in neutral["seen"]}
