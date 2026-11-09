extends Node
## Stato globale della partita: punteggio, vite, opzioni della sessione e statistiche.

signal score_changed(score: int)
signal lives_changed(lives: int)

const START_LIVES := 3
## L'energia di GIG, una sola per tutta la partita (decisione A di Luigi, 8 novembre 2026).
const ENERGY_MAX := 120
## La carica della Scarica: la riempiono le bombole di ARIA+ (gameplay, recuperi). Il potere arriva più
## avanti nella storia; intanto la carica si tiene da parte.
const SCARICA_MAX := 100
const MAX_SCORE := 999999

var score: int = 0
## Vite rimaste, compresa quella in corso: a 0 è game over.
var lives: int = START_LIVES
var energy: int = ENERGY_MAX
var scarica: int = 0
## Contatori della partita (colpi per mossa, KO, prese...): li usano i test e la fine demo.
var stats: Dictionary[StringName, int] = {}
var options: SessionOptions = SessionOptions.new()
## I registri delle braccia già copiati, per id_testo (vedi Registri). Restano per tutta la sessione,
## anche con NUOVA PARTITA: un capitolo rigiocato mostra le basi già lette. Il salvataggio su disco
## ancora non c'è.
var registri: Dictionary[String, bool] = {}
var _quitting: bool = false


func _ready() -> void:
	options = SessionOptions.parse(OS.get_cmdline_user_args())
	for a in options.unknown:
		push_warning("Argomento sconosciuto: %s" % a)


func reset_run() -> void:
	score = 0
	lives = START_LIVES
	energy = ENERGY_MAX
	scarica = 0
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


## Una vita in più (l'abbonamento omaggio), fino a `max_lives`.
func add_life(n: int = 1, max_lives: int = START_LIVES) -> int:
	lives = mini(lives + n, maxi(max_lives, lives))
	lives_changed.emit(lives)
	return lives


## Dopo CONTINUA?: vite piene e punteggio azzerato, come nei cabinati.
func continue_run() -> void:
	score = 0
	lives = START_LIVES
	energy = ENERGY_MAX
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
