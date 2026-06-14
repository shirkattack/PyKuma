# PyKuma Hitbox Pipeline — Working Notes & Nuances

> Living document. Captures the coordinate conventions, data sources, cross-validation
> results, and open issues discovered while building the ROM-accurate Akuma hitbox
> pipeline. Hand this to a terminal session to continue the work with full context.
>
> Last updated: 2026-06-14. Branch: `rom-accurate-hitboxes`.

---

## 1. TL;DR / current state

- Akuma's boxes are now sourced from **`Grouflon/3rd_training_lua`** (ROM dump, rev
  `sfiii3nr1`), converted to PyKuma coordinates, with **provenance enforced in code**
  (a box with no source cannot load). No invented geometry.
- The conversion math is **cross-validated against a second independent source**
  (Baston / ensabahnur): the **pushbox matches to the pixel**.
- Two real issues remain (details below): **(A)** the live collision `get_rect` uses a
  convention inconsistent with the data (wrong for left-facing + centered boxes);
  **(B)** several move *names* are inferred guesses — geometry is ROM-accurate, the
  pointer→name assignment is not.

---

## 2. Data sources (provenance catalog)

| # | Source | What it gives | Reachable? | Role |
|---|--------|---------------|-----------|------|
| 1 | **Grouflon/3rd_training_lua** `data/sfiii3nr1/framedata/gouki_framedata.json` | Per-frame boxes keyed by move-script pointer (`1e88`, `1438`, …) + string states (`idle`) | git clone (vendored) | **Primary** box geometry |
| 2 | **Baston / ensabahnur** (`hitboxesDisplay`) | Per-frame boxes + sprites, per move, P1/P2 | web only (host not allowlisted; pasted manually) | **Independent cross-check** |
| 3 | **"Hitbox structure" doc** | Raw memory layout, draw math, border rule | — (pasted) | Convention oracle |
| 4 | **RAM memory map** (3fv / Fightcade) | Live addresses: `hb_*_base_address`, `state`, `anim_frame`, `pos_x/y`, `facing_dir`, … | — (pasted) | Future **live emulator reader** |
| 5 | **Input bit addresses** (GGPO-FBA / FBA-RR) | Per-button RAM bytes, P1/P2 | — (pasted) | Future input capture/validation |
| 6 | **Google Sheet** `1eLi9phXMj…` "ROM mappings" | May hold standing-normal pointer→name map | **blocked** (`docs.google.com` not allowlisted, sheet not link-public) | Could resolve remaining names |
| 7 | **`3rd_training_lua` `data/sfiii3nr1/framedata_meta.lua`** | **Authoritative** move-name table (pointer→name, hit types) | raw.githubusercontent (fetched) | **Resolved 4 of 7 names** (§7) |

Vendored copy + pinned commit recorded in `data/sources/SOURCE.txt`.

---

## 3. Raw box format (both sources agree)

A box is four numbers. The two sources order them differently but mean the same thing:

| Field | 3rd_training_lua JSON key | Baston array index | Meaning |
|-------|---------------------------|--------------------|---------|
| X     | `left`                    | `[0]`              | horizontal offset from the **axis** (between the feet) |
| WIDTH | `width`                   | `[1]`              | box width |
| HEIGHT| `height`                  | `[2]`              | box height |
| Y     | `bottom`                  | `[3]`              | height **above ground** of the box's **bottom** edge (Y points up) |

- Origin / axis = point between the feet. `pos_x`,`pos_y` is the character's world position.
- Native scale ≈ **107 px** tall Akuma — same space PyKuma already uses, **no rescale**.
- Character data is authored **facing right**, with **forward = −X** (attack boxes sit at
  negative `left`). Facing flips X (see §5).
- Box X spans `[X, X+WIDTH]`; Y-above-ground spans `[Y, Y+HEIGHT]`.

