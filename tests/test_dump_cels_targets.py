"""The rip session's shopping list: `build_rom_animations.py --targets-lua`
emits what the repo still needs, and `dump_cels.lua` counts it down live so a
Fightcade pass ends when the list is empty instead of when it feels done.

The Lua half runs here under a stubbed FBNeo (memory/gui/input/emu), so the
checklist is verified without an emulator. Skipped where lupa is unavailable;
the generator half is tested in test_build_rom_animations.py either way.
"""

import shutil
from pathlib import Path

import pytest

lupa = pytest.importorskip("lupa")

ROM_EXTRACT = Path(__file__).resolve().parents[1] / "tools" / "rom_extract"
P1_BASE = 0x02068C6C
ANIM_OFF, CEL_OFF = 0x202, 0x21A

STUBS = r"""
_G.MEM = {}
local function rd(a) return MEM[a] or 0 end
memory = { readdword = rd, readword = rd, readbyte = rd,
           readwordsigned = rd, readbytesigned = rd,
           writebyte = function() end, writeword = function() end }
gui = { text = function(x, y, s) LINES[#LINES + 1] = s end }
input = { get = function() return {} end }
joypad = { set = function() end }
savestate = nil
emu = { registerbefore = function(f) BEFORE = f end,
        registerafter = function(f) AFTER = f end }
LINES = {}
io.open = function() return nil end     -- the ripper must not write during the test
"""

TARGETS = """return {
  cels = { [22441] = "HEAVY_KICK (1b08)", [21890] = "LIGHT_PUNCH:close (13a8)" },
  anims = { [10912] = "DIVE_KICK (2aa0) -- never performed" },
}
"""


def _load(tmp_path, lua):
    src = (tmp_path / "dump_cels.lua").read_text().replace(
        "local SAVE_STATE   = true", "local SAVE_STATE   = false")
    lua.execute(STUBS)
    lua.execute(src)
    g = lua.globals()

    def frame(anim=0x8800, cel=1):
        g.MEM[P1_BASE + ANIM_OFF] = anim
        g.MEM[P1_BASE + CEL_OFF] = cel
        g.LINES = lua.table()
        g.AFTER()
        return [g.LINES[i] for i in range(1, len(g.LINES) + 1)]

    return frame


@pytest.fixture
def ripper(tmp_path, monkeypatch):
    """dump_cels.lua loaded next to a targets file, driven frame by frame."""
    shutil.copy(ROM_EXTRACT / "dump_cels.lua", tmp_path / "dump_cels.lua")
    (tmp_path / "pykuma_targets.lua").write_text(TARGETS)
    monkeypatch.chdir(tmp_path)
    return _load(tmp_path, lupa.LuaRuntime(unpack_returned_tuples=True))


def _line(lines, prefix):
    return next((l for l in lines if l.startswith(prefix)), None)


def test_the_ripper_counts_the_remaining_targets_down(ripper):
    assert "TARGETS 3 left" in _line(ripper(), "TARGETS")
    # a missing cel shows up -> ticked off, with its move named
    got = _line(ripper(anim=0x1b08, cel=22441), "GOT")
    assert got == "GOT HEAVY_KICK (1b08) (cel 22441) -- 2 left"
    # a move that was never performed in any capture -> ticked off by its anim id
    assert "DIVE_KICK" in _line(ripper(anim=0x2aa0, cel=777), "GOT")
    assert "TARGETS 1 left" in _line(ripper(), "TARGETS")


def test_a_target_seen_twice_is_only_counted_once(ripper):
    ripper(anim=0x1b08, cel=22441)
    first = _line(ripper(), "TARGETS")
    ripper(anim=0x1b08, cel=22441)
    assert _line(ripper(), "TARGETS") == first


def test_the_list_reports_done_when_everything_is_ripped(ripper):
    for anim, cel in ((0x1b08, 22441), (0x13a8, 21890), (0x2aa0, 1)):
        ripper(anim=anim, cel=cel)
    assert _line(ripper(), "TARGETS") == "TARGETS: all done"


def test_without_a_targets_file_the_ripper_is_unchanged(tmp_path, monkeypatch):
    shutil.copy(ROM_EXTRACT / "dump_cels.lua", tmp_path / "dump_cels.lua")
    monkeypatch.chdir(tmp_path)                      # no pykuma_targets.lua here
    frame = _load(tmp_path, lupa.LuaRuntime(unpack_returned_tuples=True))
    lines = frame()
    assert lines and lines[0].startswith("CEL RIP")
    assert not _line(lines, "TARGETS")
