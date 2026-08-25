"""Test utility to detect and map joystick/hitbox buttons."""

import pygame
import sys

from street_fighter_3rd.util.logging_config import get_logger

log = get_logger(__name__)


def main():
    """Test joystick input and display button mappings."""
    pygame.init()
    pygame.joystick.init()

    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Joystick/Hitbox Button Tester")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 24)

    # Check for joysticks
    joystick_count = pygame.joystick.get_count()
    log.info("%s", "="*60)
    log.info("Joysticks detected: %s", joystick_count)
    log.info("%s", "="*60)

    if joystick_count == 0:
        log.warning("No joystick detected!")
        log.warning("Please connect your Brooks UFB hitbox and restart.")
        input("\nPress Enter to exit...")
        return

    # Initialize first joystick
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    log.info("Controller Name: %s", joystick.get_name())
    log.info("Number of Axes: %s", joystick.get_numaxes())
    log.info("Number of Buttons: %s", joystick.get_numbuttons())
    log.info("Number of Hats: %s", joystick.get_numhats())
    log.info("%s", "="*60)
    log.info("Press buttons to see their numbers!")
    log.info("Press ESC to exit")
    log.info("%s", "="*60)

    # Track button states
    button_states = {}
    axis_values = {}
    hat_values = {}

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                button_states[event.button] = True
                log.info("Button %s PRESSED", event.button)
            elif event.type == pygame.JOYBUTTONUP:
                button_states[event.button] = False
                log.info("Button %s released", event.button)

        # Clear screen
        screen.fill((20, 20, 40))

        # Title
        title = font.render("Hitbox Button Tester", True, (255, 255, 255))
        screen.blit(title, (250, 20))

        # Controller info
        info_y = 80
        name_text = small_font.render(f"Controller: {joystick.get_name()}", True, (200, 200, 200))
        screen.blit(name_text, (20, info_y))

        # Button display
        y_offset = 140
        buttons_title = font.render("Buttons:", True, (255, 255, 100))
        screen.blit(buttons_title, (20, y_offset))
        y_offset += 40

        for i in range(joystick.get_numbuttons()):
            is_pressed = joystick.get_button(i)
            color = (0, 255, 0) if is_pressed else (100, 100, 100)
            text = small_font.render(f"Button {i}: {'PRESSED' if is_pressed else 'Released'}", True, color)
            screen.blit(text, (30, y_offset))
            y_offset += 30

            if y_offset > 550:  # Wrap to second column
                y_offset = 180
                break

        # Axes (for analog sticks, if any)
        if joystick.get_numaxes() > 0:
            axes_title = font.render("Axes:", True, (255, 255, 100))
            screen.blit(axes_title, (400, 140))
            y_offset = 180
            for i in range(joystick.get_numaxes()):
                value = joystick.get_axis(i)
                text = small_font.render(f"Axis {i}: {value:.3f}", True, (200, 200, 200))
                screen.blit(text, (410, y_offset))
                y_offset += 30

        # Hat (D-pad)
        if joystick.get_numhats() > 0:
            hat_y = 350 if joystick.get_numaxes() > 0 else 180
            hat_title = font.render("D-Pad/Hat:", True, (255, 255, 100))
            screen.blit(hat_title, (400, hat_y))
            for i in range(joystick.get_numhats()):
                hat_value = joystick.get_hat(i)
                text = small_font.render(f"Hat {i}: {hat_value}", True, (200, 200, 200))
                screen.blit(text, (410, hat_y + 40))

        # Instructions
        inst_text = small_font.render("Press ESC to exit", True, (150, 150, 150))
        screen.blit(inst_text, (300, 560))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
