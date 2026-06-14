"""
Provenance gate — enforces the prime directive: we do NOT make up data.

Every move in the canonical frames.yaml must declare provenance. Moves that are still
`unverified` (hand-authored placeholders pending real data) are allowed ONLY while listed
in UNVERIFIED_BACKLOG below. Adding a new unverified move without listing it here fails
this test — so fabricated data can never enter silently. As moves are verified against the
real data source, delete them from the backlog; the list only shrinks.
"""

import pytest

from street_fighter_3rd.data.frame_data_loader import get_character_frames

# Move keys still on hand-authored placeholders, pending verification against real data.
# THIS LIST MUST ONLY SHRINK. Do not add to it.
UNVERIFIED_BACKLOG = {
    "light_punch", "medium_punch", "heavy_punch",
    "light_kick", "medium_kick", "heavy_kick",
    "crouch_heavy_kick",
}


def _akuma():
    return get_character_frames("akuma").moves


def test_every_move_declares_provenance():
    """The schema makes provenance required; assert it loaded for every move."""
    for key, move in _akuma().items():
        assert move.provenance.status in {"verified", "unverified", "derived"}, key


def test_no_unlisted_unverified_moves():
    """No move may be unverified unless explicitly tracked in the backlog."""
    moves = _akuma()
    unverified = {k for k, m in moves.items() if m.provenance.status == "unverified"}
    rogue = unverified - UNVERIFIED_BACKLOG
    assert not rogue, (
        f"Made-up/unverified moves not tracked in UNVERIFIED_BACKLOG: {sorted(rogue)}. "
        "Either verify them against the real data source or add them to the backlog (which must only shrink)."
    )


def test_backlog_stays_honest():
    """Backlog entries must exist and must actually still be unverified (keeps it shrinking)."""
    moves = _akuma()
    for key in UNVERIFIED_BACKLOG:
        assert key in moves, f"UNVERIFIED_BACKLOG names '{key}' which no longer exists — remove it"
        assert moves[key].provenance.status == "unverified", (
            f"'{key}' is now {moves[key].provenance.status}; remove it from UNVERIFIED_BACKLOG"
        )


def test_verified_moves_cite_a_source():
    """Anything marked verified must carry a source URL (schema-enforced; double-checked)."""
    for key, move in _akuma().items():
        if move.provenance.status == "verified":
            assert move.provenance.source, f"verified move '{key}' has no source URL"


def test_report_tally(capsys):
    """Print the VERIFIED/UNVERIFIED tally so progress is legible in CI output."""
    moves = _akuma()
    verified = sorted(k for k, m in moves.items() if m.provenance.status == "verified")
    unverified = sorted(k for k, m in moves.items() if m.provenance.status == "unverified")
    with capsys.disabled():
        print(f"\nAkuma provenance: {len(verified)}/{len(moves)} VERIFIED")
        if unverified:
            print(f"  UNVERIFIED ({len(unverified)}): {unverified}")
