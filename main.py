# Entry point — CTRL+ALT REVENGE!
# Esegui con: python main.py
import sys
import os

# Assicurati che il path del progetto sia nel Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ctrl_alt_revenge.main import Game

if __name__ == "__main__":
    game = Game()
    game.run()
