"""Hit-reaction system tests (knockdown / launch / block / clamp)."""

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.characters.character import apply_reaction
from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import CharacterState, HitEffect


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


class FakeHit:
    def __init__(self, damage=20, hitstun=16):
        self.damage = damage
        self.hitstun = hitstun
        self.hit_position_x = 0
        self.hit_position_y = 0


@pytest.fixture
def fighters():
    return Akuma(200, STAGE_FLOOR, 1), Akuma(300, STAGE_FLOOR, 2)


def _hit(attacker_state):
    adapter = SF3CollisionAdapter()
    a = Akuma(200, STAGE_FLOOR, 1)
    b = Akuma(300, STAGE_FLOOR, 2)
    a._transition_to_state(attacker_state)
    return adapter, a, b


def test_normal_hit_goes_to_hitstun_and_recovers():
    adapter, a, b = _hit(CharacterState.LIGHT_PUNCH)
    adapter._apply_hit_to_character(a, b, FakeHit(), None)
    assert b.state == CharacterState.HITSTUN_STANDING
    assert b.hitstun_frames > 0
    for _ in range(40):
        b.update(a)
    assert b.state == CharacterState.STANDING


def test_sweep_knocks_down():
    adapter, a, b = _hit(CharacterState.CROUCH_HEAVY_KICK)  # AKUMA_CR_HK -> KNOCKDOWN
    adapter._apply_hit_to_character(a, b, FakeHit(), None)
    assert b.state == CharacterState.KNOCKDOWN


def test_heavy_punch_launches():
    adapter, a, b = _hit(CharacterState.HEAVY_PUNCH)  # AKUMA_ST_HP -> JUGGLE
    adapter._apply_hit_to_character(a, b, FakeHit(), None)
    assert b.state == CharacterState.HITSTUN_AIRBORNE
    assert b.velocity_y < 0 and not b.is_grounded
    # falls under gravity, lands, recovers
    for _ in range(120):
        b.update(a)
        if b.is_grounded and b.state == CharacterState.STANDING:
            break
    assert b.is_grounded and b.state == CharacterState.STANDING


def test_block_gives_chip_and_blockstun_not_hitstun():
    adapter, a, b = _hit(CharacterState.LIGHT_PUNCH)
    b.is_blocking = True
    start = b.health
    adapter._apply_hit_to_character(a, b, FakeHit(), None)
    assert b.state in (CharacterState.BLOCKSTUN_HIGH, CharacterState.BLOCKSTUN_LOW)
    assert b.blockstun_frames > 0
    assert 0 < (start - b.health) < FakeHit().damage  # chip only, less than full


def test_damage_never_goes_negative():
    adapter, a, b = _hit(CharacterState.HEAVY_PUNCH)
    b.health = 5
    adapter._apply_hit_to_character(a, b, FakeHit(damage=99), None)
    assert b.health == 0  # clamped, not negative


def test_take_damage_respects_hit_effect():
    a = Akuma(200, STAGE_FLOOR, 1)
    a.take_damage(10, 16, HitEffect.KNOCKDOWN)
    assert a.state == CharacterState.KNOCKDOWN
    assert a.health == 135


def test_reaction_animations_resolve():
    a = Akuma(200, STAGE_FLOOR, 1)
    for state in (CharacterState.HITSTUN_STANDING, CharacterState.HITSTUN_CROUCHING,
                  CharacterState.HITSTUN_AIRBORNE, CharacterState.KNOCKDOWN,
                  CharacterState.BLOCKSTUN_HIGH, CharacterState.BLOCKSTUN_LOW):
        a._transition_to_state(state)
        assert a.animation_controller.get_current_sprite() is not None, f"{state.name} sprite missing"
