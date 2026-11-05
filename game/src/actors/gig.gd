class_name Gig
extends Fighter
## GIG, il giocatore. Controlli del §5:
## - camminata 1,5 px/tick in orizzontale e 1 px/tick in profondità;
## - corsa con il doppio tocco della direzione entro 12 tick (3 px/tick);
## - salto (4,4 px/tick, gravità 0,26) e calcio in salto;
## - combo jab1 → jab2 → gancio → calcio che avanza solo se il colpo va a segno, buffer di 8 tick;
## - presa automatica camminando contro un nemico, due ginocchiate e proiezione;
## - morte, vite e rientro con invulnerabilità.

enum GrabAction { HOLD, KNEE, THROW }

const BUFFER_TICKS := 8
const RUN_TAP_WINDOW := 12
## Tick dopo la fine di un attacco andato a segno in cui il tasto attacco continua la combo.
const COMBO_WINDOW := 30
const GRAB_RANGE_X := 22.5
const GRAB_RANGE_Y := 5.0
const GRAB_ESCAPE_TICKS := 90
## La presa scatta entro GRAB_RANGE_X, ma la posa la vuole a circa 30 px (voce victim): la
## vittima ci scivola in questi tick invece di scattare di 12-14 px in un tick.
const GRAB_SETTLE_TICKS := 4
const MAX_KNEES := 2
## Distanza della vittima al rilascio della proiezione se lo sprite non ha la voce victim.
const THROW_RELEASE_DX := 22.5
const RESPAWN_HEIGHT := 187.5
const RESPAWN_INVULN := 120
const DEAD_BLINK_TICKS := 60
## Pignoramento del rider: pressioni per divincolarsi e durata del braccio sospeso (4 s).
const ESCAPE_PRESSES := 8
const ARM_OFF_TICKS := 240
const ESCAPE_INVULN := 24

const CHAIN: Array[StringName] = [&"gig_jab1", &"gig_jab2", &"gig_hook", &"gig_kick"]
const ATTACK_IDS: Array[StringName] = [&"gig_jab1", &"gig_jab2", &"gig_hook", &"gig_kick", &"gig_air_kick",
	&"gig_knee", &"gig_throw", &"gig_throw_body"]

var input: InputFrame = InputFrame.new()
var buf_attack: int = 0
var buf_jump: int = 0
## Indice in CHAIN della prossima mossa, valido finché combo_timer > 0.
var combo_step: int = 0
var combo_timer: int = 0
var knees: int = 0
var grab_action: GrabAction = GrabAction.HOLD
var grab_action_tick: int = 0
var air_attacked: bool = false
var attacks: Dictionary[StringName, AttackData] = {}
## Pressioni contate mentre un rider tenta il pignoramento.
var escape_presses: int = 0
## Tick rimasti di braccio sospeso: niente prese, niente calcio in salto, pugni a metà danno.
var arm_off: int = 0

var _run_dir: int = 0
var _last_tap_dir: int = 0
var _last_tap_tick: int = -1000
var _grab_cooldown: int = 0
var _waiting_life: bool = false
## Proiezione all'indietro chiesta: GIG si gira al secondo fotogramma della proiezione.
var _throw_back: bool = false
## Avvicinamento della vittima appena afferrata: tick rimasti e distanza di partenza.
var _settle: int = 0
var _settle_from: float = 0.0


func setup_gig(lvl: Level, id: int) -> void:
	setup(load("res://data/fighters/gig.tres") as FighterData, lvl, id, Team.PLAYER)
	for a in ATTACK_IDS:
		attacks[a] = load("res://data/attacks/%s.tres" % a) as AttackData


## Ingressi del tick, chiamata a ogni tick del mondo (anche durante hitstop e congelamenti),
## così una pressione non va persa: resta nel buffer per 8 tick di GIG.
func feed_input(frame: InputFrame, world_tick: int) -> void:
	input = frame
	# Afferrato da un rider ogni tasto premuto conta per divincolarsi, e non resta nel buffer.
	if state == State.GRABBED:
		if frame.pressed != 0:
			escape_presses += 1
		return
	if frame.was_pressed(InputFrame.ATTACK):
		buf_attack = BUFFER_TICKS
	if frame.was_pressed(InputFrame.JUMP):
		buf_jump = BUFFER_TICKS
	for dir: int in [-1, 1]:
		if frame.was_pressed(InputFrame.LEFT if dir < 0 else InputFrame.RIGHT):
			if _last_tap_dir == dir and world_tick - _last_tap_tick <= RUN_TAP_WINDOW:
				_run_dir = dir
			_last_tap_dir = dir
			_last_tap_tick = world_tick


