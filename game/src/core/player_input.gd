class_name PlayerInput
extends RefCounted
## Fonte degli ingressi di GIG, uno per tick di simulazione: dal vivo (tastiera e joypad),
## da un replay oppure da una funzione (pilota automatico o test).
## Se è attivo un registratore, ogni tick viene anche salvato nel replay di uscita.

enum Mode { LIVE, REPLAY, PROVIDER, NONE }

var mode: Mode = Mode.NONE
var replay: Replay
## Callable(tick: int) -> int con i tasti tenuti: per il pilota automatico e i test.
var provider: Callable
## Riferimento forte all'oggetto del provider (una Callable non tiene in vita un RefCounted).
var provider_owner: RefCounted
var recorder: Replay

var _prev_held: int = 0


static func live() -> PlayerInput:
	var p := PlayerInput.new()
	p.mode = Mode.LIVE
	return p


static func from_replay(r: Replay) -> PlayerInput:
	var p := PlayerInput.new()
	p.mode = Mode.REPLAY
	p.replay = r
	r.rewind()
	return p


static func from_provider(fn: Callable, owner: RefCounted = null) -> PlayerInput:
	var p := PlayerInput.new()
	p.mode = Mode.PROVIDER
	p.provider = fn
	p.provider_owner = owner
	return p


## Ingressi del tick `tick` della simulazione.
func next_frame(tick: int) -> InputFrame:
	var frame: InputFrame
	match mode:
		Mode.LIVE:
			var held: int = Controls.sample_held()
			var pressed: int = (held & ~_prev_held) | Controls.sample_just_pressed()
			frame = InputFrame.new(held, pressed)
		Mode.REPLAY:
			frame = replay.frame_at(tick)
		Mode.PROVIDER:
			var held: int = int(provider.call(tick))
			frame = InputFrame.new(held, held & ~_prev_held)
		_:
			frame = InputFrame.new()
	_prev_held = frame.held
	if recorder != null:
		recorder.record(tick, frame.held, frame.pressed)
	return frame


func replay_finished(tick: int) -> bool:
	return mode == Mode.REPLAY and replay.finished(tick)


## Riallinea i tasti tenuti con lo stato attuale, dopo la pausa o CONTINUA?: un tasto ancora
## tenuto dal menu (ATTACCO per confermare, A del joypad) non conta come appena premuto nel
## primo tick di gioco. Vale solo dal vivo: replay e provider non passano dai menu.
func resync() -> void:
	if mode == Mode.LIVE:
		_prev_held = Controls.sample_held()
