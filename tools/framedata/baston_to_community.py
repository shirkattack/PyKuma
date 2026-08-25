#!/usr/bin/env python3
"""Regenerate the community-tier yaml from the vendored Baston ESN3S tables.

    uv run python tools/framedata/baston_to_community.py \
        --baston data/sources/baston \
        --yaml data/characters/akuma/sf3_authentic_frame_data.yaml

Reads the three saved Baston tables (normals / specials / supers, "revised"
data; see data/sources/baston/SOURCE.md) and rewrites the move sections of the
community yaml IN PLACE: startup / active / recovery / total (Baston's own
numbers -- the engine's timing still comes from the ROM dump), damage, stun,
hit_advantage, block_advantage, plus a `baston:` provenance line per move.
Everything else on a move (hitboxes, invincibility_frames, cancel flags,
projectile params) and the non-move sections are preserved. Moves without a
Baston row keep their values and get `baston: null`.

Damage scale -- PROVISIONAL. Baston lists per-hit damage on the game's own
scale (st. Fierce = 24, jab = 3). The yaml keeps Akuma's 1050 vitality and
converts every row with ONE anchor, Fierce 24 -> 180 (x7.5), so the ratios
between moves match the real game (a jab is ~2% of the bar, as in 3S). The
absolute scale (how many fierces kill) is a choice until the damage table is
read from the ROM (tools/rom_extract). Multi-hit specials list their TOTAL
damage; the ROM converter splits it per hit window.
"""

import argparse
import html
import re
from pathlib import Path

import yaml

DAMAGE_SCALE = 180 / 24          # anchor: Baston st. Fierce 24 == yaml 180
SOURCE = "Baston ESN3S revised (data/sources/baston, fetched 2026-08-25)"

