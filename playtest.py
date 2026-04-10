#!/usr/bin/env python3
# playtest.py — Simula un playthrough completo con screenshot
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((1440, 810))
pygame.display.set_caption("CTRL+ALT REVENGE! — Playtest")
from ctrl_alt_revenge.main import Game
game = Game()

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(SAVE_DIR, exist_ok=True)
shot_count = 0

def screenshot(name):
    global shot_count
    shot_count += 1
    path = os.path.join(SAVE_DIR, f"{shot_count:02d}_{name}.png")
    pygame.image.save(screen, path)
    print(f"  Screenshot: {shot_count:02d}_{name}.png")

def tick(n=1):
    for _ in range(n):
        events = pygame.event.get()
        game.input_mgr.update(events)
        game.fsm.update(1.0)
        game.internal_surface.fill((13,11,43))
        game.fsm.draw(game.internal_surface)
        scaled = pygame.transform.scale(game.internal_surface, (1440, 810))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        game.clock.tick(60)

def press(key, hold=1):
    game.input_mgr.update([pygame.event.Event(pygame.KEYDOWN, key=key)])
    tick()
    for _ in range(hold):
        tick()
    game.input_mgr.update([pygame.event.Event(pygame.KEYUP, key=key)])

def hold_key(key, frames):
    for _ in range(frames):
        game.input_mgr.update([pygame.event.Event(pygame.KEYDOWN, key=key)])
        game.fsm.update(1.0)
        game.internal_surface.fill((13,11,43))
        game.fsm.draw(game.internal_surface)
        scaled = pygame.transform.scale(game.internal_surface, (1440, 810))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        game.clock.tick(60)
    game.input_mgr.update([pygame.event.Event(pygame.KEYUP, key=key)])

def run_right_jump(frames):
    """Corri a destra saltando gli ostacoli."""
    ps = game.fsm._states["play"]
    last_x = ps.player.x
    stuck = 0
    for i in range(frames):
        events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT)]
        if abs(ps.player.x - last_x) < 0.2 and ps.player.on_ground:
            stuck += 1
            if stuck > 3:
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        else:
            stuck = 0
        if i % 20 == 0:
            events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))
        elif i % 20 == 2:
            events.append(pygame.event.Event(pygame.KEYUP, key=pygame.K_j))
        game.input_mgr.update(events)
        game.fsm.update(1.0)
        game.internal_surface.fill((13,11,43))
        game.fsm.draw(game.internal_surface)
        scaled = pygame.transform.scale(game.internal_surface, (1440, 810))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        game.clock.tick(60)
        if game.fsm.current_name == "dialog":
            return "dialog"
        elif game.fsm.current_name != "play":
            return game.fsm.current_name
        last_x = ps.player.x
    return "ok"

# ==========================================
print("=== CTRL+ALT REVENGE! — PLAYTEST ===")
print()

# 1. MENU
print("1. Menu principale")
tick(30)
screenshot("menu")

# 2. COMANDI
print("2. Schermata comandi")
press(pygame.K_DOWN)
press(pygame.K_RETURN)
tick(20)
screenshot("comandi")
press(pygame.K_RETURN)
tick(5)

# 3. AVVIA GIOCO
print("3. Avvio gioco -> Dialogo intro")
press(pygame.K_UP)
press(pygame.K_RETURN)
tick(10)
screenshot("dialog_intro")

# 4. NAVIGA DIALOGO
print("4. Dialogo intro completo")
for _ in range(20):
    press(pygame.K_RETURN, 3)
    tick(5)
tick(10)
if game.fsm.current_name == "dialog":
    screenshot("dialog_scelte")
    for _ in range(10):
        press(pygame.K_RETURN, 3)
        tick(5)
tick(10)
screenshot("gameplay_inizio")

# 5. CORSA
print("5. Corsa a destra")
hold_key(pygame.K_RIGHT, 60)
screenshot("corsa")

# 6. SALTO
print("6. Salto e doppio salto")
press(pygame.K_SPACE, 3)
tick(10)
screenshot("salto_aria")
press(pygame.K_SPACE, 3)
tick(5)
screenshot("doppio_salto")
tick(30)

# 7. ACCOVACCIAMENTO
print("7. Accovacciamento")
press(pygame.K_DOWN, 10)
screenshot("accovacciato")
tick(5)

# 8. VERSO TERMINALE + HACK
print("8. Corsa verso terminale e hacking")
hold_key(pygame.K_RIGHT, 180)
tick(5)
screenshot("vicino_terminale")

