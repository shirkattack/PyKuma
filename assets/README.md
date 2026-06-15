# Assets

This is the **one canonical home** for every game asset: character art, stages,
effects, intro/menu art, sounds, and misc data. Nothing game-facing should load
art from anywhere else (no `tools/…`, no `public/…`, no scattered copies).

## Ownership

The contents of this tree are the project owner's **licensed / paid resources**.
They are theirs to use. Treat them as first-class:

- **Never delete** an asset file. Consolidate or reorganize by **moving** it
  (`mv`), never `rm`. Moves are reversible; deletes are not.
- When importing from the owner's machine (e.g. `~/Downloads/...`), **copy in**
  and leave the originals untouched.
- The entire tree is **gitignored** (copyrighted Capcom sprites), so these files
  live on disk only and are not in version control. This README is the one
  tracked file here (via a `.gitignore` negation) so the layout + this note stay
  in the repo. "Missing from git" does **not** mean "deleted" — it's by design.

## Layout

```
assets/
  characters/<name>/
    animations/      one PNG-sequence folder per move (frame_000.png, …)
    sprite_sheets/   numbered sprite frames (projectiles, fx, legacy numbered loader)
    raw_gifs/        source gifs the frames were extracted from
  stages/            stage backgrounds (e.g. ryu-stage.gif)
  vfx/ingame_effects/  hit sparks and other in-game effects
  intro/             menu / intro art (intro_*.png)
  sounds/            audio
  data/              misc data
  sprites/           legacy loose numbered sprites (pre-consolidation; unused)
```

Akuma's animations were consolidated here from
`tools/sprite_extraction/akuma_animations/`, and his sprite sheets / raw gifs
from `assets/sprites/akuma/`. The extraction **scripts** remain under
`tools/sprite_extraction/` (they are code, not assets).

## How loaders find these files

All asset paths are stored **repo-relative** (e.g.
`"assets/characters/akuma/animations"`) and resolved against the repo root by
`street_fighter_3rd.util.assets` (`ASSETS_ROOT`, `resolve_asset`, `asset_path`),
so the game loads the same files regardless of the working directory it is
launched from. Point any new loader through that helper.
