extends RefCounted
## Sequenza della galleria visiva (vedi ui_gallery.gd).

const STEP := 90
## Schermate mostrate (0-7); dopo l'ultima la galleria chiude il gioco.
const PHASES := 8

var _t: int = 0
var _screen: Node
var _level: Level


func frame(root: Node) -> void:
	var phase := _t / STEP
	if phase >= PHASES:
		# Fine della galleria: chiude da sola, dopo aver zittito l'audio (vedi Game.quit_clean).
		if _t == PHASES * STEP:
			Game.quit_clean(0)
		_t += 1
		return
	if _t % STEP == 0:
		_show(root, phase)
	if _level != null and is_instance_valid(_level):
		match phase:
			4:
				_level.overlay.continue_count = 9 - (_t % STEP) / 10
	_t += 1


func _clear() -> void:
	if _screen != null and is_instance_valid(_screen):
		_screen.queue_free()
	_screen = null
	_level = null


func _show(root: Node, phase: int) -> void:
	match phase:
		0:
			_clear()
			_screen = TitleScreen.new()
			root.add_child(_screen)
		1:
			_clear()
			var layer := CanvasLayer.new()
			var c := CreditsScreen.new()
			layer.add_child(c)
			_screen = layer
			root.add_child(layer)
			c.set("_scroll", 0.0)
		2:
			_clear()
			Game.options.debug_boxes = true
			var pilot := Autopilot.new(&"combo")
			_level = Level.new()
			_level.configure({"seed": 7, "start_x": 780.0, "start_y": 178.0, "sound": false, "card": false,
				"input": PlayerInput.from_provider(pilot.decide, pilot)})
			pilot.level = _level
			_screen = _level
			root.add_child(_level)
		3:
			_level.debug_overlay.visible = false
			_level.paused = true
			_level.overlay.paused = true
			_level.overlay.pause_index = 1
		4:
			_level.paused = false
			_level.overlay.paused = false
			_level.phase = Level.Phase.CONTINUE
			_level.overlay.continue_count = 9
		5:
			_level.overlay.continue_count = -1
			_level.phase = Level.Phase.OVER
			_level.overlay.game_over_ticks = 0
		6:
			_clear()
			var layer := CanvasLayer.new()
			var d := DemoEndScreen.new()
			d.score = 2840
			d.ticks = 4134
			layer.add_child(d)
			_screen = layer
			root.add_child(layer)
		7:
			_clear()
			var layer := CanvasLayer.new()
			var d := DemoEndScreen.new()
			d.prologue = true
			d.ticks = 5480
			layer.add_child(d)
			_screen = layer
			root.add_child(layer)
