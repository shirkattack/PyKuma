#!/usr/bin/env python3
"""Replay an F11 session clip into a montage PNG you can look at.

The F11 clip (debug_snapshots/clip_*/frames.json) records, per frame, both
players' position / facing / state / exact animation+frame. This re-draws that
recorded timeline through the real render path (camera + sprites) and lays the
frames out as a single labeled contact-sheet image -- so a reported issue ("the
jump flips", "knockback flings them off-screen") can be SEEN from data.

This is STATE PLAYBACK: it renders the recorded state, it does not re-simulate,
so the picture is faithful to what actually happened in that clip. (Projectiles
aren't re-drawn yet -- the recorder stores only their count.)

Usage:
    uv run python tools/diagnostics/replay.py <clip_dir|frames.json> [--every N] [--out PNG]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Make `tools.diagnostics.harness` importable when run as a plain script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.diagnostics.harness import render_recorded_clip, build_montage


def _load_frames(path: str):
    if os.path.isdir(path):
        path = os.path.join(path, "frames.json")
    with open(path) as f:
        return json.load(f), path


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("clip", help="clip directory or path to frames.json")
    p.add_argument("--every", type=int, default=6, help="sample every Nth frame (default 6)")
    p.add_argument("--out", default=None, help="output montage PNG (default: <clip>/montage.png)")
    args = p.parse_args(argv)

    frames, src = _load_frames(args.clip)
    if not frames:
        print(f"no frames in {src}"); return 1
    out = args.out or os.path.join(os.path.dirname(src), "montage.png")
    tiles = render_recorded_clip(frames, every=args.every)
    build_montage(tiles, out)
    print(f"{len(frames)} frames -> {len(tiles)} tiles -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
