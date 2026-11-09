class_name PlatformPlayer
extends RefCounted
## GIG nei tratti platform: la simulazione pura, un tick alla volta, senza nodi.
##
## Posizione e velocità sono interi in sottopixel (SUB per pixel): niente float che si
## accumulano, così due partite con gli stessi ingressi finiscono nello stesso stato e i
## replay con hash tornano. Il movimento è "a pixel": prima l'asse x, poi l'asse y, un pixel
## alla volta contro la SolidGrid, quindi niente compenetrazioni nemmeno alla velocità massima.
##
## Il corpo è un rettangolo con i piedi in (px, py): occupa le colonne [px - w/2, px - w/2 + w)
## e le righe [py - h, py). Lo disegna TestRoom (o un livello), che legge `anim`, `facing` ed
## `events`.
##
## Mosse di questa prima tappa: corsa, salto variabile con coyote time e buffer, la Spinta
## (il doppio salto con la scarica del braccio verso il basso), piattaforme sottili con GIÙ +
## SALTO per scendere, accovacciarsi, scivolata, aggrapparsi alle sporgenze e salire.

const SUB := 256

enum State { GROUND, AIR, CROUCH, SLIDE, LEDGE_HANG, LEDGE_CLIMB, WALL_SLIDE, WALL_RUN, DASH }

const STATE_NAMES := ["A TERRA", "IN ARIA", "ACCOVACCIATO", "SCIVOLATA", "APPESO", "SALE", "AL MURO",
	"SU PER IL MURO", "SCATTO"]

## La clip ledge_climb (ClimbUp_1m_RM) ha l'ancora ferma per tutti i fotogrammi: è il punto a terra
## del primo, sotto il corpo. Misurata sui fotogrammi (mani e piedi contro un muro disegnato): il
## bordo del muro sta 25 px davanti all'ancora e la cima 57 px sopra (a 60 px/m). Nel penultimo fotogramma,
## dove la salita finisce, il busto è 78 px avanti: lì si mette GIG, così il busto non scatta.
const CLIMB_FACE := 25
const CLIMB_RISE := 57
const CLIMB_FWD := 78
## Quanto dentro la sporgenza può finire la salita, dal bordo del muro: il più lontano che c'è posto,
## fino a dove porta la clip (CLIMB_FWD - CLIMB_FACE).
const CLIMB_REACH: Array[int] = [15, 30, 40, 53]
## I primi due fotogrammi della clip sono la rincorsa da terra: dalla sporgenza si parte dal terzo,
## con i piedi già sul muro.
const CLIMB_FIRST := 2
## Tick in cui lo sprite passa dall'altezza da appeso (o da salto) a quella della clip.
const CLIMB_EASE := 9
## Da appeso, quanto più in basso parte lo sprite: così le mani del terzo fotogramma restano
## sullo spigolo invece di saltare in alto.
const HANG_DROP := 14
## Appeso, il corpo è più lungo che in piedi: nella clip ledge_hang le scarpe arrivano 128 px sotto
## lo spigolo (le mani a -125 dall'ancora, più la suola). Ci si appende solo se fin lì è tutto
## libero; con il pavimento più vicino (un muro alto meno di 7 blocchi) GIG scavalca.
const HANG_LEGS := 128
## Tick dopo GIÙ in cui una direzione fa ancora partire la scivolata (GIÙ e la direzione insieme
## sul pad arrivano spesso a un tick o due di distanza).
const SLIDE_GRACE := 6
## Tick dopo un salto di corsa in cui toccare un muro fa ancora partire la corsa sul muro.
const WALLRUN_WINDOW := 12
## Ogni quanti tick il braccio piantato nel muro fa scintille.
const WALL_SPARK_EVERY := 5
## Tick dopo la corsa sul muro in cui SALTO è ancora la Spinta (non il salto a muro) e il braccio
## non frena: in cima alla corsa si sale ancora.
const WALLRUN_GRACE := 8
## Col braccio bloccato (il prologo, prima del riavvio) ci si tira su con la sola destra: bisogna
## tenere SU (o la direzione del muro) per tanti tick prima che la salita parta.
const ONE_HAND_STRAIN := 16

var moves: PlatformMoves
var grid: SolidGrid

var px: int = 0
var py: int = 0
var rx: int = 0
var ry: int = 0
var vx: int = 0
var vy: int = 0
var facing: int = 1
var state: State = State.AIR
var height: int = 100

var boosts_left: int = 0
var coyote: int = 0
var buf_jump: int = 0
var drop_timer: int = 0
var slide_timer: int = 0
var slide_cd: int = 0
var ledge_cd: int = 0
var climb_timer: int = 0
var climb_total: int = 1
## Dove finisce la salita, in px dal bordo del muro, e quanto più in basso parte lo sprite.
var climb_dx: int = 15
var climb_yoff: int = 0
## Tick passati da accovacciato (per la scivolata con GIÙ e poi la direzione).
var crouch_age: int = 0
## Spigolo della sporgenza a cui GIG è appeso: x della colonna di pixel del muro, y della cima.
var ledge_x: int = 0
var ledge_y: int = 0
var tick: int = 0

## Muri: da che parte è il muro toccato (1 destra, -1 sinistra), i tick di presa del braccio, il
## coyote time del muro e il blocco del controllo dopo un salto a muro.
var wall_dir: int = 1
var wall_stick_t: int = 0
var wall_coyote_t: int = 0
var wall_lock: int = 0
var dash_left: int = 1
var dash_timer: int = 0
var wallrun_used: bool = false
var wallrun_end_t: int = 0
## Tick in cui vale ancora lo slancio della corsa, e se il salto in corso è partito di corsa.
var momentum: int = 0
var _jump_fast: bool = false

## Il salto in corso si può ancora "tagliare" lasciando il tasto.
var _can_cut: bool = false
var _just_boosted: bool = false

