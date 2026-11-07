extends Node
## Scena principale: flusso delle schermate titolo → livello → fine demo → crediti → titolo.
## NUOVA PARTITA: titolo → prologo → capitolo 2, «Il Wind Day» (lo slice) → fine demo; dai CAPITOLI ogni pezzo si gioca da solo.
## Argomenti utente (dopo "--"): vedi SessionOptions (--autostart, --replay, --seed, --record...).

const FADE_TICKS := 16
## Dal prologo allo slice, in NUOVA PARTITA: una dissolvenza lenta, con la musica che sfuma insieme.
const FADE_SLOW := 50
## Dopo il prologo, in NUOVA PARTITA: cosa viene adesso, sotto «FINE DEL PROLOGO», una riga per voce. Il
## capitolo 1 non c'è ancora, si va dritti al 2, lo slice (la sua scheda dice «2 · IL WIND DAY»).
## Testo approvato da car-storia il 7 novembre 2026.
const AFTER_PROLOGUE: PackedStringArray = [
	"Il capitolo 1, I tetti dei Tamburi, è in arrivo.",
	"Adesso si gioca il capitolo 2: Il Wind Day.",
]

var _screen: Node
var _fade_layer: CanvasLayer
var _fade: ColorRect
var _fade_t: int = 0
var _fade_dir: int = 0
## Tick della dissolvenza in corso, in uscita e in entrata.
var _fade_len: int = FADE_TICKS
var _pending: Callable
## Richiesta arrivata durante la dissolvenza in entrata: parte appena questa finisce.
var _queued: Callable


func _ready() -> void:
	_fade_layer = CanvasLayer.new()
	_fade_layer.layer = 50
	add_child(_fade_layer)
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.size = View.SIZE
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade_layer.add_child(_fade)
	if Game.options.new_game:
		_start_new_game()
	elif Game.options.prologue:
		_start_prologue()
	elif Game.options.room:
		_start_room()
	elif Game.options.autostart:
		_start_level()
	else:
		_show_title()


func _physics_process(_delta: float) -> void:
	if _fade_dir == 0:
		return
	_fade_t += 1
	var a := clampf(float(_fade_t) / _fade_len, 0.0, 1.0)
	_fade.color.a = a if _fade_dir > 0 else 1.0 - a
	if _fade_t >= _fade_len:
		if _fade_dir > 0:
			_fade_dir = -1
			_fade_t = 0
			if _pending.is_valid():
				var c := _pending
				_pending = Callable()
				c.call()
		else:
			_fade_dir = 0
			_fade.color.a = 0.0
			_fade_len = FADE_TICKS
			if _queued.is_valid():
				var q := _queued
				_queued = Callable()
				_go(q)


## Cambia schermata con una dissolvenza al nero. Durante l'uscita verso un'altra schermata le
## richieste nuove si ignorano (vince la prima); durante l'entrata si mettono in coda, così una
## conferma data negli ultimi tick della dissolvenza non va persa. `ticks`: quanto dura ognuna delle due metà.
func _go(next: Callable, ticks: int = FADE_TICKS) -> void:
	if _fade_dir > 0:
		return
	if _fade_dir < 0:
		_queued = next
		return
	_pending = next
	_fade_dir = 1
	_fade_t = 0
	_fade_len = ticks


func _set_screen(s: Node) -> void:
	if _screen != null:
		# La schermata vecchia non deve più ricevere tick prima di essere liberata.
		_screen.process_mode = Node.PROCESS_MODE_DISABLED
		_screen.queue_free()
	_screen = s
	add_child(s)
	move_child(s, 0)


func _show_title() -> void:
	var t := TitleScreen.new()
	t.new_game.connect(func() -> void: _go(_start_new_game))
	t.start_game.connect(func() -> void: _go(_start_level))
	t.show_credits.connect(func() -> void: _go(_show_credits))
	t.test_room.connect(func() -> void: _go(_start_room))
	t.prologue.connect(func() -> void: _go(_start_prologue))
	t.quit_game.connect(func() -> void: Game.quit_clean())
	_set_screen(t)


func _show_credits() -> void:
	var c := CreditsScreen.new()
	var layer := CanvasLayer.new()
	layer.add_child(c)
	c.done.connect(func() -> void: _go(_show_title))
	_set_screen(layer)


