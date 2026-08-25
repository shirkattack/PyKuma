# Developer Scripts

Utilities for working on the engine. **To play**, run `uv run sf3-menu`
(`sf3-training` / `sf3-dev` skip the menu). The old `demo_*.py` scripts were
removed — they imported modules that no longer exist; git history has them.

### `animation_contact_sheets.py`
Renders every registered animation as a labeled filmstrip (`docs/animation_audit/`,
git-ignored) and regenerates the reference table `docs/ANIMATIONS.md`. Red cell =
size-outlier frame to review; orange `MISSING` = no source art. Also catalogs
arbitrary sprite sets (`--folder`, `--range`, `--all-effects`; see
`docs/ASSET_LAYOUT.md`). Needs the (git-ignored) `assets/` tree.
```bash
SDL_VIDEODRIVER=dummy uv run python scripts/animation_contact_sheets.py
```
Not to be confused with `tools/framelab/audit_animations.py`, which is the
static *timing* audit (animation length vs ROM totals -> `bugs/*.yaml`).

### `hud_visual_preview.py`
Opens a window and renders the HUD once so custom vs fallback graphics can be
compared by eye.
```bash
uv run python scripts/hud_visual_preview.py
```

### Joystick probe
Packaged with the engine (not in this folder): prints axes/buttons/hats of a
connected stick so bindings can be checked.
```bash
uv run python -m street_fighter_3rd.tools.joystick_probe
```

### Headless diagnostics
`tools/diagnostics/` — scripted scenarios through the real sim, replays,
montages (`docs/DIAGNOSTIC_FRAMEWORK.md`).