# Chiudi eventuali dialoghi rimasti
for _ in range(30):
    if game.fsm.current_name != "dialog":
        break
    press(pygame.K_RETURN, 3)
    tick(5)
tick(10)

ps = game.fsm._states["play"]
# Forza lo stato play se ancora in dialog
if game.fsm.current_name != "play":
    ps.dialog_sys.active = False
    game.fsm.change("play")
    tick(10)

if ps.player.nearby_hackable:
    press(pygame.K_e)
    tick(15)
    screenshot("hacking")

    from collections import deque
    grid = ps.hacking.grid
    visited = set()
    queue = deque([(0, 0, [(0, 0)])])
    path = None
    while queue:
        r, c, p = queue.popleft()
        if (r, c) == (3, 3):
            path = p
            break
        if (r, c) in visited:
            continue
        visited.add((r, c))
        for dr, dc in [(0,1),(1,0),(0,-1),(-1,0)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < 4 and 0 <= nc < 4 and (nr,nc) not in visited and grid[nr][nc] != 1:
                queue.append((nr, nc, p + [(nr, nc)]))

    if path:
        dir_map = {(1,0): pygame.K_DOWN, (-1,0): pygame.K_UP, (0,1): pygame.K_RIGHT, (0,-1): pygame.K_LEFT}
        for i in range(1, len(path)):
            d = (path[i][0]-path[i-1][0], path[i][1]-path[i-1][1])
            press(dir_map[d], 2)
            tick(3)
        tick(10)
        screenshot("hack_riuscito")
    tick(20)

# 9. DOPO IL CANCELLO
print("9. Attraverso il cancello")
hold_key(pygame.K_RIGHT, 100)
screenshot("dopo_cancello")

# 10. COMBATTIMENTO
print("10. Combattimento")
result = run_right_jump(400)
screenshot("combattimento")

# 11. VISIONE TERMICA
print("11. Innesto: Visione Termica")
press(pygame.K_1)
tick(15)
screenshot("visione_termica")
press(pygame.K_1)

# 12. EMP
print("12. Innesto: EMP")
press(pygame.K_2)
tick(10)
screenshot("emp")

# 13. PAUSA
print("13. Pausa")
press(pygame.K_ESCAPE)
tick(15)
screenshot("pausa")
press(pygame.K_RETURN)
tick(5)

# 14. VERSO IL BOSS
print("14. Corsa verso il boss")
for chunk in range(5):
    result = run_right_jump(500)
    if result == "dialog":
        screenshot("boss_intro_dialog")
        for _ in range(20):
            press(pygame.K_RETURN, 3)
            tick(3)
        tick(10)
    elif result not in ("ok", "play"):
        game.fsm.change("play")

ps = game.fsm._states["play"]
print(f"   Player x={ps.player.x:.0f}")
screenshot("arena_boss")

# 15. BOSS FIGHT
print("15. Boss fight")
ps.player.iframes = 99999
ps.boss.hp = 4
ps.boss.intro_done = True

for frame in range(800):
    events = []
    dx = ps.boss.x - ps.player.x
    if abs(dx) > 20:
        events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT if dx > 0 else pygame.K_LEFT))
    if frame % 10 == 0:
        events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j))
    elif frame % 10 == 2:
        events.append(pygame.event.Event(pygame.KEYUP, key=pygame.K_j))
    if not events:
        events = pygame.event.get()
    game.input_mgr.update(events)
    game.fsm.update(1.0)
    game.internal_surface.fill((13,11,43))
    game.fsm.draw(game.internal_surface)
    scaled = pygame.transform.scale(game.internal_surface, (1440, 810))
    screen.blit(scaled, (0, 0))
    pygame.display.flip()
    game.clock.tick(60)

    if frame == 30:
        screenshot("boss_fight")

    if game.fsm.current_name == "level_complete":
        tick(30)
        screenshot("livello_completato")
        break
    elif game.fsm.current_name != "play":
        game.fsm.change("play")

# 16. GAME OVER
print("16. Game Over")
game.fsm.change("play", reload=True)
ps2 = game.fsm._states["play"]
ps2.triggered_dialogs = {"intro", "boss_intro"}
ps2.boss_intro_shown = True
tick(30)
ps2.player.hp = 0
ps2.player.alive = False
tick(5)
tick(90)
screenshot("game_over")

pygame.quit()
print()
print(f"Playtest completato! {shot_count} screenshot in {SAVE_DIR}")
