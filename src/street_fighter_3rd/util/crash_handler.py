"""Write a crash report when the game loop raises.

Used by the main loops to record a traceback (plus a little game context) to a
file so a crash can be diagnosed after the fact, while the loop exits cleanly
in release mode.
"""

import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from street_fighter_3rd.util.logging_config import get_logger

log = get_logger(__name__)


def write_crash_report(exc: BaseException, game: Optional[Any] = None) -> str:
    """Write a crash report for ``exc`` and return the report file path.

    Args:
        exc: the exception that was raised.
        game: optional game object; ``frame_count`` is recorded if present.

    Returns:
        The path to the written report (best-effort; returns the intended path
        even if writing failed).
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(tempfile.gettempdir()) / "pykuma_crashes"
    report_path = report_dir / f"crash_{timestamp}.txt"

    frame = getattr(game, "frame_count", None)
    lines = [
        f"PyKuma crash report ({datetime.now().isoformat()})",
        f"frame_count: {frame}",
        "",
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    ]

    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines))
    except OSError as write_err:
        log.error("Could not write crash report to %s: %s", report_path, write_err)

    return str(report_path)
