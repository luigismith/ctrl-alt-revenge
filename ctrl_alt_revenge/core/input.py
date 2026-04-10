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

    def is_held(self, action):
        """Tasto/pulsante tenuto premuto."""
        for key in INPUT_MAP.get(action, []):
            if key in self._pressed:
                return True
        if action in GAMEPAD_MAP:
            if ("joy", GAMEPAD_MAP[action]) in self._pressed:
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
        return False

    def is_just_released(self, action):
        """Tasto/pulsante appena rilasciato questo frame."""
        for key in INPUT_MAP.get(action, []):
            if key in self._just_released:
                return True
        if action in GAMEPAD_MAP:
            if ("joy", GAMEPAD_MAP[action]) in self._just_released:
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
