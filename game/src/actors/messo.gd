class_name Messo
extends Thug
## Il messo di SIDERA (decisione 63): il regista degli Esattori. Non picchia e non chiede mai il turno
## d'attacco: sta in fondo all'arena e dirige i rider. Le scelte di Luigi del 6 novembre 2026, una
## domanda alla volta:
## - «Regista da fermare»: si allontana se GIG si avvicina e, finché è in piedi, chiama un rider ogni
##   CALL_EVERY tick (circa 8 secondi), al massimo MAX_RIDERS rider in campo insieme;
## - «Rider all'attacco»: ogni tanto si mette nella corsia di GIG e mira col laser lungo la corsia per
##   AIM_TICKS tick (la linea rossa sottile), poi spara. Se GIG è ancora nella corsia gli resta il segno
##   sul braccio (Gig.mark) e i rider attaccano tutti insieme. Si evita uscendo dalla corsia, come la
##   carica dell'esattore; un colpo al messo mentre mira lo interrompe;
## - «Una combo e giù»: pochi punti vita (messo.tres). KO, le chiamate finiscono e i rider già arrivati
##   restano da battere. Superata l'8 novembre 2026 (Luigi: «almeno 2 combo per morire e un minimo di
##   autodifesa»): la vita basta per due combo, e dopo DEFEND_HITS colpi di fila, appena è di nuovo in
##   piedi, il messo si difende con la scossa del tablet (messo_impulso.tres): lo alza e si carica per
##   un quarto di secondo, con l'anello rosso che cresce intorno ai piedi e i colpi parati; poi la
##   scossa butta giù GIG, se è vicino. Si evita con un passo indietro. Dopo la scossa chiama un rider;
##   la prima chiamata arriva presto (Luigi: «non chiama altri riders... o lo fa dopo troppo tempo»);
## - «Si può fermare»: è raggiungibile come gli altri. Contro il bordo dell'arena non ha più dove
##   scappare: il prologo insegna che è il primo da fermare.
##
## Lo sprite viene dalla pipeline 3D: legge dal tablet ("read"), punta la penna laser ("laser"), chiama
## i rinforzi col braccio alzato ("call").

enum Act { NONE, ALIGN, AIM, CALL }

## Più vicino di così GIG lo fa scappare; scappando cerca questa distanza.
const KEEP_AWAY := 130.0
const FLEE_TO := 175.0
## Il richiamo dei rinforzi: la prima chiamata (dall'inizio dello scontro), ogni quanto le altre, quanto
## dura il braccio alzato, a che tick entra il rider.
const FIRST_CALL := 90
const CALL_EVERY := 300
const CALL_TICKS := 44
const CALL_AT := 22
const MAX_RIDERS := 3
## Il laser: ogni quanto prova a mirare (minimo e massimo), quanto cerca la corsia di GIG prima di
## rinunciare, quanto mira, quanto è larga la corsia, quanto resta disegnato il colpo.
const AIM_EVERY := Vector2i(420, 600)
const ALIGN_MAX := 90
const AIM_TICKS := 60
const LASER_LANE := 8.0
const SHOT_TICKS := 10
## Il laser non parte da più lontano di così, né da più vicino.
const AIM_RANGE := Vector2(60.0, 300.0)
## L'autodifesa: i colpi di fila che la fanno scattare, i tick da libero senza colpi che azzerano il
## conto, e la distanza (x, profondità) entro cui GIG deve essere perché il messo la tenti.
const DEFEND_HITS := 3
const STREAK_RESET := 60
const PULSE_TRIGGER := Vector2(95.0, 30.0)
const PULSE_ATTACK := "res://data/attacks/messo_impulso.tres"
## Raggio dell'anello sul pavimento (come la hitbox della scossa) e quanto dura l'onda (solo disegno).
const PULSE_RADIUS := 56.0
const PULSE_WAVE := 14

