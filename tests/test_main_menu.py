"""Main menu: START GAME goes straight to opponent select; no MODE SELECT /
MOVES LIST entries (each entry starts its own mode; the special-move inputs
live on the CONTROLS screen)."""

import os

import pygame
import pytest

from street_fighter_3rd.core.main_menu import MainMenu, MenuState


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def test_main_menu_entries():
    menu = MainMenu(pygame.display.get_surface())
    labels = [i.text for i in menu.menus[MenuState.MAIN]]
    assert labels == ["START GAME", "TRAINING MODE", "DEV MODE", "HITBOX VIEWER",
                      "CONTROLS", "EXIT GAME"]
    assert not {"MOVES", "MODE_SELECT"} & {s.name for s in MenuState}


def test_every_screen_renders():
    menu = MainMenu(pygame.display.get_surface())
    for state in menu.menus:
        menu.current_state = state
        menu.selected_index = 0
        menu.render()
