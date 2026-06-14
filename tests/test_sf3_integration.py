"""
SF3 Integration Tests

Tests the integration of the authentic SF3 subsystems:
- Core data structures and 8-level state machine
- Collision system with 32-slot hit queue
- Parry system with 7-frame window
- Damage scaling
"""

import pytest

from street_fighter_3rd.systems.sf3_core import (
    SF3GamePhase, SF3StateCategory, create_sf3_player, SF3_DAMAGE_SCALING,
)
from street_fighter_3rd.systems.sf3_collision import (
    SF3CollisionSystem, SF3CollisionEvent,
)
from street_fighter_3rd.systems.sf3_parry import SF3ParrySystem, SF3ParryResult
from street_fighter_3rd.systems.sf3_hitboxes import SF3Hitbox, SF3HitLevel


@pytest.fixture
def player1():
    player = create_sf3_player(1, team=1)
    player.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.NEUTRAL, 0)
    player.work.position.x = 100
    player.work.position.y = 200
    return player


@pytest.fixture
def player2():
    player = create_sf3_player(2, team=2)
    player.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.NEUTRAL, 0)
    player.work.position.x = 200
    player.work.position.y = 200
    return player


@pytest.fixture
def collision_system():
    return SF3CollisionSystem()


@pytest.fixture
def parry_system():
    return SF3ParrySystem()


def _medium_punch_hitbox() -> SF3Hitbox:
    return SF3Hitbox(
        offset_x=50, offset_y=-65, width=60, height=40,
        damage=115, stun=7, hitstun=12, blockstun=8,
        hit_level=SF3HitLevel.MID,
    )


def test_attack_scenario(player1, player2, collision_system):
    """An attack hitbox overlapping the defender's body enters the hit queue."""
    player1.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.ATTACKING, 5)

    attack_hitbox = _medium_punch_hitbox()
    body_hitbox = SF3Hitbox(offset_x=0, offset_y=-80, width=40, height=80)

    pos1 = (player1.work.position.x, player1.work.position.y)
    pos2 = (player2.work.position.x, player2.work.position.y)

    assert attack_hitbox.overlaps(
        body_hitbox, pos1, player1.work.face, pos2, player2.work.face
    ), "MP hitbox at range 100 must overlap the defender's body box"

    collision_event = SF3CollisionEvent(
        attacker=player1,
        defender=player2,
        attack_box=attack_hitbox,
        hit_box=body_hitbox,
        collision_type="attack",
        hit_position=pos2,
        frame_number=6,
    )
    collision_system.add_collision_event(collision_event)
    assert collision_system.hit_queue_input == 1

    # Processing consumes the queue
    collision_system.hit_check_main_process()
    assert collision_system.hit_queue_input == 0

    old_health = player2.work.vitality
    player2.apply_damage(attack_hitbox.damage, combo_scaling=False)
    assert player2.work.vitality == old_health - attack_hitbox.damage


def test_parry_scenario(player1, player2, parry_system):
    """Forward input opens a 7-frame window during which a mid attack is parried."""
    parry_system.update_parry_inputs(player2, {'forward': True, 'down_forward': False})

    assert parry_system.is_in_parry_window(player2)
    # The window opens at 7 frames and counts down within the same update
    assert 0 < parry_system.get_parry_frames_remaining(player2) <= SF3ParrySystem.PARRY_WINDOW_FRAMES

    result = parry_system.defense_ground(player1, player2, _medium_punch_hitbox(), "mid")

    assert result == SF3ParryResult.PARRY_SUCCESS
    assert parry_system.has_parry_advantage(player2)
    assert parry_system.get_parry_counter(player2) == 1


def test_parry_window_expires(player1, player2, parry_system):
    """After 7 frames the window closes and the same attack hits."""
    parry_system.update_parry_inputs(player2, {'forward': True, 'down_forward': False})

    # Hold forward past the window; the window must not refresh while held
    for _ in range(SF3ParrySystem.PARRY_WINDOW_FRAMES):
        parry_system.update_parry_inputs(player2, {'forward': True, 'down_forward': False})

    assert not parry_system.is_in_parry_window(player2)

    result = parry_system.defense_ground(player1, player2, _medium_punch_hitbox(), "mid")
    assert result == SF3ParryResult.HIT_CONFIRMED


def test_low_parry_does_not_parry_mid(player1, player2, parry_system):
    """A down-forward (low) parry must not parry a mid attack."""
    parry_system.update_parry_inputs(player2, {'forward': False, 'down_forward': True})
    assert parry_system.is_in_parry_window(player2)

    result = parry_system.defense_ground(player1, player2, _medium_punch_hitbox(), "mid")
    assert result == SF3ParryResult.HIT_CONFIRMED


def test_combo_scenario(player2):
    """Damage scaling follows SF3's [100, 90, 80, ...] table."""
    player2.work.vitality = 1000
    player2.combo_count = 0

    base_damage = 100
    for hit in range(5):
        old_health = player2.work.vitality
        player2.apply_damage(base_damage, combo_scaling=True)
        player2.increment_combo()
        actual_damage = old_health - player2.work.vitality

        if hit == 0:
            expected = base_damage  # First hit: 100%
        else:
            scale = SF3_DAMAGE_SCALING[min(hit, len(SF3_DAMAGE_SCALING) - 1)]
            expected = int(base_damage * scale / 100)
        assert actual_damage == expected, f"Hit {hit + 1}: expected {expected}, got {actual_damage}"


def test_state_machine_integration(player1):
    """SF3's 8-level routine hierarchy transitions and reports states correctly."""
    player1.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.ATTACKING, 5)
    assert player1.work.is_in_gameplay()
    assert player1.work.is_attacking()
    assert not player1.work.is_damaged()

    player1.work.set_routine_state(SF3GamePhase.GAMEPLAY, SF3StateCategory.DAMAGED, 2)
    assert player1.work.is_damaged()
    assert not player1.work.is_attacking()

    assert len(player1.work.routine_no) == 8
