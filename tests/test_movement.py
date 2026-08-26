"""Movement / pushbox tests: airborne characters can pass over each other."""

import pygame
import pytest

from street_fighter_3rd.characters.akuma import Akuma
from street_fighter_3rd.systems.input_system import PlayerInput
from street_fighter_3rd.data.constants import STAGE_FLOOR
from street_fighter_3rd.data.enums import CharacterState, InputDirection


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    pygame.init()
    yield
    pygame.quit()


def test_grounded_characters_separate():
    """Two grounded, overlapping characters get pushed apart."""
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    b = Akuma(210, STAGE_FLOOR, player_number=2)  # overlapping (10px < min_distance)
    a.is_grounded = b.is_grounded = True
    before = abs(a.x - b.x)
    a._resolve_character_collision(b)
    assert abs(a.x - b.x) > before, "grounded overlap should push apart"


def test_airborne_character_passes_over():
    """An airborne character is NOT separated, so you can jump over the opponent."""
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    b = Akuma(205, STAGE_FLOOR, player_number=2)
    a.is_grounded = False   # a is mid-jump, directly above b
    b.is_grounded = True
    ax, bx = a.x, b.x
    a._resolve_character_collision(b)
    assert (a.x, b.x) == (ax, bx), "airborne character must pass over (no separation)"


def test_can_jump_forward_out_of_walking():
    """Holding forward (-> WALKING_FORWARD) then up must start a forward jump.

    Regression: jump used to be gated to STANDING/CROUCHING, so a pad forward-jump
    (hold forward, then up) never left the ground.
    """
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    a.input = PlayerInput(1)
    a.is_grounded = True
    a._transition_to_state(CharacterState.WALKING_FORWARD)
    a._check_movement(InputDirection.UP_FORWARD)
    assert a.state == CharacterState.JUMP_STARTUP
    assert a.jump_direction == InputDirection.UP_FORWARD


def test_can_jump_backward_out_of_walking():
    a = Akuma(200, STAGE_FLOOR, player_number=1)
    a.input = PlayerInput(1)
    a.is_grounded = True
    a._transition_to_state(CharacterState.WALKING_BACKWARD)
    a._check_movement(InputDirection.UP_BACK)
    assert a.state == CharacterState.JUMP_STARTUP
    assert a.jump_direction == InputDirection.UP_BACK


def test_grounded_normals_freeze_horizontal_movement():
    """A ground normal is stationary: starting one out of a walk must not let
    the character keep sliding (the 'punch while walking' bug). Air normals
    keep their jump momentum."""
    import os, sys
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pygame
    if not pygame.get_init():
        pygame.init(); pygame.display.set_mode((896, 512))
    from tools.diagnostics.harness import new_game
    from tools.diagnostics.scenario import ScriptedInputSystem, hold
    from street_fighter_3rd.data.enums import InputDirection as I, Button, CharacterState

    for button in (Button.LIGHT_PUNCH, Button.HEAVY_PUNCH, Button.MEDIUM_KICK):
        g = new_game(); p1 = g.player1
        p1.x, g.player2.x = 300, 700; p1._prev_x = p1.x
        g.input_system = ScriptedInputSystem(
            hold(I.FORWARD, 6) + [(I.FORWARD, [button])] + hold(I.FORWARD, 40), [])
        p1.input, g.player2.input = g.input_system.player1, g.input_system.player2
        moved_during_attack = 0.0
        attack_states = {CharacterState.LIGHT_PUNCH, CharacterState.HEAVY_PUNCH, CharacterState.MEDIUM_KICK}
        for _ in range(50):
            x0 = p1.x; g.update()
            if p1.state in attack_states:
                moved_during_attack += abs(p1.x - x0)
                assert p1.velocity_x == 0, f"{button.name}: vx {p1.velocity_x} during the attack"
        assert moved_during_attack == 0, f"{button.name}: slid {moved_during_attack}px while attacking"


def test_air_normal_keeps_jump_momentum():
    """An air normal must NOT freeze -- the jump arc continues."""
    import os, sys
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import pygame
    if not pygame.get_init():
        pygame.init(); pygame.display.set_mode((896, 512))
    from tools.diagnostics.harness import new_game
    from tools.diagnostics.scenario import ScriptedInputSystem, hold
    from street_fighter_3rd.data.enums import InputDirection as I, Button, CharacterState

    g = new_game(); p1 = g.player1
    p1.x, g.player2.x = 300, 700; p1._prev_x = p1.x
    g.input_system = ScriptedInputSystem(
        hold(I.UP_FORWARD, 4) + hold(None, 10) + [(None, [Button.HEAVY_PUNCH])] + hold(None, 30), [])
    p1.input, g.player2.input = g.input_system.player1, g.input_system.player2
    xs = []
    for _ in range(30):
        g.update()
        if p1.state == CharacterState.JUMP_HEAVY_PUNCH:
            xs.append(p1.x)
    assert len(xs) > 1 and xs[-1] - xs[0] > 0, "air normal must keep forward jump momentum"
