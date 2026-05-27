# systems/perks.py — Upgrade/perk system with CHIP currency
"""Perks are persistent upgrades the player buys with CHIPs dropped by enemies.

CHIPs are earned by:
- Killing enemies (thug = 5, drone = 8, boss = 50)
- Picking up CHIP pickups in levels (+10)

Perks are bought in the Workshop (accessed from main menu or between levels).
Each perk has multiple levels — buying upgrades the perk to next tier.
"""
import pygame
from ctrl_alt_revenge.settings import (
    COLOR_BG_NIGHT, COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_WHITE_UI,
    COLOR_GREEN_HACK, COLOR_RED_ALARM, COLOR_NEON_PURPLE, COLOR_YELLOW,
    COLOR_DARK_GRAY, INTERNAL_WIDTH, INTERNAL_HEIGHT,
)


# Perk definitions: each has id, name, description, max_level, cost_per_level, effect_per_level
PERK_DEFINITIONS = [
    {
        "id": "vitality",
        "name": "Vitalita' Cibernetica",
        "desc": "+1 HP massimo per livello",
        "max_level": 4,
        "cost": [20, 40, 80, 150],
        "icon_color": (255, 46, 77),  # red heart
    },
    {
        "id": "strength",
        "name": "Pugno Servoassistito",
        "desc": "+1 danno pugno per livello",
        "max_level": 3,
        "cost": [30, 70, 150],
        "icon_color": (255, 122, 26),  # orange fist
    },
    {
        "id": "speed",
        "name": "Boost Gambe",
        "desc": "+10% velocita' di movimento per livello",
        "max_level": 3,
        "cost": [25, 60, 120],
        "icon_color": (0, 229, 255),  # cyan
    },
    {
        "id": "ammo",
        "name": "Caricatore Esteso",
        "desc": "+4 munizioni massime per livello",
        "max_level": 3,
        "cost": [25, 50, 100],
        "icon_color": (255, 220, 50),  # yellow
    },
    {
        "id": "gun_damage",
        "name": "Calibro Aumentato",
        "desc": "+1 danno proiettile per livello",
        "max_level": 3,
        "cost": [40, 90, 180],
        "icon_color": (200, 200, 220),  # silver
    },
    {
        "id": "iframes",
        "name": "Pelle Reattiva",
        "desc": "+10 frame di invincibilita' per livello",
        "max_level": 3,
        "cost": [30, 60, 100],
        "icon_color": (160, 32, 240),  # purple
    },
    {
        "id": "hacker",
        "name": "Hacker Esperto",
        "desc": "+1 secondo al timer hacking per livello",
        "max_level": 3,
        "cost": [35, 70, 140],
        "icon_color": (0, 255, 100),  # green
    },
    {
        "id": "regen",
        "name": "Rigenerazione",
        "desc": "Recupera 1 HP ogni 8s fuori combattimento",
        "max_level": 1,
        "cost": [200],
        "icon_color": (255, 180, 100),  # peach
    },
]


