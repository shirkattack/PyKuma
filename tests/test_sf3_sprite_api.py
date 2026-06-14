"""
Tests for the SF3SpriteManager API.

Sprite image assets are not shipped in the repository, so these tests verify
the manager's API contract and its graceful behavior when assets are absent.
"""

from pathlib import Path

import pygame
import pytest

from street_fighter_3rd.graphics.sprite_manager import (
    SF3SpriteManager,
    SpriteAnimation,
    SpriteFrame,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_PATH = PROJECT_ROOT / "tools" / "sprite_extraction"


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture
def manager():
    return SF3SpriteManager(str(ASSETS_PATH))


def test_sprite_manager_construction(manager):
    """The manager constructs with the expected public API."""
    assert manager.assets_base_path == ASSETS_PATH
    assert manager.loaded_characters == set(), "no characters loaded at construction"

    for method in (
        "load_character_sprites",
        "get_character_animation",
        "get_character_animations",
        "get_animation_frame",
        "render_character_sprite",
        "is_character_loaded",
        "unload_character",
    ):
        assert callable(getattr(manager, method, None)), f"missing API method: {method}"


def test_unloaded_character_access(manager):
    """Accessing an unloaded character is safe and returns empty results."""
    assert not manager.is_character_loaded("akuma")
    assert manager.get_character_animations("akuma") == {}
    assert manager.get_character_animation("akuma", "stance") is None
    assert manager.get_animation_frame("akuma", "stance", 0) is None


def test_sprite_animation_frame_access():
    """SpriteAnimation frame lookup loops and clamps correctly."""
    surface = pygame.Surface((10, 10))
    frames = [SpriteFrame(frame_number=i, image=surface) for i in range(3)]
    animation = SpriteAnimation(animation_name="stance", frames=frames, loop=True)

    assert animation.get_frame(0) is frames[0]
    assert animation.get_frame(2) is frames[2]
    assert animation.get_frame(3) is frames[0], "looping animation must wrap around"
    assert animation.get_total_duration() == 3

    animation.loop = False
    assert animation.get_frame(99) is frames[-1], "non-looping animation must clamp to last frame"

    empty = SpriteAnimation(animation_name="empty")
    assert empty.get_frame(0) is None, "empty animation must return None"
