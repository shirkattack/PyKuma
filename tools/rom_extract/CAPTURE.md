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
