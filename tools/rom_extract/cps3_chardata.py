#!/usr/bin/env python3
"""Read a character's data tables straight out of the arcade ROM (sfiii3nr1).

    uv run python tools/rom_extract/cps3_chardata.py <sfiii3nr1.zip> --char akuma \
        --out data/sources/cps3_akuma_chardata.json

Decrypts the four program SIMMs the way crowded-street/3sx does
(src/arcade/cps3_decrypt.c, rom_load.c -- the standard CPS3 cipher with the
sfiii3 keys) and reads the per-character arrays at the locations 3sx's
arcade_char_data.c documents. Nothing but small numeric tables is written:
the decrypted image stays in memory.

Tables (names are Capcom's; struct layouts from 3sx tools/compare_char_data.py
and the 3s-decomp structs.h):
  atta  attack boxes            s16 att_box[4][4] per entry (left, width, bottom, height) x4
  atit  attack data (UNK_7)     reaction, level, mkh_ix, but_ix, dipsw, guard, dir, free,
                                pow (-> Power_Data[pow] = raw damage), impact, piyo (stun),
                                ng_type, hs_me, hs_you (hitstop), hit_mark, dmg_mark
  boda / hana / cata / caua / hosa   body / hand hurtboxes, catch, caught, hosei boxes
  hiit  per-cel box indices     caix, cuix, atix, hoix ... (u16 x8)

Provenance: geometry/values are the ROM's own bytes ("verified"); the
decryption and offsets are 3sx's (commit noted in the output).
"""

from __future__ import annotations

import argparse
import json
import struct
import zipfile
from pathlib import Path

BASE_OFFSET = 0x6000000
KEY_1 = 0xA55432B4
KEY_2 = 0x0C129981
SIMM_PREFIX = "sfiii3-simm1."
THREESX_COMMIT = "main (crowded-street/3sx, fetched 2026-08-26)"

# From 3sx tools/compare_char_data.py
STRUCTS = {
    "ovct": "hhBBBBBBhHH", "ovix": "hhhh", "rict": "hhBBh", "hiit": "HHHHHHHH",
    "boda": "h" * 16, "hana": "h" * 16, "cata": "hhhh", "caua": "hhhh",
    "atta": "h" * 16, "hosa": "hhhh", "atit": "BBBBBBBBBBBBbbBB", "prot": "h" * 24,
    "stxy": "h", "mvxy": "h",
}
ATIT_FIELDS = ("reaction", "level", "mkh_ix", "but_ix", "dipsw", "guard", "dir", "free",
               "pow", "impact", "piyo", "ng_type", "hs_me", "hs_you", "hit_mark", "dmg_mark")
# 3sx src/arcade/arcade_char_data.c location_data[akuma] (offsets are into the
# decrypted 8 MB program image; sizes in bytes)
LOCATIONS = {
    "akuma": {
        "ovct": (0x333A48, 0x730), "ovix": (0x333938, 0x110), "rict": (0x334178, 0x1800),
        "hiit": (0x41EA10, 0x1190), "boda": (0x41FBA0, 0x1540), "hana": (0x4210E0, 0x620),
        "cata": (0x44DC28, 0x98), "caua": (0x44DCC0, 0x30), "atta": (0x44D248, 0x9E0),
        "hosa": (0x421700, 0x30), "atit": (0x459F4C, 0x600), "prot": (0x468F8C, 0x930),
        "stxy": (0x4688A8, 0x240), "mvxy": (0x468AE8, 0x4A4),
    },
}
# POW_DATA.c (3s-decomp): raw damage per `pow` index; 0,5,10,...,995,999...
POWER_DATA = [min(999, 5 * i) for i in range(200)] + [999] * 56
POWER_DATA[180] = 800  # the ROM table has this one odd entry (sic)


def _rotl16(v: int, n: int) -> int:
    v &= 0xFFFF
    return ((v << n) | (v >> (16 - n))) & 0xFFFF


def _rotxor(val: int, xorval: int) -> int:
    val &= 0xFFFF
    xorval &= 0xFFFF
    res = (val + _rotl16(val, 2)) & 0xFFFFFFFF
    res = (_rotl16(res, 4) ^ (res & (val ^ xorval))) & 0xFFFFFFFF
    return res


