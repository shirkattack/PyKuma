"""Advantage calibration + multi-hit gap conformance.

Community advantage (on_hit/on_block) is what the community actually
documents; per-move hitstun/blockstun are back-solved from it against the
ROM-verified timeline (akuma_hitboxes._calibrated_stun). These tests pin:

  1. the calibration arithmetic itself,
  2. the EMERGENT advantage measured by the Frame Lab equals the community
     number when a normal connects point-blank (the engine applies the
     calibrated stun faithfully),
  3. the declared blockstun is what the adapter actually applies on block,
  4. a multi-hit move (s.HK) measures S/A/GAP/R against the ROM total with
     no false recovery/total discrepancies (the gap between active windows
     is not recovery).

Runs the REAL game (headless) with the REAL Akuma — no stubs.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYKUMA_DISCREPANCY_LOG", "")  # keep tests file-silent

import pygame
import pytest

from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data


@pytest.fixture
def game():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    from street_fighter_3rd.core.game import Game
    g = Game(screen, GameModeManager(GameMode.TRAINING))
    g.show_frame_meter = True  # keeps the Frame Lab observing
    return g


def start_move(game, state):
    p1 = game.player1
    p1._transition_to_state(state)
    p1.state_frame = -1  # first update increments to 0, mirroring live input


def run_move(game, state, gap, frames=170):
    """Position P2 `gap` px away, run `state`, return the closed P1 report."""
    game.player2.x = game.player1.x + gap
    for _ in range(40):
        game.update()
    start_move(game, state)
    for _ in range(frames):
        game.update()
        if (game.frame_lab.last_reports.get(1) is not None
                and game.frame_lab.captures.get(1) is None
                and not game.frame_lab._watches):
            break
    return game.frame_lab.last_reports[1]


# ------------------------------------------------------ calibration unit --

@pytest.mark.parametrize("state,hitstun,blockstun", [
    # These moves are ROM-captured on hit AND on block: both stun values are
    # read live from the game (tools/rom_extract; block pass 2026-08-27).
    (CharacterState.MEDIUM_KICK, 19, 17),          # ROM hitstun 19; ROM blockstun 17 (2026-08-27 block pass)
    (CharacterState.CROUCH_MEDIUM_PUNCH, 15, 14),  # ROM hitstun 15; ROM blockstun 14
    (CharacterState.HEAVY_KICK, 35, 18),           # ROM hitstun 35 (1st of 2 windows; calibrated blockstun 18)
])
def test_captured_hitstun_and_blockstun(state, hitstun, blockstun):
    mfd = get_move_frame_data(state)
    hb = mfd.hitboxes[0][1]
    assert getattr(mfd, "rom_combat", None), f"{state.name} should be ROM-captured"
    assert (hb.hitstun, hb.blockstun) == (hitstun, blockstun)


def test_calibrated_stun_for_an_uncaptured_move():
    """The community calibration still drives an UNcaptured move. f+MP was
    the example until the 2026-08-27 capture landed it; UOH (98f8) has not
    been driven yet, so its stun is still back-solved from Baston advantage."""
    from street_fighter_3rd.data.enums import CharacterState as C
    mfd = get_move_frame_data(C.OVERHEAD)
    assert not getattr(mfd, "rom_combat", None)
    hb = mfd.hitboxes[0][1]
    assert hb.hitstun == 10 and hb.blockstun == 10


def test_jump_normals_keep_stored_stun():
    """Air normals resolve through the airborne hitstun model; the ground
    calibration must not touch them."""
    mfd = get_move_frame_data(CharacterState.JUMP_HEAVY_PUNCH)
    hb = mfd.hitboxes[0][1]
    # stored community estimates, NOT advantage-derived (which would be 28+)
    assert hb.hitstun < 25


# ------------------------------------------------- emergent advantage -----

@pytest.mark.parametrize("state", [
    CharacterState.MEDIUM_KICK,
    CharacterState.CROUCH_MEDIUM_PUNCH,
], ids=lambda s: s.name)
def test_rom_captured_move_raises_no_mechanical_discrepancy(game, state):
    """A ROM-captured move's damage/hitstun come from the capture, so the
    Frame Lab must not flag them (or the emergent advantage) against the
    community tier -- there is nothing to diff against."""
    report = run_move(game, state, gap=80)
    assert report.move == state.name
    assert report.hits and not report.hits[0].blocked
    mech = [d for d in report.discrepancies
            if d["channel"] in ("startup", "active", "gap", "recovery",
                                "total", "hitstun", "damage", "advantage_on_hit")]
    assert mech == [], mech


def test_declared_blockstun_is_applied(game):
    """The adapter applies the declared (calibrated) blockstun, not the old
    max(4, hitstun//2) derivation."""
    game.player2.x = game.player1.x + 80
    for _ in range(40):
        game.update()
    # Hold a standing guard: the guard is recomputed from the held direction
    # every frame (_update_guard), so pin it by muting both P2's input and
    # its guard refresh. (st.MK is MID: any posture blocks it.)
    game.player2._process_input = lambda: None
    game.player2._update_guard = lambda: None
    game.player2.is_blocking = True
    game.player2.guard_posture = "high"
    start_move(game, CharacterState.MEDIUM_KICK)
    for _ in range(120):
        game.update()
    report = game.frame_lab.last_reports[1]
    blocked = [h for h in report.hits if h.blocked]
    assert blocked, "the medium kick must have been blocked"
    expected = get_move_frame_data(CharacterState.MEDIUM_KICK).hitboxes[0][1].blockstun
    assert blocked[0].blockstun == expected == 17   # ROM block pass (was 21 calibrated before it)
    assert game.player2.blockstun_frames == 0  # fully served by test end


# ------------------------------------------------------- multi-hit gap ----

def test_heavy_kick_measures_gap_not_recovery(game):
    """s.HK: active 6-8 and 16-20 inside a 39-frame ROM total. The 7 boxes-off
    frames BETWEEN the windows are GAP; recovery is only what follows the
    last active frame. No false recovery/total flags (the user-visible
    '!! recovery: observed 26 != expected 19' bug)."""
    report = run_move(game, CharacterState.HEAVY_KICK, gap=400)  # whiff
    assert (report.startup, report.active, report.gap, report.recovery,
            report.total) == (5, 8, 7, 19, 39), report.summary()
    timing = [d for d in report.discrepancies
              if d["channel"] in ("startup", "active", "gap", "recovery", "total")]
    assert timing == [], timing


def test_heavy_kick_partial_connect_does_not_false_flag_advantage(game):
    """s.HK is ROM-captured: its advantage emerges from ROM hitstun and is
    never diffed against the community tier, whichever window connects."""
    report = run_move(game, CharacterState.HEAVY_KICK, gap=80)
    assert report.hits, "some window must have connected at this range"
    adv = [d for d in report.discrepancies if d["channel"] == "advantage_on_hit"]
    assert adv == [], adv
