"""Frame Lab tests.

The core promise under test: a move executed with ROM-correct timing produces
ZERO discrepancies, and a move executed with a seeded wrong value (damage,
timing) produces exactly the right dimensioned discrepancy — which then
round-trips through the BugTicket schema as valid YAML.

Characters are stubbed; the expected side is the REAL ROM-verified repository
(hitboxes.yaml via the akuma_hitboxes shim), so these tests also pin the
contract between the Frame Lab and the data layer.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.data.akuma_hitboxes import get_move_frame_data
from street_fighter_3rd.core.frame_lab import FrameLab, Phase, _expected_for
from street_fighter_3rd.schemas.bug_ticket import load_ticket


# ---------------------------------------------------------------- stubs ----

class StubCharacter:
    def __init__(self, player_number):
        self.player_number = player_number
        self.state = CharacterState.STANDING
        self.state_frame = 0
        self.hitstun_frames = 0
        self.blockstun_frames = 0
        self.hitfreeze_frames = 0

    def set(self, state, state_frame):
        self.state = state
        self.state_frame = state_frame


class StubAdapter:
    def __init__(self):
        self.hit_events = []

    def drain_hit_events(self):
        ev, self.hit_events = self.hit_events, []
        return ev


class StubGame:
    def __init__(self):
        self.frame_count = 0
        self.player1 = StubCharacter(1)
        self.player2 = StubCharacter(2)
        self.collision_system = StubAdapter()
        self.recorder = None

    def step(self, lab):
        self.frame_count += 1
        lab.observe(self)


def pick_normal_with_data():
    """Find a grounded normal that has ROM move data + a combat-tier hitbox,
    so the tests don't hardcode one state name."""
    for state in (CharacterState.MEDIUM_PUNCH, CharacterState.HEAVY_PUNCH,
                  CharacterState.LIGHT_PUNCH, CharacterState.MEDIUM_KICK,
                  CharacterState.HEAVY_KICK, CharacterState.LIGHT_KICK):
        mfd = get_move_frame_data(state)
        if mfd and mfd.active and mfd.hitboxes:
            return state, mfd
    pytest.skip("no ROM move data available for any grounded normal")


def run_move(game, lab, char, state, total_frames, whiff=True):
    """Drive a stub character through a move: state_frame 0..total-1, then
    back to STANDING (which closes the capture)."""
    for sf in range(total_frames):
        char.set(state, sf)
        game.step(lab)
    char.set(CharacterState.STANDING, 0)
    game.step(lab)


# ---------------------------------------------------------------- tests ----

def test_correct_move_produces_no_discrepancies():
    state, mfd = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()

    run_move(game, lab, game.player1, state, exp.total)

    report = lab.last_reports[1]
    assert report is not None and report.move == state.name
    assert (report.startup, report.active, report.recovery) == \
           (exp.startup, exp.active, exp.recovery)
    assert report.discrepancies == [], report.discrepancies


def test_phase_classification_matches_rom_windows():
    """Every sampled frame's phase must match the declared timeline exactly —
    this is the 'measured active window == adapter active window' guarantee."""
    state, mfd = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    run_move(game, lab, game.player1, state, exp.total)

    phases = [s.phase for s in lab.samples[1] if s.expected_phase is not None
              or s.phase in (Phase.STARTUP, Phase.ACTIVE, Phase.RECOVERY)]
    move_phases = phases[-exp.total:]
    assert move_phases == ([Phase.STARTUP] * exp.startup
                           + [Phase.ACTIVE] * exp.active
                           + [Phase.RECOVERY] * exp.recovery)


def test_hitstop_frames_excluded_from_measurement():
    """Frozen frames must not inflate measured timing (state_frame does not
    advance during hitstop in the real engine; we mirror that here)."""
    state, mfd = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    char = game.player1

    freeze_at = exp.startup + 1  # freeze mid-active
    sf = 0
    while sf < exp.total:
        char.set(state, sf)
        if sf == freeze_at:
            char.hitfreeze_frames = 5
            for _ in range(5):           # frozen: same state_frame repeats
                game.step(lab)
                char.hitfreeze_frames -= 1
        game.step(lab)
        sf += 1
    char.set(CharacterState.STANDING, 0)
    game.step(lab)

    report = lab.last_reports[1]
    assert report.frozen_frames == 5
    assert (report.startup, report.active, report.recovery) == \
           (exp.startup, exp.active, exp.recovery)
    assert not any(d["channel"] in ("startup", "active", "recovery", "total")
                   for d in report.discrepancies)


