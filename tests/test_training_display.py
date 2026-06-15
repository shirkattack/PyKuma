"""Training-mode display tools: input history, damage numbers, frame data.

These cover the data + capture layer behind the on-screen overlays (the overlays
themselves draw from these). Rendering is exercised headlessly to prove it never
raises with the dummy SDL driver.
"""

import pygame
import pytest

from street_fighter_3rd.systems.input_system import PlayerInput
from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data
from street_fighter_3rd.data.enums import CharacterState, InputDirection, Button


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    yield
    pygame.quit()


# --- A1: input history -------------------------------------------------------

def _feed(pi, direction, buttons=(), frames=1):
    """Push N frames of a (direction, held-buttons) state into the buffer."""
    from street_fighter_3rd.systems.input_system import InputState
    for _ in range(frames):
        pi.frame_count += 1
        pi.input_buffer.append(InputState(
            direction=direction,
            buttons_pressed=set(buttons),
            buttons_just_pressed=set(),
            buttons_just_released=set(),
            frame_number=pi.frame_count,
        ))


def test_input_history_collapses_repeats():
    pi = PlayerInput(1)
    _feed(pi, InputDirection.FORWARD, frames=30)
    rows = pi.get_input_history(10)
    assert len(rows) == 1
    assert rows[0].direction == InputDirection.FORWARD
    assert rows[0].repeat == 30
    assert not rows[0].buttons


def test_input_history_new_row_on_button_or_direction_change():
    pi = PlayerInput(1)
    _feed(pi, InputDirection.DOWN, frames=3)
    _feed(pi, InputDirection.DOWN_FORWARD, frames=2)
    _feed(pi, InputDirection.FORWARD, frames=2)
    _feed(pi, InputDirection.FORWARD, buttons=(Button.LIGHT_PUNCH,), frames=1)
    rows = pi.get_input_history(10)
    # down, down-forward, forward, forward+LP  -> 4 distinct rows (QCF + button)
    assert [r.direction for r in rows] == [
        InputDirection.DOWN, InputDirection.DOWN_FORWARD,
        InputDirection.FORWARD, InputDirection.FORWARD,
    ]
    assert Button.LIGHT_PUNCH in rows[-1].buttons


def test_input_history_limit():
    pi = PlayerInput(1)
    # 12 alternating rows; only the last 5 should be returned, newest last.
    for i in range(12):
        _feed(pi, InputDirection.FORWARD if i % 2 == 0 else InputDirection.BACK, frames=1)
    rows = pi.get_input_history(5)
    assert len(rows) == 5
    assert rows[-1].last_frame == 12  # newest is last


# --- A2: damage numbers ------------------------------------------------------

def test_health_drop_spawns_damage_number():
    from street_fighter_3rd.core.game import Game
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    pygame.display.set_mode((8, 8))
    g = Game(pygame.display.get_surface(), GameModeManager(GameMode.TRAINING))
    assert g._damage_popups == []
    g.player2.health -= 40           # simulate a hit on P2
    g._update_health_dynamics()
    assert len(g._damage_popups) == 1
    pop = g._damage_popups[0]
    assert pop["amount"] == 40 and pop["player"] == 2
    assert list(g._recent_damage)[-1]["amount"] == 40


def test_damage_number_ages_out():
    from street_fighter_3rd.core.game import Game
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    pygame.display.set_mode((8, 8))
    g = Game(pygame.display.get_surface(), GameModeManager(GameMode.TRAINING))
    g._on_damage(g.player1, 25)
    for _ in range(Game.DAMAGE_POPUP_LIFETIME + 1):
        g._update_damage_popups()
    assert g._damage_popups == []


# --- A3: frame data ----------------------------------------------------------

def test_frame_data_lookup_has_startup_active_recovery():
    fd = get_move_frame_data(CharacterState.MEDIUM_PUNCH)
    assert fd is not None
    assert fd.startup > 0
    assert len(fd.active) > 0
    assert fd.recovery >= 0


def test_frame_advantage_values_present_and_signed():
    # HEAVY_KICK is minus on block in the data; LIGHT_PUNCH is plus on hit.
    hk = get_move_frame_data(CharacterState.HEAVY_KICK)
    lp = get_move_frame_data(CharacterState.LIGHT_PUNCH)
    assert hk.on_block < 0
    assert lp.on_hit > 0


def test_unmapped_state_has_no_frame_data():
    assert get_move_frame_data(CharacterState.STANDING) is None


# --- capture + render smoke --------------------------------------------------

def test_debug_state_includes_training_block():
    from street_fighter_3rd.core.game import Game
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    pygame.display.set_mode((8, 8))
    g = Game(pygame.display.get_surface(), GameModeManager(GameMode.TRAINING))
    st = g.debug_state()
    assert "training" in st
    assert set(st["training"]) == {"inputs", "recent_damage", "current_moves"}


def test_training_overlays_render_without_error():
    from street_fighter_3rd.core.game import Game
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    screen = pygame.display.set_mode((896, 512))
    g = Game(screen, GameModeManager(GameMode.TRAINING))
    # Put a player into an attack state so the frame-data strip draws too.
    g.player1._transition_to_state(CharacterState.MEDIUM_PUNCH)
    g._on_damage(g.player2, 30)
    g._render_training_overlays()  # must not raise
