extends SceneTree
## Test automatici da riga di comando:
##   godot --headless --path game -s res://tests/run_tests.gd
## Stampa una riga per test e, se tutto passa, l'ultima riga "DONE"; il codice d'uscita è 0 solo se tutto passa.

var _failures: int = 0
var _count: int = 0


func _initialize() -> void:
	_run_all()
	if _failures == 0:
		print("Test passati: %d" % _count)
		print("DONE")
		quit(0)
	else:
		printerr("Test falliti: %d su %d" % [_failures, _count])
		quit(1)


func check(condition: bool, name: String) -> void:
	_count += 1
	if condition:
		print("ok   - " + name)
	else:
		_failures += 1
		printerr("FAIL - " + name)


func _run_all() -> void:
	check(ProjectSettings.get_setting("display/window/size/viewport_width") == 384, "risoluzione interna larga 384")
	check(ProjectSettings.get_setting("display/window/size/viewport_height") == 216, "risoluzione interna alta 216")
	check(ProjectSettings.get_setting("display/window/stretch/scale_mode") == "integer", "scala intera")
	check(Engine.physics_ticks_per_second == 60, "fisica a 60 tick")
	check(ResourceLoader.exists("res://scenes/main.tscn"), "la scena principale esiste")