def test_seeded_wrong_damage_yields_damage_discrepancy_and_valid_ticket(tmp_path):
    """The user's canonical complaint: 'the HP does too much damage'. Seed a
    hit event whose raw damage disagrees with the community value and demand
    a dimensioned discrepancy + a schema-valid ticket."""
    state, mfd = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    char = game.player1

    wrong_damage = exp.damage + 20
    for sf in range(exp.total):
        char.set(state, sf)
        if sf == exp.startup:  # first active frame: the hit lands
            game.collision_system.hit_events.append({
                "attacker": 1, "defender": 2,
                "raw_damage": wrong_damage, "scaled_damage": wrong_damage,
                "hitstun": exp.hitstun, "hitstop": 8, "blocked": False,
            })
        game.step(lab)
    char.set(CharacterState.STANDING, 0)
    game.step(lab)

    report = lab.last_reports[1]
    dmg = [d for d in report.discrepancies if d["channel"] == "damage"]
    assert len(dmg) == 1
    assert dmg[0]["observed"] == wrong_damage and dmg[0]["expected"] == exp.damage

    paths = lab.dump_tickets(out_dir=str(tmp_path))
    assert paths, "F9 must emit at least one ticket"
    tickets = [load_ticket(p) for p in paths]  # validates via Pydantic
    dmg_tickets = [t for t in tickets if t.channel == "damage"]
    assert len(dmg_tickets) == 1
    t = dmg_tickets[0]
    assert t.observed == wrong_damage
    assert t.expected.value == exp.damage
    assert t.expected.provenance == "community"
    assert t.delta == 20.0
    assert any("sf3_authentic_frame_data.yaml" in h for h in t.fix_hints)
    assert t.measured_summary["measured"]["startup"] == exp.startup
    assert t.repro["phase_timeline"], "ticket must carry the phase timeline"


def test_cancel_truncation_does_not_false_flag_recovery():
    """Cancelling s.MP into a special truncates recovery legitimately; the
    diff must not report recovery/total discrepancies for the cancelled move."""
    state, mfd = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    char = game.player1

    for sf in range(exp.startup + exp.active):  # cancel right after active
        char.set(state, sf)
        game.step(lab)
    for sf in range(6):  # into a special
        char.set(CharacterState.GOHADOKEN, sf)
        game.step(lab)
    char.set(CharacterState.STANDING, 0)
    game.step(lab)

    # The cancelled normal is no longer last_report (the special is), but its
    # close path ran; verify via the special's predecessor semantics instead:
    # re-run capturing the cancelled report directly.
    game2, lab2 = StubGame(), FrameLab()
    c2 = game2.player1
    for sf in range(exp.startup + exp.active):
        c2.set(state, sf)
        game2.step(lab2)
    c2.set(CharacterState.GOHADOKEN, 0)
    game2.step(lab2)
    cancelled = lab2.last_reports[1]
    assert cancelled.move == state.name and cancelled.cancelled
    assert not any(d["channel"] in ("recovery", "total")
                   for d in cancelled.discrepancies)


def test_blocked_hit_records_blockstun_channel():
    """Blockstun is engine-derived (max(4, hitstun//2)) and ignores declared
    data — when they differ, the diff must say so on the blockstun channel."""
    state, mfd = pick_normal_with_data()
    exp = _expected_for(state)
    if not exp.blockstun:
        pytest.skip("move has no declared blockstun to compare")
    engine_blockstun = max(4, exp.hitstun // 2)
    if engine_blockstun == exp.blockstun:
        pytest.skip("engine formula coincides with declared value here")

    game, lab = StubGame(), FrameLab()
    char = game.player1
    for sf in range(exp.total):
        char.set(state, sf)
        if sf == exp.startup:
            game.collision_system.hit_events.append({
                "attacker": 1, "defender": 2, "raw_damage": exp.damage,
                "scaled_damage": 0, "hitstun": exp.hitstun, "hitstop": 6,
                "blocked": True, "blockstun": engine_blockstun,
                "chip_damage": max(1, exp.damage // 8),
            })
        game.step(lab)
    char.set(CharacterState.STANDING, 0)
    game.step(lab)

    bs = [d for d in lab.last_reports[1].discrepancies
          if d["channel"] == "blockstun"]
    assert len(bs) == 1
    assert bs[0]["observed"] == engine_blockstun
    assert bs[0]["expected"] == exp.blockstun
