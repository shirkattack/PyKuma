--[[ ============================================================================
  PyKuma - CPS3 sprite (cel) ripper PROBE for sfiii3nr1 (FBNeo / Fightcade)

  Dumps, for one emulated frame, everything the PPU needs to draw the
  screen's sprite objects: the sprite main list + sub-lists (tile numbers,
  flips, palette, per-part offsets, sizes), the raw 16x16 8bpp tiles those
  parts reference (read from CHARACTER RAM, bank-switched), and the palettes
  they use (colour RAM, 15-bit RGB). tools/rom_extract/cel_decode.py turns a
  dump into one PNG per object, positioned relative to the object's own
  origin (its axis), so a character's cel comes out pixel-exact with the true
  sprite<->axis offset.

  Memory layout (MAME src/mame/capcom/cps3.cpp, FBNeo src/burn/drv/cps3/cps3run.cpp):
    0x04000000  sprite RAM: main list, 16 bytes/record, bit31 of dword0 = end
                dword0: gscroll idx (bits 28-30), sublist length (16-24),
                        sublist start (4-14) -> byte offset start*0x100
                dword1: xpos (16-25), ypos (0-9)
                dword2: whichbpp(30) whichpal(29) gxflip(28) gyflip(27)
                        galpha(26) gbpp(25) global_pal (16-24)
                sub-list entry, 16 bytes: v1 tileno(17-31) flipx(12) flipy(11)
                        alpha(10) bpp(9) pal(0-8); v2 xpos2(16-25) ypos2(0-9);
                        v3 ysizedraw(24-30)+1 xsizedraw(16-22)+1 ysize(2-3) xsize(0-1)
                        with size code -> tiles {8,1,2,4}; xsize code 0 = tilemap cmd
    0x04080000  colour RAM, 0x20000 x u16 (5-5-5 RGB); palette base = pal*256
                (pal*64 when the bpp flag is set), masked to 0x1ffff
    0x04100000  1 MB window into the 8 MB character RAM (bank register
                0x040C0086 -- a WORD register the Lua API cannot reach: Lua
                writes go through the byte handler, which ignores it, so only
                the currently mapped bank is readable from here). A tile is
                256 bytes at tileno*256.

  Because of that bank limit the tiles are taken from a SAVESTATE written on
  the same frame (FBNeo states are uncompressed and carry the whole 8 MB of
  character RAM as the "Sprite ROM" entry); the JSON carries the sprite list,
  palettes and player state, plus the tiles of the mapped bank as a check.

  USAGE: Misc > Lua Scripting > Browse to this file > Run. With AUTO_NEW_CELS
  the script dumps by itself the first time P1 shows each cel id (anim_frame),
  so a whiff pass through the move list rips every sprite; DUMP_KEY ('C')
  dumps the current frame on demand. Output next to the script:
  pykuma_cels.jsonl (one JSON object per dump, naming its state file) and
  pykuma_cels_f<frame>.fs (the savestate, ~0.8 MB each). Top-left shows the
  count of cels ripped and the last dump.
============================================================================ ]]

local OUT_PATH     = "pykuma_cels.jsonl"
local DUMP_KEY     = "C"
local SAVE_STATE   = true    -- write pykuma_cels_f<frame>.fs (source of the tiles for cel_decode.py)
local AUTO_NEW_CELS = true   -- dump automatically the first time P1 shows a cel id
local MAX_TILES    = 64      -- bank-0 tiles read through the window: the decoder's anchor into the state

local SPR_BASE  = 0x04000000
local PAL_BASE  = 0x04080000
local CRAM_WIN  = 0x04100000
local P1_BASE, P2_BASE = 0x02068C6C, 0x02069104
local TILES_TABLE = { [0] = 8, [1] = 1, [2] = 2, [3] = 4 }

local rdd, rdw, rdb = memory.readdword, memory.readword, memory.readbyte
local rdws, rdbs = memory.readwordsigned, memory.readbytesigned

