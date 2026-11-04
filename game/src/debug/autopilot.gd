class_name Autopilot
extends RefCounted
## Pilota automatico: GIG gioca da solo. Serve solo a generare i replay di prova e la
## dimostrazione (game/tests/make_replays.gd); i replay poi si riproducono senza pilota.
## Legge soltanto lo stato della simulazione, quindi è deterministico come il gioco.
##
## Scenari:
##   walk_right  cammina sempre a destra (prova del cavo toccato)
##   cable_jump  cammina a destra e salta il cavo
##   combo       combatte solo con le combo
##   grab        afferra il nemico: due ginocchiate e proiezione, poi combo
##   arena       combatte (combo, prese, calci in salto) finché la zona è liberata
##   demo        tutto il livello: camminata, corsa, combo, presa, calcio in salto,
##               bidone e mela, salto del cavo, arena

const L := InputFrame.LEFT
const R := InputFrame.RIGHT
const U := InputFrame.UP
const D := InputFrame.DOWN
const A := InputFrame.ATTACK
const J := InputFrame.JUMP

var scenario: StringName
var level: Level
var _grab_done: Dictionary[int, bool] = {}
var _next_press: int = 0
var _beat: int = 0
var _beat_tick: int = 0
var _jump_kick: int = 0
var _jump_kicks_done: int = 0
var _last_jump_kick: int = -10000


func _init(s: StringName) -> void:
	scenario = s


func decide(tick: int) -> int:
	if level == null or level.player == null:
		return 0
	match scenario:
		&"walk_right":
			return R
		&"cable_jump":
			return _cable_jump()
		&"combo":
			return _fight(tick, false, false)
		&"grab":
			return _fight(tick, true, false)
		&"arena":
			return _fight(tick, true, true)
		&"demo":
			return _demo(tick)
	return 0


func _cable_jump() -> int:
	var g := level.player
	var c := _cable()
	if c != null and g.ph <= 0.0 and g.is_free() and g.px >= c.x0 - 9.0 and g.px < c.x0 - 2.0:
		return R | J
	return R


func _cable() -> PropCable:
	for p in level.props:
		if p is PropCable:
			return p as PropCable
	return null


## Combattimento: si allinea in profondità, si mette a distanza di pugno e preme attacco;
## schiva in profondità gli attacchi in carica; con `grabs` prova una presa per nemico;
## con `jumps` ogni tanto attacca con il calcio in salto.
func _fight(tick: int, grabs: bool, jumps: bool) -> int:
	var g := level.player
	if g.state == Fighter.State.GRAB:
		return _in_grab(tick)
	if _jump_kick > 0:
		return _do_jump_kick()
	var e := _target()
	if e == null:
		# Nessun nemico in vista: avanti verso la prossima ondata.
		return 0 if level.zone_cleared else R
	if not (g.is_free() or g.state == Fighter.State.ATTACK):
		return 0
	var dx := e.px - g.px
	var dy := e.py - g.py
	var toward := R if dx > 0.0 else L
	var away := L if dx > 0.0 else R
	# Schivata: un attacco nemico in carica nella mia corsia.
	for t in level.enemies():
		if t.state == Fighter.State.ATTACK and t.attack != null and t.attack_tick < t.attack.startup \
				and absf(t.py - g.py) < 14.0 and absf(t.px - g.px) < 80.0 and g.is_free():
			return U if g.py > (level.band_top + level.band_bottom) * 0.5 else D
	# Presa: stessa corsia, poi cammina contro il nemico. Da quando i nemici sono più aggressivi
	# un nemico libero non resta fermo vicino a GIG: la presa si cerca sul nemico stordito da un
	# colpo (HURT), oppure su quello libero già a portata, e altrimenti si combatte.
	var grabbable := e.state == Fighter.State.HURT or (e.is_free() and absf(dx) < 30.0)
	if grabs and not _grab_done.has(e.uid) and grabbable and not e.is_attacking():
		if absf(dy) > 2.0:
			return (D if dy > 0.0 else U) | (toward if absf(dx) > 30.0 else 0)
		return toward
	if jumps and g.is_free() and e.is_free() and absf(dy) <= 3.0 and absf(dx) > 44.0 and absf(dx) < 60.0 \
			and tick - _last_jump_kick > 360:
		_last_jump_kick = tick
		_jump_kick = 1
		return toward | J
	if absf(dy) > 3.0:
		var v := D if dy > 0.0 else U
		if absf(dx) < 24.0:
			return v | away
		return v | (toward if absf(dx) > 40.0 else 0)
	if absf(dx) > 38.0:
		return toward
	if absf(dx) < 22.0:
		return away
	# Nemico a terra o invulnerabile dopo il rialzo: si aspetta in guardia, senza colpi a vuoto.
	if e.is_down() or e.invuln > 0 or e.is_airborne():
		return toward if g.facing != (1 if dx > 0.0 else -1) else 0
	# Di fronte al nemico: un tocco di direzione per girarsi, poi attacco a ritmo regolare.
	if g.facing != (1 if dx > 0.0 else -1):
		return toward
	return A if tick % 4 == 0 else 0


