"""Main entry point for Street Fighter Third Strike Python Edition."""

import sys
import pygame
from street_fighter_3rd.core.game import Game
from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, WINDOW_TITLE


def main():
    """Initialize and run the game."""
    pygame.init()
    
    # Initialize joystick subsystem explicitly with error handling
    try:
        pygame.joystick.init()
        print(f"Joystick subsystem initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize joystick subsystem: {e}")
        print("Continuing with keyboard-only input")

    # Create game window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)

    # Create clock for frame rate control
    clock = pygame.time.Clock()

    # Initialize game
    game = Game(screen)

    # Main game loop
    running = True
    while running:
        # Handle events
        try:
            # Clear any problematic events first
            pygame.event.pump()
            events = []
            try:
                events = pygame.event.get()
            except Exception as e:
                print(f"Warning: Error getting events: {e}")
                # Try to clear the event queue
                try:
                    pygame.event.clear()
                except:
                    pass
                continue
            
            for event in events:
                try:
                    if event.type == pygame.QUIT:
                        running = False
                    else:
                        game.handle_event(event)
                except Exception as e:
                    print(f"Warning: Error handling event {event.type}: {e}")
                    continue
        except Exception as e:
            print(f"Warning: Critical error in event processing: {e}")
            # Try to recover by clearing events
            try:
                pygame.event.clear()
            except:
                pass
            continue

        # Fixed time step (60 FPS)
        dt = clock.tick(FPS) / 1000.0

        # Update game state
        game.update(dt)

        # Render
        game.render()

        # Update display
        pygame.display.flip()

    # Cleanup
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