var act: Act = Act.NONE
var act_t: int = 0
var _call_timer: int = FIRST_CALL
var _aim_timer: int = 0
## Il colpo appena sparato (solo disegno): tick rimasti, se ha preso GIG e dove.
var shot_t: int = 0
var shot_hit: bool = false
var shot_to: Vector2 = Vector2.ZERO
var _fx_node: Node2D
## Gli aloni del laser (solo disegno).
var _glow: Glow
## Colpi presi di fila, e tick passati da libero dopo l'ultimo.
var hit_streak: int = 0
var _streak_t: int = 0
var pulse_attack: AttackData
## L'onda della scossa appena partita (solo disegno): tick rimasti.
var wave_t: int = 0


func setup_thug(type_id: StringName, lvl: Level, id: int, rng_seed: int) -> void:
	super.setup_thug(type_id, lvl, id, rng_seed)
	_aim_timer = rng.randi_range(AIM_EVERY.x, AIM_EVERY.y) / 2
	pulse_attack = load(PULSE_ATTACK) as AttackData
	_fx_node = Node2D.new()
	_fx_node.name = "Laser"
	_fx_node.z_as_relative = false
	_fx_node.z_index = 2500
	_fx_node.draw.connect(_draw_laser)
	add_child(_fx_node)
	_glow = Glow.new(_fx_node)


func _think() -> void:
	if shot_t > 0:
		shot_t -= 1
	if wave_t > 0:
		wave_t -= 1
	if state == State.ENTER:
		_think_enter()
		return
	if not is_free():
		_stop_act()
		return
	if hit_streak > 0:
		_streak_t += 1
		if _streak_t > STREAK_RESET:
			hit_streak = 0
	var p := level.player
	if not ai_enabled or p == null or not p.is_alive() or p.state == State.DEAD:
		_stop_act()
		_walk_towards(px, py, 0.0)
		return
	if hit_streak >= DEFEND_HITS:
		hit_streak = 0
		if absf(p.px - px) <= PULSE_TRIGGER.x and absf(p.py - py) <= PULSE_TRIGGER.y:
			_start_pulse(p)
			return
	if grace > 0:
		grace -= 1
		facing = 1 if p.px >= px else -1
		_stand(&"read")
		return
	if _call_timer > 0:
		_call_timer -= 1
	if _aim_timer > 0:
		_aim_timer -= 1
	match act:
		Act.ALIGN:
			_think_align(p)
		Act.AIM:
			_think_aim(p)
		Act.CALL:
			_think_call()
		_:
			_think_idle(p)


## Niente da fare: chiama i rinforzi, mira, oppure legge il tablet tenendosi lontano da GIG.
func _think_idle(p: Fighter) -> void:
	var dist := absf(p.px - px)
	var close := dist < KEEP_AWAY
	# I rinforzi li chiama anche con GIG addosso: è il suo modo di difendersi (resta fermo e colpibile).
	if _call_timer <= 0 and riders_alive() < MAX_RIDERS:
		_start_act(Act.CALL)
		set_state(State.IDLE, &"call")
		return
	if not close and _aim_timer <= 0 and (p as Gig).marked == 0 and dist >= AIM_RANGE.x and dist <= AIM_RANGE.y:
		_start_act(Act.ALIGN)
		_think_align(p)
		return
	facing = 1 if p.px >= px else -1
	if close:
		_flee(p)
		return
	_walk_towards(px, py, 0.0)
	_stand(&"read")


## Si allontana da GIG lungo la x, dentro i muri, e intanto torna verso il fondo della fascia.
func _flee(p: Fighter) -> void:
	var away := 1 if px >= p.px else -1
	var margin := Level.WALL_MARGIN + 7.5
	var lo := level.view_left() + margin
	var hi := level.view_right() - margin
	var tx := clampf(p.px + away * FLEE_TO, lo, hi)
	var ty := clampf(py, level.band_top, level.band_top + 24.0)
	_walk_towards(tx, ty, 2.5)
	# Cammina nella direzione in cui va; fermo (contro il bordo) guarda GIG.
	if vx != 0.0:
		facing = 1 if vx > 0.0 else -1


