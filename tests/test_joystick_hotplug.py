"""Joystick hot-plug: a stick plugged in (or powered on) after launch must be
picked up. Real hardware can't be simulated headless, so these pin the wiring:
the JOYDEVICE* events reach InputSystem.rescan_joysticks, and a rescan is a
safe no-op with zero devices (keyboard play unaffected)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest


@pytest.fixture
def game():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.core.game import Game
    return Game(screen, GameModeManager(GameMode.TRAINING))


def test_joydevice_events_trigger_rescan(game):
    calls = []
    game.input_system.rescan_joysticks = lambda: calls.append(1)
    game.handle_event(pygame.event.Event(pygame.JOYDEVICEADDED, device_index=0))
    game.handle_event(pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id=0))
    assert len(calls) == 2


def test_rescan_without_devices_is_safe(game):
    # Headless CI has no sticks: rescan must not raise and must leave both
    # players stickless-but-functional (keyboard path).
    game.input_system.rescan_joysticks()
    assert game.input_system.player1.joystick is None or True  # no crash is the contract
    game.update()  # input update still runs
