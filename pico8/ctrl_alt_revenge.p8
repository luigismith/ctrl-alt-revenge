pico-8 cartridge // http://www.pico-8.com
version 42
__lua__
-- ctrl+alt revenge!
-- pico-8 isometric port
-- 128x128, 16 colors

-- ============================================
-- isometric helpers
-- iso projection: 2:1 ratio, classic style
-- world coords (wx, wy) -> screen (sx, sy)
-- ============================================
function w2s(wx, wy)
 local sx = (wx - wy) * 8
 local sy = (wx + wy) * 4
 return sx, sy
end

-- ============================================
-- game state
-- ============================================
state = "title"  -- title, play, win, gameover
frame = 0
flash = 0

-- camera (in world coords)
cam_x = 0
cam_y = 0

-- player
p = nil

-- enemies, particles, hits
enemies = {}
hits = {}
chips = 0

-- ============================================
-- player
-- ============================================
function make_player()
 return {
  -- world position (iso plane)
  wx = 4,
  wy = 4,
  -- velocity
  vx = 0,
  vy = 0,
  -- facing: 1=right, 2=down, 3=left, 4=up
  facing = 1,
  hp = 4,
  max_hp = 4,
  iframes = 0,
  -- combat
  attack_t = 0,
  attack_dir = 1,
  -- anim
  anim_f = 0,
  anim_t = 0,
  -- gun
  ammo = 6,
  gun_cd = 0,
 }
end

function update_player()
 if p.iframes > 0 then p.iframes -= 1 end
 if p.attack_t > 0 then p.attack_t -= 1 end
 if p.gun_cd > 0 then p.gun_cd -= 1 end

 -- input (only if not attacking)
 if p.attack_t == 0 then
  local dx, dy = 0, 0
  if btn(0) then dx -= 1 end
  if btn(1) then dx += 1 end
  if btn(2) then dy -= 1 end
  if btn(3) then dy += 1 end

  -- normalize diagonal
  if dx != 0 and dy != 0 then
   dx *= 0.7
   dy *= 0.7
  end

  p.vx = dx * 0.12
  p.vy = dy * 0.12

  -- facing
  if dx > 0.1 then p.facing = 1
  elseif dx < -0.1 then p.facing = 3
  elseif dy > 0.1 then p.facing = 2
  elseif dy < -0.1 then p.facing = 4
  end

  -- attack (O button = z)
  if btnp(4) then
   p.attack_t = 8
   p.attack_dir = p.facing
   try_attack()
  end

  -- gun (X button = x)
  if btnp(5) and p.ammo > 0 and p.gun_cd == 0 then
   p.ammo -= 1
   p.gun_cd = 15
   try_shoot()
  end
 else
  p.vx = 0
  p.vy = 0
 end

 -- apply velocity with bounds
 p.wx = mid(0, p.wx + p.vx, 16)
 p.wy = mid(0, p.wy + p.vy, 16)

 -- anim tick
 p.anim_t += 1
 if p.anim_t >= 6 then
  p.anim_t = 0
  p.anim_f = (p.anim_f + 1) % 2
 end
end

function try_attack()
 -- hit enemies in front
 local rx, ry = p.wx, p.wy
 if p.attack_dir == 1 then rx += 1.2
 elseif p.attack_dir == 3 then rx -= 1.2
 elseif p.attack_dir == 2 then ry += 1.2
 elseif p.attack_dir == 4 then ry -= 1.2
 end

 for e in all(enemies) do
  if e.alive and e.iframes == 0 then
   local d = abs(e.wx - rx) + abs(e.wy - ry)
   if d < 1.2 then
    e.hp -= 1
    e.iframes = 12
    -- knockback
    e.vx = (e.wx - p.wx) * 0.1
    e.vy = (e.wy - p.wy) * 0.1
    add(hits, {wx=e.wx, wy=e.wy, t=8})
    sfx(0)
    if e.hp <= 0 then
     e.alive = false
     chips += 5
     sfx(2)
    end
   end
  end
 end
end

