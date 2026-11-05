class_name Esattore
extends Thug
## L'esattore di professione (decisione 63): il bruto con la pettorina catarifrangente ESATTORE e il
## logo di SIDERA. Pesante, para e carica (scelte di Luigi del 5 novembre 2026):
## - la guardia: da libero para i pugni che arrivano da davanti, con le scintille e un colpo secco;
##   al terzo colpo parato la guardia salta e barcolla, aperto alla combo. La presa e il calcio in
##   salto passano sempre;
## - la carica: col turno, a volte, si mette nella corsia di GIG a distanza di rincorsa, si abbassa
##   lampeggiando e parte di corsa lungo la corsia. Se prende GIG lo atterra e frena; se lo manca
##   sbatte contro il bordo dello schermo e resta stordito, ed è il momento di picchiarlo;
## - per il resto picchia come il bruto dello slice, col pugno pesante con l'armatura.
##
## Lo sprite è ancora quello del bruto, con la canotta ricolorata in arancione ad alta visibilità, e
## le sue animazioni dalla pipeline 3D: la guardia ("block"), la preparazione e la corsa della spallata
## ("charge_wind", "charge_run") e lo stordimento ("dizzy"). La pettorina vera, con le strisce
## catarifrangenti e la scritta, arriverà con lo sprite suo.

enum Charge { NONE, WIND, RUN }

## Colpi parati prima che la guardia salti, e tick senza colpi dopo cui il conto riparte.
const GUARD_HITS := 3
const GUARD_RESET := 90
const GUARD_BREAK_STUN := 50
const BLOCK_HITSTOP := 6
## Probabilità che col turno scelga la carica invece del pugno.
const CHARGE_CHANCE := 0.5
## Distanza da GIG da cui parte la rincorsa, e la più corta che accetta se lo spazio manca.
const CHARGE_DX := 120.0
const CHARGE_DX_MIN := 80.0
## Tick della preparazione (abbassato, lampeggia), velocità e durata massima della corsa.
const CHARGE_WIND := 32
const CHARGE_SPEED := 4.5
const CHARGE_MAX := 160
## Stordimento dopo aver sbattuto contro il bordo.
const DIZZY_TICKS := 60
## Tick in cui resta in guardia, fermo, dopo un colpo parato.
const BLOCK_HOLD := 16

## Colpi parati di fila.
var guard_hits: int = 0
var charge: Charge = Charge.NONE
var charge_t: int = 0
var charge_dir: int = 1
## Tick di stordimento dopo la carica a vuoto (per le stelline; 0 = non stordito).
var dizzy: int = 0
var _guard_t: int = 0
## Tick di guardia che restano dopo l'ultimo colpo parato.
var _block_t: int = 0
## Barcolla (guardia rotta o carica a vuoto): finito un colpo subito, torna all'animazione "dizzy".
var _staggered: bool = false
var _charge_try: bool = false
var _charge_atk: AttackData
var _stars: Node2D


func setup_thug(type_id: StringName, lvl: Level, id: int, rng_seed: int) -> void:
	super.setup_thug(type_id, lvl, id, rng_seed)
	_charge_atk = load("res://data/attacks/esattore_charge.tres") as AttackData
	_stars = Node2D.new()
	_stars.draw.connect(_draw_stars)
	add_child(_stars)


func _think() -> void:
	if guard_hits > 0:
		_guard_t += 1
		if _guard_t > GUARD_RESET:
			guard_hits = 0
	if dizzy > 0:
		dizzy -= 1
	if state == State.HURT and _staggered and anim.finished:
		play_anim(&"dizzy")
	if _block_t > 0:
		# In guardia dopo il colpo parato: fermo, poi riprende a pensare.
		_block_t -= 1
		vx = 0.0
		vy = 0.0
		if _block_t == 0 and is_free():
			set_state(State.IDLE)
		return
	if charge != Charge.NONE:
		_think_charge()
		return
	super._think()


func _choose_attack() -> AttackData:
	_charge_try = rng.randf() < CHARGE_CHANCE
	return super._choose_attack()


# --- La carica ----------------------------------------------------------------------------------

func _think_approach(p: Fighter) -> void:
	if not _charge_try:
		super._think_approach(p)
		return
	_approach_ticks += 1
	if _approach_ticks > data.approach_timeout:
		_release_token()
		level.director.set_cooldown(self, level.tick + data.cooldown_ticks.x)
		mind = Mind.WAIT
		_charge_try = false
		return
	# Nella corsia di GIG, a distanza di rincorsa dalla parte dove già si trova (o dall'altra, se
	# lì lo spazio non basta).
	var margin := Level.WALL_MARGIN + 7.5
	var lo := level.view_left() + margin
	var hi := level.view_right() - margin
	var side := 1 if px >= p.px else -1
	var tx := p.px + side * CHARGE_DX
	if tx < lo or tx > hi:
		side = -side
		tx = p.px + side * CHARGE_DX
	tx = clampf(tx, lo, hi)
	if absf(tx - p.px) < CHARGE_DX_MIN:
		# Lo schermo è troppo stretto per la rincorsa: resta il pugno.
		_charge_try = false
		return
	if absf(px - tx) <= 4.0 and absf(py - p.py) <= 2.5:
		_start_charge(p)
		return
	_walk_towards(tx, p.py, 2.0, APPROACH_SPEED)


