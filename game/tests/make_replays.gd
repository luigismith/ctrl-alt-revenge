extends SceneTree
## Genera i replay di prova in res://tests/replays/ con il pilota automatico:
##   godot --headless --path game -s res://tests/make_replays.gd [-- nome1 nome2 ...]
## La logica è in replay_maker.gd, caricato a runtime: uno script -s viene compilato prima
## che gli autoload (Game, Sfx...) esistano, quindi non deve dipendere dalle classi del gioco.
## Si parte dal primo _process: in _initialize i nodi aggiunti alla radice non sono ancora "ready".

var _started: bool = false


func _process(_delta: float) -> bool:
	if _started:
		return false
	_started = true
	var script: GDScript = load("res://tests/replay_maker.gd")
	if script == null or not script.can_instantiate():
		printerr("replay_maker.gd non si compila")
		quit(1)
		return false
	var maker: RefCounted = script.new()
	var ok: bool = maker.call("run", root, OS.get_cmdline_user_args())
	print("DONE" if ok else "FALLITO")
	quit(0 if ok else 1)
	return false