def cps3_mask(address: int, key1: int = KEY_1, key2: int = KEY_2) -> int:
    address ^= key1
    val = (address & 0xFFFF) ^ 0xFFFF
    val = _rotxor(val, key2 & 0xFFFF)
    val ^= (address >> 16) ^ 0xFFFF
    val = _rotxor(val, key2 >> 16)
    val ^= (address & 0xFFFF) ^ (key2 & 0xFFFF)
    return (val | (val << 16)) & 0xFFFFFFFF


def decrypt_simms(simms: list[bytes]) -> bytes:
    """Interleave the four SIMM images and decrypt: image[4i..4i+4] =
    BE(u32(s0[i],s1[i],s2[i],s3[i]) ^ mask(BASE + 4i))."""
    n = len(simms[0])
    out = bytearray(n * 4)
    s0, s1, s2, s3 = simms
    for i in range(n):
        cur = (s0[i] << 24) | (s1[i] << 16) | (s2[i] << 8) | s3[i]
        v = cur ^ cps3_mask(BASE_OFFSET + i * 4)
        out[4 * i:4 * i + 4] = v.to_bytes(4, "big")
    return bytes(out)


def load_program_image(rom_zip: Path) -> bytes:
    with zipfile.ZipFile(rom_zip) as z:
        names = sorted(n for n in z.namelist() if n.startswith(SIMM_PREFIX))[:4]
        if len(names) != 4:
            raise SystemExit(f"{rom_zip}: expected 4 '{SIMM_PREFIX}*' files, found {names}")
        return decrypt_simms([z.read(n) for n in names])


def read_table(image: bytes, name: str, offset: int, size: int) -> list[tuple]:
    fmt = ">" + STRUCTS[name]
    elem = struct.calcsize(fmt)
    return [struct.unpack(fmt, image[o:o + elem]) for o in range(offset, offset + size - elem + 1, elem)]


def boxes4(row: tuple) -> list[dict]:
    """A 16-short box row -> up to 4 {left,width,bottom,height} (empty slots dropped)."""
    out = []
    for i in range(4):
        left, width, bottom, height = row[4 * i:4 * i + 4]
        if width > 0 and height > 0:
            out.append({"left": left, "width": width, "bottom": bottom, "height": height})
    return out


def extract(image: bytes, char: str) -> dict:
    loc = LOCATIONS[char]
    tables = {name: read_table(image, name, off, size) for name, (off, size) in loc.items()}
    atit = []
    for i, row in enumerate(tables["atit"]):
        e = dict(zip(ATIT_FIELDS, row))
        e["index"] = i
        e["damage_raw"] = POWER_DATA[e["pow"]]
        atit.append(e)
    return {
        "_meta": {
            "character": char, "rom": "sfiii3nr1 (program SIMMs 1.0-1.3, decrypted in memory)",
            "decryption": "CPS3 cipher, keys 0xA55432B4/0x0C129981 (crowded-street/3sx src/arcade/cps3_decrypt.c)",
            "locations": "crowded-street/3sx src/arcade/arcade_char_data.c",
            "threesx": THREESX_COMMIT, "status": "verified",
            "power_data": "3s-decomp POW_DATA.c (damage_raw = Power_Data[pow]; applied = raw * level% * att_plus/8 * def_plus/8)",
        },
        "atit": atit,
        "atta": [boxes4(r) for r in tables["atta"]],
        "boda": [boxes4(r) for r in tables["boda"]],
        "hana": [boxes4(r) for r in tables["hana"]],
        "cata": [list(r) for r in tables["cata"]],
        "caua": [list(r) for r in tables["caua"]],
        "hosa": [list(r) for r in tables["hosa"]],
        "hiit": [list(r) for r in tables["hiit"]],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom_zip", help="sfiii3nr1.zip (your own, read-only)")
    ap.add_argument("--char", default="akuma", choices=sorted(LOCATIONS))
    ap.add_argument("--out", default=None, help="write the tables as JSON here")
    args = ap.parse_args(argv)
    image = load_program_image(Path(args.rom_zip))
    data = extract(image, args.char)
    if args.out:
        Path(args.out).write_text(json.dumps(data, indent=1) + "\n")
        print(f"wrote {args.out}")
    print(f"{args.char}: atit {len(data['atit'])} attack entries, atta {len(data['atta'])} box rows, "
          f"boda {len(data['boda'])}, hana {len(data['hana'])}, hiit {len(data['hiit'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
