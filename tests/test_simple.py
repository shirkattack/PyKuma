#!/usr/bin/env python3
print("🎮 Simple test starting...")
import pygame
print("✅ Pygame imported")
pygame.init()
print("✅ Pygame initialized")
screen = pygame.display.set_mode((800, 600))
print("✅ Screen created")
pygame.display.set_caption("Test")
print("✅ Test complete - pygame working!")
pygame.quit()