func _think() -> void:
	if combo_timer > 0 and state != State.ATTACK:
		combo_timer -= 1
		if combo_timer == 0:
			combo_step = 0
	if _grab_cooldown > 0:
		_grab_cooldown -= 1
	if arm_off > 0:
		arm_off -= 1
	if input.axis_x() != _run_dir:
		_run_dir = 0
	match state:
		State.IDLE, State.WALK, State.RUN:
			_think_free()
		State.JUMP:
			_think_air()
		State.ATTACK:
			_think_attack()
		State.GRAB:
			_think_grab()
		State.GRABBED:
			# Si dimena: alterna i due fotogrammi del colpo subito. La posizione la tiene chi afferra.
			anim.show_frame(&"hurt_high", (state_ticks / 6) % 2)
	if buf_attack > 0:
		buf_attack -= 1
	if buf_jump > 0:
		buf_jump -= 1


func _think_free() -> void:
	if buf_jump > 0:
		_start_jump()
		return
	if buf_attack > 0:
		_start_chain_attack()
		return
	var ax := input.axis_x()
	var ay := input.axis_y()
	if ax != 0:
		facing = ax
	var running := _run_dir != 0 and ax == _run_dir
	if ax == 0 and ay == 0:
		if state != State.IDLE:
			set_state(State.IDLE)
	elif running:
		if state != State.RUN:
			set_state(State.RUN)
			_fx(&"dust_skid", 0)
	elif state != State.WALK:
		set_state(State.WALK)
	# Dopo il cambio di stato (che azzera le velocità entrando in IDLE).
	vx = ax * (data.run_speed if running else data.walk_speed.x)
	vy = ay * data.walk_speed.y
	if ax != 0 and _grab_cooldown == 0 and arm_off == 0:
		var target := level.find_grab_target(self)
		if target != null:
			_start_grab(target)


func _start_jump() -> void:
	buf_jump = 0
	var ax := input.axis_x()
	var running := state == State.RUN
	if ax != 0:
		facing = ax
	set_state(State.JUMP, &"jump_rise")
	vx = ax * (data.run_speed if running else data.walk_speed.x)
	vy = input.axis_y() * data.walk_speed.y * 0.5
	vh = data.jump_velocity
	grav = data.gravity
	air_attacked = false
	_sfx_unless_anim(&"jump")


func _think_air() -> void:
	if buf_attack > 0 and not air_attacked and arm_off == 0:
		buf_attack = 0
		air_attacked = true
		start_attack(attacks[&"gig_air_kick"], level.next_attack_serial())
		return
	if vh <= 0.0 and anim.name == &"jump_rise":
		play_anim(&"jump_fall")


func _start_chain_attack() -> void:
	buf_attack = 0
	var ax := input.axis_x()
	if ax != 0:
		facing = ax
	if combo_timer <= 0:
		combo_step = 0
	start_attack(attacks[CHAIN[combo_step]], level.next_attack_serial())
	vx = 0.0
	vy = 0.0


func _think_attack() -> void:
	if attack == null or attack.air:
		return
	var idx := CHAIN.find(attack.id)
	if idx < 0 or idx >= CHAIN.size() - 1:
		return
	# Concatenazione: solo se il colpo è andato a segno e nella finestra di cancel.
	if connected and buf_attack > 0 and _in_cancel_window():
		combo_step = idx + 1
		combo_timer = COMBO_WINDOW
		_start_chain_attack()


## Finestra di cancel: i fotogrammi con il tag "cancel"; se l'animazione non ne ha,
## tutto il recupero (dopo i fotogrammi attivi).
func _in_cancel_window() -> bool:
	if anim.clip.has_tag_anywhere(AnimFrame.TAG_CANCEL):
		return anim.has_tag(AnimFrame.TAG_CANCEL)
	return attack_tick >= attack.startup + attack.active


func _end_attack() -> void:
	var idx := CHAIN.find(attack.id) if attack != null else -1
	if idx >= 0 and connected and idx < CHAIN.size() - 1:
		combo_step = idx + 1
		combo_timer = COMBO_WINDOW
	else:
		combo_step = 0
		combo_timer = 0
	super._end_attack()


## Chiamata dal CombatSystem quando l'attacco corrente colpisce qualcuno.
func on_attack_connected(_victim: Entity) -> void:
	connected = true


# --- Presa ------------------------------------------------------------------------------------

