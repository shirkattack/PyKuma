"""Generate a diagnostic dev stage background at the exact world size.

Draws the gameplay reference lines (floor / feet / walls / center / start
marks) and a labelled x-ruler so on-screen positioning can be read directly.
Not art -- a positioning aid. Regenerate after changing world/camera constants:

    uv run python tools/dev/make_dev_bg.py

Writes assets/backgrounds/dev-grid.png. Because backgrounds load
alphabetically-first, `dev-grid.png` sorts ahead of `izakaya-stage.png` and
becomes the active stage while present; delete/rename it to fall back.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
from street_fighter_3rd.data.constants import (
    WORLD_WIDTH, WORLD_HEIGHT, STAGE_FLOOR, CAMERA_GROUND_Y,
    STAGE_LEFT_BOUND, STAGE_RIGHT_BOUND,
)
# Round-start X positions live in core.game (module-level); mirror them here.
P1_START_X, P2_START_X = 648, 888  # keep in sync with core/game.py

pygame.init()
pygame.display.set_mode((1, 1))
surf = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT))
font = pygame.font.SysFont("monospace", 14, bold=True)
big = pygame.font.SysFont("monospace", 20, bold=True)

SKY_TOP, SKY_BOT = (28, 32, 46), (44, 40, 60)
GROUND = (58, 46, 40)
MARGIN_SHADE = (0, 0, 0)
C_WALL = (220, 70, 70)
C_CENTER = (90, 210, 120)
C_FLOOR = (230, 90, 200)     # STAGE_FLOOR (.y reference)
C_FEET = (90, 210, 230)      # CAMERA_GROUND_Y (feet line)
C_START = (240, 210, 90)
C_GRID = (70, 74, 92)

def label(text, x, y, color=(230, 230, 230), center=False, f=font):
    t = f.render(text, True, color)
    r = t.get_rect()
    if center: r.midtop = (x, y)
    else: r.topleft = (x, y)
    bg = pygame.Surface((r.w + 6, r.h + 2)); bg.set_alpha(150); bg.fill((0, 0, 0))
    surf.blit(bg, (r.x - 3, r.y - 1)); surf.blit(t, r)

# sky gradient
for y in range(WORLD_HEIGHT):
    f = y / WORLD_HEIGHT
    col = tuple(int(SKY_TOP[i] + (SKY_BOT[i] - SKY_TOP[i]) * f) for i in range(3))
    pygame.draw.line(surf, col, (0, y), (WORLD_WIDTH, y))
# ground band below the feet line
pygame.draw.rect(surf, GROUND, (0, CAMERA_GROUND_Y, WORLD_WIDTH, WORLD_HEIGHT - CAMERA_GROUND_Y))
# floor hatch so horizontal scroll is visible
for x in range(0, WORLD_WIDTH, 32):
    pygame.draw.line(surf, (48, 38, 34), (x, CAMERA_GROUND_Y), (x, WORLD_HEIGHT), 1)

# vertical reference grid every 128px + x labels along the top
for x in range(0, WORLD_WIDTH + 1, 128):
    pygame.draw.line(surf, C_GRID, (x, 0), (x, WORLD_HEIGHT), 1)
    label(str(x), min(x, WORLD_WIDTH - 30), 4, (150, 156, 176))

# scroll-margin shading (outside the walls)
for (x0, x1) in [(0, STAGE_LEFT_BOUND), (STAGE_RIGHT_BOUND, WORLD_WIDTH)]:
    shade = pygame.Surface((x1 - x0, WORLD_HEIGHT)); shade.set_alpha(90); shade.fill(MARGIN_SHADE)
    surf.blit(shade, (x0, 0))
label("SCROLL MARGIN", STAGE_LEFT_BOUND // 2, WORLD_HEIGHT // 2, (170, 170, 170), center=True)
label("SCROLL MARGIN", (STAGE_RIGHT_BOUND + WORLD_WIDTH) // 2, WORLD_HEIGHT // 2, (170, 170, 170), center=True)

# horizontal reference lines
pygame.draw.line(surf, C_FLOOR, (0, STAGE_FLOOR), (WORLD_WIDTH, STAGE_FLOOR), 2)
label(f"STAGE_FLOOR (.y) y={STAGE_FLOOR}", 8, STAGE_FLOOR - 20, C_FLOOR)
pygame.draw.line(surf, C_FEET, (0, CAMERA_GROUND_Y), (WORLD_WIDTH, CAMERA_GROUND_Y), 3)
label(f"FEET / CAMERA_GROUND_Y y={CAMERA_GROUND_Y}", 8, CAMERA_GROUND_Y + 4, C_FEET)

# vertical reference lines: walls, center, starts
for x, col, txt in [
    (STAGE_LEFT_BOUND, C_WALL, f"WALL {STAGE_LEFT_BOUND}"),
    (STAGE_RIGHT_BOUND, C_WALL, f"WALL {STAGE_RIGHT_BOUND}"),
    (WORLD_WIDTH // 2, C_CENTER, f"CENTER {WORLD_WIDTH // 2}"),
]:
    pygame.draw.line(surf, col, (x, 0), (x, WORLD_HEIGHT), 2)
    label(txt, x, 24, col, center=True)
for x, txt in [(P1_START_X, f"P1 {P1_START_X}"), (P2_START_X, f"P2 {P2_START_X}")]:
    pygame.draw.line(surf, C_START, (x, STAGE_FLOOR - 40), (x, WORLD_HEIGHT), 1)
    # feet marker at the start position
    pygame.draw.circle(surf, C_START, (x, CAMERA_GROUND_Y), 5)
    label(txt, x, CAMERA_GROUND_Y - 24, C_START, center=True)

label(f"DEV GRID  world {WORLD_WIDTH}x{WORLD_HEIGHT}", WORLD_WIDTH // 2, WORLD_HEIGHT - 26, (235, 235, 235), center=True, f=big)

out = "assets/backgrounds/dev-grid.png"
pygame.image.save(surf, out)
print(f"wrote {out} ({WORLD_WIDTH}x{WORLD_HEIGHT})")
