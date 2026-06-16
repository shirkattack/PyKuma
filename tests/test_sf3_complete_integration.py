"""
Complete SF3 Integration Test

Tests all the major SF3 systems we've integrated:
1. SF3CollisionAdapter with authentic collision detection
2. YAML-based hitbox data loading
3. Parry system integration
4. Combo system with damage scaling
5. Game wired to the SF3 collision adapter
"""

from pathlib import Path

import pygame
import pytest
import yaml

from street_fighter_3rd.systems.sf3_collision_adapter import SF3CollisionAdapter
from street_fighter_3rd.systems.sf3_combo_system import SF3ComboSystem
from street_fighter_3rd.systems.sf3_parry import SF3ParrySystem

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANIMATIONS_YAML = PROJECT_ROOT / "src" / "street_fighter_3rd" / "data" / "animations.yaml"


def test_sf3_collision_adapter():
    """SF3CollisionAdapter exposes combo info in the format the UI expects."""
    adapter = SF3CollisionAdapter()

    combo_info = adapter.get_combo_info(1)
    assert combo_info['count'] == 0, "no hits yet: combo count must start at 0"
    assert combo_info['damage'] == 0, "no hits yet: combo damage must start at 0"
    assert combo_info['active'] is False, "no combo can be active before any hit"
    for key in ('count', 'damage', 'active', 'scaling', 'type'):
        assert key in combo_info, f"combo info missing '{key}' key"


def test_combo_system():
    """Standalone combo system applies SF3 damage scaling per hit.

    A combo only continues while the defender is still in hitstun, so hits 2/3
    pass defender_in_hitstun=True to express a genuine 3-hit combo.
    """
    combo_system = SF3ComboSystem()

    scaled_damage_1 = combo_system.register_hit(1, 2, 100, "normal")  # 1st hit
    scaled_damage_2 = combo_system.register_hit(1, 2, 100, "normal", defender_in_hitstun=True)  # 2nd hit
    scaled_damage_3 = combo_system.register_hit(1, 2, 100, "normal", defender_in_hitstun=True)  # 3rd hit

    print(f"Damage scaling: 100 -> {scaled_damage_1}, {scaled_damage_2}, {scaled_damage_3}")
    assert scaled_damage_1 == 100, f"1st hit must be unscaled, got {scaled_damage_1}"
    assert scaled_damage_2 == 90, f"2nd hit must scale to 90, got {scaled_damage_2}"
    assert scaled_damage_3 == 80, f"3rd hit must scale to 80, got {scaled_damage_3}"


def test_combo_resets_when_defender_recovers():
    """Mashing on a recovered defender must NOT rack a fake multi-hit combo.

    Each hit lands with defender_in_hitstun=False (the defender recovered between
    hits), so every hit is a fresh 1-hit combo at full, unscaled damage -- not a
    growing combo counter. This is the B1 fix for the clip's bogus "7 HITS".
    """
    combo_system = SF3ComboSystem()
    for _ in range(7):
        dmg = combo_system.register_hit(1, 2, 100, "normal", defender_in_hitstun=False)
        assert dmg == 100, "a hit on a recovered defender is unscaled (new combo)"
        assert combo_system.get_combo_count(2) == 1, "must never exceed a 1-hit combo"


def test_yaml_hitbox_loading():
    """The animations YAML contains hitbox data for Akuma's moves."""
    assert ANIMATIONS_YAML.exists(), f"animation data file missing: {ANIMATIONS_YAML}"

    with open(ANIMATIONS_YAML, 'r') as f:
        anim_data = yaml.safe_load(f)

    akuma_anims = anim_data.get('characters', {}).get('akuma', {}).get('animations', {})
    assert akuma_anims, "animations.yaml must define animations for akuma"

    hitbox_moves = [name for name, data in akuma_anims.items() if 'hitbox' in data]
    assert hitbox_moves, "at least one Akuma move must define hitbox data"

    print(f"Found {len(hitbox_moves)} moves with hitbox data")
    for move in hitbox_moves:
        hitbox = akuma_anims[move]['hitbox']
        assert hitbox.get('damage', 0) > 0, f"{move}: hitbox must deal damage"
        assert hitbox.get('width', 0) > 0, f"{move}: hitbox must have a width"
        assert hitbox.get('height', 0) > 0, f"{move}: hitbox must have a height"


def test_sf3_parry_system():
    """SF3 parry system uses the authentic frame windows."""
    parry_system = SF3ParrySystem()

    assert parry_system.PARRY_WINDOW_FRAMES == 7, (
        f"SF3 parry window must be 7 frames, got {parry_system.PARRY_WINDOW_FRAMES}"
    )
    assert parry_system.PARRY_ADVANTAGE_FRAMES == 8, (
        f"SF3 parry advantage must be 8 frames, got {parry_system.PARRY_ADVANTAGE_FRAMES}"
    )


def test_game_integration():
    """The Game wires up the SF3 collision adapter."""
    from street_fighter_3rd.core.game import Game

    pygame.init()
    try:
        screen = pygame.display.set_mode((800, 600))
        game = Game(screen)

        assert hasattr(game.collision_system, 'sf3_combo_system'), (
            "Game must use SF3CollisionAdapter as its collision system"
        )
    finally:
        pygame.quit()
