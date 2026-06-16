"""
Collision detection tests for the live SF3 collision path:

1. YAML/frame-data hitbox loading via SF3CollisionAdapter
2. Hit detection between two characters
3. Damage application
4. Combo scaling
5. Full Game integration (one fixed-timestep update)
"""

import pygame
import pytest

from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
from street_fighter_3rd.systems.sf3_combo_system import SF3ComboSystem
from street_fighter_3rd.systems.vfx import VFXManager
from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.data.constants import STAGE_FLOOR


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_yaml_hitbox_loading():
    """Frame-data hitboxes load for an attack on its active frames."""
    character = Akuma(200, STAGE_FLOOR, player_number=1)
    character._transition_to_state(CharacterState.LIGHT_PUNCH)
    # Standing LP is active on frames 5-7 (1-indexed); the adapter reads
    # state_frame + 1, so state_frame=4 puts us on active frame 5.
    character.state_frame = 4

    adapter = SF3CollisionAdapter()
    hitboxes = adapter._get_character_hitboxes(character)

    assert hitboxes, "Standing LP must have an active hitbox on frame 5"
    hitbox_data, rect = hitboxes[0]
    print(f"Loaded hitbox: damage={hitbox_data.damage}, "
          f"size={hitbox_data.width}x{hitbox_data.height}, "
          f"pos=({rect.x}, {rect.y}), hit_type={hitbox_data.hit_type}")
    assert hitbox_data.damage > 0, "hitbox must deal damage"
    assert hitbox_data.width > 0 and hitbox_data.height > 0, "hitbox must have a real size"
    assert rect.width == hitbox_data.width and rect.height == hitbox_data.height


def test_collision_detection():
    """A light punch on its active frame must hit a nearby defender."""
    attacker = Akuma(200, STAGE_FLOOR, player_number=1)
    defender = Akuma(250, STAGE_FLOOR, player_number=2)  # Close enough to hit

    # Standing MP/LK rom pointers are unidentified (framedata_meta.lua disproved
    # the old guesses), so use LP (rom 1438), which is authoritatively named.
    attacker._transition_to_state(CharacterState.LIGHT_PUNCH)
    # Standing LP is active on frame 5 (1-indexed); adapter reads state_frame + 1.
    attacker.state_frame = 4

    adapter = SF3CollisionAdapter()
    vfx_manager = VFXManager()

    initial_health = defender.health

    adapter.tick()  # advance the SF3 core one game frame
    hit_occurred = adapter.check_attack_collision(attacker, defender, vfx_manager)

    assert hit_occurred, "LP active frame at 50px range must register a hit"
    assert defender.health < initial_health, (
        f"hit must deal damage: health stayed at {defender.health}"
    )
    print(f"Damage dealt: {initial_health - defender.health}")

    combo_info = adapter.get_combo_info(2)  # Defender is player 2
    assert combo_info['count'] == 1, f"first hit must start a 1-hit combo, got {combo_info['count']}"
    assert combo_info['damage'] == initial_health - defender.health, (
        "combo damage must match the health lost"
    )


def test_combo_scaling():
    """Combo scaling follows SF3's 100/90/80/70/60 sequence."""
    combo_system = SF3ComboSystem()

    damages = []
    for i in range(5):
        # defender stays in hitstun across the chain -> a genuine 5-hit combo
        scaled_damage = combo_system.register_hit(
            1, 2, 100, "normal", defender_in_hitstun=(i > 0))
        damages.append(scaled_damage)
        print(f"Hit {i + 1}: 100 -> {scaled_damage}")

    expected = [100, 90, 80, 70, 60]
    assert damages == expected, f"scaling sequence wrong: got {damages}, expected {expected}"


def test_game_integration():
    """The game uses SF3CollisionAdapter and survives a fixed-timestep update."""
    from street_fighter_3rd.core.game import Game

    screen = pygame.display.set_mode((800, 600))
    game = Game(screen)

    assert hasattr(game.collision_system, 'sf3_combo_system'), (
        "Game must use SF3CollisionAdapter as its collision system"
    )

    # One frame of the fixed-timestep loop must not raise
    game.update()
