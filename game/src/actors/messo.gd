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
##   restano da battere;
## - «Si può fermare»: è raggiungibile come gli altri. Contro il bordo dell'arena non ha più dove
##   scappare: il prologo insegna che è il primo da fermare.
##
## Lo sprite viene dalla pipeline 3D: legge dal tablet ("read"), punta la penna laser ("laser"), chiama
## i rinforzi col braccio alzato ("call").

enum Act { NONE, ALIGN, AIM, CALL }

## Più vicino di così GIG lo fa scappare; scappando cerca questa distanza.
const KEEP_AWAY := 130.0
const FLEE_TO := 175.0
## Il richiamo dei rinforzi: ogni quanto, quanto dura il braccio alzato, a che tick entra il rider.
const CALL_EVERY := 480
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

var act: Act = Act.NONE
var act_t: int = 0
var _call_timer: int = CALL_EVERY
var _aim_timer: int = 0
## Il colpo appena sparato (solo disegno): tick rimasti, se ha preso GIG e dove.
var shot_t: int = 0
var shot_hit: bool = false
var shot_to: Vector2 = Vector2.ZERO
var _fx_node: Node2D


func setup_thug(type_id: StringName, lvl: Level, id: int, rng_seed: int) -> void:
	super.setup_thug(type_id, lvl, id, rng_seed)
	_aim_timer = rng.randi_range(AIM_EVERY.x, AIM_EVERY.y) / 2
	_fx_node = Node2D.new()
	_fx_node.name = "Laser"
	_fx_node.z_as_relative = false
	_fx_node.z_index = 2500
	_fx_node.draw.connect(_draw_laser)
	add_child(_fx_node)


func _think() -> void:
	if shot_t > 0:
		shot_t -= 1
	if state == State.ENTER:
		_think_enter()
		return
	if not is_free():
		_stop_act()
		return
	var p := level.player
	if not ai_enabled or p == null or not p.is_alive() or p.state == State.DEAD:
		_stop_act()
		_walk_towards(px, py, 0.0)
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
	if not close and _call_timer <= 0 and riders_alive() < MAX_RIDERS:
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
	if not visible:
		return
	var feet := Vector2(roundf(px), roundf(py))
	var a := pen_tip_local() + Vector2(0, -roundf(ph))
	if act == Act.AIM:
		var b := Vector2(_lane_end() - feet.x, a.y)
		ArmMark.draw_beam(_fx_node, a, b, level.tick, float(act_t) / AIM_TICKS)
	elif shot_t > 0:
		var to := shot_to - feet
		var k := float(shot_t) / SHOT_TICKS
		_fx_node.draw_line(a.round(), to.round(), Color(ArmMark.C_MARK, 0.35 * k), 3.0)
		_fx_node.draw_line(a.round(), to.round(), Color(ArmMark.C_CORE, k), 1.0)
		if shot_hit:
			ArmMark.draw_flash(_fx_node, to, shot_t)
