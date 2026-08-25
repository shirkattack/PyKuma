"""Quick visual test of the new HUD rendering."""

import pygame
import sys
from street_fighter_3rd.core.game import Game
from street_fighter_3rd.data.constants import SCREEN_WIDTH, SCREEN_HEIGHT

def main():
    """Run a quick visual test of the HUD."""
    pygame.init()

    # Create window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("HUD Test")
    clock = pygame.time.Clock()

    # Initialize game
    game = Game(screen)

    print(f"HUD assets loaded: {len(game.hud_assets)}")
    if game.hud_assets:
        print("Using custom HUD graphics")
    else:
        print("Using fallback HUD rendering")

    # Simulate some damage for visual testing
    game.player1.health = int(game.player1.max_health * 0.7)  # 70% health
    game.player2.health = int(game.player2.max_health * 0.5)  # 50% health
    game.p1_ghost_health = game.player1.max_health  # Show chip damage
    game.p2_ghost_health = int(game.player2.max_health * 0.8)  # Show chip damage

    # Set some super meter
    game.player1.super_meter = 0.6  # 60% meter
    game.player2.super_meter = 1.0   # Full meter

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Toggle damage for testing
                    if game.player1.health > 0:
                        game.player1.health = max(0, game.player1.health - 100)
                    else:
                        game.player1.health = game.player1.max_health
                        game.p1_ghost_health = game.player1.max_health

        # Render game
        game.render()
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)

if __name__ == "__main__":
    main()
