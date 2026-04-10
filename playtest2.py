#!/usr/bin/env python3
# playtest2.py — Screenshot precisi di ogni area del gioco
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pygame
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((960, 720))
pygame.display.set_caption("CTRL+ALT REVENGE! — Playtest")
from ctrl_alt_revenge.main import Game
game = Game()

SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(SAVE_DIR, exist_ok=True)
shot = 0

def snap(name):
    global shot
    shot += 1
    path = os.path.join(SAVE_DIR, f"{shot:02d}_{name}.png")
    game.internal_surface.fill((13,11,43))
    game.fsm.draw(game.internal_surface)
    scaled = pygame.transform.scale(game.internal_surface, (960, 720))
    screen.blit(scaled, (0, 0))
    pygame.display.flip()
    pygame.image.save(screen, path)
    print(f"  {shot:02d}_{name}.png")

def sim(n):
    for _ in range(n):
        game.input_mgr.update(pygame.event.get())
        game.fsm.update(1.0)
        game.internal_surface.fill((13,11,43))
        game.fsm.draw(game.internal_surface)
        scaled = pygame.transform.scale(game.internal_surface, (960, 720))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        game.clock.tick(60)

def keys(key_list, frames=1):
    for _ in range(frames):
        evts = [pygame.event.Event(pygame.KEYDOWN, key=k) for k in key_list]
        game.input_mgr.update(evts)
        game.fsm.update(1.0)
        game.internal_surface.fill((13,11,43))
        game.fsm.draw(game.internal_surface)
        scaled = pygame.transform.scale(game.internal_surface, (960, 720))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        game.clock.tick(60)
    game.input_mgr.update([pygame.event.Event(pygame.KEYUP, key=k) for k in key_list])

print("=== CTRL+ALT REVENGE! PLAYTEST ===\n")

# 1. MENU
print("Menu principale:")
sim(30)
snap("menu")

# 2. COMANDI
print("Comandi:")
keys([pygame.K_DOWN], 2)
keys([pygame.K_RETURN], 2)
sim(15)
snap("comandi")
keys([pygame.K_RETURN], 2)
sim(5)
keys([pygame.K_UP], 2)

# 3. GAMEPLAY — skip dialoghi con forza diretta
print("Gameplay:")
game.fsm.change("play", reload=True)
ps = game.fsm._states["play"]
# Forza skip di tutti i dialoghi
ps.triggered_dialogs = {"intro", "boss_intro"}
ps.boss_intro_shown = True
ps.dialog_sys.active = False
sim(30)  # atterraggio
snap("gameplay_inizio")

# 4. CORSA
print("Corsa:")
keys([pygame.K_RIGHT], 80)
snap("corsa")

# 5. SALTO
print("Salto:")
keys([pygame.K_SPACE], 2)
sim(12)
snap("salto")
sim(30)

# 6. DOPPIO SALTO
print("Doppio salto:")
keys([pygame.K_SPACE], 2)
sim(8)
keys([pygame.K_SPACE], 2)
sim(6)
snap("doppio_salto")
sim(30)

# 7. ACCOVACCIATO
print("Accovacciato:")
keys([pygame.K_DOWN], 15)
snap("accovacciato")
sim(5)

# 8. PUGNO
print("Pugno:")
keys([pygame.K_j], 2)
sim(3)
snap("pugno")
sim(10)

# 9. CALCIO
print("Calcio:")
keys([pygame.K_k], 2)
sim(3)
snap("calcio")
sim(10)

# 10. TERMINALE E HACK
print("Terminale:")
# Corri fino al terminale
keys([pygame.K_RIGHT], 150)
sim(5)
snap("vicino_terminale")