class PerkSystem:
    """Manages player progression with perks and CHIP currency.

    Persists between levels. Effects are applied to the Player when applying
    `apply_to_player(player)`.
    """

    def __init__(self):
        self.chips = 0
        self.perks = {p["id"]: 0 for p in PERK_DEFINITIONS}  # id -> current level
        self.regen_timer = 0  # for regen perk: frames since last damage
        self.regen_interval = 480  # 8s at 60fps

    def add_chips(self, amount):
        self.chips += amount

    def can_buy(self, perk_id):
        """Check if player has chips and perk is not maxed."""
        perk = next((p for p in PERK_DEFINITIONS if p["id"] == perk_id), None)
        if not perk:
            return False
        level = self.perks.get(perk_id, 0)
        if level >= perk["max_level"]:
            return False
        cost = perk["cost"][level]
        return self.chips >= cost

    def buy_perk(self, perk_id):
        """Buy next level of a perk. Returns True on success."""
        if not self.can_buy(perk_id):
            return False
        perk = next(p for p in PERK_DEFINITIONS if p["id"] == perk_id)
        level = self.perks.get(perk_id, 0)
        cost = perk["cost"][level]
        self.chips -= cost
        self.perks[perk_id] = level + 1
        return True

    def get_level(self, perk_id):
        return self.perks.get(perk_id, 0)

    def cost_next(self, perk_id):
        """Return cost of next upgrade level, or None if maxed."""
        perk = next((p for p in PERK_DEFINITIONS if p["id"] == perk_id), None)
        if not perk:
            return None
        level = self.perks.get(perk_id, 0)
        if level >= perk["max_level"]:
            return None
        return perk["cost"][level]

    def apply_to_player(self, player):
        """Apply all active perks to a Player instance.

        Called when level loads. Modifies player stats based on perk levels.
        """
        # Base stats from settings
        from ctrl_alt_revenge.settings import (
            PLAYER_HP, PLAYER_SPEED, PUNCH_DAMAGE, GUN_DAMAGE, GUN_AMMO_MAX,
            PLAYER_IFRAMES, HACK_TIME_LIMIT,
        )

        # Vitality: +1 max HP per level
        vit_level = self.perks.get("vitality", 0)
        new_max_hp = PLAYER_HP + vit_level
        # If hp is at full, keep it at new full; otherwise add the bonus
        if player.hp >= player.max_hp:
            player.max_hp = new_max_hp
            player.hp = new_max_hp
        else:
            player.max_hp = new_max_hp

        # Strength: +1 punch damage
        str_level = self.perks.get("strength", 0)
        player.punch_damage_bonus = str_level

        # Speed: +10% per level
        speed_level = self.perks.get("speed", 0)
        player.speed_mult = 1.0 + speed_level * 0.10

        # Ammo: +4 max per level
        ammo_level = self.perks.get("ammo", 0)
        player.gun_ammo_max = GUN_AMMO_MAX + ammo_level * 4
        if player.gun_ammo > player.gun_ammo_max:
            player.gun_ammo = player.gun_ammo_max

        # Gun damage: +1 per level
        gd_level = self.perks.get("gun_damage", 0)
        player.gun_damage_bonus = gd_level

        # I-frames: +10 per level
        if_level = self.perks.get("iframes", 0)
        player.iframes_bonus = if_level * 10

        # Hacker: +1s hack time per level (applied via PlayState)
        # The PlayState reads this on level load.

        # Regen: store flag on player
        player.has_regen = self.perks.get("regen", 0) > 0

    def update_regen(self, player, dt=1.0):
        """Tick regen if perk active. Call once per frame in update."""
        if not getattr(player, 'has_regen', False):
            return
        if player.hp <= 0 or player.hp >= player.max_hp:
            self.regen_timer = 0
            return
        # If player took damage recently, reset timer
        if player.iframes > 0:
            self.regen_timer = 0
            return
        self.regen_timer += dt
        if self.regen_timer >= self.regen_interval:
            self.regen_timer = 0
            player.hp = min(player.max_hp, player.hp + 1)


