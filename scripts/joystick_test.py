#!/usr/bin/env python3
"""Joystick diagnostic tool - shows real-time button presses and directions."""

import pygame
import sys

def main():
    pygame.init()
    pygame.joystick.init()
    
    # Create a small window for the diagnostic
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Joystick Diagnostic Tool")
    font = pygame.font.Font(None, 24)
    clock = pygame.time.Clock()
    
    # Check for joysticks
    joystick_count = pygame.joystick.get_count()
    print(f"Found {joystick_count} joystick(s)")
    
    if joystick_count == 0:
        print("No joysticks detected. Connect a controller and restart.")
        return
    
    # Initialize the first joystick
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    
    print(f"Joystick: {joystick.get_name()}")
    print(f"Buttons: {joystick.get_numbuttons()}")
    print(f"Axes: {joystick.get_numaxes()}")
    print(f"Hats: {joystick.get_numhats()}")
    print("\nPress buttons and move directions to see mapping...")
    print("Press ESC to exit")
    
    # Street Fighter button mapping for reference
    sf_mapping = {
        0: "Light Punch", 1: "Medium Punch", 2: "Heavy Punch",
        3: "Light Kick", 4: "Medium Kick", 5: "Heavy Kick",
        6: "Up?", 7: "Down?", 8: "Right?", 9: "Left?",
        10: "Up?", 11: "Down?", 12: "Right?", 13: "Left?",
        14: "Up?", 15: "Down?", 16: "Left?", 17: "Right?"
    }
    
    running = True
    last_buttons = set()
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Clear screen
        screen.fill((0, 0, 0))
        y_offset = 20
        
        # Title
        title = font.render("Street Fighter Joystick Diagnostic", True, (255, 255, 255))
        screen.blit(title, (20, y_offset))
        y_offset += 40
        
        # Show joystick info
        info = font.render(f"Controller: {joystick.get_name()}", True, (200, 200, 200))
        screen.blit(info, (20, y_offset))
        y_offset += 30
        
        # Check all buttons
        pressed_buttons = []
        for i in range(joystick.get_numbuttons()):
            try:
                if joystick.get_button(i):
                    pressed_buttons.append(i)
            except:
                pass
        
        # Show currently pressed buttons
        if pressed_buttons:
            buttons_text = font.render("Pressed Buttons:", True, (255, 255, 0))
            screen.blit(buttons_text, (20, y_offset))
            y_offset += 25
            
            for btn in pressed_buttons:
                sf_name = sf_mapping.get(btn, f"Button {btn}")
                btn_text = font.render(f"  Button {btn}: {sf_name}", True, (0, 255, 0))
                screen.blit(btn_text, (40, y_offset))
                y_offset += 20
        else:
            no_buttons = font.render("No buttons pressed", True, (128, 128, 128))
            screen.blit(no_buttons, (20, y_offset))
            y_offset += 25
        
        y_offset += 20
        
        # Check axes (analog stick/d-pad)
        axes_text = font.render("Axes (Analog/D-pad):", True, (255, 255, 0))
        screen.blit(axes_text, (20, y_offset))
        y_offset += 25
        
        for i in range(joystick.get_numaxes()):
            try:
                value = joystick.get_axis(i)
                if abs(value) > 0.1:  # Only show if significant movement
                    axis_text = font.render(f"  Axis {i}: {value:.2f}", True, (0, 255, 255))
                    screen.blit(axis_text, (40, y_offset))
                    y_offset += 20
            except:
                pass
        
        y_offset += 20
        
        # Check hats (d-pad)
        if joystick.get_numhats() > 0:
            hats_text = font.render("D-pad (Hat):", True, (255, 255, 0))
            screen.blit(hats_text, (20, y_offset))
            y_offset += 25
            
            for i in range(joystick.get_numhats()):
                try:
                    hat_value = joystick.get_hat(i)
                    if hat_value != (0, 0):
                        hat_text = font.render(f"  Hat {i}: {hat_value}", True, (255, 0, 255))
                        screen.blit(hat_text, (40, y_offset))
                        y_offset += 20
                except:
                    pass
        
        # Show instructions
        y_offset += 40
        instructions = [
            "Street Fighter Button Layout:",
            "0=LP  1=MP  2=HP",
            "3=LK  4=MK  5=HK", 
            "",
            "Direction buttons (hitbox):",
            "6,10,14=Up  7,11,15=Down",
            "8,12,16=Right  9,13,17=Left",
            "",
            "Press ESC to exit"
        ]
        
        for instruction in instructions:
            inst_text = font.render(instruction, True, (180, 180, 180))
            screen.blit(inst_text, (20, y_offset))
            y_offset += 20
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()