# Baston row name -> (yaml section, yaml key). One Baston row may feed several
# keys (the three fireball strengths share one row).
NAME_MAP = {
    # normals ------------------------------------------------------------
    "Jab":                       ("normal_attacks", "standing_light_punch_close"),
    "Far Jab":                   ("normal_attacks", "standing_light_punch"),
    "Strong":                    ("normal_attacks", "standing_medium_punch"),
    "Far Strong":                ("normal_attacks", "standing_medium_punch_far"),
    "Fierce":                    ("normal_attacks", "standing_heavy_punch_close"),
    "Far Fierce":                ("normal_attacks", "standing_heavy_punch"),
    "Crouching Jab":             ("normal_attacks", "crouching_light_punch"),
    "Crouching Strong":          ("normal_attacks", "crouching_medium_punch"),
    "Crouching Fierce":          ("normal_attacks", "crouching_heavy_punch"),
    "Short":                     ("normal_attacks", "standing_light_kick"),
    "Forward":                   ("normal_attacks", "standing_medium_kick"),
    "Far Forward":               ("normal_attacks", "standing_medium_kick_far"),
    "Roundhouse":                ("normal_attacks", "standing_heavy_kick"),
    "Far Roundhouse":            ("normal_attacks", "standing_heavy_kick_far"),
    "Crouching Short":           ("normal_attacks", "crouching_light_kick"),
    "Crouching Forward":         ("normal_attacks", "crouching_medium_kick"),
    "Crouching Roundhouse":      ("normal_attacks", "crouching_heavy_kick"),
    "Jumping Jab":               ("normal_attacks", "jump_light_punch"),
    "Jumping Strong":            ("normal_attacks", "jump_medium_punch"),
    "Jumping Fierce":            ("normal_attacks", "jump_heavy_punch"),
    "Jumping Short":             ("normal_attacks", "jump_light_kick"),
    "Jumping Forward":           ("normal_attacks", "jump_medium_kick"),
    "Jumping Roundhouse":        ("normal_attacks", "jump_heavy_kick"),
    "Neutral Jumping Fierce":    ("normal_attacks", "jump_heavy_punch_neutral"),
    "Neutral Jumping Forward":   ("normal_attacks", "jump_medium_kick_neutral"),
    "Neutral Jumping Roundhouse": ("normal_attacks", "jump_heavy_kick_neutral"),
    "Towards + Strong":          ("normal_attacks", "forward_medium_punch"),
    "Dive Kick":                 ("normal_attacks", "dive_kick"),
    "Throw":                     ("normal_attacks", "forward_throw"),
    "Back + Throw":              ("normal_attacks", "back_throw"),
    "Universal Overhead":        ("normal_attacks", "universal_overhead"),
    # specials -----------------------------------------------------------
    "Gou Hadouken":              ("special_moves", ["gohadoken_light", "gohadoken_medium", "gohadoken_heavy"]),
    "Zankuu Hadouken":           ("special_moves", "air_gohadoken"),
    "Gou Shoryuken (Jab)":       ("special_moves", "goshoryuken_light"),
    "Gou Shoryuken (Strong)":    ("special_moves", "goshoryuken_medium"),
    "Gou Shoryuken (Fierce)":    ("special_moves", "goshoryuken_heavy"),
    "Tatsumaki Zankuu Kyaku (Short)":   ("special_moves", "tatsumaki_light"),
    "Tatsumaki Zankuu Kyaku (Forward)": ("special_moves", "tatsumaki_medium"),
    "Tatsumaki Zankuu Kyaku (RH)":      ("special_moves", "tatsumaki_heavy"),
    "Air Tatsumaki Zankuu Kyaku (Short)":   ("special_moves", "air_tatsumaki_light"),
    "Air Tatsumaki Zankuu Kyaku (Forward)": ("special_moves", "air_tatsumaki_medium"),
    "Air Tatsumaki Zankuu Kyaku (RH)":      ("special_moves", "air_tatsumaki_heavy"),
    "Shakunetsu Hadouken (Jab)":    ("special_moves", "shakunetsu_hadouken_light"),
    "Shakunetsu Hadouken (Strong)": ("special_moves", "shakunetsu_hadouken_medium"),
    "Shakunetsu Hadouken (Fierce)": ("special_moves", "shakunetsu_hadouken_heavy"),
    "Hyakki Shuu":               ("special_moves", "demon_flip"),
    "Hyakki Goushou":            ("special_moves", "demon_flip_palm"),
    "Hyakki Goujin":             ("special_moves", "demon_flip_kick"),
    "Hyakki Gousai":             ("special_moves", "demon_flip_throw"),
    # supers -------------------------------------------------------------
    "Messatsu Gou Hadou":        ("super_arts", "messatsu_gou_hadou"),
    "Tenma Gou Zankuu":          ("super_arts", "messatsu_gou_hadou_air"),
    "Messatsu Gou Shoryuu":      ("super_arts", "messatsu_gou_shoryu"),
    "Messatsu Gou Rasen (Ground)": ("super_arts", "messatsu_gou_rasen"),
    "Messatsu Gou Rasen (Air)":  ("super_arts", "messatsu_gou_rasen_air"),
    "Shun Goku Sastu":           ("super_arts", "shun_goku_satsu"),   # sic (Baston's spelling)
    "Kongou Kokuretsu Zan":      ("super_arts", "kongou_kokuretsu_zan"),
}
# The yaml used to file SA2 under a wrong name; migrate it.
RENAMES = {("super_arts", "tensho_kaireki_jin"): ("super_arts", "messatsu_gou_shoryu")}

BANNER = """# Akuma community frame data: damage / stun / frame advantage (+ Baston's own
# startup-active-recovery). GENERATED by tools/framedata/baston_to_community.py
# from the vendored Baston ESN3S "revised" tables (data/sources/baston) -- do not
# hand-edit the numbers; edit the tool's NAME_MAP / DAMAGE_SCALE and regenerate.
#
# PROVENANCE. This is the COMMUNITY tier, NOT ROM-verified. It is the source of
# damage, stun and hit/block advantage (hitstun/blockstun are back-solved from
# the advantage against the ROM timeline -- akuma_hitboxes._calibrated_stun).
# Box geometry and move timing that the engine actually runs come from the
# ROM dump via tools/framedata/convert_3rd_training.py -> hitboxes.yaml; the
# `hitboxes:` blocks below are old hand-approximations kept for the legacy
# loader/tests only. `baston:` on each move records the row it came from.
#
# DAMAGE SCALE (provisional): Baston's per-hit numbers x7.5, anchored on
# st. Fierce 24 -> 180 against Akuma's 1050 vitality. Multi-hit specials list
# the move TOTAL (split per ROM hit window at conversion).
"""