class WorkshopScreen:
    """UI for browsing and buying perks. Shown from the menu or between levels."""

    def __init__(self, perk_system, audio=None):
        self.perks = perk_system
        self.audio = audio
        self.selected = 0
        self.font_title = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_name = pygame.font.SysFont("consolas", 11, bold=True)
        self.font_desc = pygame.font.SysFont("consolas", 9)
        self.font_chips = pygame.font.SysFont("consolas", 12, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 9)
        self.message = ""
        self.message_timer = 0

    def update(self, input_mgr, dt=1.0):
        """Returns 'back' to close, None otherwise."""
        if input_mgr.is_just_pressed("up"):
            self.selected = (self.selected - 1) % len(PERK_DEFINITIONS)
            if self.audio:
                self.audio.play_sfx("menu_select")
        if input_mgr.is_just_pressed("down"):
            self.selected = (self.selected + 1) % len(PERK_DEFINITIONS)
            if self.audio:
                self.audio.play_sfx("menu_select")

        if input_mgr.is_just_pressed("confirm") or input_mgr.is_just_pressed("punch"):
            perk = PERK_DEFINITIONS[self.selected]
            if self.perks.buy_perk(perk["id"]):
                self.message = f"+{perk['name']} acquistato!"
                self.message_timer = 90
                if self.audio:
                    self.audio.play_sfx("hack_success")
            else:
                level = self.perks.get_level(perk["id"])
                if level >= perk["max_level"]:
                    self.message = "MAX LEVEL"
                else:
                    self.message = "CHIP insufficienti"
                self.message_timer = 60
                if self.audio:
                    self.audio.play_sfx("hack_fail")

        if input_mgr.is_just_pressed("pause") or input_mgr.is_just_pressed("hack"):
            return "back"

        if self.message_timer > 0:
            self.message_timer -= dt
        return None

    def draw(self, surface):
        surface.fill(COLOR_BG_NIGHT)

        # Title
        title = self.font_title.render("OFFICINA INNESTI", False, COLOR_NEON_BLUE)
        surface.blit(title, (INTERNAL_WIDTH // 2 - title.get_width() // 2, 8))

        # CHIP counter top-right
        chip_text = self.font_chips.render(f"CHIP: {self.perks.chips}",
                                            False, COLOR_YELLOW)
        surface.blit(chip_text,
                     (INTERNAL_WIDTH - chip_text.get_width() - 6, 8))

        # Perk list
        list_x = 8
        list_y = 32
        row_h = 22
        col_w = 152

        for i, perk in enumerate(PERK_DEFINITIONS):
            row = i % 4
            col = i // 4
            x = list_x + col * (col_w + 4)
            y = list_y + row * (row_h + 4)

            level = self.perks.get_level(perk["id"])
            is_selected = (i == self.selected)
            is_maxed = level >= perk["max_level"]

            # Background
            bg_color = (40, 38, 60) if is_selected else (25, 22, 45)
            pygame.draw.rect(surface, bg_color, (x, y, col_w, row_h))

            # Border (neon when selected)
            border_color = COLOR_NEON_ORANGE if is_selected else (60, 55, 80)
            pygame.draw.rect(surface, border_color, (x, y, col_w, row_h), 1)

            # Icon (colored square)
            pygame.draw.rect(surface, perk["icon_color"], (x + 3, y + 5, 8, 8))
            pygame.draw.rect(surface, (5, 3, 15), (x + 3, y + 5, 8, 8), 1)

            # Name
            name_color = COLOR_WHITE_UI if not is_maxed else COLOR_GREEN_HACK
            name = self.font_name.render(perk["name"], False, name_color)
            surface.blit(name, (x + 16, y + 2))

            # Level dots
            for lvl in range(perk["max_level"]):
                dot_color = perk["icon_color"] if lvl < level else (60, 55, 80)
                pygame.draw.rect(surface, dot_color,
                                (x + 16 + lvl * 6, y + 12, 4, 4))

            # Cost / status
            cost = self.perks.cost_next(perk["id"])
            if cost is None:
                cost_text = "MAX"
                cost_color = COLOR_GREEN_HACK
            else:
                cost_text = f"{cost}c"
                cost_color = COLOR_YELLOW if self.perks.chips >= cost else COLOR_RED_ALARM
            cost_surf = self.font_small.render(cost_text, False, cost_color)
            surface.blit(cost_surf,
                         (x + col_w - cost_surf.get_width() - 4, y + 12))

        # Selected perk description at bottom
        desc_y = INTERNAL_HEIGHT - 36
        pygame.draw.rect(surface, (20, 18, 40), (4, desc_y, INTERNAL_WIDTH - 8, 32))
        pygame.draw.rect(surface, COLOR_NEON_BLUE, (4, desc_y, INTERNAL_WIDTH - 8, 32), 1)

        sel_perk = PERK_DEFINITIONS[self.selected]
        desc = self.font_desc.render(sel_perk["desc"], False, COLOR_WHITE_UI)
        surface.blit(desc, (10, desc_y + 4))

        level = self.perks.get_level(sel_perk["id"])
        lvl_text = self.font_small.render(
            f"Livello attuale: {level}/{sel_perk['max_level']}",
            False, (180, 180, 200))
        surface.blit(lvl_text, (10, desc_y + 16))

        # Help
        help_text = self.font_small.render(
            "FRECCE: naviga | INVIO/J: compra | E/ESC: esci",
            False, (140, 140, 160))
        surface.blit(help_text,
                     (INTERNAL_WIDTH - help_text.get_width() - 6,
                      INTERNAL_HEIGHT - 12))

        # Message popup
        if self.message_timer > 0:
            msg = self.font_name.render(self.message, False, COLOR_NEON_ORANGE)
            mx = INTERNAL_WIDTH // 2 - msg.get_width() // 2
            my = INTERNAL_HEIGHT // 2 - 8
            pygame.draw.rect(surface, (20, 18, 40),
                            (mx - 4, my - 2, msg.get_width() + 8, msg.get_height() + 4))
            pygame.draw.rect(surface, COLOR_NEON_ORANGE,
                            (mx - 4, my - 2, msg.get_width() + 8, msg.get_height() + 4), 1)
            surface.blit(msg, (mx, my))
