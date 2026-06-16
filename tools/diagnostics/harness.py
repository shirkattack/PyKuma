"""Headless render + montage helpers for the diagnostics framework.

Two ways to turn a timeline of game state into something I can *see*:

- `render_recorded_clip`  -- STATE PLAYBACK: take the per-frame state an F11 clip
  already recorded (positions, facing, state, exact animation+frame) and re-draw
  each frame through the real render path (camera + sprites). No re-simulation, so
  it's a faithful picture of exactly what happened in that clip.

- `build_montage`         -- arrange sampled frames into one labeled contact-sheet
  PNG (frame #, both players' state + position) that can be opened/Read at a glance.

Run headless via the SDL dummy driver (set SDL_VIDEODRIVER=dummy). The scenario
runner (scenario.py) re-uses `build_montage` for scripted, re-simulated runs.
"""

from __future__ import annotations

import math
import os
from typing import List, Optional

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from street_fighter_3rd.data.enums import CharacterState, FacingDirection


def ensure_display():
    """Init pygame + a real-size surface (the game renders into self.screen)."""
    if not pygame.get_init():
        pygame.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    return pygame.display.get_surface()


def new_game(mode="TRAINING"):
    from street_fighter_3rd.core.game import Game
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    return Game(ensure_display(), GameModeManager(GameMode[mode]))


# ---- state playback (render a recorded clip faithfully) ---------------------

def _apply_record(player, rec: dict):
    """Set a character's visual state from one recorded player snapshot."""
    pos = rec.get("pos")
    if pos:
        player.x, player.y = float(pos[0]), float(pos[1])
    player.facing = (FacingDirection.RIGHT if rec.get("facing") == "R"
                     else FacingDirection.LEFT)
    st = rec.get("state")
    if st and hasattr(CharacterState, st):
        player.state = CharacterState[st]
    if "health" in rec:
        player.health = rec["health"]
    anim = rec.get("anim") or {}
    name = anim.get("animation")
    if name:
        ac = player.animation_controller
        ac.play_animation(name, force_restart=True)
        ca = ac.current_animation
        fi = anim.get("frame_index")
        if ca is not None and isinstance(fi, int) and ca.frames:
            ca.current_frame_index = max(0, min(fi, len(ca.frames) - 1))


def render_recorded_clip(frames: List[dict], every: int = 6) -> List[dict]:
    """Re-draw recorded frames through the real render path; return sampled tiles.

    Each tile = {"surface", "label"}. `every` keeps every Nth frame so the montage
    is readable.
    """
    game = new_game()
    tiles: List[dict] = []
    for i, fr in enumerate(frames):
        players = fr.get("players", [])
        if len(players) >= 1:
            _apply_record(game.player1, players[0])
        if len(players) >= 2:
            _apply_record(game.player2, players[1])
        game.render()
        if i % every == 0 or i == len(frames) - 1:
            p1, p2 = (players + [{}, {}])[:2]
            label = (f"f{fr.get('frame','?')} "
                     f"P1 {p1.get('state','?')} {p1.get('pos','')} "
                     f"P2 {p2.get('state','?')} {p2.get('pos','')}")
            tiles.append({"surface": game.screen.copy(), "label": label})
    return tiles


# ---- montage ----------------------------------------------------------------

def build_montage(tiles: List[dict], out_path: str, cols: int = 6,
                  tile_w: int = 260) -> str:
    """Arrange sampled frames into one labeled contact-sheet PNG."""
    if not tiles:
        raise ValueError("no tiles to montage")
    ensure_display()
    font = pygame.font.Font(None, 18)
    tile_h = int(tile_w * SCREEN_HEIGHT / SCREEN_WIDTH)
    label_h = 20
    cell_w, cell_h = tile_w, tile_h + label_h
    rows = math.ceil(len(tiles) / cols)
    sheet = pygame.Surface((cols * cell_w, rows * cell_h))
    sheet.fill((20, 20, 24))
    for idx, t in enumerate(tiles):
        r, c = divmod(idx, cols)
        x, y = c * cell_w, r * cell_h
        sheet.blit(pygame.transform.scale(t["surface"], (tile_w, tile_h)), (x, y + label_h))
        sheet.blit(font.render(t["label"], True, (230, 230, 120)), (x + 2, y + 2))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    pygame.image.save(sheet, out_path)
    return out_path