## `after_prologue`: arriva da NUOVA PARTITA. Un replay o il pilota della riga di comando erano del
## prologo, non dello slice: qui si gioca coi tasti.
func _start_level(after_prologue: bool = false) -> void:
	Game.reset_run()
	var o := Game.options
	var opts := {"seed": o.level_seed, "record": o.record_path}
	if o.start_x >= 0.0:
		opts["start_x"] = o.start_x
	var input: PlayerInput = null
	if o.replay_path != "" and not after_prologue:
		var r := Replay.load_file(o.replay_path)
		if r == null:
			push_error("Replay non leggibile: %s" % o.replay_path)
		else:
			input = PlayerInput.from_replay(r)
			if not o.seed_given:
				opts["seed"] = r.level_seed
			if r.start.has("x"):
				opts["start_x"] = float(r.start["x"])
			if r.start.has("y"):
				opts["start_y"] = float(r.start["y"])
			opts["card"] = not r.start.has("x")
	var lvl := Level.new()
	if input == null and o.autopilot != "" and not after_prologue:
		var pilot := Autopilot.new(StringName(o.autopilot))
		input = PlayerInput.from_provider(pilot.decide, pilot)
		pilot.level = lvl
	opts["input"] = input if input != null else PlayerInput.live()
	lvl.configure(opts)
	lvl.finished.connect(_on_level_finished)
	lvl.quit_to_title.connect(func() -> void: _go(_show_title))
	lvl.restart_requested.connect(func() -> void: _go(_start_level))
	lvl.game_over.connect(func() -> void: _go(_show_title))
	_set_screen(lvl)


## NUOVA PARTITA: il prologo e, alla fine, lo slice, con la dissolvenza lenta.
func _start_new_game() -> void:
	_start_prologue(true)


## Il prologo in grigio: gira sul motore della stanza di prova. `then_level`: alla fine prosegue nello slice
## (NUOVA PARTITA) invece di chiudere con la fine della demo (CAPITOLI → PROLOGO).
func _start_prologue(then_level: bool = false) -> void:
	var p := Prologue.new()
	if then_level:
		p.next_title = AFTER_PROLOGUE
	_start_room(p)
	p.prologue_finished.connect(func(result: Dictionary) -> void:
		if Game.options.quit_at_end and not then_level:
			print("Prologo finito: tick %d" % int(result.get("ticks", 0)))
			print("DONE")
			Game.quit_clean(0)
			return
		if then_level:
			Music.stop(FADE_SLOW / 60.0)
			_go(_start_level.bind(true), FADE_SLOW)
		else:
			_go(func() -> void: _show_demo_end(result)))


## La stanza di prova in grigio: ESC o START torna al titolo.
func _start_room(room: TestRoom = null) -> void:
	if room == null:
		room = TestRoom.new()
	var o := Game.options
	var input := PlayerInput.live()
	var pilot: RoomPilot = null
	var record := ""
	if o.replay_path != "":
		var r := Replay.load_file(o.replay_path)
		if r == null:
			push_error("Replay non leggibile: %s" % o.replay_path)
		else:
			input = PlayerInput.from_replay(r)
	elif o.autopilot == "stanza":
		pilot = RoomPilot.new()
		input = PlayerInput.from_provider(pilot.decide, pilot)
	elif o.record_path != "":
		record = o.record_path
	elif OS.is_debug_build():
		record = TestRoom.SESSION_DIR.path_join(Time.get_datetime_string_from_system().replace(":", "-") + ".json")
	room.configure({"input": input, "pilot": pilot, "record": record})
	room.quit_to_title.connect(func() -> void: _go(_show_title))
	room.replay_done.connect(func() -> void:
		if o.quit_at_end:
			print("DONE")
			Game.quit_clean(0))
	_set_screen(room)


func _on_level_finished(result: Dictionary) -> void:
	if Game.options.quit_at_end:
		var lvl := _screen as Level
		print("Livello finito: punteggio %d, tick %d, hash %s" % [result["score"], result["ticks"], lvl.final_hash() if lvl != null else ""])
		print("DONE")
		Game.quit_clean(0)
		return
	_go(func() -> void: _show_demo_end(result))


func _show_demo_end(result: Dictionary) -> void:
	var d := DemoEndScreen.new()
	d.score = int(result.get("score", 0))
	d.ticks = int(result.get("ticks", 0))
	d.prologue = bool(result.get("prologue", false))
	var layer := CanvasLayer.new()
	layer.add_child(d)
	d.done.connect(func() -> void: _go(_show_credits))
	_set_screen(layer)
