"""Phase 3 VFX & game-feel tests: sparks, hitstop scaling, deterministic shake."""

import pygame
import pytest

from street_fighter_3rd.systems.vfx import VFXManager, HitSparkType, SPARK_TABLE
from street_fighter_3rd.systems.sf3_collision_adapter import (
    _spark_for_state, HITSTOP_BASE, HITSTOP_PER, HITSTOP_MAX,
)
from street_fighter_3rd.data.enums import CharacterState


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def _hitstop(damage):
    return min(HITSTOP_MAX, HITSTOP_BASE + damage // HITSTOP_PER)


def test_block_and_parry_sparks_load_from_cache():
    m = VFXManager()
    for spark_type in (HitSparkType.BLOCK, HitSparkType.PARRY, HitSparkType.HEAVY):
        _sub, lo, hi = SPARK_TABLE[spark_type]
        assert all(i in m.sprite_cache for i in range(lo, hi + 1)), \
            f"{spark_type} sprites not cached (per-category load failed?)"


def test_spark_by_strength():
    assert _spark_for_state(CharacterState.LIGHT_PUNCH) == HitSparkType.LIGHT
    assert _spark_for_state(CharacterState.MEDIUM_KICK) == HitSparkType.MEDIUM
    assert _spark_for_state(CharacterState.HEAVY_PUNCH) == HitSparkType.HEAVY
    assert _spark_for_state(CharacterState.GOHADOKEN) == HitSparkType.SPECIAL
    assert _spark_for_state(None) == HitSparkType.LIGHT  # unknown -> light


def test_light_and_heavy_spawn_different_effects():
    m = VFXManager()
    m.spawn_hit_spark(0, 0, HitSparkType.LIGHT)
    light = len(m.effects[-1].sprites)
    m.spawn_hit_spark(0, 0, HitSparkType.HEAVY)
    heavy = len(m.effects[-1].sprites)
    assert light != heavy


def test_hitstop_scales_with_damage():
    assert _hitstop(25) > _hitstop(5)
    assert HITSTOP_BASE <= _hitstop(5) <= HITSTOP_MAX
    assert _hitstop(9999) == HITSTOP_MAX  # capped


def test_request_shake_keeps_max_and_clears():
    m = VFXManager()
    assert m.shake_request == 0
    m.request_shake(3)
    m.request_shake(5)
    m.request_shake(2)
    assert m.shake_request == 5
    m.clear()
    assert m.shake_request == 0


def _game():
    from street_fighter_3rd.core.game import Game
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT
    gmm = GameModeManager(GameMode.NORMAL)
    gmm.config.no_rounds = True
    return Game(pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)), gmm)


def test_shake_offset_zero_when_idle():
    g = _game()
    assert g.shake_frames == 0
    assert g.shake_offset() == (0, 0)


def test_shake_offset_deterministic_and_decays():
    g = _game()
    g.shake_intensity = 4
    g.shake_frames = g.SHAKE_TOTAL
    assert g.shake_offset() == g.shake_offset()       # pure function
    big = abs(g.shake_offset()[0])
    g.shake_frames = 1
    small = abs(g.shake_offset()[0])
    assert small <= big                                # decays toward 0


def test_shake_request_drives_countdown():
    g = _game()
    g.vfx_manager.request_shake(4)
    g.update()
    assert g.shake_frames == g.SHAKE_TOTAL            # picked up the request
    assert g.vfx_manager.shake_request == 0           # drained
    g.update()
    assert g.shake_frames == g.SHAKE_TOTAL - 1        # counts down


def test_render_with_shake_active_does_not_raise():
    g = _game()
    for _ in range(3):
        g.update()
    g.shake_intensity = 4
    g.shake_frames = g.SHAKE_TOTAL
    g.debug_display = True
    g.render()  # overlay drawn on real screen after the offset blit
