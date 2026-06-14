"""Main entry point with menu system and command line support."""

import sys
import argparse
import pygame
from street_fighter_3rd.core.game import Game
from street_fighter_3rd.core.main_menu import MainMenu
from street_fighter_3rd.core.game_modes import GameMode, GameModeManager
from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE
from street_fighter_3rd.util.logging_config import get_logger, is_strict
from street_fighter_3rd.util.crash_handler import write_crash_report

log = get_logger(__name__)

# Window is this many times the native render resolution. Everything draws at
# SCREEN_WIDTH x SCREEN_HEIGHT, then the finished frame is scaled up to the
# window with nearest-neighbor scaling (crisp pixel art, no blur).
WINDOW_SCALE = 2


def present(render_surface, window):
    """Scale the native-resolution frame up to the window and flip."""
    pygame.transform.scale(render_surface, window.get_size(), window)
    pygame.display.flip()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Street Fighter III: 3rd Strike - Python Edition')
    
    parser.add_argument('--mode', '-m', 
                       choices=['normal', 'training', 'dev', 'versus', 'demo'],
                       default=None,
                       help='Start directly in specified game mode')
    
    parser.add_argument('--no-menu', 
                       action='store_true',
                       help='Skip main menu and start game directly')
    
    parser.add_argument('--debug', '-d',
                       action='store_true', 
                       help='Enable debug features (same as dev mode)')
    
    parser.add_argument('--training', '-t',
                       action='store_true',
                       help='Start in training mode (infinite health, hitboxes)')
    
    parser.add_argument('--hitboxes',
                       action='store_true',
                       help='Show hitboxes and hurtboxes')
    
    parser.add_argument('--infinite-health',
                       action='store_true', 
                       help='Enable infinite health')
    
    parser.add_argument('--no-rounds',
                       action='store_true',
                       help='Disable round system')

    parser.add_argument('--strict',
                       action='store_true',
                       help='Fail loud: crash on a frame error instead of logging + continuing')
    
    parser.add_argument('--fps',
                       type=int,
                       default=FPS,
                       help=f'Set target FPS (default: {FPS})')
    
    return parser.parse_args()


def determine_game_mode(args) -> GameMode:
    """Determine game mode from command line arguments."""
    if args.mode:
        mode_map = {
            'normal': GameMode.NORMAL,
            'training': GameMode.TRAINING,
            'dev': GameMode.DEV,
            'versus': GameMode.VERSUS,
            'demo': GameMode.DEMO
        }
        return mode_map[args.mode]
    elif args.debug:
        return GameMode.DEV
    elif args.training:
        return GameMode.TRAINING
    else:
        return GameMode.NORMAL


def apply_custom_config(game_mode_manager: GameModeManager, args):
    """Apply custom configuration from command line arguments."""
    config = game_mode_manager.get_config()
    
    if args.hitboxes:
        config.show_hitboxes = True
        config.show_hurtboxes = True
        
    if args.infinite_health:
        config.infinite_health = True
        
    if args.no_rounds:
        config.no_rounds = True


def run_menu_loop(screen, window, clock) -> tuple[bool, GameMode, GameModeManager]:
    """Run the main menu loop. Returns (should_start_game, game_mode, game_mode_manager)."""
    menu = MainMenu(screen)
    
    while True:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False, GameMode.NORMAL, menu.get_game_mode_manager()
            menu.handle_event(event)
        
        # Check menu state
        if menu.should_quit():
            return False, GameMode.NORMAL, menu.get_game_mode_manager()
        elif menu.should_start_game():
            return True, menu.get_selected_mode(), menu.get_game_mode_manager()
        
        # Render
        menu.render()
        present(screen, window)
        clock.tick(60)


def run_game_loop(screen, window, clock, game_mode_manager: GameModeManager, target_fps: int):
    """Run the main game loop with the specified configuration."""
    game = Game(screen, game_mode_manager)
    
    running = True
    while running:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    # Training mode hotkeys
                    if game_mode_manager.is_training_mode() or game_mode_manager.is_dev_mode():
                        if event.key == pygame.K_F1:
                            game_mode_manager.toggle_feature('show_hitboxes')
                            game_mode_manager.toggle_feature('show_hurtboxes')
                        elif event.key == pygame.K_F2:
                            game_mode_manager.toggle_feature('show_frame_data')
                        elif event.key == pygame.K_F3:
                            game.reset_positions()
                        elif event.key == pygame.K_r:
                            game.reset_health()
                        elif event.key == pygame.K_ESCAPE:
                            running = False  # return to menu
                        else:
                            # Forward unhandled keys (ENTER, F10/F11/F12, ...) to the game
                            game.handle_event(event)
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    else:
                        game.handle_event(event)
                else:
                    game.handle_event(event)

            # Fixed timestep: one loop iteration is one game frame
            clock.tick(target_fps)
            game.update()
            game.render()
            present(screen, window)
        except Exception as exc:
            report = write_crash_report(exc, game)
            log.exception("Frame %d crashed; report at %s", game.frame_count, report)
            if is_strict():
                raise          # dev: surface the bug immediately
            running = False     # release: leave the game loop gracefully


def main():
    """Main entry point."""
    args = parse_arguments()

    from street_fighter_3rd.util.logging_config import setup_logging
    setup_logging(strict=True if (getattr(args, "strict", False) or args.debug) else None)

    # Initialize Pygame
    pygame.init()
    
    # Initialize joystick subsystem with error handling
    try:
        pygame.joystick.init()
        log.info("Joystick subsystem initialized successfully")
    except pygame.error as e:
        log.warning("Failed to initialize joystick subsystem: %s", e)
        log.info("Continuing with keyboard-only input")

    # Create the (larger) window, plus a native-resolution surface that the
    # menu and game render into. The frame is scaled up to the window each tick.
    window = pygame.display.set_mode((SCREEN_WIDTH * WINDOW_SCALE, SCREEN_HEIGHT * WINDOW_SCALE))
    pygame.display.set_caption(WINDOW_TITLE)
    screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # Create clock for frame rate control
    clock = pygame.time.Clock()
    
    # Determine initial game mode
    initial_mode = determine_game_mode(args)
    game_mode_manager = GameModeManager(initial_mode)
    
    # Apply custom configuration from command line
    apply_custom_config(game_mode_manager, args)
    
    log.info("Starting Street Fighter III: 3rd Strike")
    log.info("Mode: %s", game_mode_manager.current_mode.name)
    log.info("Description: %s", game_mode_manager.get_mode_description())

    try:
        if args.no_menu:
            # Skip menu and start game directly
            log.info("Skipping menu, starting game directly...")
            run_game_loop(screen, window, clock, game_mode_manager, args.fps)
        else:
            # Show menu first
            while True:
                should_start, selected_mode, menu_game_mode_manager = run_menu_loop(screen, window, clock)

                if not should_start:
                    break

                # Start game with selected mode
                run_game_loop(screen, window, clock, menu_game_mode_manager, args.fps)
                
                # After game ends, return to menu
                log.info("Returning to main menu...")

    except KeyboardInterrupt:
        log.info("Game interrupted by user")
    except Exception as e:
        log.exception("Error: %s", e)
    finally:
        pygame.quit()
        log.info("Game shutdown complete")


def main_training():
    """Entry point for training mode."""
    import sys
    sys.argv = ['sf3-training', '--training', '--no-menu']
    main()


def main_dev():
    """Entry point for dev mode."""
    import sys
    sys.argv = ['sf3-dev', '--dev', '--no-menu']
    main()


if __name__ == "__main__":
    main()
