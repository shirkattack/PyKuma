# Demo Assets

## Generating demo.gif

To create `demo.gif` for the README:

1. Run Training Mode: `uv run sf3`
2. Record 5-10 seconds showing:
   - Movement, attacks, special moves
   - Hitbox visualization
3. Convert to GIF (keep under 5MB):
   ```bash
   # Using FFmpeg
   ffmpeg -i recording.mp4 -vf "fps=15,scale=640:-1:flags=lanczos" demo.gif
   ```

## Guidelines

- Show impressive features (hitboxes, parry, special moves)
- Keep short (5-10 seconds), looped
- Use Training Mode for clean background
- Enable hitbox display for technical depth

---

*Contributors: Replace `demo.gif` with better recordings as the engine improves!*
