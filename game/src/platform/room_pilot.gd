class_name RoomPilot
extends RefCounted
## Pilota automatico della stanza di prova (--autopilot stanza): corre verso destra e reagisce
## a quello che ha davanti, come un giocatore prudente. Serve a guardare la stanza senza pad,
## a registrare le GIF e a controllare che il percorso si faccia tutto.
##
## Legge solo lo stato della simulazione e la griglia: decide i tasti del tick, che poi
## passano da PlayerInput come quelli veri.

var player: PlatformPlayer
## La stanza (la imposta lei): serve per i pannelli dell'hacking.
var room: TestRoom
## L'arena in corso (la imposta la stanza): lì combatte il pilota dello slice.
var arena: Level
## I pannelli da forzare, in ordine. Nella prova dei due pannelli quello giusto è prima R (sul
## ballatoio), poi Q; i test provano anche l'ordine sbagliato.
var hack_plan: Array[String] = ["P", "R", "Q"]
## Entro questa distanza orizzontale il pilota smette di correre e va al pannello.
const HACK_LOOKAHEAD := 360
var _plan_i: int = 0
var _fighter: Autopilot
var _jump_hold: int = 0
var _boost_wait: int = -1
var _dash_wait: int = -1
var _down_hold: int = 0
## Dove va in aria: verso destra, o via dal muro dopo un salto a muro.
var _dir: int = 1
var _last_jump: bool = false


func decide(_tick: int) -> int:
	if arena != null:
		if _fighter == null or _fighter.level != arena:
			_fighter = Autopilot.new(&"arena")
			_fighter.level = arena
		_last_jump = false
		return _fighter.decide(_tick)
	var keys := _decide(_tick)
	_last_jump = (keys & InputFrame.JUMP) != 0
	return keys


func _decide(_tick: int) -> int:
	var p := player
	if p == null:
		return 0
	# I tratti con una regia loro (il prologo: vignette, riavvio, garage) decidono prima.
	if room != null:
		var sk := room.pilot_keys(_tick)
		if sk >= 0:
			return sk
	var hk := _hack_keys()
	if hk >= 0:
		return hk
	# Il sigillo della Vedetta: si stacca pestando SALTO.
	if p.stuck_left > 0:
		return InputFrame.JUMP if _tick % 4 == 0 else 0
	var keys := InputFrame.RIGHT if _dir > 0 else InputFrame.LEFT
	var g := p.grid
	var T := SolidGrid.TILE
	match p.state:
		PlatformPlayer.State.LEDGE_HANG:
			_dir = 1
			# Con una mano sola bisogna tenere SU per tirarsi su.
			if p.arm_locked:
				return InputFrame.UP
			return InputFrame.UP if _tick % 6 == 0 else 0
		PlatformPlayer.State.LEDGE_CLIMB:
			return 0
		PlatformPlayer.State.WALL_SLIDE:
			# Salto a muro: si rilascia SALTO per un tick, poi lo si tiene, e in aria si va via dal muro.
			_boost_wait = -1
			# Col pavimento a meno di due blocchi si scende e basta (per esempio nel fosso prima del
			# cunicolo): il salto a muro serve solo nei pozzi.
			if _last_jump or g.rect_hits_solid(p.left(), p.py, p.right(), p.py + 2 * T):
				return 0
			_dir = -p.wall_dir
			_jump_hold = 14
			return InputFrame.JUMP
		PlatformPlayer.State.WALL_RUN:
			# In cima alla corsa sul muro, la Spinta per salire ancora lungo il muro.
			_boost_wait = -1
			if p.vy > -PlatformPlayer.SUB and not _last_jump and p.boosts_left > 0:
				_jump_hold = 20
				return keys | InputFrame.JUMP
			return keys
		PlatformPlayer.State.GROUND, PlatformPlayer.State.CROUCH, PlatformPlayer.State.SLIDE:
			_dir = 1
			keys = InputFrame.RIGHT
			_boost_wait = -1
			_dash_wait = -1
			var l := p.left()
			var r := p.right()
			# Soffitto basso davanti (cunicolo): GIÙ, così parte la scivolata o si va accovacciati.
			var low_ceiling := g.rect_hits_solid(r, p.py - 100, r + 50, p.py - 62) and not g.rect_hits_solid(r, p.py - 58, r + 50, p.py)
			if low_ceiling or p.state != PlatformPlayer.State.GROUND and g.rect_hits_solid(l, p.py - 100, r, p.py - 58):
				_down_hold = 4
			if _down_hold > 0:
				_down_hold -= 1
				return keys | InputFrame.DOWN
			# Muro o fosso davanti: salto pieno.
			var wall := g.rect_hits_solid(r, p.py - 25, r + 18, p.py)
			# La processione davanti: dalla strada non si scavalca. Lo spintone (SCATTO attaccato alla coda)
			# apre la fila, e poi la Vedetta lo prende: il sigillo si stacca pestando SALTO, qui sopra.
			if _procession_ahead(r):
				return keys | (InputFrame.DASH if _tick % 20 == 0 else 0)
			var gap := not g.floor_at(r, r + 22, p.py, true)
			if (wall or gap) and _jump_hold == 0 and p.state == PlatformPlayer.State.GROUND and not _last_jump:
				_jump_hold = 22
				# La Spinta in cima al salto, se serve: un muro più alto di dove arrivano le mani
				# (allora ci si aggrappa) o un fosso largo. Per un fosso molto largo, anche lo scatto.
				var tall := g.rect_hits_solid(r + 10, p.py - 188, r + 28, p.py - 175)
				var wide := not g.floor_at(r + 22, r + 22 + 7 * T, p.py, true)
				var very_wide := not g.floor_at(r + 22, r + 22 + 11 * T, p.py, true)
				_boost_wait = 20 if tall or wide else -1
				_dash_wait = 40 if very_wide and not wall else -1
		PlatformPlayer.State.AIR:
			if _dash_wait > 0:
				_dash_wait -= 1
				if _dash_wait == 0:
					_dash_wait = -1
					keys |= InputFrame.DASH
			if _boost_wait > 0:
				_boost_wait -= 1
				if _boost_wait == 0:
					_jump_hold = 20
					_boost_wait = -1
					# Rilascio di un tick, poi la nuova pressione è la Spinta.
					return keys
	if _jump_hold > 0:
		_jump_hold -= 1
		keys |= InputFrame.JUMP
	return keys


