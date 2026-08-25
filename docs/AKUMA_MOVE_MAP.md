# Akuma (Gouki) ROM Pointer → Move Map

Authoritative mapping of SF3:3S ROM move-script pointers to move names for Akuma
(`gouki`, rev `sfiii3nr1`). Generated from the vendored frame data; do not hand-edit —
regenerate from the sources below.

**Sources**
- `framedata_meta.lua` — Grouflon/3rd_training_lua authoritative name table (meta)
- Baston ESN3S (`baston.esn3s.com`, iChar=14) — active-box cross-match for standing normals;
  startup/active cross-match (frame-exact) for the specials, plus their combat tier
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
| OVERHEAD | `98f8` | UOH | meta | 15/8/25 | (26, -46, 44, 18) |
| LIGHT_PUNCH:close | `13a8` | close LP (Jab) | Baston (3/3 exact) | 3/3/15 | (32, -92, 14, 22) |
| MEDIUM_PUNCH:far | `1598` | far MP (Far Strong) | Baston (5/4; reach 80) | 5/4/24 | (62, -80, 18, 16) |
| HEAVY_PUNCH:close | `1728` | close HP (Fierce) | Baston (4/4 exact) | 4/4/34 | (38, -90, 30, 24) |
| MEDIUM_KICK:far | `1a38` | far MK (Far Forward) | Baston (5/5 exact) | 5/5/30 | (18, -54, 42, 10) |
| HEAVY_KICK:far | `1bf8` | far HK (Far Roundhouse) | Baston (9/5 exact) | 9/5/40 | (62, -104, 24, 18) |
| JUMP_LIGHT_PUNCH:neutral | `21c8` | Straight Air LP | meta | 4/26/30 | (28, -72, 24, 12) |
| JUMP_HEAVY_PUNCH:neutral | `2388` | Straight Air HP | meta | 7/3/39 | (34, -100, 50, 10) |
| JUMP_LIGHT_KICK:neutral | `2448` | Straight Air LK | meta | 4/19/35 | (22, -50, 24, 14) |
| JUMP_MEDIUM_KICK:neutral | `2558` | Straight Air MK | meta | 5/6/22 | (70, -70, 18, 16) |
| JUMP_HEAVY_KICK:neutral | `2628` | Straight Air HK | meta | 6/5/31 | (60, -100, 22, 18) |
| FORWARD_MP | `1638` | f+MP Zugai Hasatsu (overhead, 2 hits) | meta | 14/2/42 | (54, -72, 24, 14) |
| DIVE_KICK | `2aa0` | air d+MK Tenma Kujin Kyaku | meta | 8/12/20† | dives 92px fwd / 116px down (ROM movement) |
| GOSHORYUKEN:light | `84f8` | LP Goshoryuken | Baston (3/14 exact; 1 hit) | 3/14/35† | rises 56px, ROM movement |
| GOSHORYUKEN:medium | `85c8` | MP Goshoryuken | Baston (2/7 exact; 2 hits) | 2/7/19† | rises 87px (script ends mid-rise) |
| GOSHORYUKEN:heavy | `8658` | HP Goshoryuken | Baston (1/23 exact; 3 hits) | 1/23/24† | rises 124px (script ends mid-rise) |
| TATSUMAKI:light | `86e8` | LK Tatsumaki | Baston (11/4 exact; 2 windows) | 11/4/24† | spin box −64..+76, 92px travel |
| TATSUMAKI:medium | `87f8` | MK Tatsumaki | Baston (2/10 exact; 5 windows) | 2/10/30† | 130px travel |
| TATSUMAKI:heavy | `8968` | HK Tatsumaki | Baston (2/18 exact; 9 windows) | 2/18/38† | 173px travel |
| TATSUMAKI:air_light | `9618` | air LK Tatsumaki | Baston (5/3 exact) | 5/3/18† | descends |
| TATSUMAKI:air_medium | `9738` | air MK Tatsumaki | Baston (5/6 exact) | 5/6/18† | descends |
| TATSUMAKI:air_heavy | `9818` | air HK Tatsumaki | Baston (5/12 exact) | 5/12/26† | descends |

† `timing_scope: segment` — the ROM script covers the rise/spin only (fall and landing
are separate scripts the dump does not chain). The engine drives these moves from the
script's per-frame `movement` table (physics resumes when it ends) and holds the DP for
its landing recovery so the move lasts the Baston total (43/50/59). `hit_windows` come
from the dump's `hit_frames` (the ROM's distinct hit registrations).

## All gouki ground/air/special pointers