### Box-type taxonomy
| Baston `_hb` | 3rd_training_lua `type` | PyKuma meaning |
|--------------|--------------------------|----------------|
| `a_hb` (active)        | `attack`        | **hitbox** (offensive) |
| `p_hb` (passive)       | (in `idle`)     | **base body hurtbox** — present every frame |
| `v_hb` (vulnerability) | `vulnerability` | **move-specific** hurt extension (e.g. the extended arm during a jab) |
| `pu_hb`                | `push`          | **pushbox** |
| `t_hb`                 | `throwable`?    | throw box |
| `ta_hb`                | `throwable`     | throwable box |

> **Nuance:** an attacking move records (almost) only its **attack** boxes. The hurtbox
> is the **shared base body hurtbox** (`p_hb`, taken from `idle`) — *plus* any move-specific
> **`v_hb`** extensions on active frames. The pipeline now supports per-move `v_hb`
> (`frames[].vulnerability[]` → repository → `get_akuma_hurtboxes(state, frame)` layering →
> collision + viewer in magenta). **The ROM dump omits per-move `v_hb`** (only `idle`/`wakeup`),
> so st.LP/st.LK/st.MK are seeded from Baston (`data/characters/akuma/vhb_supplement.json`,
> status `baston`) until the ROM extractor backfills the rest — see `tools/rom_extract/README.md`.
> **Invincibility is NOT derivable from a missing hurtbox** — a move with no recorded hurtbox
> just didn't record one. Invincible frames come from frame-data notes, not the box data.

---

## 4. Conversion to PyKuma coordinates

PyKuma origin = feet; **y negative = up**. Implemented in
`tools/framedata/convert_3rd_training.py :: convert_box`.

```
# attack boxes — offset_x is the LEFT (near) edge, forward-positive:
offset_x = -left - width
offset_y = -(bottom + height)          # TOP edge, negative = up
width, height = unchanged

# centered boxes (hurt / push / throw / throwable) — offset_x is the CENTER:
offset_x = -(left + width/2)
offset_y = -(bottom + height)
```

No scale factor (native ≈107 px).

### Cross-validation (two independent sources)
| Box | Baston raw `[X,W,H,Y]` | Baston → PyKuma | Our `3rd_training_lua` value | Match? |
|-----|------------------------|-----------------|------------------------------|--------|
| Pushbox | `-25,50,84,0` | `(0, -84, 50, 84)` | `(0, -84, 50, 84)` | ✅ **exact** |
| Jab active | `-48,14,12,84` | `(34, -96, 14, 12)` | `13a8` LP = `(32, -92, 14, 22)` | ⚠️ width only |

The pushbox match (independent sources, identical to the pixel) validates the centering,
Y-flip, and scale. The jab mismatch is a **naming** problem, not a math problem (§6).

---

## 5. Facing convention (the part the engine must get right)

From the structure doc and confirmed by Baston's P1 (right) vs P2 (left) draw data:

```
facing RIGHT (P1):  screen box = [center - X - W, center - X]
facing LEFT  (P2):  screen box = [center + X,     center + X + W]   # mirror about center
```

In PyKuma offset terms (offset_x = forward-positive near edge for attacks):
```
facing right:  rect_left = char_x + offset_x;              width extends + (forward)
facing left:   rect_left = char_x - offset_x - width;      mirror BOTH edges
centered box:  rect_left = char_x + (offset_x * facing) - width/2
```

**Worked example — jab, facing right** (Baston `X=-48, W=14`):
far edge `center - X = center + 48`, near edge `center + 34`. PyKuma `offset_x = 34`,
extends to `48`. ✓ Matches Baston's `a_hb_to_draw` exactly.

### Border rule
> "Border of a box is not part of it; for two boxes to cross, one must be inside the other."

pygame's `Rect.colliderect` already treats right/bottom edges as **exclusive** (half-open
rects), so touching boxes do **not** register a hit. This matches the game. Keep boxes
integer-rounded so this stays consistent.