## Si mette nella corsia di GIG, restando alla sua distanza.
func _think_align(p: Fighter) -> void:
	act_t += 1
	if absf(p.px - px) < KEEP_AWAY * 0.6 or act_t > ALIGN_MAX:
		_stop_act()
		_aim_timer = rng.randi_range(AIM_EVERY.x, AIM_EVERY.y) / 3
		return
	facing = 1 if p.px >= px else -1
	if absf(p.py - py) <= 1.5:
		_start_act(Act.AIM)
		set_state(State.IDLE, &"laser")
		if level.sound_enabled:
			Sfx.play_at(&"glint", px, 0.0, -6.0)
		return
	_walk_towards(px, p.py, 1.0)
	facing = 1 if p.px >= px else -1


## Mira lungo la sua corsia, fermo; alla fine spara.
func _think_aim(p: Fighter) -> void:
	act_t += 1
	vx = 0.0
	vy = 0.0
	if act_t < AIM_TICKS:
		return
	_fire(p as Gig)
	_stop_act()
	_aim_timer = rng.randi_range(AIM_EVERY.x, AIM_EVERY.y)
	set_state(State.IDLE, &"read")


## Il colpo: prende GIG se è nella corsia, davanti alla penna, e colpibile.
func _fire(g: Gig) -> void:
	var front := (g.px - px) * facing > 0.0
	var in_lane := absf(g.py - py) <= LASER_LANE
	shot_hit = front and in_lane and g.invuln == 0 and not g.is_down() and g.state != State.DEAD
	shot_t = SHOT_TICKS
	if shot_hit:
		g.mark()
		shot_to = g.arm_point()
		Game.count(&"segni_laser")
		if level.sound_enabled:
			Sfx.play_at(&"zap", g.px, 0.0, -4.0)
	else:
		shot_to = Vector2(_lane_end(), roundf(py) + pen_tip_local().y)
		Game.count(&"laser_evitati")


## Il richiamo: il braccio alzato e, a metà, un rider che arriva di corsa dal viale (da sinistra).
func _think_call() -> void:
	act_t += 1
	vx = 0.0
	vy = 0.0
	if act_t == CALL_AT and riders_alive() < MAX_RIDERS:
		var y := rng.randf_range(level.band_top + 8.0, level.band_bottom - 8.0)
		level.spawn_thug(&"rider", -1, y, wave_id)
		Game.count(&"rinforzi")
	if act_t >= CALL_TICKS:
		_stop_act()
		_call_timer = CALL_EVERY
		set_state(State.IDLE, &"read")


## I rider in campo, vivi.
func riders_alive() -> int:
	var n := 0
	for f in level.fighters:
		if f is Rider and not f.dead and not f.removed:
			n += 1
	return n


# --- L'autodifesa -----------------------------------------------------------------------------

## La scossa del tablet: girato verso GIG, la carica (colpi parati) e poi l'onda tutt'intorno.
func _start_pulse(p: Fighter) -> void:
	_stop_act()
	facing = 1 if p.px >= px else -1
	start_attack(pulse_attack, level.next_attack_serial())
	Game.count(&"scosse_messo")


func is_pulsing() -> bool:
	return state == State.ATTACK and attack == pulse_attack


## Durante la carica della scossa il messo para tutto, da tutte e due le parti.
func try_block(_attacker: Entity, _atk: AttackData) -> bool:
	if not is_pulsing() or attack_tick >= attack.startup or dead:
		return false
	hitstop = 4
	_shake_ticks = 4
	flash = FLASH_TICKS
	return true


func _on_hit_taken(attacker: Entity, atk: AttackData) -> void:
	super._on_hit_taken(attacker, atk)
	if attacker is Gig:
		hit_streak += 1
		_streak_t = 0


func _end_attack() -> void:
	var was_pulse := attack == pulse_attack
	super._end_attack()
	if was_pulse:
		# Dopo la scossa i rinforzi, subito.
		_call_timer = 0


func _anim_output() -> void:
	super._anim_output()
	if is_pulsing() and attack_tick == attack.startup:
		wave_t = PULSE_WAVE


func _start_act(a: Act) -> void:
	act = a
	act_t = 0


## L'azione in corso finisce (anche perché lo colpiscono): il laser e il richiamo si interrompono.
func _stop_act() -> void:
	if act == Act.AIM or act == Act.ALIGN:
		_aim_timer = maxi(_aim_timer, AIM_EVERY.x / 2)
	if act == Act.CALL:
		_call_timer = maxi(_call_timer, CALL_EVERY / 4)
	act = Act.NONE
	act_t = 0


