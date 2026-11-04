extends RefCounted
## Genera i replay di prova in res://tests/replays/ facendo giocare il pilota automatico.
## Si lancia con lo script make_replays.gd. Va rilanciato quando cambiano le regole del
## gameplay: un replay registra solo gli ingressi.

const Harness := preload("res://tests/harness.gd")
const OUT_DIR := "res://tests/replays"

var root: Node
var game: Node
var _haymakers: int = 0
var _glints: int = 0


func run(tree_root: Node, only: PackedStringArray) -> bool:
	root = tree_root
	game = Game
	var ok := true
	for scenario_name: String in Harness.SCENARIOS:
		if not only.is_empty() and not only.has(scenario_name):
			continue
		ok = _make(scenario_name, Harness.SCENARIOS[scenario_name]) and ok
	return ok


func _make(scenario_name: String, sc: Dictionary) -> bool:
	var pilot := Autopilot.new(StringName(sc["pilot"]))
	var input := PlayerInput.from_provider(pilot.decide, pilot)
	var rec := Replay.new()
	rec.level_seed = int(sc.get("seed", Harness.SEED))
	rec.note = sc["note"]
	if float(sc["start_x"]) >= 0.0:
		rec.start = {"x": sc["start_x"], "y": sc["start_y"]}
	input.recorder = rec
	var lvl := Harness.make_level(root, input, float(sc["start_x"]), float(sc["start_y"]), float(sc["start_x"]) < 0.0, rec.level_seed)
	pilot.level = lvl
	var stop := _stop_condition(scenario_name)
	_haymakers = 0
	_glints = 0
	var watch := func(l: Level) -> bool:
		for t in l.enemies():
			if t.state == Fighter.State.ATTACK and t.attack != null and t.attack.id == &"thug_punk_haymaker":
				if t.attack_tick == 0:
					_haymakers += 1
				if t.attack_tick == t.attack.glint_tick:
					_glints += 1
		return stop.call(l) if stop.is_valid() else false
	var ticks := Harness.run(lvl, int(sc["max"]), watch)
	var reached: bool = bool(stop.call(lvl)) if stop.is_valid() else true
	# Qualche tick in più dopo l'obiettivo, per vedere la conclusione.
	if reached and scenario_name != "demo":
		ticks += Harness.run(lvl, 40)
	rec.length = lvl.tick
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(OUT_DIR))
	var path := ProjectSettings.globalize_path(OUT_DIR.path_join(scenario_name + ".json"))
	var err := rec.save_file(path)
	var p := lvl.player
	print("%-12s %s  tick %5d  (%.1f s)  GIG %3d/%d  vite %d  punti %6d  hash %s" % [scenario_name,
		"OK  " if reached else "NO! ", lvl.tick, lvl.tick / 60.0, p.hp, p.data.max_hp, game.lives, game.score, lvl.final_hash().left(12)])
	print("             seme %d, haymaker %d, glint %d" % [rec.level_seed, _haymakers, _glints])
	var keys: Array = game.stats.keys()
	keys.sort()
	var parts: PackedStringArray = []
	for k in keys:
		parts.append("%s=%d" % [k, game.stats[k]])
	print("             ", ", ".join(parts))
	Harness.free_level(lvl)
	return reached and err == OK


func _stop_condition(scenario_name: String) -> Callable:
	match scenario_name:
		"combo_punk":
			return func(l: Level) -> bool: return l.waves_cleared >= 1
		"grab_throw":
			return func(l: Level) -> bool: return game.stat(&"throws") >= 1 and _no_flying(l)
		"cable_touch", "cable_jump":
			return Callable()
		"arena", "demo":
			return func(l: Level) -> bool: return l.phase == Level.Phase.DONE
	return Callable()


static func _no_flying(l: Level) -> bool:
	for f in l.fighters:
		if f.state == Fighter.State.THROWN or f.state == Fighter.State.KNOCK_AIR:
			return false
	return true