function try_shoot()
 sfx(1)
 -- instant hitscan in facing direction
 local rx, ry = p.wx, p.wy
 local stepx, stepy = 0, 0
 if p.attack_dir == 1 then stepx = 0.5
 elseif p.attack_dir == 3 then stepx = -0.5
 elseif p.attack_dir == 2 then stepy = 0.5
 elseif p.attack_dir == 4 then stepy = -0.5
 end

 -- check 8 steps
 for i=1,8 do
  rx += stepx
  ry += stepy
  for e in all(enemies) do
   if e.alive and abs(e.wx - rx) < 0.7 and abs(e.wy - ry) < 0.7 then
    e.hp -= 2
    e.iframes = 12
    add(hits, {wx=e.wx, wy=e.wy, t=10})
    if e.hp <= 0 then
     e.alive = false
     chips += 5
    end
    return
   end
  end
 end
end

-- ============================================
-- enemies
-- ============================================
function make_thug(wx, wy)
 return {
  wx = wx,
  wy = wy,
  vx = 0,
  vy = 0,
  hp = 2,
  alive = true,
  iframes = 0,
  facing = 1,
  ai_state = "patrol",
  patrol_t = 0,
  attack_t = 0,
  anim_f = 0,
  anim_t = 0,
  kind = "thug",
 }
end

function make_drone(wx, wy)
 local e = make_thug(wx, wy)
 e.hp = 1
 e.kind = "drone"
 return e
end

function update_enemy(e)
 if not e.alive then return end
 if e.iframes > 0 then e.iframes -= 1 end
 if e.attack_t > 0 then e.attack_t -= 1 end

 -- apply knockback first
 if abs(e.vx) > 0.01 or abs(e.vy) > 0.01 then
  e.wx += e.vx
  e.wy += e.vy
  e.vx *= 0.7
  e.vy *= 0.7
  if abs(e.vx) < 0.01 then e.vx = 0 end
  if abs(e.vy) < 0.01 then e.vy = 0 end
 end

 if e.iframes > 0 then
  e.anim_t += 1
  if e.anim_t >= 4 then
   e.anim_t = 0
   e.anim_f = (e.anim_f + 1) % 2
  end
  return  -- stunned during iframes
 end

 -- distance to player
 local dx = p.wx - e.wx
 local dy = p.wy - e.wy
 local dist = sqrt(dx*dx + dy*dy)

 if dist < 6 then
  e.ai_state = "chase"
 elseif dist > 9 then
  e.ai_state = "patrol"
 end

 if e.ai_state == "chase" then
  if dist > 0.8 then
   local spd = (e.kind == "drone") and 0.06 or 0.04
   e.wx += (dx / dist) * spd
   e.wy += (dy / dist) * spd
   if abs(dx) > abs(dy) then
    e.facing = (dx > 0) and 1 or 3
   else
    e.facing = (dy > 0) and 2 or 4
   end
  else
   -- attack player
   if e.attack_t == 0 and p.iframes == 0 then
    e.attack_t = 30
    p.hp -= 1
    p.iframes = 30
    p.vx = (p.wx - e.wx) * 0.15
    p.vy = (p.wy - e.wy) * 0.15
    add(hits, {wx=p.wx, wy=p.wy, t=8})
    sfx(3)
   end
  end
 else
  -- patrol: random wander
  e.patrol_t -= 1
  if e.patrol_t <= 0 then
   e.patrol_t = 30 + flr(rnd(30))
   e.vx = (rnd(2) - 1) * 0.03
   e.vy = (rnd(2) - 1) * 0.03
  end
 end

 -- anim
 e.anim_t += 1
 if e.anim_t >= 8 then
  e.anim_t = 0
  e.anim_f = (e.anim_f + 1) % 2
 end

 -- bounds
 e.wx = mid(0, e.wx, 16)
 e.wy = mid(0, e.wy, 16)
end

-- ============================================
-- level
-- ============================================
function init_level()
 enemies = {}
 hits = {}
 chips = 0
 p = make_player()
 -- spawn enemies
 add(enemies, make_thug(10, 4))
 add(enemies, make_thug(12, 8))
 add(enemies, make_thug(6, 12))
 add(enemies, make_drone(14, 12))
 add(enemies, make_drone(8, 14))
 cam_x = p.wx
 cam_y = p.wy
