#!/usr/bin/env python3
"""Debug script to detect hitbox button mappings."""

import pygame
import sys

def main():
    pygame.init()
    pygame.joystick.init()
    
    joystick_count = pygame.joystick.get_count()
    print(f"Detected {joystick_count} joystick(s)")
    
    if joystick_count == 0:
        print("No joysticks detected. Please connect your hitbox and try again.")
        return
    
    # Connect to first joystick
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    
    print(f"Connected to: {joystick.get_name()}")
    print(f"Number of buttons: {joystick.get_numbuttons()}")
    print(f"Number of axes: {joystick.get_numaxes()}")
    print(f"Number of hats: {joystick.get_numhats()}")
    print("\nPress buttons on your hitbox to see their numbers.")
    print("Press ESC to quit.\n")
    
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                print(f"Button {event.button} pressed")
            elif event.type == pygame.JOYBUTTONUP:
                print(f"Button {event.button} released")
        
        # Also show currently pressed buttons
        pressed_buttons = []
        for i in range(joystick.get_numbuttons()):
            if joystick.get_button(i):
                pressed_buttons.append(i)
        
        if pressed_buttons:
            print(f"Currently pressed: {pressed_buttons}")
        
        clock.tick(60)
    
    pygame.quit()

if __name__ == "__main__":
    main()