---

## 6. ISSUE A — live `get_rect` convention  ✅ RESOLVED

**Fixed** in `SF3Hitbox` (added an `anchor` field: `"edge"` for attack boxes, `"center"` for
hurt/push/throw) and a rewritten `get_rect` that mirrors width on facing and centers
center-anchored boxes. `_sync_hitbox_manager` now tags ATTACK boxes `anchor="edge"` and BODY boxes
`anchor="center"`; `render_debug` draws via `get_rect(...)` so the overlay matches collision exactly.
Pinned by `tests/test_hitbox_geometry.py` (facing mirror + centering + end-to-end facing symmetry,
oracle = Baston jab). The original problem, kept for context:

There were **two** rect builders in the engine and they disagreed:

| | facing-left attack | centered hurt/push |
|---|---|---|
| `sf3_collision_adapter._get_character_hitboxes/_hurtboxes` | `x - offset_x - width` ✅ mirrors both edges | `x + offset_x - width//2` ✅ centered |
| **`sf3_hitboxes.SF3Hitbox.get_rect`** (the LIVE hit path) | `x + offset_x*facing` then `Rect(x, width)` ❌ width not mirrored | treats `offset_x` as left edge ❌ no `-width/2` |

The **live** hit detection routes through the buggy one:
`check_attack_collision → sf3_system.check_collision_between_players → attack_box.overlaps → get_rect`.

Consequences against our (correct) data:
- **Left-facing attacks** land ~`width` px off (wrong side of the body). One player always faces left.
- **Hurtboxes** (stored center-anchored) sit ~`width/2` off (e.g. 62 px chest box → ~31 px off).

Independently confirmed by Baston's P1/P2 mirror (§5).

**Fix (proposed, needs go-ahead — this is gameplay logic):** make `SF3Hitbox.get_rect`
mirror width on facing and center the non-attack box types (or normalize at the
`_sync_hitbox_manager` boundary). Add a regression test that pins:
- jab facing right → `[center+34, center+48]`
- jab facing left  → `[center-48, center-34]`
- pushbox → centered `[center-25, center+25]`

(Use the Baston jab as the oracle: `X=-48, W=14, H=12, Y=84`.)

---

## 7. ISSUE B — move names  ✅ RESOLVED (all 7 verified)

All seven PyKuma attack states now map to a ROM pointer confirmed by an authoritative source —
either `framedata_meta.lua` (source #7) or a Baston ESN3S active-box cross-match (geometry is
pixel/sequence-exact and unique, trustworthy per the §4 pushbox match). **Five of our original
guesses were wrong and got corrected:**

| PyKuma state | ROM pointer | Source | Note |
|---|---|---|---|
| LIGHT_PUNCH | `1438` | meta | `1438`=LP *(was `13a8`; `1438` had been mislabeled LK)* |
| MEDIUM_PUNCH | `14e8` | Baston "Strong" | active box `(32,-66,24,18)` pixel-exact, unique |
| HEAVY_PUNCH | `1818` | meta | Target HP `3850`→`1818` ⇒ HP *(was `1e88`)* |
| LIGHT_KICK | `1908` | Baston "Short" | active box `(34,-24,38,10)` pixel-exact, unique |
| MEDIUM_KICK | `1988` | Baston "Forward" | multi-box active **sequence** unique match *(corrected from `1dd8`)* |
| HEAVY_KICK | `1b08` | meta | `1b08`=Close HK (far st.HK not separately named) |
| CROUCH_HEAVY_KICK | `20d8` | meta | `20d8`=Cr HK — low/long sweep box `(22,-12,68,12)` *(was `2008`=Cr MK)* |

Method for the kicks/MP: pull Baston's labeled move (Strong/Short/Forward), convert its active
`a_hb` boxes (`offset_x=-X-W`, `offset_y=-(Y+H)`), and match the box set + active-frame count to a
unique ROM pointer. Startup/total differ by 1 between sources (0-index / idle-transition
convention) but the geometry is identical.

