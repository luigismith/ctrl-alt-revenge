class_name Thug
extends Fighter
## Nemico (punk o bruto) con intelligenza semplice e prevedibile:
## - entra da fuori schermo;
## - senza turno d'attacco aspetta a 40-66 px da GIG (wait_distance nei dati), fuori dalla sua corsia, e si sposta di lato;
## - con il turno (concesso dall'AttackDirector) si allinea, si avvicina con passo deciso e attacca;
## - il punk annuncia il gancio caricato con il lampo; il bruto ha l'armatura durante l'avvio.

enum Mind { ENTER, WAIT, APPROACH }

## Passo di chi ha il turno, rispetto alla camminata d'attesa.
const APPROACH_SPEED := 1.7

var mind: Mind = Mind.WAIT
var rng: RandomNumberGenerator = RandomNumberGenerator.new()
var attack_options: Array[AttackData] = []
var ai_enabled: bool = true
## Ondata a cui appartiene (per sapere quando è finita).
var wave_id: String = ""

var _enter_x: float = 0.0
var _chosen: AttackData
var _approach_ticks: int = 0
var _lane_sign: int = 1
var _lane_timer: int = 0
var _wait_frac: float = 0.5
var _side: int = 1
## Il colpo in corso ha già avuto la hitbox attiva (per lasciare il turno quando si spegne).
var _hit_was_active: bool = false


func setup_thug(type_id: StringName, lvl: Level, id: int, rng_seed: int) -> void:
	setup(load("res://data/fighters/%s.tres" % type_id) as FighterData, lvl, id, Team.ENEMY)
	rng.seed = rng_seed
	for a in data.attacks:
		attack_options.append(load("res://data/attacks/%s.tres" % a) as AttackData)
	_lane_sign = 1 if rng.randi() % 2 == 0 else -1
	_lane_timer = rng.randi_range(80, 160)
	_wait_frac = rng.randf()


## Entra camminando da fuori schermo fino a `target_x`.
func enter_from(target_x: float) -> void:
	_enter_x = target_x
	mind = Mind.ENTER
	facing = 1 if target_x > px else -1
	set_state(State.ENTER, &"walk")


func _think() -> void:
	if state == State.ENTER:
		_think_enter()
		return
	# Il turno si lascia appena il colpo smette di poter colpire, non a fine recupero: così il
	# prossimo nemico si muove prima, e due colpi attivi insieme restano impossibili.
	if state == State.ATTACK and level.director.is_holder(self):
		if not active_hitboxes().is_empty():
			_hit_was_active = true
		elif _hit_was_active:
			_release_token()
	if not is_free():
		return
	var p := level.player
	if not ai_enabled or p == null or not p.is_alive() or p.state == State.DEAD:
		_release_token()
		mind = Mind.WAIT
		_walk_towards(px, py, 0.0)
		return
	facing = 1 if p.px >= px else -1
	if mind == Mind.APPROACH:
		_think_approach(p)
	else:
		mind = Mind.WAIT
		if level.director.request(self, level.tick):
			mind = Mind.APPROACH
			_approach_ticks = 0
			_chosen = _choose_attack()
			_think_approach(p)
		else:
			_think_wait(p)


func _think_enter() -> void:
	var dir := 1 if _enter_x > px else -1
	facing = dir
	vx = dir * data.walk_speed.x
	vy = 0.0
	if absf(_enter_x - px) <= data.walk_speed.x:
		px = _enter_x
		mind = Mind.WAIT
		set_state(State.IDLE)


func _think_wait(p: Fighter) -> void:
	_lane_timer -= 1
	if _lane_timer <= 0:
		_lane_sign = -_lane_sign
		_lane_timer = rng.randi_range(90, 170)
		_wait_frac = rng.randf()
	_side = _pick_side(p)
	var dist := lerpf(data.wait_distance.x, data.wait_distance.y, _wait_frac)
	var tx := p.px + _side * dist
	var lane := lerpf(data.wait_lane_offset.x, data.wait_lane_offset.y, _wait_frac)
	var ty := p.py + _lane_sign * lane
	if ty < level.band_top + 3 or ty > level.band_bottom - 3:
		_lane_sign = -_lane_sign
		ty = p.py + _lane_sign * lane
	ty = clampf(ty, level.band_top, level.band_bottom)
	# Il punto di attesa resta un poco dentro i muri invisibili.
	var margin := Level.WALL_MARGIN + 7.5
	tx = clampf(tx, level.view_left() + margin, level.view_right() - margin)
	_walk_towards(tx, ty, 2.5)


