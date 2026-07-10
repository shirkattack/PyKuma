"""Frame Lab phase-2 tests — the sprite track.

Same contract as the mechanical tests: a move whose animation behaves
correctly produces zero sprite discrepancies; each seeded sprite failure mode
(wrong animation, missing art, animation ending early / cut off) produces
exactly the right dimensioned discrepancy; and the static audit provably
detects the real drift that exists in the repo's data today.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pytest

from street_fighter_3rd.data.enums import CharacterState
from street_fighter_3rd.core.frame_lab import FrameLab, _expected_for
from street_fighter_3rd.schemas.bug_ticket import load_ticket

from tests.test_frame_lab import StubGame, pick_normal_with_data


# ---------------------------------------------------------------- stubs ----

class StubAnimController:
    """Scriptable stand-in for AnimationController: plays `anim_name` for
    `length` game frames (1 cel per frame), then reports complete and holds."""

    def __init__(self, anim_name, length):
        self.anim_name, self.length, self.t = anim_name, length, 0

    def step(self):
        self.t += 1

    def get_current_frame_info(self):
        idx = min(self.t, self.length - 1)
        return {"animation": self.anim_name, "frame_index": idx,
                "total_frames": self.length, "complete": self.t >= self.length,
                "sprite_number": 18000 + idx}


def sprite_char(game, anim_name, anim_length, state):
    """Give the stub P1 a sprite track + the state->anim mapping."""
    char = game.player1
    char.animation_controller = StubAnimController(anim_name, anim_length)
    char._rendered_fallback = False
    char._STATE_ANIM = {state: anim_name if anim_name else "expected_anim"}
    return char


def drive(game, lab, char, state, total, fallback_frames=()):
    for sf in range(total):
        char.set(state, sf)
        char._rendered_fallback = sf in fallback_frames
        game.step(lab)
        char.animation_controller.step()
    char.set(CharacterState.STANDING, 0)
    char._rendered_fallback = False
    game.step(lab)
    return lab.last_reports[1]


# ---------------------------------------------------------------- tests ----

def test_correct_animation_produces_no_sprite_discrepancies():
    state, _ = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    char = sprite_char(game, "right_anim", exp.total, state)
    char._STATE_ANIM = {state: "right_anim"}

    report = drive(game, lab, char, state, exp.total)
    sprite_channels = {"sprite_mapping", "sprite_timing", "sprite_sync",
                       "sprite_fallback"}
    assert not [d for d in report.discrepancies
                if d["channel"] in sprite_channels], report.discrepancies
    assert report.anims_seen == ["right_anim"]
    assert report.cel_timeline, "cel timeline must be recorded"


def test_wrong_animation_yields_sprite_mapping():
    state, _ = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    char = sprite_char(game, "walk_forward", exp.total, state)  # wrong anim
    char._STATE_ANIM = {state: "medium_punch_anim"}

    report = drive(game, lab, char, state, exp.total)
    m = [d for d in report.discrepancies if d["channel"] == "sprite_mapping"]
    assert len(m) == 1
    assert m[0]["observed"] == "walk_forward"
    assert m[0]["expected"] == "medium_punch_anim"


def test_fallback_frames_yield_sprite_fallback():
    state, _ = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    char = sprite_char(game, "right_anim", exp.total, state)
    char._STATE_ANIM = {state: "right_anim"}

    report = drive(game, lab, char, state, exp.total, fallback_frames={2, 3, 4})
    fb = [d for d in report.discrepancies if d["channel"] == "sprite_fallback"]
    assert len(fb) == 1 and fb[0]["observed"] == 3 and fb[0]["expected"] == 0


def test_short_animation_yields_sprite_timing():
    """The real repo bug class: an 18-frame animation inside a 22-frame move
    finishes early and holds its last cel."""
    state, _ = pick_normal_with_data()
    exp = _expected_for(state)
    short = exp.total - 4
    game, lab = StubGame(), FrameLab()
    char = sprite_char(game, "right_anim", short, state)
    char._STATE_ANIM = {state: "right_anim"}

    report = drive(game, lab, char, state, exp.total)
    t = [d for d in report.discrepancies if d["channel"] == "sprite_timing"]
    assert len(t) == 1
    assert t[0]["observed"] == short and t[0]["expected"] == exp.total


def test_animation_ending_before_active_also_flags_sprite_sync():
    """If the animation is over before the active window even begins, the
    visible motion cannot possibly match the hit — auto-flagged."""
    state, _ = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    char = sprite_char(game, "right_anim", max(1, exp.startup - 1), state)
    char._STATE_ANIM = {state: "right_anim"}

    report = drive(game, lab, char, state, exp.total)
    assert [d for d in report.discrepancies if d["channel"] == "sprite_sync"]


def test_cut_off_animation_yields_sprite_timing():
    """The inverse drift: a too-long animation whose trailing cels are never
    shown because the move ends first (e.g. HK: 42-frame anim, 32-frame move)."""
    state, _ = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    long_len = exp.total + 6
    char = sprite_char(game, "right_anim", long_len, state)
    char._STATE_ANIM = {state: "right_anim"}

    report = drive(game, lab, char, state, exp.total)
    t = [d for d in report.discrepancies if d["channel"] == "sprite_timing"]
    assert len(t) == 1
    assert "cels" in str(t[0]["observed"])


def test_sprite_ticket_round_trips_with_cel_timeline(tmp_path):
    state, _ = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    char = sprite_char(game, "right_anim", exp.total - 4, state)
    char._STATE_ANIM = {state: "right_anim"}
    drive(game, lab, char, state, exp.total)

    paths = lab.dump_tickets(out_dir=str(tmp_path))
    tickets = [load_ticket(p) for p in paths]
    st = [t for t in tickets if t.channel == "sprite_timing"]
    assert st, [t.channel for t in tickets]
    t = st[0]
    assert t.repro.get("cel_timeline"), "sprite tickets must carry the alignment table"
    assert any("animations.yaml" in h for h in t.fix_hints)
    assert t.measured_summary["sprite"]["anims_seen"] == ["right_anim"]


def test_mechanical_stubs_without_sprites_are_unaffected():
    """v1 stub characters (no animation controller) must keep producing clean
    mechanical reports with no sprite channels."""
    state, _ = pick_normal_with_data()
    exp = _expected_for(state)
    game, lab = StubGame(), FrameLab()
    from tests.test_frame_lab import run_move
    run_move(game, lab, game.player1, state, exp.total)
    report = lab.last_reports[1]
    assert report.anims_seen == []
    assert not [d for d in report.discrepancies
                if d["channel"].startswith("sprite")]


# ------------------------------------------------------------ static audit --

def test_audit_detects_real_medium_punch_drift():
    """Pin the audit against the repo's actual data: the medium_punch
    animation is 18 game frames vs the ROM move's 22, and its embedded
    frame_data block has drifted from the ROM repository."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "audit_animations",
        os.path.join(os.path.dirname(__file__), "..", "tools", "framelab",
                     "audit_animations.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    findings = mod.audit()
    assert findings, "audit must detect the known drift in the current data"

    mp = [f for f in findings if f["move"] == "MEDIUM_PUNCH"]
    timing = [f for f in mp if f["channel"] == "sprite_timing"]
    assert timing and timing[0]["observed"] == 18 and timing[0]["expected"] == 22

    # The legacy embedded frame_data/hitbox blocks were removed from
    # animations.yaml (data-harmony pass); this guards against reintroduction.
    assert not [f for f in findings if f["channel"] == "data_drift"], \
        "embedded frame_data/hitbox blocks have crept back into animations.yaml"

    # And the findings must convert into schema-valid tickets.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        paths = mod.write_tickets(findings[:3], out_dir=td)
        assert len(paths) == 3
        for p in paths:
            load_ticket(p)
