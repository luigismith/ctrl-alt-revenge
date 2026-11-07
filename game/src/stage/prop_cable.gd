class_name PropCable
extends Prop
## Cavo dell'alta tensione strappato in una pozzanghera, da x0 a x1 su tutta la fascia
## calpestabile: chiunque lo tocchi stando a terra prende 10 di danno e viene atterrato,
## chi lo salta passa indenne.

var x0: float = 1538.0
var x1: float = 1588.0
var zap: AttackData
## Tick di ricarica per ogni vittima, così una scossa non si ripete a ogni tick.
var _recharge: Dictionary[int, int] = {}


func setup_cable(lvl: Level, id: int, from_x: float, to_x: float) -> void:
	setup_prop(&"cable", lvl, id)
	team = Team.NEUTRAL
	x0 = from_x
	x1 = to_x
	px = (from_x + to_x) * 0.5
	# La pozzanghera copre tutta la fascia calpestabile: l'ancora è sul suo bordo alto.
	py = lvl.band_top
	depth_bias = -400
	event_volume_db = -12.0
	zap = load("res://data/attacks/hazard_cable.tres") as AttackData
	anim.play(pick_anim([&"sparks", &"scintille", &"idle"]))
	anim.take_events()


func sim_tick() -> void:
	advance_anim()
	for k: int in _recharge.keys():
		_recharge[k] -= 1
		if _recharge[k] <= 0:
			_recharge.erase(k)
	for f in level.fighters:
		if f.removed or f.dead or _recharge.has(f.uid):
			continue
		if f.px < x0 or f.px > x1 or f.ph > 0.5:
			continue
		if not _can_shock(f):
			continue
		_shock(f)


func _can_shock(f: Fighter) -> bool:
	if f.invuln > 0:
		return false
	match f.state:
		Fighter.State.KNOCK_DOWN, Fighter.State.GETUP, Fighter.State.DEAD, Fighter.State.GRABBED, \
				Fighter.State.KNOCK_AIR, Fighter.State.THROWN, Fighter.State.ENTER:
			return false
	return true


func _shock(f: Fighter) -> void:
	_recharge[f.uid] = 30
	# Spinta lontano dal centro del cavo, così la vittima cade fuori dalla pozzanghera.
	var dir := 1 if f.px >= px else -1
	if f is Gig:
		dir = -f.facing
	f.receive_hit(self, zap, HitInfo.new(Vector2(f.px, f.py - 38.0), dir, false))
	if level.sound_enabled:
		Sfx.play_at(&"zap", f.px)
	# Viola e arancio come l'arco del cavo: il cyan è solo del braccio di GIG.
	level.fx.spawn(&"cable_spark", f.px, f.py - 25.0, 1, f.depth_z(2))
	level.fx.spawn(&"cable_spark", f.px - 8.0, f.py - 60.0, -1, f.depth_z(2))
	level.add_shake(0.25)
	Game.count(&"cable_zaps")
	if f is Gig:
		Game.count(&"cable_zaps_gig")