## Lato di attesa: quello attuale, salvo che un altro nemico in attesa (con uid minore)
## lo occupi già o che sul lato non ci sia spazio dentro lo schermo.
func _pick_side(p: Fighter) -> int:
	var side := 1 if px >= p.px else -1
	var room_right := level.view_right() - Level.WALL_MARGIN - p.px
	var room_left := p.px - (level.view_left() + Level.WALL_MARGIN)
	for other in level.enemies():
		if other == self or other.uid > uid or other.mind == Mind.APPROACH or not other.is_free():
			continue
		var other_side := 1 if other.px >= p.px else -1
		if other_side == side:
			side = -side
			break
	if side > 0 and room_right < data.wait_distance.x * 0.7:
		side = -1
	elif side < 0 and room_left < data.wait_distance.x * 0.7:
		side = 1
	return side


func _think_approach(p: Fighter) -> void:
	_approach_ticks += 1
	if _approach_ticks > data.approach_timeout:
		_release_token()
		level.director.set_cooldown(self, level.tick + data.cooldown_ticks.x)
		mind = Mind.WAIT
		return
	var reach := _reach(_chosen)
	var side := 1 if px >= p.px else -1
	var tx := p.px + side * reach
	var dx := absf(px - tx)
	var dy := absf(py - p.py)
	if dx <= 3.75 and dy <= 2.5:
		vx = 0.0
		vy = 0.0
		facing = -side
		level.director.on_attack_start(self, level.tick)
		_hit_was_active = false
		start_attack(_chosen, level.next_attack_serial())
		return
	# Chi ha il turno si avvicina con passo deciso: la camminata d'attesa era troppo lenta e
	# allungava il turno (Luigi, 4 novembre 2026: nemici molto più aggressivi).
	_walk_towards(tx, p.py, 0.625, _approach_speed())


## Passo di chi ha il turno (il rider arriva di corsa).
func _approach_speed() -> float:
	return APPROACH_SPEED


## Distanza a cui attaccare: la punta della hitbox poco dentro la hurtbox di GIG.
func _reach(atk: AttackData) -> float:
	var c := sheet.attack_clip(atk.anim, atk)
	var r := c.max_reach()
	if r <= 0:
		r = atk.hitbox.position.x + atk.hitbox.size.x
	return clampf(r - 12.5, 20.0, 70.0)


func _choose_attack() -> AttackData:
	if attack_options.size() == 1:
		return attack_options[0]
	var total := 0.0
	for i in attack_options.size():
		total += _weight(i)
	var roll := rng.randf() * total
	for i in attack_options.size():
		roll -= _weight(i)
		if roll <= 0.0:
			return attack_options[i]
	return attack_options[attack_options.size() - 1]


func _weight(i: int) -> float:
	return data.attack_weights[i] if i < data.attack_weights.size() else 1.0


func _walk_towards(tx: float, ty: float, tolerance: float, speed: float = 1.0) -> void:
	var dx := tx - px
	var dy := ty - py
	var sx := data.walk_speed.x * speed
	var sy := data.walk_speed.y * speed
	vx = clampf(dx, -sx, sx) if absf(dx) > tolerance else 0.0
	vy = clampf(dy, -sy, sy) if absf(dy) > tolerance else 0.0
	if vx == 0.0 and vy == 0.0:
		if state != State.IDLE:
			set_state(State.IDLE)
	elif state != State.WALK:
		set_state(State.WALK)


func _end_attack() -> void:
	_release_token()
	level.director.set_cooldown(self, level.tick + rng.randi_range(data.cooldown_ticks.x, data.cooldown_ticks.y))
	mind = Mind.WAIT
	super._end_attack()


func _on_hit_taken(_attacker: Entity, _atk: AttackData) -> void:
	# Con l'armatura un colpo leggero non ferma il pugno del bruto: il turno resta suo fino a
	# _end_attack, altrimenti un altro nemico attaccherebbe insieme a lui.
	if state == State.ATTACK:
		return
	_interrupt()


func _on_grabbed() -> void:
	_interrupt()


func _interrupt() -> void:
	if level.director.is_holder(self):
		_release_token()
		# Anche un attacco interrotto conta: il prossimo arriva dopo 0,6-1,0 s.
		level.director.set_cooldown(self, level.tick + rng.randi_range(data.cooldown_ticks.x, data.cooldown_ticks.y))
	mind = Mind.WAIT


func _release_token() -> void:
	level.director.release(self, level.tick)


func _on_state_changed(_prev: State, next: State) -> void:
	if next == State.DEAD or next == State.KNOCK_AIR or next == State.THROWN:
		if level.director.is_holder(self):
			_release_token()
