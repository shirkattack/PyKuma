#!/usr/bin/env python3
"""Diff a scenario timeline against a golden one (ROM capture or decomp-expected).

Both timelines are lists of frames `{"frame", "players":[{pos,state,health,...}]}`
(the shape `run_scenario` returns and `debug_state`/FrameRecorder produce). The
golden can be a ROM capture converted to that shape (see tools/rom_extract/) or a
small hand-authored decomp-derived expectation. Reports per-frame deltas in the
fields that matter for combat correctness: position, state, health, hitstun.

Usage:
    uv run python tools/diagnostics/compare.py actual.json golden.json [--pos-tol 2]
"""

from __future__ import annotations

import argparse
import json
from typing import List, Optional


def _player_fields(p: dict) -> dict:
    return {
        "pos": tuple(p.get("pos", ())),
        "state": p.get("state"),
        "health": p.get("health"),
        "hitstun": p.get("hitstun"),
    }


def compare_timelines(actual: List[dict], golden: List[dict],
                      pos_tol: float = 2.0) -> List[dict]:
    """Return a list of per-frame discrepancies (empty == match within tolerance)."""
    diffs = []
    n = min(len(actual), len(golden))
    for i in range(n):
        for pi in (0, 1):
            ap = actual[i]["players"][pi]
            gp = golden[i]["players"][pi]
            a, g = _player_fields(ap), _player_fields(gp)
            row = {}
            if a["state"] != g["state"]:
                row["state"] = (a["state"], g["state"])
            if a["pos"] and g["pos"]:
                dx = abs(a["pos"][0] - g["pos"][0])
                dy = abs(a["pos"][1] - g["pos"][1])
                if dx > pos_tol or dy > pos_tol:
                    row["pos"] = (a["pos"], g["pos"], round(dx, 1), round(dy, 1))
            for f in ("health", "hitstun"):
                if a[f] is not None and g[f] is not None and a[f] != g[f]:
                    row[f] = (a[f], g[f])
            if row:
                diffs.append({"frame": actual[i].get("frame", i), "player": pi + 1, **row})
    if len(actual) != len(golden):
        diffs.append({"note": f"length differs: actual={len(actual)} golden={len(golden)}"})
    return diffs


def print_report(diffs: List[dict], limit: int = 40) -> None:
    if not diffs:
        print("MATCH: timelines agree within tolerance.")
        return
    print(f"{len(diffs)} discrepancies (showing {min(limit, len(diffs))}):")
    for d in diffs[:limit]:
        print(" ", d)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("actual"); p.add_argument("golden")
    p.add_argument("--pos-tol", type=float, default=2.0)
    args = p.parse_args(argv)
    actual = json.load(open(args.actual))
    golden = json.load(open(args.golden))
    print_report(compare_timelines(actual, golden, args.pos_tol))


if __name__ == "__main__":
    main()
