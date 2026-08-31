"""BT2: Demon Flip / Hyakkishu (QCF+K) -- an arcing forward jump toward the
opponent, and its ROM followups: a punch during the arc cancels into b118
(Hyakki Goushou, the palm), a kick into b218 (Hyakki Goujin). The flip itself
stays hitless -- see test_the_flip_itself_stays_hitless."""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game
from tools.diagnostics.scenario import ScriptedInputSystem, hold
from street_fighter_3rd.data.enums import (
    Button, InputDirection, FacingDirection, CharacterState)


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def test_qcf_kick_demon_flip_arcs_and_lands():
    g = new_game()
    g.player1.x, g.player2.x = 300, 560
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    motion = [(InputDirection.DOWN, []), (InputDirection.DOWN_FORWARD, []),
              (InputDirection.FORWARD, [Button.MEDIUM_KICK])]
    g.input_system = ScriptedInputSystem(hold(InputDirection.NEUTRAL, 2) + motion + hold(None, 60), [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2

    x0, y0 = g.player1.x, g.player1.y
    triggered = airborne = False
    peak = 0.0
    for _ in range(60):
        g.update()
        if g.player1.state == CharacterState.DEMON_FLIP:
            triggered = True
            airborne = airborne or not g.player1.is_grounded
            peak = min(peak, g.player1.y - y0)
    assert triggered, "QCF+K should start a demon flip"
    assert airborne, "demon flip should go airborne"
    assert -peak > 40, "should rise into an arc"
    assert g.player1.x - x0 > 100, "should travel forward toward the opponent"
    assert g.player1.is_grounded and g.player1.state == CharacterState.STANDING, "should land + recover"


def _flip_then(button: Button, delay: int = 12):
    """Run a QCF+K demon flip, press `button` `delay` frames into the arc, and
    return (game, states seen, the followup's peak forward travel)."""
    g = new_game()
    g.player1.x, g.player2.x = 300, 560
    g.player1.facing, g.player2.facing = FacingDirection.RIGHT, FacingDirection.LEFT
    motion = [(InputDirection.DOWN, []), (InputDirection.DOWN_FORWARD, []),
              (InputDirection.FORWARD, [Button.MEDIUM_KICK])]
    script = (hold(InputDirection.NEUTRAL, 2) + motion + hold(None, delay)
              + [(None, [button])] + hold(None, 90))
    g.input_system = ScriptedInputSystem(script, [])
    g.player1.input = g.input_system.player1
    g.player2.input = g.input_system.player2
    states = []
    for _ in range(110):
        g.update()
        states.append(g.player1.state)
    return g, states


def test_punch_during_the_flip_cancels_into_the_rom_palm():
    """b118 (framedata_meta 'Demon flip P cancel' = Hyakki Goushou)."""
    g, states = _flip_then(Button.MEDIUM_PUNCH)
    assert CharacterState.DEMON_FLIP in states
    assert CharacterState.DEMON_FLIP_PALM in states, "P during the flip should cancel into the palm"
    assert g.player1.is_grounded and g.player1.state == CharacterState.STANDING, "should land + recover"


def test_kick_during_the_flip_cancels_into_the_rom_kick():
    """b218 (framedata_meta 'Demon flip K cancel' = Hyakki Goujin)."""
    g, states = _flip_then(Button.HEAVY_KICK)
    assert CharacterState.DEMON_FLIP_KICK in states, "K during the flip should cancel into the dive"
    assert g.player1.is_grounded and g.player1.state == CharacterState.STANDING


def test_followups_carry_their_rom_boxes_and_captured_combat():
    """The boxes and the damage/stun are the ROM's, not invented: b118/b218
    were captured live (rom_combat: 23/13 and 17/11)."""
    from street_fighter_3rd.data.akuma_hitboxes import get_akuma_hitboxes
    from street_fighter_3rd.data.hitbox_repository import HitboxRepository

    for state, rom_id, damage, stun in (
            (CharacterState.DEMON_FLIP_PALM, "b118", 23, 13),
            (CharacterState.DEMON_FLIP_KICK, "b218", 17, 11)):
        move = HitboxRepository.instance().get_move_by_state(state.name)
        assert move is not None and move.rom_id == rom_id
        assert move.rom_combat and move.rom_combat["status"] == "verified"
        hit = move.rom_combat["hits"][0]
        assert (hit["damage"], hit["stun"]) == (damage, stun)
        window = move.hit_windows_or_derived()[0]
        assert get_akuma_hitboxes(state, window[0]), f"{rom_id} should have an active box in its window"


def test_the_flip_itself_stays_hitless():
    """af08 carries attack boxes in the vendored framedata but the live capture
    read none while driving it; until that is resolved the flip does not hit."""
    from street_fighter_3rd.data.akuma_hitboxes import get_akuma_hitboxes
    assert not any(get_akuma_hitboxes(CharacterState.DEMON_FLIP, f) for f in range(1, 72))