## Eventi del tick per gli effetti e i suoni: "jump", "spinta", "land", "slide", "grab", "climb".
var events: PackedStringArray = []
## Dove lo scatto ha rotto un Rompibile (l'evento «rompe»): il riquadro in pixel delle celle rotte.
var last_break: Rect2i = Rect2i()
## Una posa imposta da fuori (per esempio l'hacking della stanza), al posto di quella dello stato.
## Solo disegno: non entra nell'impronta dello stato.
var pose_override: StringName = &""
## Braccio cyber bloccato (decisione 34 e scelta di Luigi del 5 novembre 2026: «base + appeso»):
## corsa, salto semplice, accovacciarsi, scivolata e sporgenze con la sola destra. Niente Spinta,
## muri, scatto né corsa sul muro.
var arm_locked: bool = false
## Tick di sforzo già fatti per tirarsi su con una mano (0 = non sta salendo).
var strain: int = 0
## La planata dell'ombrello (power-up): in discesa, tenendo SALTO, GIG non cade più veloce di così
## (px/tick). 0 = niente planata. `gliding` dice se in questo tick sta planando.
var glide_fall: float = 0.0
var gliding: bool = false
## La corsa rallentata (i fanghi della bonifica): la velocità massima in percentuale.
var speed_pct: int = 100
## Lo scatto del caffè: la velocità massima in percentuale, sopra quella delle zone. Lo decide la stanza.
var boost_pct: int = 100

## Il colpo solo contro i droni (legenda §4b): un jab a terra, un calcio in aria. Lo accende la stanza
## solo dove ci sono droni, così altrove ATTACCO resta libero e le impronte di prima non cambiano.
var can_jab: bool = false
## Vicino alla processione il colpo non parte (legenda §4c): lo decide la stanza a ogni tick.
var jab_block: bool = false
## Tick che restano del colpo in corso (0 = nessuno); `jab_hit` dice che ha già rotto qualcosa.
var jab_t: int = 0
var jab_hit: bool = false
## La spinta indietro di un colpo preso: per `hurt_t` tick i tasti non contano e GIG scivola di
## `knock_vx` sottopixel a tick. Poi `inv_t` tick di invulnerabilità, che lampeggia.
var hurt_t: int = 0
var knock_vx: int = 0
var inv_t: int = 0
## Il sigillo «PIGNORATO» della Vedetta: incollato, si stacca dopo tante pressioni di tasti.
var stuck_left: int = 0
var anim: FrameAnim
## I fogli di GIG: col braccio cyber acceso e, se c'è, col braccio morto (prima del riavvio: luci spente, il
## braccio che pende). Solo disegno: la salita (ledge_climb), l'unica clip che la fisica legge, dura uguale nei due.
var sheet_free: SpriteSheet
var sheet_locked: SpriteSheet

## Misure per la taratura, mostrate dalla stanza di prova: altezza massima dell'ultimo salto
## (in px, dai piedi alla partenza) e tick passati in aria.
var last_peak: int = 0
var air_ticks: int = 0
var _takeoff_y: int = 0
var _peak_y: int = 0


func _init(m: PlatformMoves, g: SolidGrid, sheet: SpriteSheet = null) -> void:
	moves = m
	grid = g
	height = moves.body_height
	sheet_free = sheet
	if sheet != null:
		anim = FrameAnim.new(sheet)
		anim.play(&"idle")


static func to_sub(v: float) -> int:
	return roundi(v * SUB)


func place(x: int, y: int) -> void:
	px = x
	py = y
	rx = 0
	ry = 0
	vx = 0
	vy = 0
	height = moves.body_height
	state = State.GROUND if _on_floor() else State.AIR
	boosts_left = boosts_max()
	dash_left = 1
	wallrun_used = false
	wall_lock = 0
	momentum = 0
	jab_t = 0
	jab_hit = false
	hurt_t = 0
	knock_vx = 0
	inv_t = 0
	stuck_left = 0


# ------------------------------------------------------------------ geometria

func left() -> int:
	return px - moves.body_width / 2


func right() -> int:
	return left() + moves.body_width


func top() -> int:
	return py - height


func _on_floor() -> bool:
	return grid.floor_at(left(), right(), py, drop_timer == 0)


func _fits(h: int, x: int = px, y: int = py) -> bool:
	var l := x - moves.body_width / 2
	return not grid.rect_hits_solid(l, y - h, l + moves.body_width, y)


## Sposta di `amount` sottopixel in orizzontale; restituisce la direzione del muro toccato (0 se nessuno).
func _move_x(amount: int) -> int:
	rx += amount
	var steps := rx / SUB
	rx -= steps * SUB
	var dir := signi(steps)
	while steps != 0:
		if grid.rect_hits_solid(left() + dir, top(), right() + dir, py):
			vx = 0
			rx = 0
			return dir
		px += dir
		steps -= dir
	return 0


## Sposta di `amount` sottopixel in verticale; restituisce 1 se ha toccato terra, -1 il soffitto.
func _move_y(amount: int) -> int:
	ry += amount
	var steps := ry / SUB
	ry -= steps * SUB
	var dir := signi(steps)
	while steps != 0:
		if dir > 0:
			if _on_floor():
				ry = 0
				return 1
		elif grid.rect_hits_solid(left(), top() - 1, right(), top()):
			ry = 0
			return -1
		py += dir
		steps -= dir
	return 0


# ------------------------------------------------------------------ tick

