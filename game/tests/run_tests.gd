extends SceneTree
## Test automatici da riga di comando:
##   godot --headless --path game -s res://tests/run_tests.gd
## Stampa una riga per test e, se tutto passa, l'ultima riga "DONE"; il codice d'uscita è 0 solo se tutto passa.
## I test veri sono in test_suite.gd, caricato a runtime: uno script -s viene compilato prima che
## esistano gli autoload (Game, Sfx...), quindi non deve dipendere direttamente dalle classi del gioco.
## Si parte dal primo _process: in _initialize i nodi aggiunti alla radice non ricevono ancora _ready.

var _started: bool = false


func _process(_delta: float) -> bool:
	if _started:
		return false
	_started = true
	var script: GDScript = load("res://tests/test_suite.gd")
	if script == null or not script.can_instantiate():
		printerr("test_suite.gd non si compila")
		quit(1)
		return false
	var suite: RefCounted = script.new()
	var ok: bool = suite.call("run", root)
	var count: int = suite.get("count")
	var failures: int = suite.get("failures")
	if ok:
		print("Test passati: %d" % count)
		print("DONE")
		quit(0)
	else:
		printerr("Test falliti: %d su %d" % [failures, count])
		quit(1)
	return false