def rows(path: Path):
    raw = path.read_text(errors="replace")
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", raw, flags=re.S):
        cells = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", c)).split())
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        if cells and cells[0] != "":
            out.append(cells)
    return out


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def parse_tables(baston_dir: Path):
    """{baston_name: {startup, active, recovery, blk, hit, damage, stun}}"""
    data = {}
    # normals: | id | Name | Startup | Hit | Recovery | Blk. Adv. | Hit Adv. | Cr. Hit Adv. | Cancel | Parry | Kara | Throw | Damage | Stun | ...
    for r in rows(baston_dir / "fd_normals.html"):
        if len(r) < 14 or not r[1] or r[1] == "Name":
            continue
        data[r[1]] = dict(startup=_int(r[2]), active=_int(r[3]), recovery=_int(r[4]),
                          block_advantage=_int(r[5]), hit_advantage=_int(r[6]),
                          damage=_int(r[12]), stun=_int(r[13]))
    # specials / supers: | id | Name | Motion | Startup | Hit | Recovery | Blk. Adv. | Cancel | Parry | Throw Range | Damage | Stun | ...
    for f in ("fd_specials.html", "fd_supers.html"):
        for r in rows(baston_dir / f):
            if len(r) < 12 or not r[1] or r[1] == "Name":
                continue
            data[r[1]] = dict(startup=_int(r[3]), active=_int(r[4]), recovery=_int(r[5]),
                              block_advantage=_int(r[6]), hit_advantage=None,
                              damage=_int(r[10]), stun=_int(r[11]))
    return data


def scaled(damage):
    return int(round(damage * DAMAGE_SCALE)) if damage is not None else None


def apply(doc: dict, table: dict):
    for (sec, old), (nsec, new) in RENAMES.items():
        if sec in doc and old in doc[sec]:
            doc.setdefault(nsec, {})[new] = doc[sec].pop(old)
    for name, (section, keys) in NAME_MAP.items():
        row = table.get(name)
        if row is None:
            continue
        for key in ([keys] if isinstance(keys, str) else keys):
            move = doc.setdefault(section, {}).setdefault(key, {})
            new = {}
            for f in ("startup", "active", "recovery"):
                new[f] = row[f] if row[f] is not None else move.get(f)
            if all(new[f] is not None for f in ("startup", "active", "recovery")):
                new["total"] = new["startup"] + new["active"] + new["recovery"]
            else:
                new["total"] = move.get("total")
            new["damage"] = scaled(row["damage"]) if row["damage"] is not None else move.get("damage", 0)
            new["stun"] = row["stun"] if row["stun"] is not None else move.get("stun", 0)
            new["hit_advantage"] = row["hit_advantage"] if row["hit_advantage"] is not None else 0
            new["block_advantage"] = row["block_advantage"] if row["block_advantage"] is not None else 0
            adv = (f"{row['hit_advantage'] if row['hit_advantage'] is not None else '-'}/"
                   f"{row['block_advantage'] if row['block_advantage'] is not None else '-'}")
            new["baston"] = (f"{name}: {row['startup'] or '-'}/{row['active'] or '-'}/"
                             f"{row['recovery'] or '-'}, dmg {row['damage']}, stun {row['stun']}, "
                             f"hit/blk adv {adv}")
            # Rebuild the move with the generated fields first, then the rest.
            rest = {k: v for k, v in move.items() if k not in new}
            move.clear()
            move.update(new)
            move.update(rest)
    # Tag everything else as not covered.
    for section in ("normal_attacks", "special_moves", "super_arts"):
        for key, move in doc.get(section, {}).items():
            if isinstance(move, dict) and "baston" not in move:
                move["baston"] = None
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baston", default="data/sources/baston")
    ap.add_argument("--yaml", default="data/characters/akuma/sf3_authentic_frame_data.yaml")
    ap.add_argument("--check", action="store_true", help="exit 1 if the yaml is not up to date")
    args = ap.parse_args(argv)
    path = Path(args.yaml)
    doc = yaml.safe_load(path.read_text()) or {}
    table = parse_tables(Path(args.baston))
    apply(doc, table)
    out = BANNER + yaml.safe_dump(doc, default_flow_style=False, sort_keys=False, width=110, allow_unicode=True)
    if args.check:
        if path.read_text() != out:
            print("community yaml is out of date -- regenerate with tools/framedata/baston_to_community.py")
            return 1
        print("community yaml up to date")
        return 0
    path.write_text(out)
    mapped = sum(1 for n in NAME_MAP if n in table)
    print(f"wrote {path}: {mapped}/{len(NAME_MAP)} Baston rows applied; unmatched Baston rows: "
          f"{sorted(set(table) - set(NAME_MAP))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
