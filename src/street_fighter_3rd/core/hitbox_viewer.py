"""
Frame-step hitbox viewer — the data-verification tool.

Pick a move, step it frame-by-frame, and see the hitboxes/hurtboxes from the canonical
loader (data/frame_data_loader.py) drawn over Akuma's sprite, alongside a data panel and
the move's PROVENANCE tag. This is how unverified placeholder boxes get visually confirmed
against the game and flipped to `verified` (see scripts/baston_to_yaml.py, Phase 3).

Boxes are anchored to the sprite's FEET line (character.y + feet_offset), which is where the
box coordinate system's "ground" sits — so correct data lands on the limb. The viewer reads
ONLY the canonical loader; it never invents numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pygame

from ..data.constants import SCREEN_WIDTH, SCREEN_HEIGHT, STAGE_FLOOR
from ..data.enums import CharacterState, FacingDirection
from ..characters.akuma import Akuma
from ..data.frame_data_loader import get_character_frames, get_hitboxes, get_hurtboxes

# Box colours: hitboxes red, hurtboxes blue (matches the in-game debug overlay).
_COL_HIT = (255, 60, 60)
_COL_HURT = (60, 120, 255)
_COL_GROUND = (90, 90, 90)
_COL_ORIGIN = (255, 255, 0)
_COL_BG = (24, 24, 32)
_COL_PANEL = (240, 240, 240)
_COL_DIM = (150, 150, 150)
# Provenance tag colours.
_PROV_COL = {"verified": (60, 220, 90), "unverified": (240, 70, 70), "derived": (240, 200, 60)}


@dataclass
class _MoveEntry:
    key: str          # frames.yaml slug
    state: CharacterState
    name: str
    command: Optional[str]
    startup: int
    active: List[int]
    recovery: int
    on_hit: int
    on_block: int
    provenance_status: str
    provenance_source: Optional[str]
    provenance_imove: Optional[int]

    @property
    def total_frames(self) -> int:
        # startup + active window + recovery. At least 1 so stepping never divides by zero.
        return max(1, self.startup + len(self.active) + self.recovery)

    def phase(self, frame: int) -> str:
        if frame <= self.startup:
            return "STARTUP"
        if frame <= self.startup + len(self.active):
            return "ACTIVE"
        return "RECOVERY"


def _load_move_entries(character: str = "akuma") -> List[_MoveEntry]:
    """Build the ordered move list from the canonical loader (insertion order = yaml order)."""
    entries: List[_MoveEntry] = []
    for key, mf in get_character_frames(character).moves.items():
        entries.append(_MoveEntry(
            key=key, state=CharacterState[mf.state], name=mf.name, command=mf.command,
            startup=mf.startup, active=list(mf.active), recovery=mf.recovery,
            on_hit=mf.on_hit, on_block=mf.on_block,
            provenance_status=mf.provenance.status,
            provenance_source=mf.provenance.source,
            provenance_imove=mf.provenance.imove,
        ))
    return entries


class HitboxViewer:
    """Headless-constructable controller for the frame-step viewer.

    The pygame run loop (run_hitbox_viewer) translates key events into the public
    methods below; everything here is testable without a real window.
    """

    PLAY_FRAME_TICKS = 6  # hold each frame this many 60fps ticks when playing (~10 fps)

    def __init__(self, screen: pygame.Surface, character: str = "akuma"):
        self.screen = screen
        self.character_name = character
        self.moves = _load_move_entries(character)
        if not self.moves:
            raise ValueError(f"no moves found for '{character}' in canonical frames.yaml")

        self.move_index = 0
        self.frame = 1               # 1-indexed gameplay frame
        self.playing = False
        self._play_counter = 0

        # One Akuma, centred and facing right (yaml offsets are facing-forward).
        self.character = Akuma(x=SCREEN_WIDTH // 2, y=STAGE_FLOOR, player_number=1)
        self.character.facing = FacingDirection.RIGHT
        self.feet_offset = getattr(self.character, "feet_offset", 0)

        if not pygame.font.get_init():
            pygame.font.init()
        self.font = pygame.font.Font(None, 26)
        self.font_small = pygame.font.Font(None, 20)
        self._text_cache = {}

    # --- model / navigation -------------------------------------------------

    @property
    def current(self) -> _MoveEntry:
        return self.moves[self.move_index]

    def select_move(self, index: int) -> None:
        self.move_index = index % len(self.moves)
        self.frame = 1
        self._play_counter = 0

    def next_move(self) -> None:
        self.select_move(self.move_index + 1)

    def prev_move(self) -> None:
        self.select_move(self.move_index - 1)

    def step(self, delta: int) -> None:
        """Advance the gameplay frame by delta, wrapping within [1, total]."""
        self.playing = False
        total = self.current.total_frames
        self.frame = (self.frame - 1 + delta) % total + 1

    def toggle_play(self) -> None:
        self.playing = not self.playing
        self._play_counter = 0

    def update(self) -> None:
        """One 60fps tick; advances the frame when playing."""
        if not self.playing:
            return
        self._play_counter += 1
        if self._play_counter >= self.PLAY_FRAME_TICKS:
            self._play_counter = 0
            total = self.current.total_frames
            self.frame = self.frame % total + 1

    # --- panel text (pure; asserted by tests) -------------------------------

    def provenance_label(self) -> str:
        m = self.current
        if m.provenance_status == "verified":
            tag = "VERIFIED ✓"
            if m.provenance_imove is not None:
                tag += f" (Baston iMove={m.provenance_imove})"
            return tag
        if m.provenance_status == "derived":
            return "DERIVED (computed)"
        return "UNVERIFIED — placeholder, not from the game"

    # --- rendering ----------------------------------------------------------

    def _ground_y(self) -> int:
        return int(self.character.y) + self.feet_offset

    def _set_sprite_frame(self) -> None:
        """Drive the character's animation to roughly match the gameplay frame."""
        anim_name = getattr(Akuma, "_STATE_ANIM", {}).get(self.current.state)
        if not anim_name:
            return
        controller = getattr(self.character, "animation_controller", None)
        if controller is None:
            return
        try:
            controller.play_animation(anim_name)
        except Exception:
            return
        anim = getattr(controller, "current_animation", None)
        frames = getattr(anim, "frames", None)
        if not frames:
            return
        total = self.current.total_frames
        progress = (self.frame - 1) / max(1, total - 1)
        idx = min(len(frames) - 1, max(0, round(progress * (len(frames) - 1))))
        anim.current_frame_index = idx

    def _draw_box(self, box, color: tuple, *, centered: bool) -> None:
        ground_y = self._ground_y()
        left = int(self.character.x + box.offset_x)
        if centered:
            left -= box.width // 2
        rect = pygame.Rect(left, ground_y + box.offset_y, box.width, box.height)
        pygame.draw.rect(self.screen, color, rect, 2)

    def _text(self, font, text, color):
        key = (id(font), text, color)
        surf = self._text_cache.get(key)
        if surf is None:
            surf = font.render(text, True, color)
            self._text_cache[key] = surf
        return surf

    def render(self) -> None:
        self.screen.fill(_COL_BG)
        ground_y = self._ground_y()

        # Ground line + origin crosshair so box anchoring is legible.
        pygame.draw.line(self.screen, _COL_GROUND, (0, ground_y), (SCREEN_WIDTH, ground_y), 1)
        cx = int(self.character.x)
        pygame.draw.line(self.screen, _COL_ORIGIN, (cx, ground_y - 6), (cx, ground_y + 6), 1)

        # Sprite (behind boxes).
        self._set_sprite_frame()
        try:
            self.character.render(self.screen)
        except Exception:
            pass  # missing art shouldn't kill the viewer; boxes still verify the data

        m = self.current
        # Hurtboxes (centred on origin), then active hitboxes (left-anchored at offset_x).
        for hb in get_hurtboxes(m.state, self.character_name):
            self._draw_box(hb, _COL_HURT, centered=True)
        for hb in get_hitboxes(m.state, self.frame, self.character_name):
            self._draw_box(hb, _COL_HIT, centered=False)

        self._render_panel()

    def _render_panel(self) -> None:
        x, y = 12, 10
        self.screen.blit(self._text(self.font, self.current.name, _COL_PANEL), (x, y))
        y += 28
        cmd = f"  [{self.current.command}]" if self.current.command else ""
        info = [
            f"Frame {self.frame} / {self.current.total_frames}    {self.current.phase(self.frame)}{cmd}",
            f"startup {self.current.startup}   active {len(self.current.active)}   recovery {self.current.recovery}",
            f"on-hit {self.current.on_hit:+d}   on-block {self.current.on_block:+d}",
        ]
        boxes = get_hitboxes(self.current.state, self.frame, self.character_name)
        info.append(f"damage {boxes[0].damage}" if boxes else "damage — (not active)")
        for line in info:
            self.screen.blit(self._text(self.font_small, line, _COL_DIM), (x, y))
            y += 20

        # Provenance tag — the on-screen "visibly mark" enforcement point.
        col = _PROV_COL.get(self.current.provenance_status, _COL_PANEL)
        self.screen.blit(self._text(self.font, self.provenance_label(), col), (x, y + 4))

        help_line = "[←→] move   [, .] step frame   [space] play/pause   [esc] quit"
        self.screen.blit(self._text(self.font_small, help_line, _COL_DIM), (x, SCREEN_HEIGHT - 24))


def run_hitbox_viewer(screen: pygame.Surface, window: pygame.Surface, clock, target_fps: int = 60):
    """Run the viewer loop (mirrors main_with_menu.run_game_loop)."""
    from ..main_with_menu import present  # local import to avoid a cycle at module load

    viewer = HitboxViewer(screen)
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE,):
                    running = False
                elif event.key in (pygame.K_RIGHT, pygame.K_RIGHTBRACKET):
                    viewer.next_move()
                elif event.key in (pygame.K_LEFT, pygame.K_LEFTBRACKET):
                    viewer.prev_move()
                elif event.key in (pygame.K_PERIOD, pygame.K_d):
                    viewer.step(+1)
                elif event.key in (pygame.K_COMMA, pygame.K_a):
                    viewer.step(-1)
                elif event.key == pygame.K_SPACE:
                    viewer.toggle_play()

        clock.tick(target_fps)
        viewer.update()
        viewer.render()
        present(screen, window)