func step(input: InputFrame) -> void:
	tick += 1
	events = PackedStringArray()
	_just_boosted = false
	gliding = false
	if can_jab or hurt_t > 0 or stuck_left > 0 or inv_t > 0 or jab_t > 0:
		input = _combat_input(input)
	if input.was_pressed(InputFrame.JUMP):
		buf_jump = moves.jump_buffer
	elif buf_jump > 0:
		buf_jump -= 1
	drop_timer = maxi(drop_timer - 1, 0)
	slide_cd = maxi(slide_cd - 1, 0)
	ledge_cd = maxi(ledge_cd - 1, 0)
	wall_coyote_t = maxi(wall_coyote_t - 1, 0)
	wall_lock = maxi(wall_lock - 1, 0)
	momentum = maxi(momentum - 1, 0)
	wallrun_end_t = maxi(wallrun_end_t - 1, 0)
	match state:
		State.GROUND:
			_tick_ground(input)
		State.AIR:
			_tick_air(input)
		State.CROUCH:
			_tick_crouch(input)
		State.SLIDE:
			_tick_slide(input)
		State.LEDGE_HANG:
			_tick_hang(input)
		State.LEDGE_CLIMB:
			_tick_climb()
		State.WALL_SLIDE:
			_tick_wall_slide(input)
		State.WALL_RUN:
			_tick_wall_run(input)
		State.DASH:
			_tick_dash(input)
	if state == State.AIR:
		air_ticks += 1
		_peak_y = mini(_peak_y, py)
	_update_anim()


func _tick_ground(input: InputFrame) -> void:
	var ax := input.axis_x()
	if ax != 0:
		facing = ax
	if input.is_held(InputFrame.DOWN):
		# GIÙ in corsa, o GIÙ con una direzione anche da fermi: scivolata. GIÙ da solo: accovacciato.
		var fast := absi(vx) >= to_sub(moves.slide_min_speed)
		if input.was_pressed(InputFrame.DOWN) and _can_slide(ax if ax != 0 else (facing if fast else 0)):
			_start_slide()
			return
		_enter_crouch()
		_tick_crouch(input)
		return
	_run(ax, to_sub(moves.run_speed), to_sub(moves.ground_accel), to_sub(moves.ground_decel), to_sub(moves.ground_turn))
	if absi(vx) >= to_sub(moves.wallrun_min_speed):
		momentum = moves.wallrun_momentum
	if buf_jump > 0 and not arm_locked and _can_wall_run(ax):
		_start_wall_run()
		return
	if buf_jump > 0:
		_jump()
		_tick_air_motion(input)
		return
	# La spallata: a terra lo scatto non c'è, ma con un Rompibile davanti, alla portata dello scatto,
	# SCATTO parte di spalla e lo rompe (le porte marce sono alte quanto GIG e poggiano sul piano).
	if input.was_pressed(InputFrame.DASH) and not arm_locked and _breakable_ahead(ax if ax != 0 else facing):
		_start_dash(ax)
		return
	# La spallata in corsa, col braccio bloccato (prima del riavvio lo scatto non c'è): a piena corsa
	# GIG sfonda di spalla il Rompibile che ha davanti. Da fermo la corsa arriva piena in dieci tick
	# (run_speed / ground_accel), quindi serve la rincorsa e appoggiarsi alla porta non basta.
	if arm_locked and ax != 0 and signi(vx) == ax and absi(vx) >= to_sub(moves.run_speed):
		_shoulder()
	_stop_at_wall(ax)
	_move_x(vx)
	if not _on_floor():
		_leave_ground(true)


## Rompe il Rompibile che GIG incontra di spalla in questo tick, nel verso in cui guarda: l'evento
## «rompe», e in last_break dove.
func _shoulder() -> void:
	if grid.breakable.is_empty():
		return
	var reach := absi(rx + vx) / SUB + 1
	var a := right() if facing > 0 else left() - reach
	var hit := grid.break_in(a, top(), a + reach, py)
	if hit.has_area():
		last_break = hit
		events.append("rompe")


## C'è un Rompibile davanti, nel verso `dir`, entro la strada che fa uno scatto?
func _breakable_ahead(dir: int) -> bool:
	var reach := ceili(moves.dash_speed * moves.dash_ticks)
	var a := right() if dir > 0 else left() - reach
	return grid.has_breakable(a, top(), a + reach, py)


## Spingendo contro un muro già toccato la velocità non si accumula. Senza, vx sale per qualche
## tick finché il passo di un pixel non sbatte, poi si azzera: l'animazione salta fra fermo e
## corsa e GIG trema.
func _stop_at_wall(ax: int) -> void:
	if ax != 0 and signi(vx) != -ax and grid.rect_hits_solid(left() + ax, top(), right() + ax, py):
		vx = 0
		rx = 0


func _can_slide(ax: int) -> bool:
	return slide_cd == 0 and ax != 0 and not grid.rect_hits_solid(left() + ax, py - moves.crouch_height, right() + ax, py)


func _tick_crouch(input: InputFrame) -> void:
	var ax := input.axis_x()
	if ax != 0:
		facing = ax
	crouch_age += 1
	if input.is_held(InputFrame.DOWN) and crouch_age <= SLIDE_GRACE and _can_slide(ax):
		_start_slide()
		return
	var stand_ok := _fits(moves.body_height)
	if buf_jump > 0 and grid.only_thin_at(left(), right(), py):
		# GIÙ + SALTO su una piattaforma sottile: si scende.
		buf_jump = 0
		drop_timer = moves.drop_ticks
		_leave_ground(false)
		return
	if not input.is_held(InputFrame.DOWN) and stand_ok:
		height = moves.body_height
		state = State.GROUND
		_tick_ground(input)
		return
	if buf_jump > 0 and stand_ok and not input.is_held(InputFrame.DOWN):
		height = moves.body_height
		_jump()
		_tick_air_motion(input)
		return
	var sp := to_sub(moves.crouch_speed)
	_run(ax, sp, to_sub(moves.ground_accel), to_sub(moves.ground_decel), to_sub(moves.ground_turn))
	_stop_at_wall(ax)
	_move_x(vx)
	if not _on_floor():
		if stand_ok:
			height = moves.body_height
		_leave_ground(true)


