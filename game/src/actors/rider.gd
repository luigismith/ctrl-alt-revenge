class_name Rider
extends Thug
## Il rider (decisione 63): il nemico base degli Esattori, un precario a cottimo con lo zaino
## termico pieno di braccia pignorate. Veloce e in gruppo, colpisce e scappa:
## - aspetta più lontano dei nemici dello slice e, quando ha il turno, arriva di corsa;
## - tira un jab, oppure (una volta su tre) tenta il pignoramento;
## - finito l'attacco, si allontana di corsa e poi torna ad aspettare.
##
## Il pignoramento: il rider afferra GIG e gli punta il lettore sul braccio. GIG si libera
## premendo i tasti a ripetizione (Gig.ESCAPE_PRESSES pressioni); se non ce la fa in tempo il
## braccio cyber resta sospeso per qualche secondo (Gig.suspend_arm): niente prese, niente calcio
## in salto, pugni più deboli. Scelta di Luigi del 5 novembre 2026.
##
## Lo sprite viene dalla pipeline 3D: casco, occhiali da polvere, giacca senape da consegne e lo
## zaino termico con un braccio pignorato che esce dal coperchio. Nel pignoramento tiene GIG per il
## braccio con tutte e due le mani (animazione "pignora", due fotogrammi in ciclo).

## Velocità della corsa per arrivare e per scappare, rispetto alla camminata.
const DASH_SPEED := 2.0
const RETREAT_TICKS := 40
const GRAB_CHANCE := 0.35
## Distanza da GIG durante il pignoramento.
const GRAB_DX := 26.0
## Tick che il pignoramento impiega a riuscire: il tempo che GIG ha per divincolarsi.
const PIGNORA_TICKS := 100
const PIGNORA_DAMAGE := 4
## Animazione del pignoramento: due fotogrammi che si alternano ogni PIGNORA_FRAME_TICKS tick.
const PIGNORA_POSE := &"pignora"
const PIGNORA_FRAME_TICKS := 8

## Tick di fuga rimasti dopo un attacco.
var retreat: int = 0
## Tick da quando è cominciato il pignoramento (in stato GRAB).
var pign_ticks: int = 0
var _grab_try: bool = false


func _think() -> void:
	if state == State.GRAB:
		_think_pignora()
		return
	if retreat > 0 and is_free() and level.player != null and level.player.is_alive():
		retreat -= 1
		_think_retreat(level.player)
		return
	super._think()


func _approach_speed() -> float:
	return DASH_SPEED


func _choose_attack() -> AttackData:
	_grab_try = rng.randf() < GRAB_CHANCE
	return super._choose_attack()


func _think_approach(p: Fighter) -> void:
	if not _grab_try:
		super._think_approach(p)
		return
	_approach_ticks += 1
	if _approach_ticks > data.approach_timeout:
		_release_token()
		level.director.set_cooldown(self, level.tick + data.cooldown_ticks.x)
		mind = Mind.WAIT
		return
	var side := 1 if px >= p.px else -1
	var tx := p.px + side * GRAB_DX
	if absf(px - tx) <= 4.0 and absf(py - p.py) <= 3.0:
		if _can_pignorate(p):
			_start_pignora(p as Gig, side)
		else:
			# GIG non si può afferrare adesso (salta, attacca, è a terra): resta il jab.
			_grab_try = false
		return
	_walk_towards(tx, p.py, 0.625, DASH_SPEED)


func _can_pignorate(p: Fighter) -> bool:
	if not (p is Gig):
		return false
	var g := p as Gig
	return (g.is_free() or g.state == State.LAND) and not g.is_airborne() and g.invuln == 0 \
		and g.arm_off == 0 and g.grab_partner == null and g.is_alive()


func _start_pignora(g: Gig, side: int) -> void:
	vx = 0.0
	vy = 0.0
	facing = -side
	level.director.on_attack_start(self, level.tick)
	set_state(State.GRAB)
	anim.show_frame(PIGNORA_POSE, 0)
	grab_partner = g
	pign_ticks = 0
	g.become_grabbed(self)
	g.facing = side
	_sfx(&"grab")
	Game.count(&"pignoramenti")


func _think_pignora() -> void:
	var g := grab_partner as Gig
	if g == null or g.state != State.GRABBED or g.grab_partner != self:
		grab_partner = null
		_after_pignora()
		return
	pign_ticks += 1
	anim.show_frame(PIGNORA_POSE, (pign_ticks / PIGNORA_FRAME_TICKS) % 2)
	px = level.clamp_x(self, g.px - facing * GRAB_DX)
	py = g.py
	if g.escape_presses >= Gig.ESCAPE_PRESSES:
		# GIG si divincola: il rider barcolla all'indietro e scappa.
		grab_partner = null
		g.escape_from_grab()
		set_state(State.HURT, &"hurt_low")
		stun = 16
		_push_ticks = 6
		_push_v = -facing * 2.5
		_after_pignora()
		Game.count(&"pignoramenti_evitati")
	elif pign_ticks >= PIGNORA_TICKS:
		grab_partner = null
		g.suspend_arm(PIGNORA_DAMAGE)
		set_state(State.IDLE)
		_after_pignora()
		Game.count(&"braccia_sospese")


func _after_pignora() -> void:
	_grab_try = false
	_release_token()
	level.director.set_cooldown(self, level.tick + rng.randi_range(data.cooldown_ticks.x, data.cooldown_ticks.y))
	mind = Mind.WAIT
	retreat = RETREAT_TICKS
	if state == State.GRAB:
		set_state(State.IDLE)


## Scappa di corsa lontano da GIG, dentro lo schermo; arrivato, torna ad aspettare.
func _think_retreat(p: Fighter) -> void:
	var away := 1 if px >= p.px else -1
	var margin := Level.WALL_MARGIN + 7.5
	var lo := level.view_left() + margin
	var hi := level.view_right() - margin
	var tx := p.px + away * data.wait_distance.y * 1.2
	# Contro il muro si scappa dall'altra parte.
	if tx < lo or tx > hi:
		away = -away
		tx = p.px + away * data.wait_distance.y * 1.2
	tx = clampf(tx, lo, hi)
	_walk_towards(tx, py, 2.5, DASH_SPEED)
	if vx != 0.0:
		facing = 1 if vx > 0.0 else -1
	else:
		retreat = 0


func _end_attack() -> void:
	super._end_attack()
	retreat = RETREAT_TICKS


func _on_state_changed(prev: State, next: State) -> void:
	# Colpito o lanciato mentre afferra: GIG torna libero.
	if prev == State.GRAB and next != State.GRAB and grab_partner != null:
		var g := grab_partner
		grab_partner = null
		if g.state == State.GRABBED and g.grab_partner == self:
			g._release_from_grab()
	super._on_state_changed(prev, next)