func _stand(anim_name: StringName) -> void:
	if state == State.IDLE and anim.name != anim_name:
		play_anim(anim_name)


# --- Disegno --------------------------------------------------------------------------------

## La punta della penna laser, rispetto ai piedi: davanti alla mano destra (come nelle scene).
func pen_tip_local() -> Vector2:
	var f := anim.frame()
	var fist: Vector2 = Vector2(f.points["fist_r"]) if f.points.has("fist_r") else Vector2(17, -69)
	return Vector2(fist.x * facing + 5 * facing, fist.y - 1)


## Dove finisce la linea del laser: il bordo dello schermo davanti al messo (nel mondo dell'arena).
func _lane_end() -> float:
	return level.view_right() + 8.0 if facing > 0 else level.view_left() - 8.0


func sync_visual() -> void:
	super.sync_visual()
	if _fx_node != null:
		_fx_node.queue_redraw()


## Il disegno è nel nodo del messo, che sta nei suoi piedi (position = px, py arrotondati).
func _draw_laser() -> void:
	_glow.clear()
	if not visible:
		return
	var feet := Vector2(roundf(px), roundf(py))
	var a := pen_tip_local() + Vector2(0, -roundf(ph))
	if is_pulsing() and attack_tick < attack.startup:
		_draw_pulse_charge(float(attack_tick) / attack.startup)
	if wave_t > 0:
		_draw_pulse_wave(1.0 - float(wave_t) / PULSE_WAVE)
	if act == Act.AIM:
		var b := Vector2(_lane_end() - feet.x, a.y)
		ArmMark.draw_beam(_fx_node, a, b, level.tick, float(act_t) / AIM_TICKS, _glow)
	elif shot_t > 0:
		var to := shot_to - feet
		ArmMark.draw_shot(_fx_node, a, to, float(shot_t) / SHOT_TICKS, _glow)
		if shot_hit:
			ArmMark.draw_flash(_fx_node, to, shot_t, _glow)


## L'anello sul pavimento (un'ellisse schiacciata come la profondità dell'arena), coi pixel interi.
func _ellipse(r: float, c: Color, dotted: bool) -> void:
	var n := maxi(24, roundi(r * 1.6))
	var last := Vector2(INF, INF)
	for i in n:
		if dotted and i % 3 == 2:
			continue
		var ang := TAU * i / n
		var q := Vector2(roundf(cos(ang) * r), roundf(sin(ang) * r * 0.3))
		if q != last:
			_fx_node.draw_rect(Rect2(q, Vector2.ONE), c)
			last = q


## La carica: il tablet si accende e l'anello rosso cresce fino al raggio della scossa.
func _draw_pulse_charge(k: float) -> void:
	var c := Color(ArmMark.C_MARK, 0.55 + 0.45 * k)
	_ellipse(lerpf(12.0, PULSE_RADIUS, k), c, true)
	var hand := pen_tip_local() + Vector2(0, -roundf(ph))
	_fx_node.draw_rect(Rect2(hand.round() - Vector2(1, 1), Vector2(3, 3)), Color(ArmMark.C_CORE, 0.6 + 0.4 * k))
	_glow.halo(hand.round(), roundi(5.0 + 7.0 * k), Color(ArmMark.C_HOT_GLOW.lerp(ArmMark.C_MARK, k), 0.7))
	_glow.halo(Vector2(0, -2), roundi(PULSE_RADIUS * k * 0.5), Color(ArmMark.C_MARK, 0.25 * k))


## L'onda: l'anello bianco-rosso esce oltre il raggio e si spegne.
func _draw_pulse_wave(u: float) -> void:
	var c := Color(ArmMark.C_CORE.lerp(ArmMark.C_MARK, u), 1.0 - u)
	_ellipse(PULSE_RADIUS + 18.0 * u, c, false)
	_ellipse(PULSE_RADIUS * 0.7 + 14.0 * u, Color(ArmMark.C_MARK, 0.6 * (1.0 - u)), true)
	_glow.halo(Vector2(0, -40), roundi(14.0 + 20.0 * u), Color(ArmMark.C_MARK, 0.5 * (1.0 - u)))