func _tick_slide(input: InputFrame) -> void:
	slide_timer -= 1
	var fr := to_sub(moves.slide_friction)
	vx = maxi(absi(vx) - fr, 0) * signi(vx)
	var stand_ok := _fits(moves.body_height)
	if buf_jump > 0 and stand_ok:
		# Salto dalla scivolata: tiene lo slancio.
		height = moves.body_height
		_jump()
		_tick_air_motion(input)
		return
	if _move_x(vx) != 0:
		vx = 0
	if not _on_floor():
		if stand_ok:
			height = moves.body_height
		_leave_ground(true)
		return
	if slide_timer <= 0 or absi(vx) < to_sub(moves.crouch_speed):
		slide_cd = moves.slide_cooldown
		if stand_ok and not input.is_held(InputFrame.DOWN):
			height = moves.body_height
			state = State.GROUND
		else:
			state = State.CROUCH
			crouch_age = SLIDE_GRACE + 1


func _tick_air(input: InputFrame) -> void:
	var ax := input.axis_x()
	if ax != 0:
		facing = ax
	if arm_locked:
		_tick_air_one_arm(input, ax)
		return
	if input.was_pressed(InputFrame.DASH) and dash_left > 0:
		_start_dash(ax)
		return
	if air_ticks <= WALLRUN_WINDOW and _jump_fast and vy < 0 and _can_wall_run(ax):
		_start_wall_run()
		return
	# Subito dopo un salto a muro, spingere verso il muro non riporta indietro.
	var ctrl := 0 if wall_lock > 0 and ax == wall_dir else ax
	_run(ctrl, to_sub(moves.run_speed), to_sub(moves.air_accel), to_sub(moves.air_decel), to_sub(moves.air_accel))
	_stop_at_wall(ax)
	if buf_jump > 0:
		if wallrun_end_t > 0 and boosts_left > 0 and ax != -wall_dir:
			# Appena finita la corsa sul muro, SALTO è la Spinta: si sale ancora lungo il muro.
			_boost()
		elif ax != 0 and height == moves.body_height and _wall_contact(ax):
			# Spingendo contro un muro, SALTO è il salto a muro (non la Spinta).
			wall_dir = ax
			_wall_jump()
		elif wall_coyote_t > 0:
			_wall_jump()
		elif coyote > 0:
			_jump()
		elif boosts_left > 0:
			_boost()
	if coyote > 0:
		coyote -= 1
	_tick_air_motion(input)


## In aria col braccio bloccato: solo il salto semplice (anche col coyote time), niente acrobazie.
func _tick_air_one_arm(input: InputFrame, ax: int) -> void:
	_run(ax, to_sub(moves.run_speed), to_sub(moves.air_accel), to_sub(moves.air_decel), to_sub(moves.air_accel))
	_stop_at_wall(ax)
	if buf_jump > 0 and coyote > 0:
		_jump()
	else:
		_arm_click_check(input)
	if coyote > 0:
		coyote -= 1
	_tick_air_motion(input)


## SALTO in aria col braccio bloccato, quando non porta a niente: la Spinta non c'è (prima del
## riavvio) e il tasto non diventa un salto all'atterraggio, perché sotto i piedi non arriva un appoggio
## entro i tick del salto tenuto in serbo. Scrive solo l'evento "braccio_a_vuoto", per la scintilla
## spenta e il clic: lo stato non cambia.
func _arm_click_check(input: InputFrame) -> void:
	if not input.was_pressed(InputFrame.JUMP) or coyote > 0:
		return
	if vy >= 0:
		var n := moves.jump_buffer
		var reach := (vy * n + n * n * to_sub(moves.fall_gravity) / 2) / SUB
		var t := SolidGrid.TILE
		for r in range(py / t, (py + reach) / t + 1):
			for c in range(left() / t, (right() - 1) / t + 1):
				if grid.cell(c, r) != SolidGrid.Cell.EMPTY:
					return
	events.append("braccio_a_vuoto")


## Gravità, taglio del salto, spostamento e atterraggio.
func _tick_air_motion(input: InputFrame) -> void:
	var held := input.is_held(InputFrame.JUMP)
	if vy < 0 and not held and _can_cut:
		vy = roundi(vy * moves.jump_cut)
		_can_cut = false
	var g: int
	var band := to_sub(moves.apex_band)
	if held and absi(vy) < band:
		g = to_sub(moves.apex_gravity)
	elif vy < 0:
		g = to_sub(moves.gravity)
	else:
		g = to_sub(moves.fall_gravity)
	vy = mini(vy + g, to_sub(moves.max_fall))
	if glide_fall > 0.0 and held and vy >= 0:
		gliding = true
		vy = mini(vy, to_sub(glide_fall))
	var wall := _move_x(vx)
	var hit := _move_y(vy)
	if hit < 0:
		vy = 0
		_can_cut = false
	elif hit > 0:
		_land()
		return
	if vy >= 0 and ledge_cd == 0 and _try_grab(input.axis_x(), wall):
		return
	if vy > 0 and _enter_wall_slide(input.axis_x()):
		return


func _run(ax: int, top_speed: int, accel: int, decel: int, turn: int) -> void:
	var target := ax * top_speed * speed_pct / 100 * boost_pct / 100
	if ax != 0 and vx != 0 and signi(vx) != ax:
		vx = _approach(vx, target, turn)
	elif ax != 0:
		vx = _approach(vx, target, accel)
	else:
		vx = _approach(vx, 0, decel)


static func _approach(v: int, target: int, d: int) -> int:
	if v < target:
		return mini(v + d, target)
	return maxi(v - d, target)


func _jump() -> void:
	buf_jump = 0
	coyote = 0
	_jump_fast = momentum > 0
	vy = -to_sub(moves.jump_speed)
	_can_cut = true
	state = State.AIR
	_takeoff()
	events.append("jump")


func _boost() -> void:
	buf_jump = 0
	boosts_left -= 1
	vy = -to_sub(moves.boost_speed)
	_can_cut = true
	_just_boosted = true
	events.append("spinta")
	if anim != null:
		anim.play(&"double_jump")


func _leave_ground(with_coyote: bool) -> void:
	state = State.AIR
	coyote = moves.coyote_ticks if with_coyote else 0
	vy = 0
	_can_cut = false
	_takeoff()


func _takeoff() -> void:
	air_ticks = 0
	_takeoff_y = py
	_peak_y = py


