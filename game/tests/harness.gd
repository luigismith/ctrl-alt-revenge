extends RefCounted
## Aiuti comuni a test e generazione dei replay: livelli senza tempo reale, avanzati a mano.

## Scenari dei replay di prova: punto di partenza, scenario del pilota automatico,
## tick massimi e descrizione. Il seme è lo stesso per tutti.
const SEED := 7
const SCENARIOS := {
	"combo_punk": {"start_x": 975.0, "start_y": 223.0, "pilot": "combo", "max": 3600,
		"note": "GIG sconfigge da solo il punk dell'ondata 1 usando solo le combo."},
	"grab_throw": {"start_x": 975.0, "start_y": 223.0, "pilot": "grab", "max": 2400,
		"note": "GIG afferra il punk, due ginocchiate e la proiezione."},
	"cable_touch": {"start_x": 1438.0, "start_y": 228.0, "pilot": "walk_right", "max": 150,
		"note": "GIG cammina dentro il cavo: 10 di danno e atterramento."},
	"cable_jump": {"start_x": 1438.0, "start_y": 228.0, "pilot": "cable_jump", "max": 150,
		"note": "GIG salta il cavo e passa indenne."},
	"arena": {"start_x": 1900.0, "start_y": 230.0, "pilot": "arena", "max": 7200,
		"note": "Arena: punk e bruto (entra dopo 3 s); dopo i KO la zona è liberata."},
	"demo": {"start_x": -1.0, "start_y": -1.0, "pilot": "demo", "max": 5400, "seed": 13,
		"note": "Dimostrazione: corsa, combo, presa, bidone e mela, salto del cavo, arena."},
}


static func make_level(root: Node, input: PlayerInput, start_x: float, start_y: float, card: bool = false, level_seed: int = SEED) -> Level:
	Game.reset_run()
	SpriteSheet.clear_cache()
	var lvl := Level.new()
	lvl.configure({"seed": level_seed, "start_x": start_x, "start_y": start_y, "input": input,
		"sound": false, "auto_tick": false, "card": card})
	root.add_child(lvl)
	return lvl


static func free_level(lvl: Level) -> void:
	if lvl != null and is_instance_valid(lvl):
		lvl.get_parent().remove_child(lvl)
		lvl.free()


## Livello da un replay: stesso seme e stesso punto di partenza della registrazione.
static func level_from_replay(root: Node, r: Replay) -> Level:
	Game.reset_run()
	SpriteSheet.clear_cache()
	var lvl := Level.new()
	var opts := {"seed": r.level_seed, "input": PlayerInput.from_replay(r), "sound": false, "auto_tick": false, "card": false}
	if r.start.has("x"):
		opts["start_x"] = float(r.start["x"])
	if r.start.has("y"):
		opts["start_y"] = float(r.start["y"])
	lvl.configure(opts)
	root.add_child(lvl)
	return lvl


## Avanza finché `stop` (Callable(level) -> bool) è vero o fino a `max_ticks`. Ritorna i tick fatti.
static func run(lvl: Level, max_ticks: int, stop: Callable = Callable()) -> int:
	var n := 0
	while n < max_ticks:
		lvl.step()
		n += 1
		if stop.is_valid() and bool(stop.call(lvl)):
			break
	return n
