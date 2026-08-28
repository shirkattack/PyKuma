"""tools/rom_extract/cel_decode.py — CPS3 sprite object reconstruction (no emulator).

A synthetic dump exercises the tile byte order, the 5-5-5 palette, the part
placement math ported from MAME's cps3 sprite loop, flips, and the xx-major
tile order of multi-tile parts.
"""

import importlib.util
import json
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "cel_decode", Path(__file__).resolve().parents[1] / "tools" / "rom_extract" / "cel_decode.py")
cel = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cel)


def _tile(pen_at):
    """256-byte tile as hex; pen_at(x, y) gives the pen index, stored in MAME's
    layout (pixel x lives in byte x ^ 3 of its 16-byte row)."""
    raw = bytearray(256)
    for y in range(16):
        for x in range(16):
            raw[y * 16 + (x ^ 3)] = pen_at(x, y)
    return raw.hex()


def _palette(colors):
    words = [0] * 256
    for pen, (r, g, b) in colors.items():
        words[pen] = (r // 8) | ((g // 8) << 5) | ((b // 8) << 10)
    return "".join(f"{w:04x}" for w in words)


def _rec(parts, **flags):
    base = {"i": 0, "length": len(parts), "start": 0, "xpos": 100, "ypos": 200, "gscroll": 0,
            "whichbpp": 0, "whichpal": 0, "gxflip": 0, "gyflip": 0, "galpha": 0, "gbpp": 0, "global_pal": 0}
    base.update(flags)
    base["parts"] = parts
    return base


def _part(tileno, xpos2, ypos2, xsize=1, ysize=1, **kw):
    p = {"tileno": tileno, "flipx": 0, "flipy": 0, "alpha": 0, "bpp": 0, "pal": 5,
         "xpos2": xpos2, "ypos2": ypos2, "xsize": xsize, "ysize": ysize,
         "xsizedraw": 16 * cel.TILES_TABLE[xsize], "ysizedraw": 16 * cel.TILES_TABLE[ysize]}
    p.update(kw)
    return p


def test_decode_tile_reads_mame_byte_order_and_palette_is_555():
    rows = cel.decode_tile(_tile(lambda x, y: x + 16 * y if (x, y) != (0, 0) else 0))
    assert rows[0][1] == 1 and rows[1][0] == 16 and rows[15][15] == 255
    pal = cel.decode_palette(_palette({1: (248, 0, 0), 2: (0, 0, 248)}))
    assert pal[0] == (0, 0, 0, 0)            # pen 0 transparent
    assert pal[1] == (255, 0, 0, 255) and pal[2] == (0, 0, 255, 255)


def test_single_tile_part_lands_at_its_offset_with_y_up():
    # one 16x16 part at xpos2 = 0, ypos2 = 16. The PPU treats the part position
    # as its centre (adds half the draw size, subtracts the tile span) and y
    # grows UP, so the tile spans x -8..7 (+1 quirk -> -7..8) and y -24..-9.
    rec = _rec([_part(7, xpos2=0, ypos2=16)])
    tiles = {"7": _tile(lambda x, y: 1)}
    pals = {str(5 * 256): _palette({1: (0, 248, 0)})}
    placed = cel.part_tiles(rec, rec["parts"][0])
    assert placed == [(7, -7, -24, False, False)]
    img, (left, top) = cel.render_object(rec, tiles, pals)
    assert (left, top) == (-7, -24) and img.size == (16, 16)
    assert img.getpixel((0, 0)) == (0, 255, 0, 255)


def test_multi_tile_part_orders_tiles_xx_major_and_flips():
    # 2x2 tiles: MAME draws tileno + count with count incrementing over yy inside xx
    rec = _rec([_part(100, xpos2=0, ypos2=32, xsize=2, ysize=2)])
    placed = cel.part_tiles(rec, rec["parts"][0])
    # 32x32 part centred on (0, 32): x -16..15 (+1), y -48..-17; tiles xx-major
    assert [(t, x, y) for t, x, y, _, _ in placed] == [(100, -15, -48), (101, -15, -32), (102, 1, -48), (103, 1, -32)]
    # flipx via the main record's global flag mirrors the whole part
    recf = _rec([_part(100, xpos2=0, ypos2=32, xsize=2, ysize=2)], gxflip=1)
    pf = cel.part_tiles(recf, recf["parts"][0])
    assert all(fx for _, _, _, fx, _ in pf)
    xs = sorted({x for _, x, _, _, _ in pf})
    assert xs[1] - xs[0] == 16
    # a flipped tile renders mirrored: pen only at pixel x=0 -> appears at x=15
    tile = _tile(lambda x, y: 1 if x == 0 else 0)
    rec1 = _rec([_part(9, xpos2=0, ypos2=16, flipx=1)])
    img, _ = cel.render_object(rec1, {"9": tile}, {str(5 * 256): _palette({1: (248, 248, 248)})})
    assert img.getpixel((15, 0))[3] == 255 and img.getpixel((0, 0))[3] == 0


def test_cli_renders_pngs_and_lists_objects(tmp_path, capsys):
    rec = _rec([_part(7, xpos2=0, ypos2=16)])
    d = {"f": 1, "p1": {"anim": "8800", "cel": 21505, "pos_x": 400, "pos_y": 0, "flip": 1, "posture": 0},
         "p2": {"anim": "8800", "cel": 21505, "pos_x": 600, "pos_y": 0, "flip": -1, "posture": 0},
         "records": [rec], "tiles": {"7": _tile(lambda x, y: 1)}, "palettes": {str(5 * 256): _palette({1: (248, 0, 0)})}}
    dump = tmp_path / "cels.jsonl"
    dump.write_text(json.dumps(d) + "\n")
    cel.main([str(dump), "--out", str(tmp_path / "out")])
    assert (tmp_path / "out" / "d0_obj000.png").exists() and (tmp_path / "out" / "d0_obj000_axis.png").exists()
    assert "16x16" in capsys.readouterr().out


def test_state_area_lookup_matches_fbneo_hash_layout(tmp_path):
    # FBNeo statec.cpp: HashString("Sprite ROM") with a tiny fake 'char RAM'
    cel2 = cel
    cram = bytes(range(256)) * 4                       # 4 tiles
    entry = (7).to_bytes(4, "little") + len(cram).to_bytes(4, "little") + cel2.fbneo_hash("Sprite ROM").to_bytes(4, "little") + cram
    other = (7).to_bytes(4, "little") + (8).to_bytes(4, "little") + cel2.fbneo_hash("Palette").to_bytes(4, "little") + b"\x01" * 8
    blob = b"FB1 " + b"FS1 " + b"\x00" * 0x40 + other + entry
    assert cel2.state_area(blob, "Sprite ROM", len(cram)) == cram
    st = cel2.StateTiles(cram)
    assert st.get("1") == (bytes(range(256))).hex() and st.get("9") is None
    with pytest.raises(ValueError):
        cel2.state_area(blob, "Sprite ROM", 512)


def test_cram_is_located_in_a_legacy_compressed_state_by_a_bank0_anchor(tmp_path):
    import zlib
    tile_cpu = bytes(range(256))                                   # what the Lua read (CPU order)
    tile_host = bytes(x for i in range(0, 256, 4) for x in tile_cpu[i:i + 4][::-1])
    cram = bytearray(cel.CRAM_SIZE)
    cram[128 * 256:129 * 256] = tile_host                            # tile 128 in bank 0
    cram[9712 * 256:9713 * 256] = bytes([7]) * 256                   # a bank-2 tile
    block = b"\x00" * 4 + zlib.compress(b"\x11" * 1000 + bytes(cram))
    state = b"FB1 " + b"FS1 " + b"\x00" * 0x40 + block
    f = tmp_path / "s.fs"; f.write_bytes(state)
    got = cel.cram_tiles_from_state(f, {"128": tile_cpu.hex()})
    assert len(got) == cel.CRAM_SIZE and got[9712 * 256] == 7
    with pytest.raises(ValueError):
        cel.cram_tiles_from_state(f, {})


def test_state_palette_words_are_swapped_back_to_cpu_order():
    # host storage is RamPal[index ^ 1]; the CPU-side (rendering) order swaps pairs back
    pal = (0x7fff).to_bytes(2, "little") + (0x001f).to_bytes(2, "little") + b"\x00" * (0x40000 - 4)
    sp = cel.StatePalettes(pal)
    assert sp.get("0")[:8] == "001f7fff"


def test_cram_is_located_by_a_palette_anchor_when_no_bank0_tile_was_read(tmp_path):
    import zlib
    words_cpu = list(range(0x100, 0x200))                          # a distinctive palette (CPU order)
    host = b"".join(words_cpu[i + 1].to_bytes(2, "little") + words_cpu[i].to_bytes(2, "little") for i in range(0, 256, 2))
    pal = bytearray(cel.PAL_SIZE); pal[512 * 2:512 * 2 + 512] = host      # palette base 512
    cram = bytearray(cel.CRAM_SIZE); cram[9712 * 256] = 7
    state = b"FB1 " + b"FS1 " + b"\x00" * 0x40 + b"\x00" * 4 + zlib.compress(b"\x22" * 777 + bytes(pal) + bytes(cram))
    f = tmp_path / "s.fs"; f.write_bytes(state)
    areas = cel.state_areas(f, {}, {"512": "".join(f"{w:04x}" for w in words_cpu)})
    assert areas["cram"][9712 * 256] == 7
    assert cel.StatePalettes(areas["pal"]).get("512")[:8] == "01000101"


def test_p1_cels_ripped_facing_left_are_stored_right_facing(tmp_path):
    # the object drawn mirrored (P1 facing byte 0): the stored cel is mirrored
    # back and its bbox reflected about the axis
    tile = _tile(lambda x, y: 1 if x < 4 else 0)            # pens on the left 4 columns of every tile
    part = _part(7, xpos2=0, ypos2=32, xsize=3, ysize=3)    # 4x4 tiles: a "body" (>= 10 tiles)
    rec = _rec([part], xpos=424)
    base = {"f": 1, "p2": {"anim": "8800", "cel": 1, "pos_x": 600, "pos_y": 0, "flip": -1, "posture": 0},
            "records": [rec], "tiles": {str(7 + i): tile for i in range(16)},
            "palettes": {str(5 * 256): _palette({1: (248, 0, 0)})}}
    right = dict(base, p1={"anim": "8800", "cel": 11, "pos_x": 424, "pos_y": 0, "flip": 1, "posture": 0})
    left = dict(base, p1={"anim": "8800", "cel": 12, "pos_x": 424, "pos_y": 0, "flip": 0, "posture": 0})
    dump = tmp_path / "cels.jsonl"
    dump.write_text(json.dumps(right) + "\n" + json.dumps(left) + "\n")
    cel.main([str(dump), "--out", str(tmp_path / "out"), "--p1", "--lua-tiles"])
    m = json.loads((tmp_path / "out" / "cels.json").read_text())
    r, l = m["11"], m["12"]
    assert not r["mirrored_from_left"] and l["mirrored_from_left"]
    assert l["left"] == -(r["left"] + r["width"])                 # bbox reflected about the axis
    from PIL import Image
    ir = Image.open(tmp_path / "out" / "cel_11.png"); il = Image.open(tmp_path / "out" / "cel_12.png")
    w = ir.size[0]
    assert ir.getpixel((0, 0))[3] == 255 and ir.getpixel((w - 1, 0))[3] == 0       # right-facing: pens on the left
    assert il.getpixel((w - 1, 0))[3] == 255 and il.getpixel((0, 0))[3] == 0       # mirrored back: pens on the right