## Le Spinte a disposizione a ogni ricarica: nessuna col braccio bloccato.
func boosts_max() -> int:
	return 0 if arm_locked else moves.boosts


func _land() -> void:
	vy = 0
	ry = 0
	boosts_left = boosts_max()
	coyote = 0
	dash_left = 1
	wallrun_used = false
	wallrun_end_t = 0
	wall_lock = 0
	wall_coyote_t = 0
	last_peak = _takeoff_y - _peak_y
	state = State.CROUCH if height < moves.body_height else State.GROUND
	crouch_age = SLIDE_GRACE + 1
	events.append("land")
	if anim != null and state == State.GROUND:
		anim.play(&"land")


func _enter_crouch() -> void:
	height = moves.crouch_height
	state = State.CROUCH
	crouch_age = 0


func _start_slide() -> void:
	height = moves.crouch_height
	state = State.SLIDE
	slide_timer = moves.slide_ticks
	vx = facing * maxi(absi(vx), to_sub(moves.slide_speed))
	events.append("slide")


# ------------------------------------------------------------------ sporgenze

## In caduta, spingendo verso un muro: se lo spigolo del muro è all'altezza delle mani e sopra
## c'è posto, GIG si aggrappa.
func _try_grab(ax: int, wall: int) -> bool:
	if ax == 0 or height < moves.body_height:
		return false
	# Il muro deve essere attaccato al corpo dal lato in cui si spinge.
	if wall != ax and not grid.rect_hits_solid(left() + ax, top(), right() + ax, py):
		return false
	var col_px := right() if ax > 0 else left() - 1
	var col := floori(float(col_px) / SolidGrid.TILE)
	var row0 := floori(float(top()) / SolidGrid.TILE)
	var row1 := floori(float(top() + moves.ledge_reach) / SolidGrid.TILE)
	for row in range(row0, row1 + 1):
		var edge := row * SolidGrid.TILE
		if edge < top() or edge > top() + moves.ledge_reach:
			continue
		if grid.cell(col, row) != SolidGrid.Cell.SOLID or grid.cell(col, row - 1) == SolidGrid.Cell.SOLID:
			continue
		# Spazio per le mani sopra lo spigolo.
		if grid.rect_hits_solid(left(), edge - 5, right(), edge):
			continue
		facing = ax
		strain = 0
		ledge_x = col_px
		ledge_y = edge
		vx = 0
		vy = 0
		rx = 0
		ry = 0
		boosts_left = boosts_max()
		dash_left = 1
		last_peak = _takeoff_y - _peak_y
		buf_jump = 0
		var hang_py := edge + moves.body_height - 8
		if _fits(HANG_LEGS + 8, px, edge + HANG_LEGS):
			py = hang_py
			state = State.LEDGE_HANG
			events.append("grab")
			return true
		# Spigolo basso, e sotto non c'è posto per le gambe (i piedi finirebbero nel pavimento):
		# GIG scavalca subito, senza fermarsi.
		if _pick_climb():
			_start_climb(false)
			return true
		return false
	return false


## Il bordo del muro della sporgenza, fra il pixel vuoto e il primo pieno.
func _face_x() -> int:
	return ledge_x if facing > 0 else ledge_x + 1


## Dove finisce GIG salendo sulla sporgenza: piedi sullo spigolo, climb_dx px dentro.
func _climb_target() -> Vector2i:
	return Vector2i(_face_x() + facing * climb_dx, ledge_y)


## Sceglie climb_dx: il più avanti possibile, fino a dove porta la clip, purché ogni posizione
## fino a lì sia libera e abbia il pavimento sotto. False se in cima non c'è posto.
func _pick_climb() -> bool:
	var found := false
	for d: int in CLIMB_REACH:
		var x := _face_x() + facing * d
		var l := x - moves.body_width / 2
		var room := _fits(moves.body_height, x, ledge_y) or _fits(moves.crouch_height, x, ledge_y)
		if not room or not grid.floor_at(l, l + moves.body_width, ledge_y, true):
			break
		climb_dx = d
		found = true
	return found


func _start_climb(from_hang: bool) -> void:
	state = State.LEDGE_CLIMB
	buf_jump = 0
	events.append("climb")
	var skip := 0
	if anim != null:
		anim.play(&"ledge_climb")
		if anim.clip.frames.size() > CLIMB_FIRST:
			for i in CLIMB_FIRST:
				skip += anim.clip.frames[i].ticks
			# L'ultimo fotogramma è già un passo di corsa, lanciato in avanti: non si mostra.
			skip += anim.clip.frames[-1].ticks
			anim.show_frame(&"ledge_climb", CLIMB_FIRST)
	# Meno uno: l'animazione avanza già nel tick in cui la salita parte.
	climb_total = maxi(_climb_ticks() - skip - 1, 1)
	climb_timer = climb_total
	# Lo sprite parte un po' più in basso, vicino a dov'è il corpo, e in CLIMB_EASE tick raggiunge
	# l'altezza della clip.
	climb_yoff = HANG_DROP if from_hang else clampi(py - ledge_y - CLIMB_RISE, 0, HANG_DROP + 6)


func _tick_hang(input: InputFrame) -> void:
	var ax := input.axis_x()
	if input.was_pressed(InputFrame.DOWN):
		ledge_cd = moves.ledge_regrab
		_leave_ground(false)
		return
	if buf_jump > 0 and ax == -facing:
		# Salto all'indietro, via dal muro.
		ledge_cd = moves.ledge_regrab
		facing = ax
		_jump()
		vx = ax * to_sub(moves.run_speed)
		return
	if arm_locked:
		_tick_hang_one_arm(input)
		return
	if input.was_pressed(InputFrame.UP) or buf_jump > 0 or _hang_push(input):
		if _pick_climb():
			_start_climb(true)