## Una processione subito davanti ai piedi di GIG.
func _procession_ahead(r: int) -> bool:
	if room == null:
		return false
	var feet := Rect2i(r, player.py - 25, 30, 25)
	for s: Rect2i in room.processions.shields():
		if s.intersects(feet):
			return true
	return false


## Il prossimo pannello del piano, quando è vicino: ci va (saltando sul ballatoio o scendendone),
## si ferma davanti e tiene SU finché il cancello si apre. -1 se non c'è niente da forzare qui.
func _hack_keys() -> int:
	if room == null:
		return -1
	while _plan_i < hack_plan.size() and (int(room.hacks_done.get(hack_plan[_plan_i], 0)) > 0 \
			or not room.grid.marks.has(hack_plan[_plan_i])):
		_plan_i += 1
	if _plan_i >= hack_plan.size():
		return -1
	var p := player
	var m: Vector2i = room.grid.marks[hack_plan[_plan_i]][0]
	# Sullo stesso piano si punta al posto col pugno sotto la presa; da sotto o da sopra, alla centralina.
	var dx := (room.hack_spot(hack_plan[_plan_i]) if p.py == m.y else m.x) - p.px
	if absi(dx) > HACK_LOOKAHEAD:
		return -1
	var toward := InputFrame.RIGHT if dx > 0 else InputFrame.LEFT
	var away := InputFrame.LEFT if dx > 0 else InputFrame.RIGHT
	var keys := 0
	match p.state:
		PlatformPlayer.State.GROUND:
			_dir = 1
			if p.py == m.y:
				if room.hack_panel != "" or absi(dx) <= 6 and absi(p.vx) < PlatformPlayer.SUB / 2:
					keys = InputFrame.UP
				elif absi(dx) <= 6:
					keys = 0
				else:
					keys = toward
			elif m.y < p.py:
				# Il pannello è sul ballatoio: un salto in corsa dalla distanza giusta, che atterra lì sopra.
				if absi(dx) < 90:
					keys = away
				elif absi(dx) > 130 or _last_jump:
					keys = toward
				else:
					_jump_hold = 22
					keys = toward | InputFrame.JUMP
					_jump_hold -= 1
			else:
				# Il pannello è più in basso: GIÙ + SALTO per scendere dal ballatoio.
				keys = InputFrame.DOWN | (0 if _last_jump else InputFrame.JUMP)
		PlatformPlayer.State.AIR:
			keys = toward if absi(dx) > 8 else 0
			if _jump_hold > 0:
				_jump_hold -= 1
				keys |= InputFrame.JUMP
		_:
			return -1
	_last_jump = (keys & InputFrame.JUMP) != 0
	return keys
