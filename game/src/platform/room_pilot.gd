class_name RoomPilot
extends RefCounted
## Pilota automatico della stanza di prova (--autopilot stanza): corre verso destra e reagisce
## a quello che ha davanti, come un giocatore prudente. Serve a guardare la stanza senza pad,
## a registrare le GIF e a controllare che il percorso si faccia tutto.
##
## Legge solo lo stato della simulazione e la griglia: decide i tasti del tick, che poi
## passano da PlayerInput come quelli veri.

var player: PlatformPlayer
var _jump_hold: int = 0
var _boost_wait: int = -1
var _dash_wait: int = -1
var _down_hold: int = 0
## Dove va in aria: verso destra, o via dal muro dopo un salto a muro.
var _dir: int = 1
var _last_jump: bool = false


func decide(_tick: int) -> int:
	var keys := _decide(_tick)
	_last_jump = (keys & InputFrame.JUMP) != 0
	return keys


func _decide(_tick: int) -> int:
	var p := player
	if p == null:
		return 0
	var keys := InputFrame.RIGHT if _dir > 0 else InputFrame.LEFT
	var g := p.grid
	var T := SolidGrid.TILE
	match p.state:
		PlatformPlayer.State.LEDGE_HANG:
			_dir = 1
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
