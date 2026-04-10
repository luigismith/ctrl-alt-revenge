# systems/implants.py — Innesti modulari sbloccabili
import json
import os
import pygame
from ctrl_alt_revenge.settings import (
    EMP_COOLDOWN, BULLET_TIME_DURATION,
    COLOR_NEON_BLUE, COLOR_NEON_ORANGE, COLOR_NEON_PURPLE, COLOR_GREEN_HACK,
)


class Implant:
    """Singolo innesto con slot, descrizione ed effetto."""

    def __init__(self, data):
        self.id = data["id"]
        self.name = data["name"]
        self.description = data["description"]
        self.slot = data["slot"]
        self.unlocked = data.get("unlocked", False)
        self.active = False
        self.cooldown = 0
        self.max_cooldown = data.get("cooldown", 0)

    def can_activate(self):
        return self.unlocked and self.cooldown <= 0

    def activate(self):
        if self.can_activate():
            self.active = True
            self.cooldown = self.max_cooldown
            return True
        return False

    def update(self, dt=1.0):
        if self.cooldown > 0:
            self.cooldown -= dt


class ImplantSystem:
    """Gestisce tutti gli innesti del player."""

    def __init__(self):
        self.implants = {}
        self.equipped = [None, None, None, None]  # 4 slot rapidi
        self._load_implants()

    def _load_implants(self):
        """Carica innesti da JSON o usa i default."""
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 "data", "implants.json")
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                implant_list = json.load(f)
        else:
            implant_list = self._default_implants()

        for imp_data in implant_list:
            imp = Implant(imp_data)
            self.implants[imp.id] = imp

        # Equip di default
        ids = list(self.implants.keys())
        for i, imp_id in enumerate(ids[:4]):
            self.equipped[i] = imp_id

    def _default_implants(self):
        return [
            {
                "id": "thermal_vision",
                "name": "Visione Termica",
                "description": "Evidenzia nemici dietro i muri",
                "slot": "occhi",
                "cooldown": 0,
                "unlocked": True
            },
            {
                "id": "emp_shot",
                "name": "Proiettile EMP",
                "description": "Stordisce nemici cibernetici. Cooldown 6s.",
                "slot": "braccia",
                "cooldown": EMP_COOLDOWN,
                "unlocked": True
            },
            {
                "id": "bullet_time",
                "name": "Bullet Time",
                "description": "3 secondi di slow-mo. Ricarica a uccisione.",
                "slot": "core",
                "cooldown": BULLET_TIME_DURATION * 3,
                "unlocked": True
            },
            {
                "id": "double_jump",
                "name": "Doppio Salto Servoassistito",
                "description": "Sblocca il double jump",
                "slot": "gambe",
                "cooldown": 0,
                "unlocked": True
            },
        ]

    def use_implant(self, slot_index, player, game_state):
        """Attiva l'innesto nello slot indicato."""
        if slot_index < 0 or slot_index >= len(self.equipped):
            return False
        imp_id = self.equipped[slot_index]
        if not imp_id or imp_id not in self.implants:
            return False

        imp = self.implants[imp_id]
        if not imp.can_activate():
            return False

        if imp.id == "thermal_vision":
            player.thermal_vision = not player.thermal_vision
            return True

        elif imp.id == "emp_shot":
            imp.activate()
            return "emp_shot"

        elif imp.id == "bullet_time":
            imp.activate()
            player.bullet_time_active = True
            player.bullet_time_timer = BULLET_TIME_DURATION
            return True

        elif imp.id == "double_jump":
            player.can_double_jump = True
            return True

        return False

    def update(self, dt=1.0):
        for imp in self.implants.values():
            imp.update(dt)

    def on_enemy_killed(self, player):
        """Ricarica bullet time su uccisione."""
        bt = self.implants.get("bullet_time")
        if bt:
            bt.cooldown = 0

    def get_equipped_info(self):
        """Restituisce info per l'HUD."""
        info = []
        for imp_id in self.equipped:
            if imp_id and imp_id in self.implants:
                imp = self.implants[imp_id]
                info.append({
                    "name": imp.name,
                    "ready": imp.can_activate(),
                    "cooldown_ratio": imp.cooldown / max(imp.max_cooldown, 1) if imp.max_cooldown > 0 else 0,
                })
            else:
                info.append(None)
        return info