# Hack forzato
if ps.player.nearby_hackable:
    keys([pygame.K_e], 2)
    sim(15)
    snap("hacking")
    # Risolvi il puzzle con BFS
    from collections import deque
    grid = ps.hacking.grid
    visited = set()
    queue = deque([(0, 0, [(0, 0)])])
    path = None
    while queue:
        r, c, p = queue.popleft()
        if (r, c) == (3, 3): path = p; break
        if (r, c) in visited: continue
        visited.add((r, c))
        for dr, dc in [(0,1),(1,0),(0,-1),(-1,0)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < 4 and 0 <= nc < 4 and (nr,nc) not in visited and grid[nr][nc] != 1:
                queue.append((nr, nc, p + [(nr, nc)]))
    if path:
        dir_map = {(1,0): pygame.K_DOWN, (-1,0): pygame.K_UP, (0,1): pygame.K_RIGHT, (0,-1): pygame.K_LEFT}
        for i in range(1, len(path)):
            d = (path[i][0]-path[i-1][0], path[i][1]-path[i-1][1])
            keys([dir_map[d]], 3)
            sim(2)
        sim(10)
        snap("hack_riuscito")
    # Torna a play
    if game.fsm.current_name != "play":
        ps.dialog_sys.active = False
        game.fsm.change("play")
    sim(10)
else:
    print("  (terminale non in range, skip)")

# 11. DOPO IL CANCELLO
print("Dopo cancello:")
keys([pygame.K_RIGHT], 120)
snap("dopo_cancello")

# 12. COMBAT — corri verso thug con salto automatico
print("Combattimento:")
last_x = ps.player.x
for i in range(600):
    kk = [pygame.K_RIGHT]
    if abs(ps.player.x - last_x) < 0.2 and ps.player.on_ground:
        kk.append(pygame.K_SPACE)
    if i % 12 == 0:
        kk.append(pygame.K_j)
    keys(kk, 1)
    if game.fsm.current_name != "play":
        game.fsm.change("play")
    last_x = ps.player.x
snap("combattimento")

# 13. VISIONE TERMICA
print("Visione termica:")
keys([pygame.K_1], 2)
sim(15)
snap("visione_termica")
keys([pygame.K_1], 2)  # toggle off

# 14. EMP
print("EMP:")
keys([pygame.K_2], 2)
sim(8)
snap("emp")

# 15. PAUSA
print("Pausa:")
game.fsm.change("pause")
sim(15)
snap("pausa")
game.fsm.change("play")
sim(5)

# 16. DIALOGO (forzato)
print("Dialogo:")
from ctrl_alt_revenge.data.dialogs.level_01_dialogs import DIALOG_INTRO
ps.dialog_sys.add_dialog_data("demo", DIALOG_INTRO)
ps.dialog_sys.start_dialog("demo")
game.fsm.change("dialog")
# Avanza typewriter
for _ in range(40):
    keys([pygame.K_RETURN], 2)
    sim(3)
snap("dialogo")
ps.dialog_sys.active = False
game.fsm.change("play")
sim(5)

# 17. BOSS ARENA — teleporta
print("Boss arena:")
ps.player.x = 155 * 16
ps.player.y = 24 * 16
ps.boss.intro_done = True
sim(30)
snap("arena_boss")

# 18. BOSS FIGHT
print("Boss fight:")
ps.player.iframes = 99999
for i in range(120):
    kk = []
    dx = ps.boss.x - ps.player.x
    if abs(dx) > 20:
        kk.append(pygame.K_RIGHT if dx > 0 else pygame.K_LEFT)
    if i % 10 == 0:
        kk.append(pygame.K_j)
    if kk:
        keys(kk, 1)
    else:
        sim(1)
    if game.fsm.current_name != "play":
        if game.fsm.current_name == "level_complete":
            break
        game.fsm.change("play")
snap("boss_fight")

# 19. LEVEL COMPLETE
print("Level complete:")
ps.boss.hp = 0
ps.boss.alive = False
sim(5)
if game.fsm.current_name == "level_complete":
    sim(30)
    snap("livello_completato")
else:
    game.fsm.change("level_complete")
    sim(30)
    snap("livello_completato")

# 20. GAME OVER
print("Game over:")
game.fsm.change("game_over")
sim(90)
snap("game_over")

# 21. HACKING (forzato pulito)
print("Hacking minigame:")
game.fsm.change("play", reload=True)
ps = game.fsm._states["play"]
ps.triggered_dialogs = {"intro", "boss_intro"}
ps.boss_intro_shown = True
sim(30)
ps.hacking.start(None, 1)
ps.hacking.target_entity = None
game.fsm.change("hack")
sim(15)
snap("hacking_minigame")

pygame.quit()
print(f"\nPlaytest completato! {shot} screenshot salvati.")
