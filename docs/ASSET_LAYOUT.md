# Asset Layout

Canonical locations for game assets. **All of `assets/` is git-ignored** (the
sprites are Capcom's copyrighted art and can't be redistributed), as are the
extracted frame folders under `tools/sprite_extraction/`. Catalog *images* in
`docs/` are ignored too; only the catalog markdown is tracked.

## Layout

| Asset | Location | Format |
|---|---|---|
| Character flat sprites | `assets/sprites/<char>/sprite_sheets/{num}.png` | numbered PNGs (e.g. Akuma 18273–19461, Dudley 04993–06115) |
| Character raw GIFs (source) | `assets/sprites/<char>/raw_gifs/` | original GIFs, extraction source |
| Per-move animation folders | `tools/sprite_extraction/<char>_animations/<move>/frame_NNN.png` | sequential frames + a `description.txt` label |
| In-game effects | `assets/vfx/ingame_effects/<category>/{num}.png` | numbered PNGs, sparse (gaps delimit sequences) |
| Stages | `assets/stages/` | backgrounds |
| Intro banner | `assets/intro/intro_N.png` | menu intro frames |
| Character-select art | `assets/select/` | portraits `1.gif`–`20.gif`, nameplates `n1`–`n20.png`, chrome (`bg`, `interface`, `selector`…), `select/new/` alts |
| Sounds | `assets/sounds/` | audio |

## Effect categories (`assets/vfx/ingame_effects/`)

`hitsparks` (374), `fireballs` (114), `fire_ice_shock` (122), `ground` (159),
`misc` (128), `qcat` (52), `qmouse` (70), `shadow` (45), `superart` (75),
`dizzies` (28). Numbering is sparse — gaps separate individual effect sequences.
Only the 4 hitspark ranges hardcoded in `systems/vfx.py` are currently wired in.

## Conventions

- A new character follows the Akuma pattern: flat numbered sprites under
  `assets/sprites/<char>/sprite_sheets/`, optional per-move folders under
  `tools/sprite_extraction/<char>_animations/`. Note each character may need its
  own `sprite_scale` / `feet_offset` (Akuma's are tuned to its sprite sizes).
- Catalog any sprite set with the auditor, e.g.:
  ```
  SDL_VIDEODRIVER=dummy uv run python scripts/audit_animations.py --folder <path>
  SDL_VIDEODRIVER=dummy uv run python scripts/audit_animations.py --range assets/sprites/dudley/sprite_sheets 4993 6115 --segment --catalog dudley
  SDL_VIDEODRIVER=dummy uv run python scripts/audit_animations.py --all-effects
  ```
  Output: `docs/asset_catalog/<set>/*.png` (ignored) + `docs/asset_catalog/<SET>.md` (tracked).
