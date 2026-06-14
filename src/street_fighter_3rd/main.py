"""Main entry point for Street Fighter Third Strike Python Edition."""

import argparse
import sys
import pygame
from street_fighter_3rd.core.game import Game
from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE
from street_fighter_3rd.util.logging_config import get_logger

log = get_logger(__name__)

# Window is this many times the native render resolution. The game always
# draws at SCREEN_WIDTH x SCREEN_HEIGHT, then the finished frame is scaled up
# to the window with nearest-neighbor scaling (crisp pixel art, no blur).
WINDOW_SCALE = 2

_EPILOG = """\
other commands:
  uv run sf3-menu       Launch with the main menu (mode select, controls, intro)
  uv run sf3-training   Training mode (visible damage, health regen, hitboxes)
  uv run sf3-dev        Full debug mode (all overlays)
  (sf3-menu has its own options: uv run sf3-menu --help)

in-game controls:
  Player 1   move WASD   punches J/K/L   kicks U/I/O   (double-tap to dash)
  Player 2   move Arrows punches KP1/2/3 kicks KP4/5/6 (double-tap to dash)
  specials   QCF+P (fireball), DP+P (dragon punch), QCB+K (hurricane)
  F1 debug overlay   F12 save snapshot   ESC pause   close window to quit
"""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="sf3",
        description="PyKuma — quick-play Akuma vs Akuma (no menu).",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scale", type=int, default=WINDOW_SCALE, metavar="N",
                        help=f"window size as a multiple of the {SCREEN_WIDTH}x{SCREEN_HEIGHT} "
                             f"render resolution (default: {WINDOW_SCALE})")
    parser.add_argument("--fps", type=int, default=FPS, metavar="N",
                        help=f"frame-rate cap (default: {FPS})")
    parser.add_argument("--rounds", action="store_true",
                        help="enable best-of round structure with timer (default: endless quick play)")
    parser.add_argument("--debug", action="store_true",
                        help="start with the F1 debug overlay enabled")
    parser.add_argument("--strict", action="store_true",
                        help="fail loud: crash on a frame error instead of logging + continuing")
    return parser.parse_args(argv)


def main():
    """Initialize and run the game."""
    args = parse_args()
    from street_fighter_3rd.util.logging_config import setup_logging
    setup_logging(strict=True if (args.strict or args.debug) else None)
    pygame.init()

    # Initialize joystick subsystem explicitly with error handling
    try:
        pygame.joystick.init()
        log.info("Joystick subsystem initialized successfully")
    except pygame.error as e:
        log.warning("Failed to initialize joystick subsystem: %s", e)
        log.info("Continuing with keyboard-only input")

    # Create the (larger) window, and a native-resolution surface the game
    # renders into. The window is SCREEN x scale; the game never sees it.
    scale = max(1, args.scale)
    window = pygame.display.set_mode((SCREEN_WIDTH * scale, SCREEN_HEIGHT * scale))
    pygame.display.set_caption(WINDOW_TITLE)
    render_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Create clock for frame rate control
    clock = pygame.time.Clock()

    # Initialize game; quick play skips the round structure unless --rounds given
    from street_fighter_3rd.core.game_modes import GameModeManager, GameMode
    game_mode_manager = GameModeManager(GameMode.NORMAL)
    game_mode_manager.config.no_rounds = not args.rounds

    # Initialize game (draws to the native-resolution surface)
    game = Game(render_surface, game_mode_manager)
    game.debug_display = args.debug

    from street_fighter_3rd.util.logging_config import is_strict
    from street_fighter_3rd.util.crash_handler import write_crash_report

    # Main game loop
    running = True
    while running:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    game.handle_event(event)

            # Fixed timestep: one loop iteration is one game frame
            clock.tick(args.fps)
            game.update()

            # Render at native resolution, then scale the frame up to the window
            game.render()
            pygame.transform.scale(render_surface, window.get_size(), window)
            pygame.display.flip()
        except Exception as exc:
            report = write_crash_report(exc, game)
            log.exception("Frame %d crashed; report at %s", game.frame_count, report)
            if is_strict():
                raise
            running = False

    # Cleanup
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
