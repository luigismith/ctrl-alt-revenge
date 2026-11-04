extends Node
## Stato globale della partita: punteggio, vite, opzioni della sessione e statistiche.

signal score_changed(score: int)
signal lives_changed(lives: int)

const START_LIVES := 3
const MAX_SCORE := 999999

var score: int = 0
## Vite rimaste, compresa quella in corso: a 0 è game over.
var lives: int = START_LIVES
## Contatori della partita (colpi per mossa, KO, prese...): li usano i test e la fine demo.
var stats: Dictionary[StringName, int] = {}
var options: SessionOptions = SessionOptions.new()
var _quitting: bool = false


func _ready() -> void:
	options = SessionOptions.parse(OS.get_cmdline_user_args())
	for a in options.unknown:
		push_warning("Argomento sconosciuto: %s" % a)


func reset_run() -> void:
	score = 0
	lives = START_LIVES
	stats.clear()
	score_changed.emit(score)
	lives_changed.emit(lives)


func add_score(points: int) -> void:
	if points == 0:
		return
	score = mini(score + points, MAX_SCORE)
	score_changed.emit(score)


func lose_life() -> int:
	lives = maxi(lives - 1, 0)
	lives_changed.emit(lives)
	return lives


## Dopo CONTINUA?: vite piene e punteggio azzerato, come nei cabinati.
func continue_run() -> void:
	score = 0
	lives = START_LIVES
	count(&"continues")
	score_changed.emit(score)
	lives_changed.emit(lives)


## Chiude il gioco dopo aver zittito l'audio per qualche fotogramma. Con Movie Maker
## l'AudioServer libera i suoni fermati solo nei cicli di mix dei fotogrammi successivi:
## uscendo subito resterebbero "resources still in use at exit".
func quit_clean(code: int = 0) -> void:
	if _quitting:
		return
	_quitting = true
	Sfx.silence()
	Music.silence()
	for i in 10:
		await get_tree().process_frame
	get_tree().quit(code)


func count(stat: StringName, n: int = 1) -> void:
	stats[stat] = stats.get(stat, 0) + n


func stat(stat_name: StringName) -> int:
	return stats.get(stat_name, 0)