func _start_grab(v: Fighter) -> void:
	facing = 1 if v.px >= px else -1
	set_state(State.GRAB, &"grab_hold")
	vx = 0.0
	vy = 0.0
	grab_partner = v
	grab_ticks = 0
	knees = 0
	grab_action = GrabAction.HOLD
	_throw_back = false
	_settle_from = absf(v.px - px)
	_settle = GRAB_SETTLE_TICKS
	v.become_grabbed(self)
	buf_attack = 0
	_sfx_unless_anim(&"grab")
	Game.count(&"grabs")
	_place_victim()


func _think_grab() -> void:
	var v := grab_partner
	if v == null or v.state != State.GRABBED:
		_leave_grab()
		return
	grab_ticks += 1
	if _settle > 0:
		_settle -= 1
	match grab_action:
		GrabAction.HOLD:
			if grab_ticks >= GRAB_ESCAPE_TICKS:
				_victim_escapes()
				return
			if buf_attack > 0:
				buf_attack = 0
				var back := input.axis_x() == -facing
				if back or knees >= MAX_KNEES:
					_start_throw(back)
				else:
					_start_knee()
		GrabAction.KNEE:
			grab_action_tick += 1
			var knee: AttackData = attacks[&"gig_knee"]
			if grab_action_tick == knee.startup:
				knees += 1
				_hit_victim(v, knee, facing)
				# Ginocchiata che manda KO: la vittima vola via (knock_air), la presa finisce.
				if grab_partner == null or v.state != State.GRABBED:
					_leave_grab()
					return
			if anim.finished:
				grab_action = GrabAction.HOLD
				play_anim(&"grab_hold")
		GrabAction.THROW:
			grab_action_tick += 1
			# Proiezione all'indietro: GIG si gira quando solleva la vittima sopra la testa
			# (secondo fotogramma), così la vittima passa dall'altra parte senza salti.
			if _throw_back and anim.index >= 1:
				_throw_back = false
				facing = -facing
			var throw: AttackData = attacks[&"gig_throw"]
			if grab_action_tick == throw.startup:
				_release_throw(v)
				return
	if grab_partner != null:
		_place_victim()


func _start_knee() -> void:
	grab_action = GrabAction.KNEE
	grab_action_tick = 0
	var knee: AttackData = attacks[&"gig_knee"]
	anim.play(&"knee", sheet.attack_clip(&"knee", knee))
	if not _clip_has_sfx(anim.clip):
		_sfx(knee.sfx_whoosh)


func _start_throw(back: bool) -> void:
	_throw_back = back
	grab_action = GrabAction.THROW
	grab_action_tick = 0
	var throw: AttackData = attacks[&"gig_throw"]
	anim.play(&"throw", sheet.attack_clip(&"throw", throw))
	if not _clip_has_sfx(anim.clip):
		_sfx(throw.sfx_whoosh)


func _hit_victim(v: Fighter, atk: AttackData, dir: int) -> void:
	hit_registry.clear()
	var hb := v.world_hurtboxes()
	var point := hb[0].get_center() if not hb.is_empty() else Vector2(v.px, v.py - 63)
	level.combat.apply_hit(self, v, atk, point, dir)


func _release_throw(v: Fighter) -> void:
	var throw: AttackData = attacks[&"gig_throw"]
	# La vittima parte da dove è disegnata nel fotogramma del rilascio (voce victim, dx ≈ 30):
	# la clip "thrown" che riprende da 0 mostra la stessa posa, quindi non c'è nessun salto.
	if _throw_back:
		_throw_back = false
		facing = -facing
	var e := anim.frame().victim_entry(v.data.sprite_id)
	var release_dx := float(e[0]) if not e.is_empty() else THROW_RELEASE_DX
	grab_partner = null
	v.grab_partner = null
	v.draw_dy = 0
	v.draw_bias = 0
	v.state = State.IDLE
	# Mai oltre i muri: la vittima resterebbe ferma fuori schermo durante l'hitstop.
	v.px = level.clamp_x(v, px + facing * release_dx)
	_hit_victim(v, throw, facing)
	if not _clip_has_event(anim.clip, "sfx:throw"):
		_sfx(&"throw")
	v.become_thrown(attacks[&"gig_throw_body"], Team.PLAYER, level.next_attack_serial())
	Game.count(&"throws")
	# GIG resta nella posa della proiezione fino alla fine del recupero.
	set_state(State.ATTACK)
	attack = throw
	attack_tick = throw.startup
	connected = true