| Pointer | Name (meta) | PyKuma state | start/active/total | active box |
|---|---|---|---|---|
| `13a8` | — | LIGHT_PUNCH:close | 3/3/15 | (32, -92, 14, 22) |
| `1438` | LP | LIGHT_PUNCH | 4/3/14 | (32, -80, 36, 8) |
| `14e8` | — | MEDIUM_PUNCH | 5/4/22 | (32, -66, 24, 18) |
| `1598` | — | MEDIUM_PUNCH:far | 5/4/24 | (62, -80, 18, 16) |
| `1638` | Forward MP | FORWARD_MP | 14/2/42 | (54, -72, 24, 14) |
| `1728` | — | HEAVY_PUNCH:close | 4/4/34 | (38, -90, 30, 24) |
| `1818` | — | HEAVY_PUNCH | 8/5/38 | (42, -70, 50, 12) |
| `1908` | — | LIGHT_KICK | 4/4/19 | (34, -24, 38, 10) |
| `1988` | — | MEDIUM_KICK | 4/5/23 | (36, -78, 24, 20) |
| `1a38` | — | MEDIUM_KICK:far | 5/5/30 | (18, -54, 42, 10) |
| `1b08` | Close HK | HEAVY_KICK | 5/8/39 | (34, -118, 12, 46) |
| `1bf8` | — | HEAVY_KICK:far | 9/5/40 | (62, -104, 24, 18) |
| `1d28` | — |  | 4/3/15 | (26, -52, 44, 8) |
| `1dd8` | — |  | 5/4/22 | (60, -52, 16, 14) |
| `1e88` | — |  | 5/5/35 | (28, -64, 32, 32) |
| `1f68` | Cr LK |  | 5/3/19 | (28, -8, 52, 8) |
| `2008` | Cr MK |  | 6/5/31 | (70, -10, 16, 10) |
| `20d8` | Cr HK | CROUCH_HEAVY_KICK | 7/5/41 | (22, -12, 68, 12) |
| `21c8` | Straight Air LP | JUMP_LIGHT_PUNCH:neutral | 4/26/30 | (28, -72, 24, 12) |
| `22a8` | Air MP |  | 5/5/31 | (56, -78, 20, 16) |
| `2388` | Straight Air HP | JUMP_HEAVY_PUNCH:neutral | 7/3/39 | (34, -100, 50, 10) |
| `2448` | Straight Air LK | JUMP_LIGHT_KICK:neutral | 4/19/35 | (22, -50, 24, 14) |
| `2558` | Straight Air MK | JUMP_MEDIUM_KICK:neutral | 5/6/22 | (70, -70, 18, 16) |
| `2628` | Straight Air HK | JUMP_HEAVY_KICK:neutral | 6/5/31 | (60, -100, 22, 18) |
| `2708` | Air LP |  | 4/28/32 | (28, -72, 24, 12) |
| `2800` | Air HP |  | 6/4/24 | (54, -64, 22, 18) |
| `28e0` | Air LK |  | 4/10/18 | (22, -50, 24, 14) |
| `29c0` | Air MK |  | 5/6/21 | (68, -68, 16, 16) |
| `2aa0` | Air Down MK | DIVE_KICK | 8/12/20 | (42, -34, 12, 10) |
| `2b30` | Air HK |  | 6/4/22 | (64, -56, 24, 16) |
| `84f8` | — | GOSHORYUKEN:light | 3/14/35 | (24, -74, 40, 32) |
| `85c8` | — | GOSHORYUKEN:medium | 2/7/19 | (24, -74, 40, 32) |
| `8658` | — | GOSHORYUKEN:heavy | 1/23/24 | (22, -54, 38, 32) |
| `86e8` | — | TATSUMAKI:light | 11/4/24 | (54, -70, 22, 12) |
| `87f8` | — | TATSUMAKI:medium | 2/10/30 | (24, -72, 26, 22) |
| `8968` | — | TATSUMAKI:heavy | 2/18/38 | (24, -72, 26, 22) |
| `9618` | — | TATSUMAKI:air_light | 5/3/18 | (54, -70, 22, 12) |
| `9738` | — | TATSUMAKI:air_medium | 5/6/18 | (54, -70, 22, 12) |
| `9818` | — | TATSUMAKI:air_heavy | 5/9/26 | (54, -70, 22, 12) |
| `98f8` | UOH | OVERHEAD | 15/8/25 | (26, -46, 44, 18) |
| `af08` | Demon flip |  | 40/15/71 | (57, -13, 19, 13) |
| `b118` | Demon flip P cancel |  | 10/3/18 | (42, -47, 24, 17) |
| `b218` | Demon flip K cancel |  | 9/11/20 | (36, -23, 14, 11) |

> The base LP/HP records are the FAR versions and the base MP/MK/HK records the CLOSE
> ones (st.LK has a single version); `Character.move_variant` ('close'/'far' by distance,
> `CLOSE_NORMAL_RANGE`, or 'neutral' for a straight jump) selects the other half. Only the
> Demon Flip followups (`af08`/`b118`/`b218`) remain unwired; geometry/timing are ROM-accurate.
