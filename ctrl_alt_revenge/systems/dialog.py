# systems/dialog.py — Dialoghi a scelta multipla, parser JSON
import json
import os


class DialogSystem:
    """Gestisce dialoghi con nodi, scelte e flag globali."""

    def __init__(self):
        self.dialogs = {}
        self.current_dialog = None
        self.current_node = None
        self.active = False
        self.flags = {}
        self.selected_choice = 0
        self.typewriter_index = 0
        self.typewriter_speed = 2  # frame per carattere
        self.typewriter_timer = 0
        self.text_complete = False

    def load_dialog(self, dialog_id, filename=None):
        """Carica un dialogo da file JSON o da dati inline."""
        if filename:
            data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                     "data", "dialogs", filename)
            if os.path.exists(data_path):
                with open(data_path, "r", encoding="utf-8") as f:
                    dialog_data = json.load(f)
                self.dialogs[dialog_id] = dialog_data
                return True
        return False

    def add_dialog_data(self, dialog_id, nodes):
        """Aggiunge dati di dialogo direttamente."""
        self.dialogs[dialog_id] = nodes

    def start_dialog(self, dialog_id, start_node="start"):
        """Avvia un dialogo."""
        if dialog_id not in self.dialogs:
            return False
        self.current_dialog = self.dialogs[dialog_id]
        self.current_node = self._find_node(start_node)
        if not self.current_node:
            return False
        self.active = True
        self.selected_choice = 0
        self.typewriter_index = 0
        self.typewriter_timer = 0
        self.text_complete = False
        return True

    def _find_node(self, node_id):
        """Trova un nodo per ID."""
        for node in self.current_dialog:
            if node["id"] == node_id:
                return node
        return None

    def update(self, input_mgr, dt=1.0):
        """Aggiorna il sistema di dialogo."""
        if not self.active or not self.current_node:
            return

        # Typewriter
        if not self.text_complete:
            self.typewriter_timer += dt
            if self.typewriter_timer >= self.typewriter_speed:
                self.typewriter_timer = 0
                self.typewriter_index += 1
                text = self.current_node.get("text", "")
                if self.typewriter_index >= len(text):
                    self.text_complete = True

            # Skip typewriter con conferma
            if input_mgr.is_just_pressed("confirm"):
                self.text_complete = True
                self.typewriter_index = len(self.current_node.get("text", ""))
                return

        # Navigazione scelte
        choices = self.current_node.get("choices", [])
        if self.text_complete and choices:
            if input_mgr.is_just_pressed("up"):
                self.selected_choice = max(0, self.selected_choice - 1)
            elif input_mgr.is_just_pressed("down"):
                self.selected_choice = min(len(choices) - 1, self.selected_choice + 1)

            if input_mgr.is_just_pressed("confirm"):
                choice = choices[self.selected_choice]
                # Imposta flag se presente
                if "flag" in choice:
                    self.flags[choice["flag"]] = True
                # Vai al nodo successivo
                next_id = choice.get("next")
                if next_id:
                    self.current_node = self._find_node(next_id)
                    if self.current_node:
                        self.selected_choice = 0
                        self.typewriter_index = 0
                        self.typewriter_timer = 0
                        self.text_complete = False
                    else:
                        self.active = False
                else:
                    self.active = False
        elif self.text_complete and not choices:
            # Nodo senza scelte: conferma per proseguire
            if input_mgr.is_just_pressed("confirm"):
                next_id = self.current_node.get("next")
                if next_id:
                    self.current_node = self._find_node(next_id)
                    if self.current_node:
                        self.selected_choice = 0
                        self.typewriter_index = 0
                        self.typewriter_timer = 0
                        self.text_complete = False
                    else:
                        self.active = False
                else:
                    self.active = False

    def get_display_data(self):
        """Restituisce dati per il rendering del box dialogo."""
        if not self.active or not self.current_node:
            return None
        text = self.current_node.get("text", "")
        displayed_text = text[:self.typewriter_index]
        return {
            "speaker": self.current_node.get("speaker", "???"),
            "text": displayed_text,
            "full_text": text,
            "text_complete": self.text_complete,
            "choices": self.current_node.get("choices", []),
            "selected_choice": self.selected_choice,
        }

    def has_flag(self, flag_name):
        return self.flags.get(flag_name, False)
