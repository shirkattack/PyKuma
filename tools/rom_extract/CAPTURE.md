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