end

-- ============================================
-- rendering
-- ============================================

-- iso world to screen, centered on cam
function project(wx, wy)
 local sx, sy = w2s(wx - cam_x, wy - cam_y)
 return sx + 64, sy + 56
end

function draw_floor()
 -- draw iso floor tiles in visible range
 for wy = 0, 16 do
  for wx = 0, 16 do
   local sx, sy = project(wx, wy)
   if sx > -16 and sx < 144 and sy > -8 and sy < 144 then
    -- draw diamond tile
    local checker = ((wx + wy) % 2 == 0)
    local col = checker and 1 or 13  -- dark blue / lavender
    -- diamond outline
    -- top point: sx, sy
    -- right: sx+8, sy+4
    -- bottom: sx, sy+8
    -- left: sx-8, sy+4
    -- fill via two triangles (use line scan)
    for dy = 0, 7 do
     local hw
     if dy < 4 then
      hw = dy * 2
     else
      hw = (7 - dy) * 2
     end
     line(sx - hw, sy + dy, sx + hw, sy + dy, col)
    end
    -- outline
    pset(sx, sy, 6)
   end
  end
 end
 -- arena border
 for wx = 0, 16 do
  local sx, sy = project(wx, -0.5)
  pset(sx, sy, 12)
  local sx2, sy2 = project(wx, 16.5)
  pset(sx2, sy2, 12)
 end
 for wy = 0, 16 do
  local sx, sy = project(-0.5, wy)
  pset(sx, sy, 12)
  local sx2, sy2 = project(16.5, wy)
  pset(sx2, sy2, 12)
 end
end

-- draw a sprite billboard at world pos with shadow
function draw_billboard(wx, wy, spr_idx, flip_x, h_off)
 local sx, sy = project(wx, wy)
 h_off = h_off or 0
 -- shadow ellipse (3x1)
 for dx = -3, 3 do
  pset(sx + dx, sy + 1, 0)
 end
 pset(sx - 4, sy, 0)
 pset(sx + 4, sy, 0)
 -- sprite anchored at bottom-center, raised by h_off
 spr(spr_idx, sx - 4, sy - 14 - h_off, 1, 2, flip_x)
end

function draw_player()
 if p.iframes > 0 and p.iframes % 4 < 2 then return end

 -- pick sprite based on state + facing
 local s
 local flip = false
 if p.attack_t > 0 then
  s = 4  -- attack sprite
  if p.attack_dir == 3 then flip = true end
 else
  -- idle/walk
  local moving = (abs(p.vx) > 0.01 or abs(p.vy) > 0.01)
  if moving then
   s = (p.anim_f == 0) and 2 or 6
  else
   s = 0
  end
  if p.facing == 3 then flip = true end
 end
 draw_billboard(p.wx, p.wy, s, flip)
end

function draw_enemy(e)
 if not e.alive then return end
 if e.iframes > 0 and e.iframes % 2 == 0 then
  -- white flash
  pal(8, 7); pal(2, 7); pal(14, 7); pal(15, 7)
 end
 local s
 local flip = (e.facing == 3)
 if e.kind == "thug" then
  s = (e.anim_f == 0) and 8 or 10
  draw_billboard(e.wx, e.wy, s, flip)
 else
  -- drone hovers higher
  s = 12
  draw_billboard(e.wx, e.wy, s, false, 8 + sin(frame/20) * 2)
 end
 pal()
end

function draw_hits()
 for i = #hits, 1, -1 do
  local h = hits[i]
  local sx, sy = project(h.wx, h.wy)
  local r = (8 - h.t)
  circ(sx, sy - 6, r, 10)
  circ(sx, sy - 6, r - 1, 9)
  h.t -= 1
  if h.t <= 0 then
   deli(hits, i)
  end
 end
end