## Calcio in salto: salta verso il nemico e colpisce in discesa.
func _do_jump_kick() -> int:
	var g := level.player
	var dir := R if g.facing > 0 else L
	if g.state == Fighter.State.JUMP and g.vh < 1.5:
		_jump_kick = 0
		_jump_kicks_done += 1
		return dir | A
	_jump_kick += 1
	if _jump_kick > 40:
		_jump_kick = 0
	return dir


func _in_grab(tick: int) -> int:
	var g := level.player
	if g.grab_partner != null:
		_grab_done[g.grab_partner.uid] = true
	if g.grab_action != Gig.GrabAction.HOLD:
		return 0
	if tick >= _next_press:
		_next_press = tick + 6
		return A
	return 0


func _target() -> Thug:
	var g := level.player
	var best: Thug = null
	var best_d := 1e9
	for t in level.enemies():
		if t.dead or t.removed or t.state == Fighter.State.ENTER:
			continue
		var d := absf(t.px - g.px) + absf(t.py - g.py) * 2.0
		if d < best_d:
			best_d = d
			best = t
	return best


## Dimostrazione completa del livello, a tappe.
func _demo(tick: int) -> int:
	var g := level.player
	if level.zone_cleared:
		return 0
	if _target() != null or g.state == Fighter.State.GRAB or _jump_kick > 0:
		return _fight(tick, true, true)
	if not g.is_free() and g.state != Fighter.State.JUMP:
		return 0
	match _beat:
		0:
			# Camminata sotto il cartello del livello, poi una pausa in guardia.
			if g.px < 190.0:
				return R | (D if g.py < 192.0 and tick % 3 == 0 else 0)
			_next_beat(tick)
			return 0
		1:
			if tick - _beat_tick < 100:
				return 0
			_next_beat(tick)
			return R
		2:
			# Doppio tocco: corsa, poi di nuovo al passo fino all'ondata 1.
			var k := tick - _beat_tick
			if k < 3:
				return 0
			if g.px < 430.0:
				return R
			_next_beat(tick)
			return 0
		3:
			if level.waves_cleared < 1:
				return R
			_next_beat(tick)
			return 0
		4:
			# Dopo l'ondata 1: un salto con calcio a vuoto, per mostrarlo.
			if g.state == Fighter.State.JUMP:
				return A if g.vh < 1.0 else 0
			if tick - _beat_tick > 40 and _jump_kicks_done == 0:
				_jump_kicks_done = 1
				return J
			if _jump_kicks_done > 0 and g.is_free() and tick - _beat_tick > 110:
				_next_beat(tick)
			return 0
		5:
			# Profondità: verso il fondo della strada e poi verso lo schermo.
			if g.py > level.band_top + 6.0:
				return R | U
			_next_beat(tick)
			return R
		6:
			if g.py < level.band_bottom - 8.0:
				return R | D
			_next_beat(tick)
			return R
	# Bidone: allinearsi e colpirlo finché si rompe; poi la mela.
	for p in level.props:
		if p is PropBin and not (p as PropBin).broken and p.px > g.px - 40.0:
			return _go_hit(tick, p.px, p.py)
		if p is PropApple:
			return _go_to(p.px, p.py)
	var c := _cable()
	if c != null and g.px < c.x1 + 10.0:
		if absf(g.py - 182.0) > 2.0 and g.px < c.x0 - 40.0:
			return R | (D if g.py < 182.0 else U)
		return _cable_jump()
	return R


func _next_beat(tick: int) -> void:
	_beat += 1
	_beat_tick = tick


func _go_hit(tick: int, x: float, y: float) -> int:
	var g := level.player
	var dx := x - g.px
	var dy := y - g.py
	if absf(dy) > 3.0:
		return (D if dy > 0.0 else U) | (R if dx > 34.0 else 0)
	if dx > 30.0:
		return R
	# Girarsi verso il bidone costa un passo di 1,5 px in avanti: lo si fa solo con un po' di margine,
	# altrimenti destra e sinistra si alternano a ogni tick e GIG resta fermo lì per sempre.
	if g.facing != 1:
		return R if dx >= 20.0 else L
	if dx < 18.0:
		return L
	return A if tick % 8 == 0 else 0


func _go_to(x: float, y: float) -> int:
	var g := level.player
	var bits := 0
	if x - g.px > 2.0:
		bits |= R
	elif g.px - x > 2.0:
		bits |= L
	if y - g.py > 2.0:
		bits |= D
	elif g.py - y > 2.0:
		bits |= U
	return bits
