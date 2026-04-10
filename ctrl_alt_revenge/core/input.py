# core/input.py — Astrazione tastiera + gamepad
import pygame
from ctrl_alt_revenge.settings import INPUT_MAP, GAMEPAD_MAP


class InputManager:
    """Gestisce input da tastiera e gamepad con buffer per azioni frame-precise."""

    def __init__(self):
        self._pressed = {}
        self._just_pressed = {}
        self._just_released = {}
        self._gamepad = None
        self._init_gamepad()

    def _init_gamepad(self):
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self._gamepad = pygame.joystick.Joystick(0)
            self._gamepad.init()

    def update(self, events):
        """Aggiorna lo stato dell'input. Chiamare una volta per frame."""
        self._just_pressed.clear()
        self._just_released.clear()

        for event in events:
            if event.type == pygame.KEYDOWN:
                self._just_pressed[event.key] = True
                self._pressed[event.key] = True
            elif event.type == pygame.KEYUP:
                self._just_released[event.key] = True
                self._pressed.pop(event.key, None)
            elif event.type == pygame.JOYBUTTONDOWN:
                self._just_pressed[("joy", event.button)] = True
                self._pressed[("joy", event.button)] = True
            elif event.type == pygame.JOYBUTTONUP:
                self._just_released[("joy", event.button)] = True
                self._pressed.pop(("joy", event.button), None)
            elif event.type == pygame.JOYHATMOTION:
                # D-pad (hat) support
                hat_x, hat_y = event.value
                # Clear previous hat state
                for key in [("hat", "left"), ("hat", "right"), ("hat", "up"), ("hat", "down")]:
                    if key in self._pressed:
                        self._just_released[key] = True
                        self._pressed.pop(key, None)
                # Set new hat state
                if hat_x < 0:
                    self._just_pressed[("hat", "left")] = True
                    self._pressed[("hat", "left")] = True
                elif hat_x > 0:
                    self._just_pressed[("hat", "right")] = True
                    self._pressed[("hat", "right")] = True
                if hat_y > 0:
                    self._just_pressed[("hat", "up")] = True
                    self._pressed[("hat", "up")] = True
                elif hat_y < 0:
                    self._just_pressed[("hat", "down")] = True
                    self._pressed[("hat", "down")] = True

        # Trigger support for implants (axis 4 = left trigger, axis 5 = right trigger)
        if self._gamepad:
            try:
                left_trigger = self._gamepad.get_axis(4)
                right_trigger = self._gamepad.get_axis(5)
                lt_key = ("trigger", "left")
                rt_key = ("trigger", "right")
                if left_trigger > 0.5:
                    if lt_key not in self._pressed:
                        self._just_pressed[lt_key] = True
                    self._pressed[lt_key] = True
                else:
                    if lt_key in self._pressed:
                        self._just_released[lt_key] = True
                        self._pressed.pop(lt_key, None)
                if right_trigger > 0.5:
                    if rt_key not in self._pressed:
                        self._just_pressed[rt_key] = True
                    self._pressed[rt_key] = True
                else:
                    if rt_key in self._pressed:
                        self._just_released[rt_key] = True
                        self._pressed.pop(rt_key, None)
            except Exception:
                pass

    def is_held(self, action):
        """Tasto/pulsante tenuto premuto."""
        for key in INPUT_MAP.get(action, []):
            if key in self._pressed:
                return True
        if action in GAMEPAD_MAP:
            if ("joy", GAMEPAD_MAP[action]) in self._pressed:
                return True
        # D-pad (hat) support
        if action in ("left", "right", "up", "down"):
            if ("hat", action) in self._pressed:
                return True
        # Trigger support for implants
        if action == "implant1" and ("trigger", "left") in self._pressed:
            return True
        if action == "implant2" and ("trigger", "right") in self._pressed:
            return True
        # Asse analogico per movimento
        if self._gamepad:
            if action == "left" and self._gamepad.get_axis(0) < -0.3:
                return True
            if action == "right" and self._gamepad.get_axis(0) > 0.3:
                return True
            if action == "up" and self._gamepad.get_axis(1) < -0.3:
                return True
            if action == "down" and self._gamepad.get_axis(1) > 0.3:
                return True
        return False

    def is_just_pressed(self, action):
        """Tasto/pulsante appena premuto questo frame."""
        for key in INPUT_MAP.get(action, []):
            if key in self._just_pressed:
                return True
        if action in GAMEPAD_MAP:
            if ("joy", GAMEPAD_MAP[action]) in self._just_pressed:
                return True
        # D-pad (hat) support
        if action in ("left", "right", "up", "down"):
            if ("hat", action) in self._just_pressed:
                return True
        # Trigger support for implants
        if action == "implant1" and ("trigger", "left") in self._just_pressed:
            return True
        if action == "implant2" and ("trigger", "right") in self._just_pressed:
            return True
        return False

    def is_just_released(self, action):
        """Tasto/pulsante appena rilasciato questo frame."""
        for key in INPUT_MAP.get(action, []):
            if key in self._just_released:
                return True
        if action in GAMEPAD_MAP:
            if ("joy", GAMEPAD_MAP[action]) in self._just_released:
                return True
        # D-pad (hat) support
        if action in ("left", "right", "up", "down"):
            if ("hat", action) in self._just_released:
                return True
        # Trigger support for implants
        if action == "implant1" and ("trigger", "left") in self._just_released:
            return True
        if action == "implant2" and ("trigger", "right") in self._just_released:
            return True
        return False

    def get_axis_x(self):
        """Restituisce -1, 0, 1 per l'asse orizzontale."""
        val = 0
        if self.is_held("left"):
            val -= 1
        if self.is_held("right"):
            val += 1
        return val

    def get_axis_y(self):
        """Restituisce -1, 0, 1 per l'asse verticale."""
        val = 0
        if self.is_held("up"):
            val -= 1
        if self.is_held("down"):
            val += 1
        return val

    def rumble(self, low=0.5, high=0.5, duration=200):
        """Attiva vibrazione del gamepad se disponibile."""
        if self._gamepad:
            try:
                self._gamepad.rumble(low, high, duration)
            except Exception:
                pass