## Appeso con una mano sola: la salita parte dopo ONE_HAND_STRAIN tick di sforzo, tenendo SU,
## SALTO o la direzione del muro; lasciando, lo sforzo riparte da capo.
func _tick_hang_one_arm(input: InputFrame) -> void:
	var toward := InputFrame.RIGHT if facing > 0 else InputFrame.LEFT
	var pushing := input.is_held(InputFrame.UP) or input.is_held(InputFrame.JUMP) or input.is_held(toward)
	if strain == 0 and not (input.was_pressed(InputFrame.UP) or buf_jump > 0 or _hang_push(input)):
		return
	if not pushing and strain > 0:
		strain = 0
		return
	buf_jump = 0
	strain += 1
	if strain == 1:
		events.append("strain")
	if strain >= ONE_HAND_STRAIN:
		strain = 0
		if _pick_climb():
			_start_climb(true)


## Spingere verso il muro da appeso fa salire solo se la direzione è appena stata premuta:
## tenerla mentre ci si aggrappa non deve far salire subito.
func _hang_push(input: InputFrame) -> bool:
	return input.was_pressed(InputFrame.RIGHT if facing > 0 else InputFrame.LEFT)


func _climb_ticks() -> int:
	if anim != null and anim.sheet != null and anim.sheet.has_anim(&"ledge_climb"):
		return maxi(anim.sheet.clip(&"ledge_climb").total_ticks(), 1)
	return 24


func _tick_climb() -> void:
	climb_timer -= 1
	if climb_timer > 0:
		return
	var t := _climb_target()
	px = t.x
	py = t.y
	rx = 0
	ry = 0
	vx = 0
	vy = 0
	if _fits(moves.body_height):
		height = moves.body_height
		state = State.GROUND
	else:
		height = moves.crouch_height
		state = State.CROUCH


# ------------------------------------------------------------------ muri e scatto

## Il muro tocca il busto dal lato dir: lì il braccio si può piantare.
func _wall_contact(dir: int) -> bool:
	return grid.rect_hits_solid(left() + dir, top() + 5, right() + dir, top() + 50)


## In caduta, spingendo contro un muro: GIG pianta il braccio e frena.
func _enter_wall_slide(ax: int) -> bool:
	if arm_locked or ax == 0 or height < moves.body_height or wallrun_end_t > 0:
		return false
	# Il muro deve arrivare all'altezza della testa: se lo spigolo è già più in basso, GIG cade
	# ancora un po' e si aggrappa con le mani invece di frenare.
	if not grid.rect_hits_solid(left() + ax, top() + 5, right() + ax, top() + 20):
		return false
	state = State.WALL_SLIDE
	wall_dir = ax
	facing = ax
	wall_stick_t = moves.wall_stick
	vx = 0
	rx = 0
	boosts_left = boosts_max()
	dash_left = 1
	events.append("wall")
	return true


func _tick_wall_slide(input: InputFrame) -> void:
	var ax := input.axis_x()
	if buf_jump > 0:
		_wall_jump()
		_tick_air_motion(input)
		return
	if input.was_pressed(InputFrame.DASH) and dash_left > 0:
		_start_dash(-wall_dir)
		return
	# Spingendo via dal muro, il braccio tiene ancora per qualche tick.
	if ax == wall_dir:
		wall_stick_t = moves.wall_stick
	else:
		wall_stick_t -= 1
		if wall_stick_t <= 0:
			_leave_wall()
			return
	var limit := to_sub(moves.wall_slide_speed)
	if vy > limit:
		vy = maxi(vy - to_sub(moves.wall_slide_brake), limit)
	else:
		vy = mini(vy + to_sub(moves.fall_gravity), limit)
	if _move_y(vy) > 0:
		_land()
		return
	# Scivolando giù, le mani passano davanti allo spigolo del muro: GIG si aggrappa.
	if ledge_cd == 0 and _try_grab(wall_dir, wall_dir):
		return
	if not _wall_contact(wall_dir):
		_leave_wall()
		return
	if tick % WALL_SPARK_EVERY == 0:
		events.append("wall_spark")


func _leave_wall() -> void:
	state = State.AIR
	wall_coyote_t = moves.wall_coyote
	coyote = 0
	_can_cut = false
	_takeoff()


## Il salto a muro: in alto e via dal muro, con il colpo del braccio.
func _wall_jump() -> void:
	buf_jump = 0
	coyote = 0
	wall_coyote_t = 0
	facing = -wall_dir
	vy = -to_sub(moves.wall_jump_speed)
	vx = -wall_dir * to_sub(moves.wall_jump_push)
	rx = 0
	_can_cut = true
	_jump_fast = false
	wall_lock = moves.wall_jump_lock
	state = State.AIR
	_takeoff()
	events.append("walljump")


func _can_wall_run(ax: int) -> bool:
	return ax != 0 and ax == facing and not wallrun_used and momentum > 0 \
		and height == moves.body_height and _wall_contact(ax)


## La corsa sul muro: qualche passo in verticale, con lo slancio della corsa.
func _start_wall_run() -> void:
	if state == State.GROUND:
		_takeoff()
	state = State.WALL_RUN
	wall_dir = facing
	wallrun_used = true
	buf_jump = 0
	coyote = 0
	_can_cut = false
	vx = 0
	rx = 0
	# La velocità che con wallrun_decel porta i piedi a wallrun_height sopra la partenza: v² = 2 a d.
	var rest := maxi(py - (_takeoff_y - moves.wallrun_height), 0) * SUB
	vy = -roundi(sqrt(2.0 * to_sub(moves.wallrun_decel) * rest))
	events.append("wallrun")


func _tick_wall_run(input: InputFrame) -> void:
	if buf_jump > 0:
		# SALTO con la direzione opposta stacca dal muro; altrimenti è la Spinta, lungo il muro.
		if input.axis_x() == -wall_dir or boosts_left == 0:
			_wall_jump()
		else:
			state = State.AIR
			_boost()
		_tick_air_motion(input)
		return
	vy += to_sub(moves.wallrun_decel)
	if _move_y(vy) < 0:
		vy = 0
	# Le mani passano davanti a uno spigolo: GIG si aggrappa anche salendo.
	if ledge_cd == 0 and _try_grab(wall_dir, wall_dir if _wall_contact(wall_dir) else 0):
		return
	if not _wall_contact(wall_dir):
		# Il muro è finito sotto le mani senza uno spigolo da prendere: si prosegue in aria.
		state = State.AIR
		return
	if vy >= 0:
		state = State.AIR
		wallrun_end_t = WALLRUN_GRACE
		wall_coyote_t = moves.wall_coyote