Other meta-named gouki pointers (for viewer labels): `1f68`=Cr LK, `2008`=Cr MK, `1d28`=Cr LP,
`1638`=Forward MP, `98f8`=UOH, `21c8/2708/...`=air normals, `af08`=Demon flip, `6A/6B/...`=fireballs.
HEAVY_KICK uses the **close** HK (`1b08`); a distinct far st.HK pointer was not separately named —
the only remaining minor caveat.

### Full pointer → name + timing join (gouki, from our vendored frames)
```
ptr   meta name        timing (startup/active/total, attack frames)
13a8  -                3/3/15      1908  -                4/4/19
1438  LP   (=st.LP)    4/3/14      1988  -                4/5/23
14e8  - (prov. st.MP)  5/4/22      1a38  -                5/5/30
1598  -                5/4/24      1b08  Close HK (=HK)    5/8/39
1638  Forward MP       14/2/42     1bf8  -                9/5/40
1728  -                4/4/34      1d28  (Cr LP)           4/3/15
1818  HP   (=st.HP)    8/5/38      1dd8  - (prov. st.MK)   5/4/22
                                   1e88  -                5/5/35
1f68  Cr LK            5/3/19      2008  Cr MK             6/5/31
20d8  Cr HK (=Cr HK)   7/5/41
```

---

## 8. Future: live emulator reader (sources #4, #5)

The RAM map exposes exactly our box taxonomy, which means a live reader could capture or
validate boxes frame-by-frame:

```
hb_base_address            0x02068C6C
hb_active_base_address     0x02068F34   (attack)
hb_passive_base_address    0x02068F0C   (base body hurt)
hb_vulnerability_pointer   0x02068F14   (move-specific hurt)
hb_push_base_address       0x02068F40   (pushbox)
hb_throw_base_address      0x02068F24
hb_throwable_base_address  0x02068F2C
state 0x02068E75   anim_frame 0x02068E86   pos_x 0x02068CD0   pos_y 0x02068CD4
facing_dir 0x02068C76   hitboxes_active 0x02009EFC
```
Input bytes (per button, P1/P2) exist for GGPO-FBA (`0x00A871xx`) and FBA-RR (`0x0151C8xx`).
Not needed for the current frame-data work; useful for an input-display / validation tool.

---

## 9. Open TODOs

1. ~~Fix `SF3Hitbox.get_rect` facing + centering (§6) + regression test.~~ ✅ **Done** (`anchor` field + `tests/test_hitbox_geometry.py`).
2. ~~Resolve remaining move names~~ ✅ **Done** — all 7 verified (§7), st.MP/LK/MK via Baston
   cross-match. Minor caveat: HEAVY_KICK uses Close HK (`1b08`); far st.HK not separately named.
3. ~~Capture per-move `v_hb`~~ — pipeline + viewer done; LP/LK/MK seeded from Baston. **Remaining:**
   run `tools/rom_extract/` to backfill authoritative per-move `v_hb` for all moves from the ROM.
4. **Invincibility** from frame-data notes (not missing hurtbox).
5. Optional: live emulator memory-reader (§8) to auto-validate boxes/inputs.

---

## 10. Project / branch state (for the terminal)

- Branch `rom-accurate-hitboxes`: commit `38fda88` (feature) + `b4fda16` (pre-existing WIP
  refactor the feature depends on). Both **SSH-signed** (signing server had an outage; resolved).
- The repo here has **no GitHub credentials**, so it was never pushed. Reconcile via
  `claude --teleport` (recommended) or the git **bundle** that was shared. Remote `main`
  (`shirkattack/PyKuma`) sits at `519cc61` = this branch's base, so it's a clean fast-forward.
- 1 pre-existing test failure (`test_akuma_creation`) is unrelated — missing sprite assets.
