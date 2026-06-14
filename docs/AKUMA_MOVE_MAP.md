# Akuma (Gouki) ROM Pointer → Move Map

Authoritative mapping of SF3:3S ROM move-script pointers to move names for Akuma
(`gouki`, rev `sfiii3nr1`). Generated from the vendored frame data; do not hand-edit —
regenerate from the sources below.

**Sources**
- `framedata_meta.lua` — Grouflon/3rd_training_lua authoritative name table (meta)
- Baston ESN3S (`ensabahnur.free.fr`, iChar=14) — active-box cross-match for standing normals
- Box geometry/timing — vendored `data/sources/gouki_framedata.json`

Coordinates are PyKuma offsets (origin at feet, +x = forward, -y = up): attack box shown as
`(offset_x, offset_y, w, h)` of the first active frame. `start/active/total` in frames.

## PyKuma game states (verified)

| PyKuma state | Pointer | Move | Source | start/active/total | active box |
|---|---|---|---|---|---|
| LIGHT_PUNCH | `1438` | st.LP | meta | 4/3/14 | (32, -80, 36, 8) |
| MEDIUM_PUNCH | `14e8` | st.MP | Baston | 5/4/22 | (32, -66, 24, 18) |
| HEAVY_PUNCH | `1818` | st.HP | meta | 8/5/38 | (42, -70, 50, 12) |
| LIGHT_KICK | `1908` | st.LK | Baston | 4/4/19 | (34, -24, 38, 10) |
| MEDIUM_KICK | `1988` | st.MK | Baston | 4/5/23 | (36, -78, 24, 20) |
| HEAVY_KICK | `1b08` | cl.HK | meta | 5/8/39 | (34, -118, 12, 46) |
| CROUCH_HEAVY_KICK | `20d8` | cr.HK | meta | 7/5/41 | (22, -12, 68, 12) |

## All gouki ground/air/special pointers

| Pointer | Name (meta) | PyKuma state | start/active/total | active box |
|---|---|---|---|---|
| `13a8` | — |  | 3/3/15 | (32, -92, 14, 22) |
| `1438` | LP | LIGHT_PUNCH | 4/3/14 | (32, -80, 36, 8) |
| `14e8` | — | MEDIUM_PUNCH | 5/4/22 | (32, -66, 24, 18) |
| `1598` | — |  | 5/4/24 | (62, -80, 18, 16) |
| `1638` | Forward MP |  | 14/2/42 | (54, -72, 24, 14) |
| `1728` | — |  | 4/4/34 | (38, -90, 30, 24) |
| `1818` | — | HEAVY_PUNCH | 8/5/38 | (42, -70, 50, 12) |
| `1908` | — | LIGHT_KICK | 4/4/19 | (34, -24, 38, 10) |
| `1988` | — | MEDIUM_KICK | 4/5/23 | (36, -78, 24, 20) |
| `1a38` | — |  | 5/5/30 | (18, -54, 42, 10) |
| `1b08` | Close HK | HEAVY_KICK | 5/8/39 | (34, -118, 12, 46) |
| `1bf8` | — |  | 9/5/40 | (62, -104, 24, 18) |
| `1d28` | — |  | 4/3/15 | (26, -52, 44, 8) |
| `1dd8` | — |  | 5/4/22 | (60, -52, 16, 14) |
| `1e88` | — |  | 5/5/35 | (28, -64, 32, 32) |
| `1f68` | Cr LK |  | 5/3/19 | (28, -8, 52, 8) |
| `2008` | Cr MK |  | 6/5/31 | (70, -10, 16, 10) |
| `20d8` | Cr HK | CROUCH_HEAVY_KICK | 7/5/41 | (22, -12, 68, 12) |
| `21c8` | Straight Air LP |  | 4/26/30 | (28, -72, 24, 12) |
| `22a8` | Air MP |  | 5/5/31 | (56, -78, 20, 16) |
| `2388` | Straight Air HP |  | 7/3/39 | (34, -100, 50, 10) |
| `2448` | Straight Air LK |  | 4/19/35 | (22, -50, 24, 14) |
| `2558` | Straight Air MK |  | 5/6/22 | (70, -70, 18, 16) |
| `2628` | Straight Air HK |  | 6/5/31 | (60, -100, 22, 18) |
| `2708` | Air LP |  | 4/28/32 | (28, -72, 24, 12) |
| `2800` | Air HP |  | 6/4/24 | (54, -64, 22, 18) |
| `28e0` | Air LK |  | 4/10/18 | (22, -50, 24, 14) |
| `29c0` | Air MK |  | 5/6/21 | (68, -68, 16, 16) |
| `2aa0` | Air Down MK |  | 8/12/20 | (42, -34, 12, 10) |
| `2b30` | Air HK |  | 6/4/22 | (64, -56, 24, 16) |
| `84f8` | — |  | 3/14/35 | (24, -74, 40, 32) |
| `85c8` | — |  | 2/7/19 | (24, -74, 40, 32) |
| `8658` | — |  | 1/23/24 | (22, -54, 38, 32) |
| `86e8` | — |  | 11/4/24 | (54, -70, 22, 12) |
| `87f8` | — |  | 2/10/30 | (24, -72, 26, 22) |
| `8968` | — |  | 2/18/38 | (24, -72, 26, 22) |
| `9618` | — |  | 5/3/18 | (54, -70, 22, 12) |
| `9738` | — |  | 5/6/18 | (54, -70, 22, 12) |
| `9818` | — |  | 5/9/26 | (54, -70, 22, 12) |
| `98f8` | UOH |  | 15/8/25 | (26, -46, 44, 18) |
| `af08` | Demon flip |  | 40/15/71 | (57, -13, 19, 13) |
| `b118` | Demon flip P cancel |  | 10/3/18 | (42, -47, 24, 17) |
| `b218` | Demon flip K cancel |  | 9/11/20 | (36, -23, 14, 11) |

> Pointers with no meta name and no PyKuma state are other moves (close variants, command
> normals, specials) not yet individually identified; geometry/timing are ROM-accurate.
