# Capture recipe — ROM frame-data + physics (Akuma / Gouki)

You run this once in FBNeo (Fightcade) on `sfiii3nr1`. It records live ROM memory
to a JSON-Lines file that `ingest.py` turns into per-move hurtboxes and physics
constants. **No data is invented** — everything is read from the game using the
exact memory layout `3rd_training_lua` uses.

The dumper **auto-records** and `ingest.py` **auto-segments** moves vs. movement,
so it's a single session: load the script, play, close. No key juggling, no
separate recordings.

---

## Fightcade on Linux (Flatpak) — the easy path

Fightcade is a sandboxed Flatpak running FBNeo under Wine, so its file browser
can't see `~/PyKuma`. The script has therefore been **copied into a folder the
emulator can already see**:

```
~/.var/app/com.fightcade.Fightcade/data/fbneo-training-mode/dump_framedata.lua
```

(Re-copy after any edit: `cp tools/rom_extract/dump_framedata.lua \
  ~/.var/app/com.fightcade.Fightcade/data/fbneo-training-mode/`)

1. Launch the **sfiii3nr1** game in Fightcade, pick **Gouki (Akuma)** as **P1**,
   enter training.
2. Open **Misc ▸ Lua Scripting** (the "Lua Script" window). Click **Browse…**.
3. In the Open dialog, the default folder ("fbneo") lists **fbneo-training-mode**
   — double-click into it and pick **`dump_framedata.lua`**. Click **Run**.
   - Top-left shows `REC <frame>`. It is now recording.
4. Do the captures below, then just **close the emulator** (or Stop the script).
   The file flushes automatically.
   - The top-left reads `REC <n>  [inf time / life]`: the script pins the round
     timer at 99 and refills a player's life whenever that player is idle
     (Grouflon's training script is not running while this one is, so the
     dumper does its job for it).
   - The arcade ROM has **no training menu**; the script drives the dummy.
     Press **B** to cycle `stand -> block -> block_always -> crouch_block -> jump`
     (shown top-left). `block` holds back only while P1 is in a move, so the
     dummy stays where it is; `block_always` holds back permanently (it retreats
     to the corner and blocks fireballs too); `jump` holds Up. Hurtbox (whiff)
     pass and hit pass: `stand`. On-block pass: `block` (and `crouch_block` for
     the lows if you want crouching blockstun as well).
5. The output lands next to the script:
   `~/.var/app/com.fightcade.Fightcade/data/fbneo-training-mode/pykuma_dump.jsonl`

> If `Browse` still fights you: the wineprefix maps `z: → /`, so you can also
> type the path directly into the Script box as
> `Z:\home\esteban\.var\app\com.fightcade.Fightcade\data\fbneo-training-mode\dump_framedata.lua`.

---

## What to drive (one recording, ~1–2 min)

With it recording, do each once, pausing a beat between so frames are clean:

