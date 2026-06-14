"""Turn a crash into an actionable artifact.

On an unhandled per-frame exception, write a folder with the traceback, the
game's numerical state, recent invariant violations and recent frames, plus the
final rendered PNG — so a crash can be handed to an assistant verbatim.
"""

import json
import os
import platform
import sys
import traceback

from street_fighter_3rd.util.logging_config import get_logger

log = get_logger(__name__)


def write_crash_report(exc, game=None, out_root="debug_snapshots"):
    """Write debug_snapshots/crash_<frame>/ and return its path (or None on failure).

    Self-guarded: a failure while reporting must not mask the original exception.
    """
    try:
        frame = getattr(game, "frame_count", 0) if game else 0
        out_dir = os.path.join(out_root, f"crash_{frame:06d}")
        os.makedirs(out_dir, exist_ok=True)

        with open(os.path.join(out_dir, "crash.txt"), "w") as f:
            f.write("PyKuma crash report\n===================\n\n")
            f.write(f"frame: {frame}\n")
            f.write(f"python: {platform.python_version()}  platform: {platform.platform()}\n")
            f.write(f"argv: {sys.argv}\n\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))

        data = {"frame": frame, "error": repr(exc)}
        if game is not None:
            try:
                data.update(game.debug_state())
            except Exception:
                pass
            diagnostics = getattr(game, "diagnostics", None)
            if diagnostics is not None:
                data["recent_violations"] = [v.as_dict() for v in diagnostics.recent(20)]
            recorder = getattr(game, "recorder", None)
            if recorder is not None:
                data["recent_frames"] = recorder.recent(60)
            # Final rendered frame
            try:
                game.save_debug_snapshot(out_dir=out_dir, name="final")
            except Exception:
                pass

        with open(os.path.join(out_dir, "crash.json"), "w") as f:
            json.dump(data, f, indent=2, default=str)

        log.error("Crash report written to %s", out_dir)
        return out_dir
    except Exception:  # reporting must never mask the real crash
        log.exception("Failed to write crash report")
        return None
