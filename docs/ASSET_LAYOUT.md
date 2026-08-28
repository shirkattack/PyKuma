# Asset Layout

Canonical locations for game assets. **All of `assets/` is git-ignored** (the
sprites are Capcom's copyrighted art and can't be redistributed); only
`assets/README.md` is tracked. Catalog *images* in `docs/` are ignored too; only
the catalog markdown is tracked.

## Layout

| Asset | Location | Format |
|---|---|---|
| **ROM cels (primary)** | `assets/characters/<char>/rom_cels/cel_<id>.png` | sprites ripped from the game's memory (`tools/rom_extract/cel_decode.py`), keyed by ROM cel id; placed and timed by `data/characters/<char>/rom_animations.json`; used for every move whose sequence is complete |
| Legacy per-move folders (fallback) | `assets/characters/<char>/legacy/animations/<move>/frame_NNN.png` | zweifuss frames + a `description.txt` label — the fallback clip when a move has no complete ROM sequence (`characters/akuma.py` `ANIM_BASE`) |
| Legacy flat sprites | `assets/characters/<char>/legacy/sprite_sheets/{num}.png` | numbered PNGs (Akuma 18273–19461); projectile art |
| Legacy raw GIFs (source) | `assets/characters/<char>/legacy/raw_gifs/` | original GIFs the folders were extracted from |
| In-game effects | `assets/vfx/ingame_effects/<category>/{num}.png` | numbered PNGs, sparse (gaps delimit sequences) |
| Stages | `assets/backgrounds/` (fallback `assets/stages/`) | backgrounds |
| Intro banner | `assets/intro/intro_N.png` | menu intro frames |
| Input-display icons | `assets/ui/inputs/` | vendored from 3rd_training_lua (see its PROVENANCE.md) |
| Character-select art | `assets/select/` | portraits, nameplates, chrome |
| Sounds | `assets/sounds/` | audio |

`tools/sprite_extraction/akuma_animations/` is an older, tracked copy of the
per-move folders that nothing reads any more; it is slated for removal.

## Effect categories (`assets/vfx/ingame_effects/`)

`hitsparks` (374), `fireballs` (114), `fire_ice_shock` (122), `ground` (159),
`misc` (128), `qcat` (52), `qmouse` (70), `shadow` (45), `superart` (75),
`dizzies` (28). Numbering is sparse — gaps separate individual effect sequences.
Six spark ranges are wired in `systems/vfx.py` (LIGHT / MEDIUM / HEAVY /
SPECIAL / BLOCK / PARRY).

## Conventions

- A new character follows the Akuma pattern under `assets/characters/<char>/`.
  Each character may need its own `sprite_scale` / `feet_offset` (Akuma's are
  tuned to its sprite sizes).
- Catalog any sprite set with the contact-sheet script, e.g.:
  ```
  SDL_VIDEODRIVER=dummy uv run python scripts/animation_contact_sheets.py --folder <path>
  SDL_VIDEODRIVER=dummy uv run python scripts/animation_contact_sheets.py --range assets/characters/dudley/sprite_sheets 4993 6115 --segment --catalog dudley
  SDL_VIDEODRIVER=dummy uv run python scripts/animation_contact_sheets.py --all-effects
  ```
  Output: `docs/asset_catalog/<set>/*.png` (ignored) + `docs/asset_catalog/<SET>.md` (tracked).
