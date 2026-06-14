"""Central logging setup for PyKuma.

One place to configure levels and a rate-limited helper for hot-path messages.
Use `get_logger(__name__)` in modules and call `setup_logging()` once at startup.

Level resolution (first that applies):
  1. explicit `level` arg to setup_logging()
  2. env var PYKUMA_LOG (e.g. DEBUG, INFO, WARNING)
  3. DEBUG_MODE in data/constants.py  (True -> DEBUG, else INFO)

Strict mode (fail-loud): the game loop re-raises exceptions instead of swallowing
them. Resolved from the `strict` arg, else env PYKUMA_STRICT, else DEBUG_MODE.
"""

import logging
import os

from street_fighter_3rd.data.constants import DEBUG_MODE

_LOG_DIR = "debug_snapshots"
_LOG_FILE = os.path.join(_LOG_DIR, "pykuma.log")

_configured = False
_strict = False
_seen_once: set = set()  # signature keys already logged by log_once


def _resolve_level(level):
    if level is not None:
        return level if isinstance(level, int) else logging.getLevelName(str(level).upper())
    env = os.environ.get("PYKUMA_LOG")
    if env:
        return logging.getLevelName(env.upper())
    return logging.DEBUG if DEBUG_MODE else logging.INFO


def _resolve_strict(strict):
    if strict is not None:
        return bool(strict)
    env = os.environ.get("PYKUMA_STRICT")
    if env is not None:
        return env.strip().lower() in ("1", "true", "yes", "on")
    return bool(DEBUG_MODE)


def setup_logging(level=None, strict=None):
    """Configure root logging once. Idempotent."""
    global _configured, _strict
    _strict = _resolve_strict(strict)
    resolved = _resolve_level(level)

    root = logging.getLogger("street_fighter_3rd")
    root.setLevel(resolved)

    if not _configured:
        fmt = logging.Formatter("%(levelname)s %(name)s: %(message)s")
        stream = logging.StreamHandler()
        stream.setFormatter(fmt)
        root.addHandler(stream)

        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
            file_handler = logging.FileHandler(_LOG_FILE)
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
            root.addHandler(file_handler)
        except OSError:
            pass  # console logging still works if the file handler can't open

        root.propagate = False
        _configured = True

    return root


def get_logger(name):
    """Return a module logger under the street_fighter_3rd namespace."""
    return logging.getLogger(name)


def is_strict() -> bool:
    """True when the game loop should re-raise instead of swallowing errors."""
    return _strict


def log_once(logger, key, level, msg, *args):
    """Log a message only the first time a given `key` signature is seen.

    For hot-path callers (per-frame state timeouts, repeated missing-sprite
    warnings) whose objects are recreated each round, so the dedup state must
    live here, not on the instance.
    """
    if key in _seen_once:
        return
    _seen_once.add(key)
    logger.log(level, msg, *args)


def reset_log_once():
    """Clear the log_once dedup set (e.g. between test cases)."""
    _seen_once.clear()