function draw_hud()
 -- hearts
 for i = 0, p.max_hp - 1 do
  local col = (i < p.hp) and 8 or 5
  -- mini heart shape
  pset(2 + i*8, 2, col)
  pset(4 + i*8, 2, col)
  rectfill(1 + i*8, 3, 5 + i*8, 4, col)
  pset(2 + i*8, 5, col)
  pset(4 + i*8, 5, col)
  pset(3 + i*8, 5, col)
  pset(3 + i*8, 6, col)
 end
 -- ammo
 print("ammo "..p.ammo, 2, 9, 10)
 -- chips top right
 print("ch "..chips, 110, 2, 10)
 -- enemies counter
 local alive = 0
 for e in all(enemies) do
  if e.alive then alive += 1 end
 end
 print("enemy "..alive, 84, 9, 8)
end

function draw_title()
 cls(1)
 -- city silhouette
 for i = 0, 16 do
  local h = 20 + (i*7 + 3) % 25
  rectfill(i*8, 128-h, i*8+7, 128, 2)
 end
 -- lit windows
 srand(0)
 for i = 1, 40 do
  local x = flr(rnd(128))
  local y = 80 + flr(rnd(40))
  if (frame + i) % 90 < 60 then
   pset(x, y, 9 + (i % 3))
  end
 end
 -- title
 local t = "ctrl+alt"
 local t2 = "revenge!"
 -- shadow
 print(t, 64 - #t * 2 + 1, 30 + 1, 12)
 print(t2, 64 - #t2 * 2 + 1, 40 + 1, 12)
 -- main
 print(t, 64 - #t * 2, 30, 7)
 print(t2, 64 - #t2 * 2, 40, 7)
 -- subtitle
 print("iso edition", 40, 50, 9)
 -- blink
 if (frame // 20) % 2 == 0 then
  print("press 🅾️ to start", 28, 90, 7)
 end
 print("⬅️➡️⬆️⬇️ move  🅾️ punch  ❎ shoot",
       3, 110, 13)
 print("@gigsoftware 2087", 28, 120, 5)
end

function draw_win()
 cls(1)
 print("stage clear!", 38, 50, 11)
 print("chip earned: "..chips, 32, 64, 10)
 if (frame // 20) % 2 == 0 then
  print("press 🅾️ for menu", 28, 90, 7)
 end
end

function draw_gameover()
 cls(0)
 -- glitch red text
 local off = (frame // 4) % 3 - 1
 print("game over", 48 + off, 50, 8)
 print("game over", 48 - off, 50, 12)
 print("game over", 48, 50, 7)
 print("reboot in corso", 32, 64, 5)
 if frame > 60 and (frame // 20) % 2 == 0 then
  print("press 🅾️ to retry", 28, 90, 7)
 end
end

-- ============================================
-- main loop
-- ============================================
function _init()
 -- title screen at start
 state = "title"
 frame = 0
end

function _update()
 frame += 1

 if state == "title" then
  if btnp(4) or btnp(5) then
   init_level()
   state = "play"
   music(0)
  end
 elseif state == "play" then
  update_player()
  for e in all(enemies) do
   update_enemy(e)
  end
  -- smooth camera follow
  cam_x += (p.wx - cam_x) * 0.1
  cam_y += (p.wy - cam_y) * 0.1
  -- check win
  local alive = 0
  for e in all(enemies) do
   if e.alive then alive += 1 end
  end
  if alive == 0 then
   state = "win"
   frame = 0
   music(-1)
  end
  -- check lose
  if p.hp <= 0 then
   state = "gameover"
   frame = 0
   music(-1)
  end
 elseif state == "win" or state == "gameover" then
  if frame > 60 and (btnp(4) or btnp(5)) then
   state = "title"
   frame = 0
  end
 end
end

function _draw()
 if state == "title" then
  draw_title()
 elseif state == "play" then
  cls(0)
  draw_floor()
  -- depth sort: collect drawables
  local drawables = {{kind="p", obj=p, depth=p.wx + p.wy}}
  for e in all(enemies) do
   if e.alive then
    add(drawables, {kind="e", obj=e, depth=e.wx + e.wy})
   end
  end
  -- bubble sort small list
  for i = 1, #drawables do
   for j = i + 1, #drawables do
    if drawables[j].depth < drawables[i].depth then
     drawables[i], drawables[j] = drawables[j], drawables[i]
    end
   end
  end
  for d in all(drawables) do
   if d.kind == "p" then
    draw_player()
   else
    draw_enemy(d.obj)
   end
  end
  draw_hits()
  draw_hud()
 elseif state == "win" then
  draw_win()
 elseif state == "gameover" then
  draw_gameover()
 end
end
__gfx__
00000000000bb000000bb00000000000000bb000000bb000000bb00000000000000000000000000000000000000000000000000000000000000000000000000
000000000bbbbbb000bbbbbb00000000000bbbbb00bbbbb0000bbbbb0000000000000000000000000000000000000000000000000000000000000000000000000
0000000005bff550005bff5500000000005ddff5005ddff50005ddff500000000000000000000000000000000000000000000000000000000000000000000000
000000000c5ff550005ff550000000000c5ff5500005ff55000c5ff55000000000000000000000000000000000000000000000000000000000000000000000000
000000000c555550005555500000000000c5555000055550000c55550000000000000000000000000000000000000000000000000000000000000000000000000
00000000044f4ff000fff44000000000044fff000fff44400004ff4400000000000000000000000000000000000000000000000000000000000000000000000000
00000000444ffff404ffff44000000004444ff44ffff4444444fff4f0000000000000000000000000000000000000000000000000000000000000000000000000
0000000004fffff404fffff4000000000044ffff0fff44000044fff40000000000000000000000000000000000000000000000000000000000000000000000000
0000000004f4444404f44444000000000044444404f4444400044444000000000000000000000000000000000000000000000000000000000000000000000000
00000000044f44400444f440000000000044f44000444f4000044f440000000000000000000000000000000000000000000000000000000000000000000000000
0000000004f0040004f0040000000000004f004004f0040000040040000000000000000000000000000000000000000000000000000000000000000000000000
000000000510010005100100000000000051001005100100000510010000000000000000000000000000000000000000000000000000000000000000000000000
0000000005400500054005000000000000540500054005000005405000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000005000000000000000005500000050000000005500000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000eee0000000eee000000000000eee000000eee0000000000000bbbb00000000000000000000000000000000000000000000000000000000000000000
000000000eeeeeee00eeeeeee00000000eeeeeee0eeeeeee00000000000bb00bb0000000000000000000000000000000000000000000000000000000000000000
0000000005faaff5005faaff50000000005faaff05faaff50000000000bb0bb0bb000000000000000000000000000000000000000000000000000000000000000
0000000005faaff5005faaff5000000000fffff500fffff50000000000bb0bb0bb000000000000000000000000000000000000000000000000000000000000000
000000000c555550005555500000000000c5555000055550000000000bbbbeebbbb00000000000000000000000000000000000000000000000000000000000000
000000000388833000333880000000000038833000333880000000000bbbb88bbbb00000000000000000000000000000000000000000000000000000000000000
00000000338888830388888330000000038888333088888330000000bbb8aa8bbbbb0000000000000000000000000000000000000000000000000000000000000
0000000003888888038888880000000000338888333888880000000000bbbbbbbbb00000000000000000000000000000000000000000000000000000000000000
000000000388888803888888000000000033888833888888000000000bbbbbbbb000000000000000000000000000000000000000000000000000000000000000
0000000000338883033888330000000000038883033333330000000000bbbbb000000000000000000000000000000000000000000000000000000000000000000
0000000000040040000400400000000000040040004004000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000510010005100100000000000510010005100100000000000000000000000000000000000000000000000000000000000000000000000000000000000
000000000054050000540050000000000054050000540050000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000005500000050000000000000005500000005000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
__sfx__
000300000c5500e55012550155501a5501f5500c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050c5050
001000001f5501f5501d5501d5501d5501a5501a55018550155501555015550155501a5501a5501f5501f550000000000000000000000000000000000000000000000000000000000000000000000000000
000100002a5502a5502a5502c5502c5502c5502c5502c550000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
000200000e750167501d75024750187501070000750007000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
__music__
00 00010203

