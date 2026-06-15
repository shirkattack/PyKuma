--[[ ============================================================================
  PyKuma ROM frame-data dumper  (Street Fighter III: 3rd Strike, sfiii3nr1)

  Runs in the SAME emulator/Lua environment as Grouflon/3rd_training_lua
  (fba-rr / FBNeo Lua). It records, for Player 1, every frame: world position,
  facing, posture, the current animation id + frame, and ALL box types
  (push / throwable / vulnerability / ext. vulnerability / attack / throw),
  read with the exact addresses + struct the training tool uses.

  Output: a JSON-Lines file (one JSON object per emulated frame) at OUT_PATH.
  Reconstruction into the converter schema + physics derivation happens in
  tools/rom_extract/ingest.py (so the Lua stays dumb and the Python is testable).

  Provenance: memory layout taken verbatim from
  github.com/Grouflon/3rd_training_lua @73ec4c06  src/gamestate.lua
  (read_game_object / read_box). Box pointer at (base+offset) is DEREFERENCED
  (readdword) then boxes are 8 bytes each: left,width,bottom,height (s16 each).

  USAGE (FBNeo Lua Script window — e.g. Fightcade on Linux):
    1. Load sfiii3nr1, pick Gouki (Akuma), enter training/versus (P1 = Akuma).
    2. Misc > Lua Scripting (or the Lua Script window) > Browse to this file >
       Run. Recording starts immediately (top-left shows "REC <n>").
    3. Drive every move once, then walk/dash/jump (see CAPTURE.md).
    4. Close the emulator (or Stop the script) — the file flushes automatically.
  Output `pykuma_dump.jsonl` is written in THIS script's folder (FBNeo uses the
  script's directory as the working dir). 'R' pauses/resumes if you want to skip
  menus. See tools/rom_extract/CAPTURE.md.
============================================================================ ]]

-- ---- config -----------------------------------------------------------------
local OUT_PATH = "pykuma_dump.jsonl"   -- written in the script's own folder
local REC_KEY  = "R"                    -- optional: press to PAUSE/resume recording
local PLAYER_BASE = 0x02068C6C          -- P1 base (P2 is 0x02069104)

-- Box arrays: a POINTER lives at (base+offset); each box is 8 bytes.
-- (number = max boxes of that type; inactive slots are filtered out below.)
local BOX_DEFS = {
  { offset = 0x2D4, type = "push",              number = 1 },
  { offset = 0x2C0, type = "throwable",         number = 1 },
  { offset = 0x2A0, type = "vulnerability",     number = 4 },
  { offset = 0x2A8, type = "ext_vulnerability", number = 4 },
  { offset = 0x2C8, type = "attack",            number = 4 },
  { offset = 0x2B8, type = "throw",             number = 1 },
}

-- ---- emulator memory shims (match 3rd_training_lua's API) --------------------
local rdword  = memory.readword
local rdwords = memory.readwordsigned
local rdbyte  = memory.readbyte
local rdbytes = memory.readbytesigned
local rddword = memory.readdword

-- ---- tiny JSON writer (records are flat: numbers, short strings, arrays) -----
local function jnum(n) return string.format("%d", n) end
local function jstr(s) return '"' .. s .. '"' end  -- ids are hex/ascii, no escapes

local function box_to_json(b)
  return "{" ..
    '"type":' .. jstr(b.type) .. "," ..
    '"left":' .. jnum(b.left) .. "," ..
    '"width":' .. jnum(b.width) .. "," ..
    '"bottom":' .. jnum(b.bottom) .. "," ..
    '"height":' .. jnum(b.height) .. "}"
end

-- ---- reads ------------------------------------------------------------------
local function read_box(ptr, btype)
  return {
    left   = rdwords(ptr + 0x0),
    width  = rdwords(ptr + 0x2),
    bottom = rdwords(ptr + 0x4),
    height = rdwords(ptr + 0x6),
    type   = btype,
  }
end

-- a box slot is "real" only when it has positive area and sane magnitude
local function box_ok(b)
  if b.width <= 0 or b.height <= 0 then return false end
  if math.abs(b.left) > 512 or math.abs(b.bottom) > 512 then return false end
  if b.width > 512 or b.height > 512 then return false end
  return true
end

local function read_boxes(base)
  local out = {}
  for _, def in ipairs(BOX_DEFS) do
    local arr = rddword(base + def.offset)       -- dereference the pointer
    if arr ~= 0 then
      for i = 1, def.number do
        local b = read_box(arr + (i - 1) * 8, def.type)
        if box_ok(b) then out[#out + 1] = b end
      end
    end
  end
  return out
end

local function frame_record(frame_num, base)
  local boxes = read_boxes(base)
  local parts = {}
  for _, b in ipairs(boxes) do parts[#parts + 1] = box_to_json(b) end
  return "{" ..
    '"f":' .. jnum(frame_num) .. "," ..
    '"pos_x":' .. jnum(rdwords(base + 0x64)) .. "," ..
    '"pos_y":' .. jnum(rdwords(base + 0x68)) .. "," ..
    '"flip":' .. jnum(rdbytes(base + 0x0A)) .. "," ..
    '"posture":' .. jnum(rdbyte(base + 0x20E)) .. "," ..
    '"anim":' .. jstr(string.format("%04x", rdword(base + 0x202))) .. "," ..
    '"anim_frame":' .. jnum(rdword(base + 0x21A)) .. "," ..
    '"boxes":[' .. table.concat(parts, ",") .. "]}"
end

-- ---- recording loop ---------------------------------------------------------
-- AUTO-RECORD: recording starts the moment the script runs and writes one line
-- per frame to OUT_PATH (in the script's own folder, since FBNeo runs a script
-- with its directory as the working dir). Optionally PAUSE_KEY toggles a pause so
-- you can skip menus. The file is flushed periodically and on emulator exit, so
-- you can simply Run -> play the moves -> close, with no key juggling.
local paused = false
local prev_key = false
local frame_num = 0
local fh = io.open(OUT_PATH, "w")

local function on_frame()
  -- optional pause toggle on PAUSE_KEY edge
  local keys = input.get()
  local down = keys[REC_KEY] == true
  if down and not prev_key then
    paused = not paused
  end
  prev_key = down

  if fh and not paused then
    frame_num = frame_num + 1
    fh:write(frame_record(frame_num, PLAYER_BASE), "\n")
    if frame_num % 60 == 0 then fh:flush() end
  end

  if gui and gui.text then
    gui.text(8, 8, (paused and "PAUSED " or "REC ") .. frame_num)
  end
end

local function close_file()
  if fh then fh:flush(); fh:close(); fh = nil end
end

-- FBNeo: run after each emulated frame; flush on exit.
emu.registerafter(on_frame)
if emu.registerexit then emu.registerexit(close_file) end

print("PyKuma dumper: RECORDING to " .. OUT_PATH ..
      " (press '" .. REC_KEY .. "' to pause/resume). Play the moves, then close.")