## Lo scatto: orizzontale, sospeso, uno per salto.
func _start_dash(dir: int) -> void:
	if dir != 0:
		facing = dir
	state = State.DASH
	dash_left -= 1
	dash_timer = moves.dash_ticks
	vx = facing * to_sub(moves.dash_speed)
	vy = 0
	ry = 0
	buf_jump = 0
	_can_cut = false
	events.append("scatto")


func _tick_dash(input: InputFrame) -> void:
	dash_timer -= 1
	# Di spalla: quello che lo scatto incontra in questo tick, se è Rompibile, si rompe e GIG passa.
	_shoulder()
	var wall := _move_x(vx)
	if wall != 0:
		state = State.AIR
		vx = 0
		if ledge_cd == 0 and _try_grab(facing, wall):
			return
		_enter_wall_slide(input.axis_x())
		return
	if dash_timer <= 0:
		state = State.AIR
		vx = facing * to_sub(moves.dash_exit_speed)
		vy = 0


# ------------------------------------------------------------------ animazione e stato

## Dove va l'ancora del fotogramma corrente, in pixel del mondo (lo sprite è specchiato con
## facing). Di solito è il punto fra i piedi; appeso, le mani restano sullo spigolo; in salita è
## il punto a terra della clip, fermo sotto lo spigolo, che a fine salita coincide con l'arrivo.
func sprite_anchor() -> Vector2i:
	match state:
		State.LEDGE_HANG:
			var g := Vector2i(4, -125)
			if anim != null and anim.frame().points.has("grip"):
				g = anim.frame().points["grip"]
			return Vector2i(_face_x() + facing * (1 - g.x), ledge_y - 1 - g.y)
		State.LEDGE_CLIMB:
			var t := climb_total - climb_timer
			var x0 := -CLIMB_FACE
			var x1 := climb_dx - CLIMB_FWD
			var ox := x0 + (x1 - x0) * t / climb_total
			var ay := ledge_y + CLIMB_RISE + climb_yoff * maxi(CLIMB_EASE - t, 0) / CLIMB_EASE
			# Un piede già sopra il muro non va sotto la superficie (l'ultimo passo della clip scende
			# di qualche pixel): lo sprite si alza di quanto serve.
			if anim != null:
				var pts: Dictionary = anim.frame().points
				var lift := 0
				for k: String in ["foot_l", "foot_r"]:
					if pts.has(k) and pts[k].x + ox > 2:
						lift = maxi(lift, ay + pts[k].y - ledge_y)
				ay -= lift
			return Vector2i(_face_x() + facing * ox, ay)
	return Vector2i(px, py)



func _update_anim() -> void:
	if anim == null:
		return
	_pick_sheet()
	if pose_override != &"" and anim.sheet.has_anim(pose_override):
		anim.ensure(pose_override)
		anim.advance()
		return
	if (jab_t > 0 or hurt_t > 0) and _combat_anim():
		return
	match state:
		State.GROUND:
			if anim.name == &"land" and not anim.finished and vx == 0:
				pass
			elif absi(vx) > SUB / 4:
				anim.ensure(&"run")
			else:
				anim.ensure(&"idle")
		State.AIR:
			if anim.name == &"double_jump" and not anim.finished:
				pass
			elif wallrun_end_t > 0 and anim.sheet.has_anim(&"wall_run_end"):
				anim.ensure(&"wall_run_end")
			elif anim.sheet.has_anim(&"jump_arc"):
				# Otto pose lungo l'arco, scelte dalla velocità verticale: nei salti lunghi
				# il corpo passa per tutte, senza scatti fra salita e discesa.
				anim.show_frame(&"jump_arc", _arc_frame())
				return
			elif vy < 0:
				anim.ensure(&"jump_rise")
			else:
				anim.ensure(&"jump_fall")
		State.CROUCH:
			if absi(vx) > SUB / 8 and anim.sheet.has_anim(&"crouch_walk"):
				anim.ensure(&"crouch_walk")
			else:
				anim.ensure(&"crouch")
		State.SLIDE:
			anim.ensure(&"slide")
		State.LEDGE_HANG:
			anim.ensure(&"ledge_hang")
		State.LEDGE_CLIMB:
			anim.ensure(&"ledge_climb")
		State.WALL_SLIDE:
			_ensure_any([&"wall_slide", &"jump_fall"])
		State.WALL_RUN:
			_ensure_any([&"wall_run", &"run"])
		State.DASH:
			_ensure_any([&"air_dash", &"jump_rise"])
	if not (_just_boosted and anim.elapsed == 0):
		anim.advance()


## Col braccio bloccato il foglio del braccio morto, se c'è; si cambia tenendo l'animazione in corso.
func _pick_sheet() -> void:
	var want := sheet_locked if arm_locked and sheet_locked != null else sheet_free
	if want == null or anim.sheet == want:
		return
	anim.sheet = want
	if anim.name != &"" and want.has_anim(anim.name):
		var i := anim.index
		anim.clip = want.clip(anim.name)
		anim.index = mini(i, anim.clip.frames.size() - 1)
	else:
		anim.play(&"idle")


## Il fotogramma di jump_arc per la velocità verticale di adesso: le soglie sono in px/tick
## (in salita negative), dalla spinta delle gambe alla caduta.
const ARC_VY: Array[float] = [-5.6, -3.75, -2.0, -0.6, 0.6, 2.25, 4.4]


func _arc_frame() -> int:
	var i := 0
	for t: float in ARC_VY:
		if vy > to_sub(t):
			i += 1
	return i