**Moves** (for per-move hurtboxes — play through each move's active frames):
- Standing LP, MP, HP, LK, MK, HK
- Crouching LP, MP, HP, LK, MK, HK
- Jumping (neutral) LP, MP, HP, LK, MK, HK
- Gohadoken (all strengths), Shoryuken, Tatsumaki (+ supers if easy)
- Stand idle a moment (re-confirms the base hurtbox stack)

**Movement** (for physics — do each in isolation with a neutral pause between):
- Walk forward ~2s, walk back ~2s
- Forward dash, back dash
- Neutral jump (full), forward jump (full), back jump (full)

Then close the emulator. (`R` pauses/resumes if you want to skip menus.)

---

## Ingest (back in the repo, via uv)

Copy the output back first:
```
cp ~/.var/app/com.fightcade.Fightcade/data/fbneo-training-mode/pykuma_dump.jsonl .
```
Then:
```
# Sanity-check the extractor read boxes correctly (must match Baston seed):
uv run python tools/rom_extract/ingest.py validate pykuma_dump.jsonl

# Per-move hurtboxes -> enriched framedata, then re-run the existing converter:
uv run python tools/rom_extract/ingest.py merge pykuma_dump.jsonl \
    --out data/sources/gouki_framedata.enriched.json
#   review, replace data/sources/gouki_framedata.json with it, then:
uv run python tools/framedata/convert_3rd_training.py \
    data/sources/gouki_framedata.json --name akuma

# Physics constants -> physics.yaml (flagged for review):
uv run python tools/rom_extract/ingest.py physics pykuma_dump.jsonl \
    --out data/characters/akuma/physics.yaml
```

Or just hand me `pykuma_dump.jsonl` and I'll do the ingest + apply (Phase 5).

## What "correct" looks like
- `validate` prints, for st.LP / st.LK / st.MK, which ROM array
  (`vulnerability` vs `ext_vulnerability`) matches the Baston seed
  (LP `{-54,22,84,18}`, LK `{-64,38,20,34}`, MK `{-62,32,44,32}` as
  `{left,width,bottom,height}`).
- `physics.yaml` lists a detected jump (gravity, initial velocity, airborne
  frames, apex), walk speed, and dash runs (distance + per-frame curve).


---

## Combat capture — ROM-exact damage / stun / hitstop / hitstun

The same script now also records both players' combat state every frame
(`c1` / `c2` in each JSONL line: life, applied damage and stun, freeze
(hitstop), recovery, blocking id, hit counters, attack/defense multipliers,
stun gauge). Every address is one 3rd_training_lua reads; the disc source
(crowded-street/3s-decomp `Pow_Pow.c` / `HITCHECK.c` / `VITAL.c`) confirms the
meaning: `dm_vital` is the damage *after* `att_plus`/`def_plus`, the life bar
is `0xA0 = 160` for everyone, hitstop is the freeze counter.

**Session (Akuma vs Akuma, training mode, dummy standing):**

1. Run the script as above. Set the dummy to **stand, no guard**.
2. Land every move **on hit** at least twice: all standing normals close AND
   far, the crouching normals, every jump normal (forward and neutral jump),
   f+MP, UOH, the dive kick, LP/MP/HP DP, LK/MK/HK tatsu (ground and air), the
   fireballs, the demon-flip followups, throws, the supers. Let the dummy
   recover fully between hits (the ingest measures hitstun by waiting for it
   to go idle).
3. Set the dummy to **guard** and repeat everything **on block** (this gives
   blockstun and chip).
4. Close the emulator. Then:

```
uv run python tools/rom_extract/ingest.py combat \
    ~/.var/app/com.fightcade.Fightcade/data/fbneo-training-mode/pykuma_dump.jsonl \
    --out data/characters/akuma/rom_combat.json --raw /tmp/rom_combat_raw.json
uv run python tools/framedata/convert_3rd_training.py data/sources/gouki_framedata.json \
    --name akuma --names data/characters/akuma/move_names.json \
    --combat data/characters/akuma/sf3_authentic_frame_data.yaml \
    --vhb data/characters/akuma/vhb_supplement.json \
    --out data/characters/akuma/hitboxes.yaml      # picks up rom_combat.json automatically
uv run pytest -q
```

`rom_combat.json` holds, per ROM animation id and hit frame, the median of the
captured samples (damage, stun, hitstop, hitstun on hit; blockstun and chip on
block). The converter attaches them per hit window as a `rom_combat` block
(`status: verified`) and records the life-bar scale in `meta.rom_combat`; the
engine then runs at 160 vitality, prefers the captured values, and rescales
any move that only has community damage. Baston stays as a cross-check
(`tests/test_rom_combat.py` reports where the two disagree).

Do **not** hand-edit `rom_combat.json` — re-capture instead.


### Notes from the first session (2026-08-26)

- A **hit-only** pass gives damage / stun / hitstop / hitstun per move, but NOT
  blockstun or chip -- for those the dummy must be **guarding** (`blocking_id`
  becomes 1..4). If a pass reports `0 blocks`, the dummy wasn't set to guard.
- `att_bonus` / `def_bonus` read 0 outside the exact hit frame, so they are not
  used; the captured `dm_vital` is already the *applied* damage, which is what
  we store.
- The first capture covered the ground normals (close+far) and a few jump
  normals. A follow-up session should add: the on-block pass, the specials
  (DP / tatsu / fireballs / demon-flip followups), f+MP, UOH, the dive kick,
  the neutral-jump normals, throws and the supers. Samples from a new session
  merge with the old by move, so re-running only the missing moves is enough.


### Merging sessions

Save each session's raw samples (`combat ... --raw sessionN.json`), vendor them
under `data/characters/akuma/rom_combat_sessions/`, and build `rom_combat.json`
from all of them:

    uv run python tools/rom_extract/ingest.py merge-combat \
        data/characters/akuma/rom_combat_sessions/*.json \
        --out data/characters/akuma/rom_combat.json

Sessions capture mostly disjoint moves, so their samples union cleanly; where
they overlap the extra samples sharpen the median. A capture's raw dump
(`pykuma_dump.jsonl`) is overwritten by the next run, so the vendored per-session
raw files are the durable artifact -- keep them. Since session 2 the full dump
is vendored too, gzipped (`sessionN_dump.jsonl.gz`; `ingest.py` reads `.gz`
directly), so hurtboxes and combat can be re-derived after an ingest fix.

### Notes from the second session (2026-08-26, specials / air normals) — ingested 2026-08-27

- **v_hb**: `ext_vulnerability` confirmed as the per-move hurtbox array (LK == Baston
  seed). Backfilled into `gouki_framedata.json`: far LP `1438`, LK `1908`, air HK
  `2628`, LP DP `84f8`, LK tatsu `86e8`. Rejected by the alignment check (the move
  connected, hitstop stretched the run and the cel timeline no longer matches the
  vendored framedata): `22a8 2388 2448 2558` (air normals), `85c8 8658` (MP/HP DP),
  `87f8` (MK tatsu), `b218`; no attack box seen at all: `21c8`, `af08`.
  **For the hurtbox pass, whiff every move** (dummy far away / jumping) — a whiff
  gives the exact framedata timeline and the same v_hb.
- **Combat**: session 2's raw samples (`rom_combat_sessions/session2_specials_jumps.json`)
  were re-derived with the hitstop-aware frame counting (a multi-hit move's later
  connects now land on their framedata window: MP DP 3/4, HP DP 2/3/4, not 3/14,
  2/13/24) and `rom_combat.json` rebuilt with `merge-combat`. Knockdowns
  are detected from the defender's posture byte and stored as `knockdown` +
  `down_frames` — their time-to-idle is NOT hitstun (`hitstun: null`, the engine
  falls back to the community value). A multi-hit move whose later hits never
  landed gets no `damage_total` (`complete: false`) so a partial sum is never
  read as the move's damage. A later hit's frame cannot be pinned from the
  defender's freeze (the attacker's own hitstop `hs_me` differs per move), so the
  ingest also records each connect's ordinal in its run (`hit_index` / `run_hits`)
  and the converter places a run that landed every hit by ordinal (cl.HK 21+12,
  MP DP 17+8, HP DP 10+9+9). Still **0 on-block samples**.
- Session 1's vendored raw had been written with `frame` = cel id (`22047`-style
  values reached `hitboxes.yaml`); it was repaired from recorded data only (see
  its `_meta.frame_repair`). It predates the knockdown flag and its dump is gone,
  so cr.HK `20d8` still reports its 60-frame knockdown as `hitstun` until re-driven.
- Not in the vendored framedata (kept in `rom_combat.json` under their anim id,
  not attached to any move): `3768` (3 connects, 0 dm_vital — a throw/grab),
  `7684`, `8210`, `a130` (10 dmg / 3 stun / hitstun 15 — fireball-class hits),
  `d524`, `d8d4`.

### Notes from the third session (2026-08-27, full pass with the built-in dummy)

- The dumper now pins the timer, refills life when idle and **drives the dummy**
  (`B` cycles stand / block / block_always / crouch_block / jump) — the arcade
  ROM has no training menu and only one Lua script runs at a time.
- **First on-block data**: 84 block samples. Blockstun reads 11 (lights) / 14
  (mediums) / 17 (heavies), chip 0 on normals and 1–2 on specials; the engine now
  takes blockstun from the capture where it exists (the calibrated community
  estimate was 4 frames high on st.MK / cr.MP).
- **v_hb**: `merge` prefers whiffed runs (a connect freezes the attacker), so the
  whiff pass landed 26 more moves — 31 of 43 attack scripts now carry the ROM
  hurtbox. The defender's posture byte turned out to be an action id
  (0 stand, 2 walk, 22 airborne, 24 launched, 38 down); knockdown is now
  "reached 24/38 from the ground", which also un-nulled blockstun.
- Not yet mapped to a PyKuma move but captured: `3768` (throw, 6 samples),
  `68cc` (12 hits — a super), `7684 8210 a130` (fireballs), `b308`.

### What is still missing

**Hurtbox pass — whiff each once (dummy `stand`, out of reach; close normals
against a `jump` dummy at its apex):** cl.MP `14e8`, far MP `1598`, cl.HP
`1728`, cl.MK `1988`, far MK `1a38`, cl.HK `1b08`, nj.HP `2388`, nj.LK `2448`,
j.LK `28e0`, dive kick `2aa0`, UOH `98f8`. (These either connected every time
or were never performed.)

**Combat:** UOH and the dive kick on hit and on block; a second sample for the
single-sample windows (`merge-combat` reports `samples`); parries if wanted.
Throw / super / fireball samples exist but need their anim ids mapped in
`move_names.json` before the converter can attach them.
