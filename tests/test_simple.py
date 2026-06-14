"""Smoke test: pygame initializes and creates a display headlessly."""

import pygame


def test_pygame_initializes_and_creates_display():
    pygame.init()
    try:
        assert pygame.display.get_init(), "pygame display module must initialize"

        screen = pygame.display.set_mode((1, 1))
        assert screen is not None, "set_mode must return a surface"
        assert screen.get_size() == (1, 1)

        pygame.display.set_caption("Test")
        caption, _ = pygame.display.get_caption()
        assert caption == "Test"
    finally:
        pygame.quit()