func _start_charge(p: Fighter) -> void:
	vx = 0.0
	vy = 0.0
	charge_dir = 1 if p.px >= px else -1
	facing = charge_dir
	level.director.on_attack_start(self, level.tick)
	set_state(State.ATTACK)
	attack = _charge_atk
	attack_tick = 0
	attack_serial = level.next_attack_serial()
	hit_registry.clear()
	connected = false
	play_anim(&"charge_wind")
	charge = Charge.WIND
	charge_t = 0
	_on_glint()
	Game.count(&"cariche")


func _think_charge() -> void:
	charge_t += 1
	match charge:
		Charge.WIND:
			# Abbassato e fermo, lampeggia: è l'avviso.
			flash = 1 if (charge_t / 4) % 2 == 0 else 0
			if charge_t >= CHARGE_WIND:
				charge = Charge.RUN
				charge_t = 0
				play_anim(&"charge_run")
				_sfx(&"whoosh_heavy")
		Charge.RUN:
			var nx := px + charge_dir * CHARGE_SPEED
			var cx := level.clamp_x(self, nx)
			if connected:
				# Ha preso GIG: frena e torna ad aspettare.
				_finish_charge(false)
			elif cx != nx or charge_t >= CHARGE_MAX:
				px = cx
				_finish_charge(true)
			else:
				px = nx


## Fine della carica: col bersaglio preso si ferma; a vuoto sbatte contro il bordo e resta stordito.
func _finish_charge(missed: bool) -> void:
	charge = Charge.NONE
	_charge_try = false
	_release_token()
	level.director.set_cooldown(self, level.tick + rng.randi_range(data.cooldown_ticks.x, data.cooldown_ticks.y))
	mind = Mind.WAIT
	if missed:
		set_state(State.HURT, &"dizzy")
		_staggered = true
		stun = DIZZY_TICKS
		dizzy = DIZZY_TICKS
		_push_ticks = 6
		_push_v = -charge_dir * 1.5
		level.add_shake(0.3)
		_sfx(&"body_thud")
		_fx(&"dust_land", 0)
		Game.count(&"cariche_a_vuoto")
	else:
		set_state(State.IDLE)


## La carica la chiude il codice (a segno o contro il bordo), non la fine dell'animazione.
func _auto_transitions() -> void:
	if charge != Charge.NONE and state == State.ATTACK:
		return
	super._auto_transitions()


## Durante la corsa la spallata colpisce col corpo intero.
func active_hitboxes() -> Array[Rect2]:
	if charge == Charge.RUN and hitstop == 0 and not removed:
		var out: Array[Rect2] = [to_world(_charge_atk.hitbox)]
		return out
	if charge == Charge.WIND:
		var none: Array[Rect2] = []
		return none
	return super.active_hitboxes()


## Pesante: in carica i colpi leggeri non lo fermano.
func has_armor() -> bool:
	return charge != Charge.NONE or super.has_armor()


# --- La guardia ---------------------------------------------------------------------------------

## Para i pugni di GIG che arrivano da davanti mentre è libero (aspetta o si avvicina). La presa,
## il calcio in salto e i corpi lanciati passano sempre. Al terzo colpo parato la guardia salta.
func try_block(attacker: Entity, atk: AttackData) -> bool:
	if not (attacker is Gig) or not is_free() or dead or charge != Charge.NONE:
		return false
	var g := attacker as Gig
	if g.state != State.ATTACK or atk.air or g.is_airborne():
		return false
	var side := 1 if g.px > px else (-1 if g.px < px else 0)
	if side != facing:
		return false
	guard_hits += 1
	_guard_t = 0
	hitstop = BLOCK_HITSTOP
	_shake_ticks = BLOCK_HITSTOP
	flash = FLASH_TICKS
	px = level.clamp_x(self, px - facing * 1.5)
	if guard_hits >= GUARD_HITS:
		guard_hits = 0
		_interrupt()
		set_state(State.HURT, &"dizzy")
		_staggered = true
		stun = GUARD_BREAK_STUN
		_push_ticks = 8
		_push_v = -facing * 1.25
		Game.count(&"guardie_rotte")
	else:
		set_state(State.IDLE, &"block")
		_block_t = BLOCK_HOLD
	return true


## Stordito (guardia rotta o carica a vuoto), i colpi non accorciano lo stordimento.
func _enter_hurt(atk: AttackData, info: HitInfo) -> void:
	var keep := stun if state == State.HURT else 0
	super._enter_hurt(atk, info)
	stun = maxi(stun, keep)


func _on_state_changed(prev: State, next: State) -> void:
	# Atterrato o afferrato in carica: la carica finisce lì.
	if charge != Charge.NONE and next != State.ATTACK:
		charge = Charge.NONE
		_charge_try = false
		if level.director.is_holder(self):
			_release_token()
	if next != State.HURT:
		dizzy = 0
		_staggered = false
	if next != State.IDLE:
		_block_t = 0
	super._on_state_changed(prev, next)


# --- Disegno ------------------------------------------------------------------------------------

func sync_visual() -> void:
	super.sync_visual()
	if _stars != null:
		_stars.queue_redraw()


## Le stelline che girano sopra la testa, quando è stordito dopo la carica a vuoto.
func _draw_stars() -> void:
	if dizzy <= 0 or removed:
		return
	var t := float(level.tick) * 0.15
	for i in 3:
		var a := t + i * TAU / 3.0
		var p := Vector2(roundf(cos(a) * 14.0), roundf(-128.0 + sin(a) * 4.0))
		var c := Color8(255, 226, 122) if sin(a) > 0.0 else Color8(200, 170, 90)
		_stars.draw_rect(Rect2(p + Vector2(-1, 0), Vector2(3, 1)), c)
		_stars.draw_rect(Rect2(p + Vector2(0, -1), Vector2(1, 3)), c)
