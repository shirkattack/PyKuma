"""G2: a fireball must come out from a REAL-keyboard QCF, not just a scripted
perfect buffer.

tests/test_fireball.py drives a hand-built QCF buffer through ScriptedInputSystem.
This test instead drives the actual InputSystem / PlayerInput.update() by mocking
pygame.key.get_pressed(), so it exercises the real keyboard -> direction ->
motion-buffer -> special-move path the player actually uses.
"""

import os
import sys

import pygame
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.diagnostics.harness import new_game

# Player-1 key map (input_system.py): K_s=down, K_d=right(=forward facing right),
# K_a=left, K_w=up, K_j=LIGHT_PUNCH.
K = pygame  # alias for readability below


class _FakeKeys:
    """Stand-in for pygame.key.get_pressed(): truthy for keys in `pressed`."""
    def __init__(self, pressed):
        self._pressed = pressed
    def __getitem__(self, key):
        return key in self._pressed


@pytest.fixture(scope="module", autouse=True)
def pygame_headless():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((896, 512))
    yield
    pygame.quit()


def test_qcf_lp_from_keyboard_spawns_a_fireball(monkeypatch):
    g = new_game()
    g.player1.x, g.player2.x = 250, 700   # P1 faces right -> forward = K_d

    # A human QCF roll: down, down-forward, forward, then +LP, then release.
    frames = [
        {K.K_s},                  # down
        {K.K_s},                  # down
        {K.K_s, K.K_d},           # down-forward (the diagonal the matcher needs)
        {K.K_d},                  # forward
        {K.K_d, K.K_j},           # forward + LP pressed -> QCF+LP completes
        set(),
    ]

    current = {"keys": set()}
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _FakeKeys(current["keys"]))

    assert _run_keys(g, frames, monkeypatch), "a keyboard QCF+LP should spawn a Gohadoken"


def test_sloppy_qcf_without_diagonal_still_fires(monkeypatch):
    # Keyboard players routinely drop the down-forward diagonal: down -> forward
    # with no diagonal frame. Input leniency must still produce a fireball (this
    # is the real reason fireballs felt unreliable).
    g = new_game()
    g.player1.x, g.player2.x = 250, 700
    frames = [{K.K_s}, {K.K_s}, {K.K_d}, {K.K_d, K.K_j}, set()]
    assert _run_keys(g, frames, monkeypatch), "a diagonal-less QCF+LP should still fire"


def test_walk_forward_then_punch_does_not_fire(monkeypatch):
    # No down at all -> not a QCF -> must NOT fireball (guards the leniency).
    g = new_game()
    g.player1.x, g.player2.x = 250, 700
    frames = [{K.K_d}, {K.K_d}, {K.K_d}, {K.K_d, K.K_j}, set()]
    assert not _run_keys(g, frames, monkeypatch), "walking forward + LP must not fireball"


def _run_keys(g, frames, monkeypatch, total=28):
    current = {"keys": set()}
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _FakeKeys(current["keys"]))
    for i in range(total):
        current["keys"] = frames[i] if i < len(frames) else set()
        g.update()
        if g.player1.projectiles:
            return True
    return False
