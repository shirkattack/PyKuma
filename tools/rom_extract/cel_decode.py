#!/usr/bin/env python3
"""Rebuild CPS3 sprite objects from a `dump_cels.lua` dump (no emulator).

    uv run python tools/rom_extract/cel_decode.py pykuma_cels.jsonl --out /tmp/cels

For every dump line and every sprite-list object in it, composes the object's
parts (16x16 8bpp tiles) exactly as the PPU does (MAME cps3.cpp draw code:
part offsets, {8,1,2,4}-tile sizes, flips, tile order xx-major) into an RGBA
PNG whose pixel (0,0) is the object's ORIGIN (its sprite-list xpos/ypos --
for a character, the axis between the feet). pen 0 is transparent. A second
PNG with a crosshair at the origin is written for eyeballing the axis.

Prints one row per object (index, origin, size, bbox relative to the origin,
parts, tiles) so P1's cel can be picked out; --only <idx> renders just that
object. The tile byte order defaults to MAME's gfx layout (pixel x reads byte
x ^ 3 of each 16-byte row); --no-swizzle reads the bytes in order, in case the
emulator's CPU byte view differs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

TILES_TABLE = {0: 8, 1: 1, 2: 2, 3: 4}
CRAM_SIZE = 0x800000        # 8 MB character RAM ("Sprite ROM" entry of a cps3 state)


def fbneo_hash(name: str) -> int:
    """statec.cpp HashString: the id an area is stored under in a state file."""
    h = 0xC0FFEE
    for ch in name.encode():
        h = ((h ^ ch) + (((h << 0x1A) & 0xFFFFFFFF) + (h >> 6))) & 0xFFFFFFFF
    return h


def state_area(state: bytes, name: str, length: int) -> bytes:
    """Return one area of an FBNeo savestate (uncompressed "FB1 "/"FS1 " file:
    entries are [block id u32][len u32][HashString(name) u32][data])."""
    key = length.to_bytes(4, "little") + fbneo_hash(name).to_bytes(4, "little")
    pos = state.find(key)
    if pos < 0:
        raise ValueError(f"state has no area {name!r} of {length:#x} bytes")
    start = pos + 8
    return state[start:start + length]


def state_block(state: bytes) -> bytes:
    """The scanned-areas block of an FBNeo/FBA state. Current FBNeo writes it
    raw after the 0x44-byte "FS1 " header; the Fightcade fork (older FBA
    lineage) zlib-compresses it, 4 bytes into the block."""
    c = state.find(b"FS1 ")
    data = state[c + 0x44:] if c >= 0 else state
    import zlib
    for off in (4, 0):
        try:
            return zlib.decompress(data[off:])
        except zlib.error:
            pass
    return data


PAL_SIZE = 0x40000          # 0x20000 x u16 colour RAM ("Palette" entry, right before the char RAM)


def state_areas(path: Path, known_tiles: dict | None = None) -> dict:
    """{"cram": 8 MB character RAM, "pal": colour RAM or None} out of a state.
    Current FBNeo: hashed entries. Older forks (Fightcade) concatenate the
    areas without headers, so the char RAM is located by anchoring on a tile
    the Lua read through the mapped bank-0 window (`known_tiles`: tileno ->
    hex, CPU byte order == host order dword-swapped) and the palette is the
    0x40000 bytes right before it."""
    state = Path(path).read_bytes()
    try:
        return {"cram": state_area(state, "Sprite ROM", CRAM_SIZE),
                "pal": state_area(state, "Palette", PAL_SIZE)}
    except ValueError:
        pass
    blob = state_block(state)
    # every non-blank bank-0 tile that occurs exactly once votes for a base;
    # the base most tiles agree on wins (a lone unique tile is enough)
    from collections import Counter
    votes: Counter = Counter()
    for k, hexdata in (known_tiles or {}).items():
        if int(k) >= 4096:
            continue
        cpu = bytes.fromhex(hexdata)
        if len(set(cpu)) < 2:
            continue                       # blank tile: matches everywhere
        host = bytes(x for i in range(0, 256, 4) for x in cpu[i:i + 4][::-1])
        pos = blob.find(host)
        if pos >= 0 and blob.find(host, pos + 1) < 0:
            base = pos - int(k) * 256
            if 0 <= base and base + CRAM_SIZE <= len(blob):
                votes[base] += 1
    if votes:
        base, n = votes.most_common(1)[0]
        if n >= 2 or len(votes) == 1:
            return {"cram": blob[base:base + CRAM_SIZE],
                    "pal": blob[base - PAL_SIZE:base] if base >= PAL_SIZE else None}
    raise ValueError("could not locate the character RAM in the state (no hashed entry, no usable bank-0 anchor tile)")


def cram_tiles_from_state(path: Path, known_tiles: dict | None = None) -> bytes:
    return state_areas(path, known_tiles)["cram"]


class StatePalettes:
    """palettes-dict stand-in over the state's colour RAM. FBNeo stores
    RamPal[index ^ 1] on little-endian hosts but renders through the CPU-side
    index (`Cps3CurPal[palindex]`), so the state's adjacent words are swapped
    back here. A palette read through the Lua API is already in CPU order."""
    def __init__(self, pal: bytes):
        self.pal = pal

    def get(self, key, default=None):
        base = int(key) * 2
        if base + 512 > len(self.pal):
            return default
        words = [int.from_bytes(self.pal[base + i:base + i + 2], "little") for i in range(0, 512, 2)]
        for i in range(0, 256, 2):
            words[i], words[i + 1] = words[i + 1], words[i]
        return "".join(f"{w:04x}" for w in words)


class StateTiles:
    """tiles-dict stand-in reading 256-byte tiles out of the state's char RAM.
    The state holds the host byte order, and FBNeo's renderer reads a pixel as
    `source[x ^ 3]` (cps3run.cpp) -- the same layout as MAME's gfx decode --
    so these decode with the default swizzle (pixel x = byte x ^ 3)."""
    def __init__(self, cram: bytes):
        self.cram = cram

    def get(self, key, default=None):
        t = int(key)
        off = t * 256
        if off + 256 > len(self.cram):
            return default
        return self.cram[off:off + 256].hex()


def decode_tile(hexdata: str, swizzle: bool = True) -> list[list[int]]:
    """256 hex-encoded bytes -> 16 rows of 16 pen indices."""
    raw = bytes.fromhex(hexdata)
    rows = []
    for y in range(16):
        row = raw[y * 16:(y + 1) * 16]
        rows.append([row[x ^ 3] if swizzle else row[x] for x in range(16)])
    return rows


def decode_palette(hexdata: str) -> list[tuple[int, int, int, int]]:
    """256 hex-encoded u16 (5-5-5 RGB) -> RGBA tuples; pen 0 is transparent."""
    out = []
    for i in range(0, len(hexdata), 4):
        v = int(hexdata[i:i + 4], 16)
        r, g, b = v & 0x1F, (v >> 5) & 0x1F, (v >> 10) & 0x1F
        out.append((r * 255 // 31, g * 255 // 31, b * 255 // 31, 255))
    if out:
        out[0] = (0, 0, 0, 0)
    return out


def part_tiles(rec: dict, part: dict) -> list[tuple[int, int, int, bool, bool]]:
    """(tile_number, x, y, flipx, flipy) for each tile of a part, x/y being the
    tile's top-left relative to the object origin (screen axes: y grows DOWN).
    Port of the MAME sprite loop with gscroll = 0 and the object at (0, 0)."""
    xsize_code, ysize_code = part["xsize"], part["ysize"]
    if xsize_code == 0:
        return []  # tilemap draw command, not a sprite part
    xsize, ysize = TILES_TABLE[xsize_code] - 1, TILES_TABLE[ysize_code] - 1
    xsizedraw, ysizedraw = part["xsizedraw"], part["ysizedraw"]
    xinc = (xsizedraw << 16) // (xsize + 1)
    yinc = (ysizedraw << 16) // (ysize + 1)
    flipx = part["flipx"] ^ rec["gxflip"]
    flipy = part["flipy"] ^ rec["gyflip"]
    xpos2, ypos2 = part["xpos2"], part["ypos2"]
    if not flipx:
        xpos2 += xsizedraw // 2
    else:
        xpos2 -= xsizedraw // 2
    ypos2 += ysizedraw // 2
    if not flipx:
        xpos2 -= ((xsize + 1) * xinc) >> 16
    else:
        xpos2 += (xsize * xinc) >> 16
    if flipy:
        ypos2 -= (ysize * yinc) >> 16
    def s10(v):
        # screen coordinates are 10-bit with sign (MAME: `& 0x3ff`, then
        # `-= 0x400` if bit 9 is set), so relative offsets wrap the same way
        return ((v + 0x200) & 0x3FF) - 0x200

    out = []
    count = 0
    for xx in range(xsize + 1):
        sx = xpos2 + ((xx * xinc) >> 16) if not flipx else xpos2 - ((xx * xinc) >> 16)
        sx = s10(sx + 1)                            # the PPU's +1
        for yy in range(ysize + 1):
            sy_ppu = ypos2 + ((yy * yinc) >> 16) if flipy else ypos2 - ((yy * yinc) >> 16)
            # screen y = 0x3ff - (ypos + sy_ppu) - 17; relative to the origin's
            # own screen y (0x3ff - ypos - 17) that is simply -sy_ppu.
            sy = s10(-sy_ppu)
            out.append((part["tileno"] + count, sx, sy, bool(flipx), bool(flipy)))
            count += 1
    return out


def render_object(rec: dict, tiles: dict, palettes: dict, swizzle: bool = True):
    """Compose one sprite-list object. Returns (image, (left, top)) where the
    image's pixel (0,0) sits at (left, top) relative to the object origin, or
    None if the object has no drawable part."""
    placed = []
    for part in rec["parts"]:
        usebpp = rec["gbpp"] if rec["whichbpp"] else part["bpp"]
        actualpal = rec["global_pal"] if rec["whichpal"] else part["pal"]
        palbase = (actualpal * (64 if usebpp else 256)) & 0x1FFFF
        pal = palettes.get(str(palbase))
        for tileno, x, y, fx, fy in part_tiles(rec, part):
            hexdata = tiles.get(str(tileno))
            if hexdata is None or pal is None:
                continue
            placed.append((decode_tile(hexdata, swizzle), decode_palette(pal), x, y, fx, fy))
    if not placed:
        return None
    left = min(p[2] for p in placed)
    top = min(p[3] for p in placed)
    right = max(p[2] for p in placed) + 16
    bottom = max(p[3] for p in placed) + 16
    img = Image.new("RGBA", (right - left, bottom - top), (0, 0, 0, 0))
    px = img.load()
    for rows, pal, x, y, fx, fy in placed:
        for ty in range(16):
            src_y = 15 - ty if fy else ty
            for tx in range(16):
                src_x = 15 - tx if fx else tx
                pen = rows[src_y][src_x]
                if pen:
                    px[x - left + tx, y - top + ty] = pal[pen]
    return img, (left, top)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump", help="pykuma_cels.jsonl from dump_cels.lua")
    ap.add_argument("--out", default="cels_out", help="output folder")
    ap.add_argument("--only", type=int, default=None, help="render only this object index")
    ap.add_argument("--no-swizzle", action="store_true", help="read tile bytes in order (no x^3)")
    ap.add_argument("--scale", type=int, default=3, help="upscale factor for the *_axis.png preview")
    ap.add_argument("--state-dir", default=None, help="folder holding the pykuma_cels_f<frame>.fs states (default: the dump's folder)")
    ap.add_argument("--lua-tiles", action="store_true", help="use the tiles the Lua read through the bank window instead of the state")
    ap.add_argument("--p1", action="store_true",
                    help="render only P1's body object, named cel_<cel id>.png, and write cels.json (cel -> anim, bbox rel. axis)")
    args = ap.parse_args(argv)
    manifest_path = Path(args.out) / "cels.json"
    manifest = json.loads(manifest_path.read_text()) if args.p1 and manifest_path.exists() else {}
    state_dir = Path(args.state_dir) if args.state_dir else Path(args.dump).resolve().parent

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for n, line in enumerate(Path(args.dump).read_text().splitlines()):
        if not line.strip():
            continue
        d = json.loads(line)
        p1, p2 = d["p1"], d["p2"]
        tiles, swizzle = d["tiles"], not args.no_swizzle
        palettes = d["palettes"]
        if d.get("state") and not args.lua_tiles:
            spath = state_dir / d["state"]
            if spath.exists():
                areas = state_areas(spath, d["tiles"])
                st = StateTiles(areas["cram"])
                if areas["pal"]:
                    palettes = StatePalettes(areas["pal"])
                # byte-order check against a tile the Lua read from the mapped bank
                for k, hexdata in d["tiles"].items():
                    if int(k) < 4096 and st.get(k) and len(set(bytes.fromhex(hexdata))) >= 2:
                        same = st.get(k) == hexdata
                        swz = bytes(b for i in range(0, 256, 4) for b in bytes.fromhex(st.get(k))[i:i + 4][::-1]).hex() == hexdata
                        print(f"   state tiles: bank-0 tile {k} vs Lua read -> {'identical' if same else 'dword-swapped' if swz else 'DIFFERENT'}")
                        break
                tiles = st
                print(f"   tiles from state {spath.name} (8 MB char RAM)")
            else:
                print(f"   !! state {spath} not found, using the Lua-read tiles (mapped bank only)")
        print(f"== dump {n} frame {d['f']}: P1 anim {p1['anim']} cel {p1['cel']} pos ({p1['pos_x']},{p1['pos_y']}) "
              f"flip {p1['flip']} | P2 anim {p2['anim']} cel {p2['cel']} pos ({p2['pos_x']},{p2['pos_y']}) | "
              f"{len(d['records'])} objects, {len(d['tiles'])} tiles, {len(d['palettes'])} palettes")
        records = d["records"]
        if args.p1:
            # P1's objects sit at xpos == pos_x; the body is the one with the most tiles (the other is the shadow)
            mine = [r for r in records if r["xpos"] == p1["pos_x"] and any(pp["xsize"] for pp in r["parts"])]
            mine.sort(key=lambda r: -sum(len(part_tiles(r, pp)) for pp in r["parts"]))
            records = mine[:1]
            if str(p1["cel"]) in manifest and not args.only:
                print(f"   cel {p1['cel']} already in cels.json, skipping")
                continue
        print(f"{'obj':>4} {'xpos':>5} {'ypos':>5} {'parts':>5} {'tiles':>5} {'size':>9}  bbox rel. origin (l,t,r,b)")
        for rec in records:
            if args.only is not None and rec["i"] != args.only:
                continue
            res = render_object(rec, tiles, palettes, swizzle=swizzle)
            ntiles = sum(len(part_tiles(rec, p)) for p in rec["parts"])
            if res is None:
                print(f"{rec['i']:>4} {rec['xpos']:>5} {rec['ypos']:>5} {len(rec['parts']):>5} {ntiles:>5}  (nothing drawable)")
                continue
            img, (left, top) = res
            w, h = img.size
            print(f"{rec['i']:>4} {rec['xpos']:>5} {rec['ypos']:>5} {len(rec['parts']):>5} {ntiles:>5} {w:>4}x{h:<4}  "
                  f"({left},{top},{left + w},{top + h})")
            stem = out / (f"cel_{p1['cel']}" if args.p1 else f"d{n}_obj{rec['i']:03d}")
            img.save(f"{stem}.png")
            if args.p1:
                manifest[str(p1["cel"])] = {"anim": p1["anim"], "flip": p1["flip"], "left": left, "top": top,
                                            "width": w, "height": h, "frame": d["f"], "state": d.get("state")}
                manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
            # axis preview: the object on a checker with a crosshair at its origin
            s = args.scale
            pad = 8
            canvas = Image.new("RGBA", ((w + 2 * pad) * s, (h + 2 * pad) * s), (40, 40, 40, 255))
            canvas.paste(img.resize((w * s, h * s), Image.NEAREST), (pad * s, pad * s), img.resize((w * s, h * s), Image.NEAREST))
            ox, oy = (pad - left) * s, (pad - top) * s
            dr = ImageDraw.Draw(canvas)
            dr.line([(ox - 6 * s, oy), (ox + 6 * s, oy)], fill=(255, 0, 0, 255), width=1)
            dr.line([(ox, oy - 6 * s), (ox, oy + 6 * s)], fill=(255, 0, 0, 255), width=1)
            canvas.save(f"{stem}_axis.png")
    print(f"PNGs in {out}/  (d<dump>_obj<idx>.png = object with pixel (0,0) at bbox left/top; *_axis.png = preview with the origin crosshair)")


if __name__ == "__main__":
    main()
