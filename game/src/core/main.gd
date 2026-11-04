extends Node
## Scena principale: flusso delle schermate titolo → livello → fine demo → crediti → titolo.
## Argomenti utente (dopo "--"): vedi SessionOptions (--autostart, --replay, --seed, --record...).

const FADE_TICKS := 16

var _screen: Node
var _fade_layer: CanvasLayer
var _fade: ColorRect
var _fade_t: int = 0
var _fade_dir: int = 0
var _pending: Callable
## Richiesta arrivata durante la dissolvenza in entrata: parte appena questa finisce.
var _queued: Callable


func _ready() -> void:
	_fade_layer = CanvasLayer.new()
	_fade_layer.layer = 50
	add_child(_fade_layer)
	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.size = Vector2(384, 216)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade_layer.add_child(_fade)
	if Game.options.autostart:
		_start_level()
	else:
		_show_title()


func _physics_process(_delta: float) -> void:
	if _fade_dir == 0:
		return
	_fade_t += 1
	var a := clampf(float(_fade_t) / FADE_TICKS, 0.0, 1.0)
	_fade.color.a = a if _fade_dir > 0 else 1.0 - a
	if _fade_t >= FADE_TICKS:
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
			if _queued.is_valid():
				var q := _queued
				_queued = Callable()
				_go(q)


## Cambia schermata con una dissolvenza al nero. Durante l'uscita verso un'altra schermata le
## richieste nuove si ignorano (vince la prima); durante l'entrata si mettono in coda, così una
## conferma data negli ultimi tick della dissolvenza non va persa.
func _go(next: Callable) -> void:
	if _fade_dir > 0:
		return
	if _fade_dir < 0:
		_queued = next
		return
	_pending = next
	_fade_dir = 1
	_fade_t = 0


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
	t.start_game.connect(func() -> void: _go(_start_level))
	t.show_credits.connect(func() -> void: _go(_show_credits))
	t.quit_game.connect(func() -> void: Game.quit_clean())
	_set_screen(t)


func _show_credits() -> void:
	var c := CreditsScreen.new()
	var layer := CanvasLayer.new()
	layer.add_child(c)
	c.done.connect(func() -> void: _go(_show_title))
	_set_screen(layer)


func _start_level() -> void:
	Game.reset_run()
	var o := Game.options
	var opts := {"seed": o.level_seed, "record": o.record_path}
	if o.start_x >= 0.0:
		opts["start_x"] = o.start_x
	var input: PlayerInput = null
	if o.replay_path != "":
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
	if input == null and o.autopilot != "":
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
	var layer := CanvasLayer.new()
	layer.add_child(d)
	d.done.connect(func() -> void: _go(_show_credits))
	_set_screen(layer)