func _victim_escapes() -> void:
	var v := grab_partner
	release_grab(true)
	if v != null:
		v.invuln = maxi(v.invuln, 12)
	_grab_cooldown = 30
	set_state(State.IDLE)


func _leave_grab() -> void:
	grab_partner = null
	set_state(State.IDLE)


## Posiziona la vittima secondo il campo "victim" del fotogramma corrente.
func _place_victim() -> void:
	var v := grab_partner
	var f := anim.frame()
	var e := f.victim_entry(v.data.sprite_id)
	var dx := 23
	var dy := 0
	var vanim: StringName = &"grabbed"
	var vframe := 0
	if e.is_empty():
		match grab_action:
			GrabAction.KNEE:
				vanim = &"kneed"
				vframe = 1 if grab_action_tick >= attacks[&"gig_knee"].startup else 0
			GrabAction.THROW:
				vanim = &"thrown"
				dy = -int(round(35.0 * grab_action_tick / maxf(1.0, attacks[&"gig_throw"].startup)))
	else:
		dx = int(e[0])
		dy = int(e[1])
		if str(e[2]) != "":
			vanim = StringName(str(e[2]))
		vframe = int(e[3])
	var want := float(dx)
	if _settle > 0:
		want = lerpf(want, _settle_from, float(_settle) / (GRAB_SETTLE_TICKS + 1))
	# La coppia resta dentro i muri: se la vittima finirebbe oltre, GIG arretra.
	var target := px + facing * want
	var fit := level.clamp_x(v, target)
	if fit != target:
		px = level.clamp_x(self, px + fit - target)
	v.px = level.clamp_x(v, px + facing * want)
	v.py = py
	v.ph = 0.0
	v.draw_dy = dy
	v.draw_bias = -1 if f.victim_behind else 1
	v.facing = -facing
	v.anim.show_frame(vanim, vframe)


func _enter_hurt(atk: AttackData, info: HitInfo) -> void:
	buf_attack = 0
	super._enter_hurt(atk, info)


# --- Pignoramento del rider -------------------------------------------------------------------

func _on_grabbed() -> void:
	escape_presses = 0
	buf_attack = 0
	buf_jump = 0
	combo_step = 0
	combo_timer = 0


## Divincolato: torna libero con un attimo di invulnerabilità.
func escape_from_grab() -> void:
	_release_from_grab()
	escape_presses = 0
	invuln = maxi(invuln, ESCAPE_INVULN)
	_sfx(&"whoosh_light")


## Pignoramento riuscito: poco danno, un colpo all'indietro e il braccio sospeso.
func suspend_arm(damage: int) -> void:
	_release_from_grab()
	escape_presses = 0
	hp = maxi(hp - damage, 1)
	flash = FLASH_TICKS
	arm_off = ARM_OFF_TICKS
	set_state(State.HURT, &"hurt_low")
	stun = 16
	_sfx(&"hit_light")


## Col braccio sospeso i pugni fanno metà danno.
func damage_scale() -> float:
	return 0.5 if arm_off > 0 else 1.0


func arm_greyed() -> bool:
	return arm_off > 0


## Una combo interrotta da un colpo riparte da jab1.
func _on_state_changed(_prev: State, next: State) -> void:
	if next == State.HURT or next == State.KNOCK_AIR:
		combo_step = 0
		combo_timer = 0


# --- Morte e rientro -------------------------------------------------------------------------

func _on_down_while_dead() -> void:
	set_state(State.DEAD)
	vanish_timer = DEAD_BLINK_TICKS
	_waiting_life = true


func _auto_transitions() -> void:
	if state == State.DEAD:
		if vanish_timer > 0:
			vanish_timer -= 1
			if vanish_timer == 0 and _waiting_life:
				_waiting_life = false
				level.on_player_died()
		return
	super._auto_transitions()


func _compute_blink() -> bool:
	if state == State.DEAD:
		return vanish_timer == 0 or (vanish_timer / BLINK_PERIOD) % 2 == 1
	return super._compute_blink()


## Rientra dall'alto con la vita piena e l'invulnerabilità.
func respawn() -> void:
	hp = data.max_hp
	dead = false
	removed = false
	ph = RESPAWN_HEIGHT
	vx = 0.0
	vy = 0.0
	vh = 0.0
	grav = data.gravity
	invuln = RESPAWN_INVULN
	arm_off = 0
	escape_presses = 0
	combo_step = 0
	combo_timer = 0
	set_state(State.JUMP, &"jump_fall")
	air_attacked = true


func shadow_width() -> int:
	if state == State.DEAD and vanish_timer == 0:
		return 0
	return super.shadow_width()
