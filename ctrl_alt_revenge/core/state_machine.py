# core/state_machine.py — FSM per stati di gioco
import pygame


class State:
    """Classe base per uno stato del gioco."""

    def __init__(self, game):
        self.game = game

    def enter(self, **kwargs):
        """Chiamato quando si entra nello stato."""
        pass

    def exit(self):
        """Chiamato quando si esce dallo stato."""
        pass

    def update(self, dt):
        """Aggiorna la logica dello stato."""
        pass

    def draw(self, surface):
        """Disegna lo stato sulla superficie interna."""
        pass

    def handle_events(self, events):
        """Gestisce eventi specifici dello stato."""
        pass


class StateMachine:
    """Macchina a stati finiti per gestire menu, gioco, pausa, hack, dialogo."""

    def __init__(self):
        self._states = {}
        self._current = None
        self._current_name = None
        self._previous_name = None

    def register(self, name, state):
        """Registra uno stato con un nome."""
        self._states[name] = state

    def change(self, name, **kwargs):
        """Cambia stato. Chiama exit sul vecchio, enter sul nuovo."""
        if self._current:
            self._current.exit()
        self._previous_name = self._current_name
        self._current_name = name
        self._current = self._states[name]
        self._current.enter(**kwargs)

    def update(self, dt):
        if self._current:
            self._current.update(dt)

    def draw(self, surface):
        if self._current:
            self._current.draw(surface)

    def handle_events(self, events):
        if self._current:
            self._current.handle_events(events)

    @property
    def current_name(self):
        return self._current_name

    @property
    def previous_name(self):
        return self._previous_name

    def go_back(self):
        """Torna allo stato precedente."""
        if self._previous_name:
            self.change(self._previous_name)
