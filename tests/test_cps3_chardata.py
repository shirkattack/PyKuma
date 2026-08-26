"""The RAM-dumped geometry lines up with the ROM's own tables.

data/sources/cps3_akuma_chardata.json holds Akuma's attack-box (`atta`) and
attack-data (`atit`) tables read straight out of the decrypted arcade ROM
(tools/rom_extract/cps3_chardata.py). Every attack box 3rd_training_lua
dumped from RAM (data/sources/gouki_framedata.json) must exist in `atta`
verbatim -- the geometry tier is verified against the ROM itself.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CHARDATA = REPO / "data/sources/cps3_akuma_chardata.json"


@pytest.fixture(scope="module")
def chardata():
    return json.loads(CHARDATA.read_text())


def test_every_dumped_attack_box_is_in_the_rom_table(chardata):
    rom = {(b["left"], b["width"], b["bottom"], b["height"]) for row in chardata["atta"] for b in row}
    src = json.loads((REPO / "data/sources/gouki_framedata.json").read_text())
    dumped = {(b["left"], b["width"], b["bottom"], b["height"])
              for m in src.values() if isinstance(m, dict) and "frames" in m
              for f in m["frames"] for b in (f.get("boxes") or []) if b.get("type") == "attack"}
    assert dumped, "no attack boxes in the dump"
    assert dumped <= rom, f"boxes in RAM dump but not in ROM: {sorted(dumped - rom)[:5]}"
    assert len(rom) == 120 and len(dumped) == 106


def test_attack_data_table_shape(chardata):
    atit = chardata["atit"]
    assert len(atit) == 96
    assert atit[0]["pow"] == 0                                  # entry 0 = no attack
    live = [e for e in atit if e["pow"]]
    assert all(e["damage_raw"] % 5 == 0 or e["damage_raw"] == 999 for e in live)
    # hitstop: the common shape is attacker +n / defender -n (a few cels --
    # projectiles/throws -- use 0 or the same sign)
    paired = [e for e in live if e["hs_me"] > 0 and e["hs_you"] < 0]
    assert len(paired) > len(live) * 0.6, f"{len(paired)}/{len(live)} entries have the +/- hitstop pair"
    assert {e["level"] & 0x3F for e in live} >= {0, 1, 2}
    assert chardata["_meta"]["status"] == "verified"


def test_extractor_cipher_is_deterministic():
    import sys
    sys.path.insert(0, str(REPO / "tools/rom_extract"))
    import cps3_chardata as c
    assert c.cps3_mask(c.BASE_OFFSET) == c.cps3_mask(c.BASE_OFFSET)
    assert c.cps3_mask(c.BASE_OFFSET) != c.cps3_mask(c.BASE_OFFSET + 4)
    m = c.cps3_mask(c.BASE_OFFSET)
    assert (m >> 16) == (m & 0xFFFF)                            # mask is a 16-bit value doubled