-- bit slicing in plain Lua 5.1 arithmetic (no dependency on the emulator's bit library):
-- bits(v, shift, width) = (v >> shift) & ((1 << width) - 1)
local function bits(v, shift, width)
  return math.floor(v / 2 ^ shift) % (2 ^ width)
end

local function hexbytes(addr, n)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.format("%02x", rdb(addr + i)) end
  return table.concat(t)
end

local function hexwords(addr, n)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.format("%04x", rdw(addr + i * 2)) end
  return table.concat(t)
end

local function player_json(base)
  return string.format('{"anim":"%04x","cel":%d,"pos_x":%d,"pos_y":%d,"flip":%d,"posture":%d}',
    rdw(base + 0x202), rdw(base + 0x21A), rdws(base + 0x64), rdws(base + 0x68),
    rdbs(base + 0x0A), rdb(base + 0x20E))
end

local function read_tile(tileno, cache, order)
  -- only the mapped 1 MB bank is reachable; the decoder uses these to check
  -- the byte order against the savestate and falls back to the state for all
  local key = tostring(tileno)
  if cache[key] or tileno >= 4096 then return end   -- only bank 0 is reachable
  local addr = tileno * 256
  cache[key] = hexbytes(CRAM_WIN + bits(addr, 0, 20), 256)
  order[#order + 1] = key
end

local function dump_frame(frame_num)
  local recs, tiles, tile_order, pals, pal_order = {}, {}, {}, {}, {}
  local ntiles = 0
  for i = 0, 0x2000 - 16, 16 do
    local d0 = rdd(SPR_BASE + i)
    if bits(d0, 31, 1) ~= 0 then break end
    local d1, d2 = rdd(SPR_BASE + i + 4), rdd(SPR_BASE + i + 8)
    local length = bits(d0, 16, 9)
    local start  = bits(d0, 4, 11) * 0x100      -- byte offset into sprite RAM
    local xpos, ypos = bits(d1, 16, 10), bits(d1, 0, 10)
    local whichbpp, whichpal = bits(d2, 30, 1), bits(d2, 29, 1)
    local gxflip, gyflip = bits(d2, 28, 1), bits(d2, 27, 1)
    local galpha, gbpp = bits(d2, 26, 1), bits(d2, 25, 1)
    local global_pal = bits(d2, 16, 9)
    local parts = {}
    for j = 0, length - 1 do
      local e = SPR_BASE + start + j * 16
      local v1, v2, v3 = rdd(e), rdd(e + 4), rdd(e + 8)
      local xsize, ysize = bits(v3, 0, 2), bits(v3, 2, 2)
      local tileno = bits(v1, 17, 15)
      local bpp = bits(v1, 9, 1)
      local pal = bits(v1, 0, 9)
      local part = string.format(
        '{"tileno":%d,"flipx":%d,"flipy":%d,"alpha":%d,"bpp":%d,"pal":%d,"xpos2":%d,"ypos2":%d,' ..
        '"xsizedraw":%d,"ysizedraw":%d,"xsize":%d,"ysize":%d}',
        tileno, bits(v1, 12, 1), bits(v1, 11, 1), bits(v1, 10, 1), bpp, pal,
        bits(v2, 16, 10), bits(v2, 0, 10),
        bits(v3, 16, 7) + 1, bits(v3, 24, 7) + 1, xsize, ysize)
      parts[#parts + 1] = part
      if xsize ~= 0 then
        local nx, ny = TILES_TABLE[xsize], TILES_TABLE[ysize]
        local usebpp = (whichbpp == 1) and gbpp or bpp
        local actualpal = (whichpal == 1) and global_pal or pal
        local palbase = bits(actualpal * ((usebpp == 1) and 64 or 256), 0, 17)
        local pkey = tostring(palbase)
        if not pals[pkey] then
          pals[pkey] = hexwords(PAL_BASE + palbase * 2, 256)
          pal_order[#pal_order + 1] = pkey
        end
        for t = 0, nx * ny - 1 do
          if ntiles < MAX_TILES then
            read_tile(tileno + t, tiles, tile_order)
            ntiles = ntiles + 1
          end
        end
      end
    end
    recs[#recs + 1] = string.format(
      '{"i":%d,"length":%d,"start":%d,"xpos":%d,"ypos":%d,"gscroll":%d,"whichbpp":%d,"whichpal":%d,' ..
      '"gxflip":%d,"gyflip":%d,"galpha":%d,"gbpp":%d,"global_pal":%d,"parts":[%s]}',
      i / 16, length, start, xpos, ypos, bits(d0, 28, 3), whichbpp, whichpal,
      gxflip, gyflip, galpha, gbpp, global_pal, table.concat(parts, ","))
  end
  local state_name = ""
  if SAVE_STATE and savestate and savestate.save then
    state_name = string.format("pykuma_cels_f%d.fs", frame_num)
    savestate.save(state_name)
  end

  local tj, pj = {}, {}
  for _, k in ipairs(tile_order) do tj[#tj + 1] = '"' .. k .. '":"' .. tiles[k] .. '"' end
  for _, k in ipairs(pal_order) do pj[#pj + 1] = '"' .. k .. '":"' .. pals[k] .. '"' end
  local line = string.format('{"f":%d,"state":"%s","p1":%s,"p2":%s,"records":[%s],"tiles":{%s},"palettes":{%s}}',
    frame_num, state_name, player_json(P1_BASE), player_json(P2_BASE),
    table.concat(recs, ","), table.concat(tj, ","), table.concat(pj, ","))
  local fh = io.open(OUT_PATH, "a")
  if fh then fh:write(line, "\n"); fh:close() end
  return #recs, ntiles
end

local frame_num, prev_key, status = 0, false, "press " .. DUMP_KEY .. " to dump the current frame"
local seen, nseen = {}, 0
local function on_frame()
  frame_num = frame_num + 1
  local cel = rdw(P1_BASE + 0x21A)
  local down = input.get()[DUMP_KEY] == true
  local want = down and not prev_key
  if AUTO_NEW_CELS and not seen[cel] then
    seen[cel] = true; nseen = nseen + 1; want = true
  end
  if want then
    local nrec, nt = dump_frame(frame_num)
    status = string.format("dumped f%d cel %d: %d objects", frame_num, cel, nrec)
  end
  prev_key = down
  if gui and gui.text then
    gui.text(8, 8, string.format("CEL RIP f%d  P1 anim %04x cel %d  ripped %d | %s",
      frame_num, rdw(P1_BASE + 0x202), cel, nseen, status))
  end
end

emu.registerafter(on_frame)
