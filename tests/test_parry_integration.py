"""
Parry integration tests at the collision-adapter level.

These exercise the live game path: SF3CollisionAdapter.update_parry_inputs
feeds the parry system every frame, and _apply_hit_to_character routes hits
through the parry check before applying damage.
"""

import pygame
import pytest

from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import CharacterState


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


class FakeHitStatus:
    """Minimal stand-in for SF3HitStatus in _apply_hit_to_character."""

    def __init__(self, damage=15, hitstun=12):
        self.damage = damage
        self.hitstun = hitstun
        self.hit_position_x = 0
        self.hit_position_y = 0


@pytest.fixture
def fighters():
    adapter = SF3CollisionAdapter()
    p1 = Akuma(200, STAGE_FLOOR, player_number=1)
    p2 = Akuma(300, STAGE_FLOOR, player_number=2)
    return adapter, p1, p2


def test_hit_applies_damage_without_parry(fighters):
    adapter, p1, p2 = fighters
    start_health = p2.health

    adapter._apply_hit_to_character(p1, p2, FakeHitStatus(), None)

    assert p2.health < start_health
    assert p2.state == CharacterState.HITSTUN_STANDING
    assert p2.hitstun_frames > 0


def test_parry_negates_damage(fighters):
    adapter, p1, p2 = fighters
    start_health = p2.health

    # Defender taps forward: opens the 7-frame parry window
    adapter.update_parry_inputs(p2, {'forward': True, 'down_forward': False})

    adapter._apply_hit_to_character(p1, p2, FakeHitStatus(), None)

    assert p2.health == start_health, "parried attack must deal no damage"
    assert p2.state == CharacterState.STANDING, "defender can act immediately after parry"
    assert p1.hitfreeze_frames > p2.hitfreeze_frames, "attacker eats the freeze, defender gets advantage"


def test_parry_window_expiry_lets_hit_through(fighters):
    adapter, p1, p2 = fighters
    start_health = p2.health

    # Open the window, then let it run out (held forward does not refresh it)
    forward = {'forward': True, 'down_forward': False}
    for _ in range(10):
        adapter.update_parry_inputs(p2, forward)

    adapter._apply_hit_to_character(p1, p2, FakeHitStatus(), None)

    assert p2.health < start_health, "attack outside the parry window must hit"


def test_adapter_reset_clears_round_state(fighters):
    adapter, p1, p2 = fighters

    adapter.tick()
    adapter.update_parry_inputs(p2, {'forward': True, 'down_forward': False})
    adapter._apply_hit_to_character(p1, p2, FakeHitStatus(), None)

    adapter.reset()

    assert adapter.frame_counter == 0
    assert adapter.sf3_system.hit_queue_input == 0
    for state in adapter.sf3_parry_system.player_parry_states.values():
        assert not state.parry_window_active
    assert adapter.sf3_combo_system.get_combo_count(1) == 0
    assert adapter.sf3_combo_system.get_combo_count(2) == 0


def test_single_tick_per_frame(fighters):
    """tick() advances the SF3 core once; collision checks must not advance it."""
    adapter, p1, p2 = fighters

    adapter.tick()
    adapter.check_attack_collision(p1, p2, None)
    adapter.check_attack_collision(p2, p1, None)

    assert adapter.frame_counter == 1
    assert adapter.sf3_system.current_frame == 1