## La prima animazione che lo sprite ha: le pose nuove arrivano dopo la fisica.
func _ensure_any(names: Array[StringName]) -> void:
	for n in names:
		if anim.sheet.has_anim(n):
			anim.ensure(n)
			return


func state_name() -> String:
	return STATE_NAMES[state]


# ------------------------------------------------------------------ il colpo solo e i colpi presi

## Quanto dura il colpo e quando colpisce: dal 3° al 7° tick, poi GIG ritira il braccio.
const JAB_TICKS := 14
const JAB_ACTIVE := Vector2i(3, 7)
## Fin dove arriva il colpo oltre il corpo, e la fascia d'altezza (dai piedi in su): arriva fino a terra,
## così rompe anche la Colomba posata e il Segugio.
const JAB_REACH := 32
const JAB_BAND := Vector2i(0, 90)
## La spinta indietro: quanto dura, il salto in su che la accompagna, l'invulnerabilità dopo.
const HURT_TICKS := 16
const HURT_HOP := 2.5
const INV_TICKS := 60
## Il rimbalzo sopra un drone rotto: come una Spinta corta.
const BOUNCE_K := 0.8


## Il rettangolo del colpo, solo nei tick in cui colpisce (altrimenti vuoto).
func jab_box() -> Rect2i:
	var age := JAB_TICKS - jab_t
	if jab_t <= 0 or jab_hit or age < JAB_ACTIVE.x or age > JAB_ACTIVE.y:
		return Rect2i()
	var x0 := right() if facing > 0 else left() - JAB_REACH
	return Rect2i(x0, py - JAB_BAND.y, JAB_REACH, JAB_BAND.y - JAB_BAND.x)


## Il corpo, per i contatti.
func body() -> Rect2i:
	return Rect2i(left(), top(), moves.body_width, height)


## Un colpo preso da `dir` (-1 da destra, 1 da sinistra): GIG vola indietro di `dist` px con un
## piccolo salto, poi resta intoccabile per un secondo.
func knock(dir: int, dist: int) -> void:
	hurt_t = HURT_TICKS
	inv_t = INV_TICKS + HURT_TICKS
	knock_vx = dir * dist * SUB / HURT_TICKS
	jab_t = 0
	if state in [State.LEDGE_HANG, State.LEDGE_CLIMB, State.WALL_SLIDE, State.WALL_RUN, State.DASH, State.SLIDE, State.CROUCH]:
		height = moves.body_height if _fits(moves.body_height) else height
	state = State.AIR
	coyote = 0
	vy = -to_sub(HURT_HOP)
	vx = 0
	_can_cut = false
	events.append("colpito")
	if anim != null and anim.sheet.has_anim(&"hurt_high"):
		anim.play(&"hurt_high")


## Il rimbalzo dopo un salto in testa a un drone.
func bounce() -> void:
	state = State.AIR
	coyote = 0
	vy = -to_sub(moves.boost_speed * BOUNCE_K)
	_can_cut = true
	events.append("rimbalzo")


## Il sigillo della Vedetta: GIG resta incollato per `presses` pressioni di tasti.
func stick(presses: int) -> void:
	stuck_left = presses
	jab_t = 0
	vx = 0
	events.append("sigillo")


## La parte del tick che riguarda colpi e sigillo: restituisce l'ingresso che la fisica deve vedere.
func _combat_input(input: InputFrame) -> InputFrame:
	inv_t = maxi(inv_t - 1, 0)
	if jab_t > 0:
		jab_t -= 1
		if jab_t == 0:
			jab_hit = false
	if stuck_left > 0:
		if input.pressed != 0:
			stuck_left -= 1
			events.append("strappo" if stuck_left > 0 else "staccato")
		return InputFrame.new()
	if hurt_t > 0:
		hurt_t -= 1
		_move_x(knock_vx)
		return InputFrame.new()
	if can_jab and not jab_block and jab_t == 0 and input.was_pressed(InputFrame.ATTACK) and state in [State.GROUND, State.AIR, State.CROUCH]:
		jab_t = JAB_TICKS
		jab_hit = false
		events.append("jab")
	return input


## La posa del colpo: jab a terra (col braccio bloccato quello della destra), calcio in aria.
func _combat_anim() -> bool:
	if hurt_t > 0 and anim.sheet.has_anim(&"hurt_high"):
		anim.ensure(&"hurt_high")
		anim.advance()
		return true
	if jab_t <= 0:
		return false
	var want: StringName = &"air_kick" if state == State.AIR else &"jab1"
	if not anim.sheet.has_anim(want):
		want = &"jab2"
	if not anim.sheet.has_anim(want):
		return false
	if anim.name != want or jab_t == JAB_TICKS:
		anim.play(want)
	anim.advance()
	return true


## Impronta dello stato per i test e i replay.
func state_hash() -> int:
	var h := [px, py, rx, ry, vx, vy, facing, state, height, boosts_left, coyote, buf_jump,
		drop_timer, slide_timer, slide_cd, ledge_cd, climb_timer, climb_total, climb_dx, climb_yoff, crouch_age,
		ledge_x, ledge_y, tick, wall_dir, wall_stick_t, wall_coyote_t, wall_lock, dash_left, dash_timer,
		wallrun_used, wallrun_end_t, momentum, _jump_fast]
	# Solo col braccio bloccato, così le impronte dei replay di prima non cambiano.
	if arm_locked:
		h.append_array([arm_locked, strain])
	# Lo stesso per la planata e la corsa rallentata, che ci sono solo coi power-up e le zone.
	if glide_fall > 0.0 or gliding or speed_pct != 100:
		h.append_array([glide_fall, gliding, speed_pct])
	if boost_pct != 100:
		h.append(boost_pct)
	# E per i colpi, che ci sono solo coi droni.
	if can_jab or jab_t > 0 or hurt_t > 0 or inv_t > 0 or stuck_left > 0:
		h.append_array([jab_t, jab_hit, hurt_t, knock_vx, inv_t, stuck_left])
	return hash(h)
