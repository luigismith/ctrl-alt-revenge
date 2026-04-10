# systems/hacking.py — Mini-gioco hacking con griglia 4x4
import pygame
import random
from ctrl_alt_revenge.settings import (
    HACK_GRID_SIZE, HACK_TIME_LIMIT, HACK_SLOWMO_FACTOR,
    COLOR_BG_NIGHT, COLOR_GREEN_HACK, COLOR_RED_ALARM,
    COLOR_NEON_BLUE, COLOR_WHITE_UI, COLOR_DARK_GRAY, COLOR_NEON_PURPLE,
    INTERNAL_WIDTH, INTERNAL_HEIGHT,
)


class HackingMinigame:
    """Griglia 4x4 — traccia un percorso da START a END evitando nodi rossi."""

    def __init__(self):
        self.active = False
        self.grid_size = HACK_GRID_SIZE
        self.grid = []  # 0=vuoto, 1=rosso(blocco), 2=start, 3=end
        self.path = []  # nodi selezionati dal giocatore
        self.cursor = [0, 0]
        self.time_left = 0.0
        self.success = False
        self.failed = False
        self.target_entity = None
        self.cell_size = 16
        self.grid_offset_x = 0
        self.grid_offset_y = 0
        self._calc_layout()

    def _calc_layout(self):
        total_w = self.grid_size * self.cell_size
        total_h = self.grid_size * self.cell_size
        self.grid_offset_x = (INTERNAL_WIDTH - total_w) // 2
        self.grid_offset_y = (INTERNAL_HEIGHT - total_h) // 2

    def start(self, target_entity, difficulty=1):
        """Avvia il mini-gioco per un'entità hackable."""
        self.active = True
        self.success = False
        self.failed = False
        self.target_entity = target_entity
        self.time_left = HACK_TIME_LIMIT
        self.path = []
        self._generate_grid(difficulty)
        # Cursore su START
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.grid[r][c] == 2:
                    self.cursor = [r, c]
                    self.path = [(r, c)]
                    break

    def _generate_grid(self, difficulty):
        """Genera una griglia con START, END e ostacoli rossi."""
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]

        # START sempre in alto a sinistra
        self.grid[0][0] = 2
        # END sempre in basso a destra
        self.grid[self.grid_size - 1][self.grid_size - 1] = 3

        # Ostacoli rossi (più difficoltà = più ostacoli)
        num_red = 2 + difficulty * 2
        placed = 0
        attempts = 0
        while placed < num_red and attempts < 100:
            r = random.randint(0, self.grid_size - 1)
            c = random.randint(0, self.grid_size - 1)
            if self.grid[r][c] == 0:
                self.grid[r][c] = 1
                # Verifica che esista ancora un percorso valido
                if not self._path_exists():
                    self.grid[r][c] = 0
                else:
                    placed += 1
            attempts += 1

    def _path_exists(self):
        """BFS per verificare che START→END sia raggiungibile."""
        visited = set()
        queue = [(0, 0)]
        target = (self.grid_size - 1, self.grid_size - 1)
        while queue:
            r, c = queue.pop(0)
            if (r, c) == target:
                return True
            if (r, c) in visited:
                continue
            visited.add((r, c))
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                    if self.grid[nr][nc] != 1 and (nr, nc) not in visited:
                        queue.append((nr, nc))
        return False

    def update(self, input_mgr, dt=1.0):
        """Aggiorna il mini-gioco."""
        if not self.active:
            return

        # Timer
        self.time_left -= dt / 60.0  # converti frame in secondi
        if self.time_left <= 0:
            self.failed = True
            self.active = False
            if self.target_entity:
                self.target_entity.on_hack_fail()
            return

        # Movimento cursore
        moved = False
        nr, nc = self.cursor[0], self.cursor[1]
        if input_mgr.is_just_pressed("up"):
            nr -= 1
            moved = True
        elif input_mgr.is_just_pressed("down"):
            nr += 1
            moved = True
        elif input_mgr.is_just_pressed("left"):
            nc -= 1
            moved = True
        elif input_mgr.is_just_pressed("right"):
            nc += 1
            moved = True

        if moved and 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
            # Non puoi tornare indietro sul percorso (no incroci)
            if (nr, nc) not in self.path:
                if self.grid[nr][nc] == 1:
                    # Nodo rosso! Fallimento
                    self.failed = True
                    self.active = False
                    if self.target_entity:
                        self.target_entity.on_hack_fail()
                    return
                # Deve essere adiacente all'ultimo nodo
                last_r, last_c = self.path[-1]
                if abs(nr - last_r) + abs(nc - last_c) == 1:
                    self.cursor = [nr, nc]
                    self.path.append((nr, nc))

                    # Raggiunto END?
                    if self.grid[nr][nc] == 3:
                        self.success = True
                        self.active = False
                        if self.target_entity:
                            self.target_entity.on_hack_success()

        # ESC per annullare
        if input_mgr.is_just_pressed("pause"):
            self.active = False
            self.failed = True

    def draw(self, surface):
        """Disegna il mini-gioco sulla superficie interna."""
        if not self.active and not self.success and not self.failed:
            return

        # Sfondo semi-trasparente
        overlay = pygame.Surface((INTERNAL_WIDTH, INTERNAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # Titolo
        font = pygame.font.SysFont("consolas", 10)
        font_label = pygame.font.SysFont("consolas", 10)
        font_result = pygame.font.SysFont("consolas", 12)
        title = font.render("< HACK IN CORSO >", False, COLOR_GREEN_HACK)
        surface.blit(title, (INTERNAL_WIDTH // 2 - title.get_width() // 2,
                             self.grid_offset_y - 36))

        # Timer
        timer_color = COLOR_GREEN_HACK if self.time_left > 2 else COLOR_RED_ALARM
        timer_text = font.render(f"T-{self.time_left:.1f}s", False, timer_color)
        surface.blit(timer_text, (INTERNAL_WIDTH // 2 - timer_text.get_width() // 2,
                                  self.grid_offset_y - 18))

        # Griglia
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                x = self.grid_offset_x + c * self.cell_size
                y = self.grid_offset_y + r * self.cell_size
                cell = self.grid[r][c]

                # Sfondo cella
                if cell == 1:
                    color = COLOR_RED_ALARM
                elif cell == 2:
                    color = COLOR_NEON_BLUE
                elif cell == 3:
                    color = COLOR_NEON_PURPLE
                elif (r, c) in self.path:
                    color = COLOR_GREEN_HACK
                else:
                    color = COLOR_DARK_GRAY

                pygame.draw.rect(surface, color,
                                 (x + 1, y + 1, self.cell_size - 2, self.cell_size - 2))

                # Etichette
                if cell == 2:
                    s = font_label.render("S", False, COLOR_WHITE_UI)
                    surface.blit(s, (x + 4, y + 3))
                elif cell == 3:
                    e = font_label.render("E", False, COLOR_WHITE_UI)
                    surface.blit(e, (x + 4, y + 3))

                # Bordo griglia
                pygame.draw.rect(surface, (40, 40, 60),
                                 (x, y, self.cell_size, self.cell_size), 1)

        # Cursore
        cx = self.grid_offset_x + self.cursor[1] * self.cell_size
        cy = self.grid_offset_y + self.cursor[0] * self.cell_size
        pygame.draw.rect(surface, COLOR_WHITE_UI,
                         (cx, cy, self.cell_size, self.cell_size), 2)

        # Linea del percorso
        if len(self.path) > 1:
            points = []
            for r, c in self.path:
                px = self.grid_offset_x + c * self.cell_size + self.cell_size // 2
                py = self.grid_offset_y + r * self.cell_size + self.cell_size // 2
                points.append((px, py))
            pygame.draw.lines(surface, COLOR_GREEN_HACK, False, points, 2)

        # Messaggio risultato
        if self.success:
            msg = font_result.render("ACCESSO GARANTITO", False, COLOR_GREEN_HACK)
            surface.blit(msg, (INTERNAL_WIDTH // 2 - msg.get_width() // 2,
                               self.grid_offset_y + self.grid_size * self.cell_size + 14))
        elif self.failed:
            msg = font_result.render("ACCESSO NEGATO", False, COLOR_RED_ALARM)
            surface.blit(msg, (INTERNAL_WIDTH // 2 - msg.get_width() // 2,
                               self.grid_offset_y + self.grid_size * self.cell_size + 14))
