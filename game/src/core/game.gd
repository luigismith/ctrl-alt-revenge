extends Node
## Stato globale della partita: punteggio, vite, cambio di schermata.

signal score_changed(score: int)
signal lives_changed(lives: int)

const START_LIVES := 3

var score: int = 0
var lives: int = START_LIVES


func reset_run() -> void:
	score = 0
	lives = START_LIVES
	score_changed.emit(score)
	lives_changed.emit(lives)


func add_score(points: int) -> void:
	score = mini(score + points, 999999)
	score_changed.emit(score)
