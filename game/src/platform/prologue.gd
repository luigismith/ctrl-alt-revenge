class_name Prologue
extends TestRoom
## Il prologo in grigio (tappa 2 del piano; scaletta della decisione 64): dalla tomba di Mimmo al
## cancello di San Brunone, il pignoramento, la fuga per i Tamburi, il garage col riavvio del braccio
## e l'uscita dal lucernario. Gira sul motore della stanza di prova, con la mappa e i contenuti suoi.
##
## Prima del riavvio GIG ha il braccio bloccato (decisione 34; scelta di Luigi del 5 novembre 2026,
## «base + appeso»): corsa, salto semplice, accovacciarsi, scivolata e sporgenze con la sola destra.
## Col riavvio arrivano la Spinta e il resto delle acrobazie.
##
## Le vignette a fumetto qui sono riquadri provvisori con una didascalia: le tavole vere sono i
## murales di Totò, che arrivano con la grafica. Nessuna battuta della sceneggiatura sta in questo
## file, che è pubblico.

const PROLOGUE_MAP := "res://data/platform/prologo.txt"
## La grafica: per ora il cimitero (tools/ambienti/componi_prologo.py); la fuga e il garage in grigio.
const PROLOGUE_ART := "res://assets/env/prologo/layers.json"

const PROLOGUE_SIGNS := {
	"a": ["CORRI E SALTA", "il braccio sinistro è bloccato: niente acrobazie"],
	"b": ["LE FOSSE", "prendi la rincorsa"],
	"d": ["LA CAPPELLA", "con una mano sola: aggrappati e tieni SU"],
	"e": ["IL PONTEGGIO CROLLATO", "GIÙ mentre corri: scivolata"],
	"f": ["IL PIGNORAMENTO", "difenditi con la destra"],
	"h": ["IL MURO DEL CIMITERO", "il cancello è chiuso: scavalca"],
	"i": ["I TAMBURI", "corri al garage di tua madre"],
	"j": ["IL GARAGE", "la porta si chiude dietro di te"],
	"k": ["LA TASTIERA DEL PADRE", "premi SU davanti alla tastiera"],
}

## Le vignette: titolo e didascalia provvisoria (le tavole vere sono i murales).
const VIGNETTES := {
	"mimmo": ["LA NOTTE DEI MORTI, 2086", "vignetta: il ricordo di Mimmo"],
	"riavvio": ["IL GARAGE", "vignetta: il ricordo del primo braccio, costruito qui"],
	"naso": ["CTRL + ALT + CANC", "vignetta: il terzo tasto, col naso"],
}
## Tick minimi di una vignetta prima che SALTO o ATTACCO la chiudano, e massimi.
const VIGNETTE_MIN := 30
const VIGNETTE_MAX := 600

## I tre tasti del riavvio, in ordine: CTRL, ALT e CANC.
const REBOOT_KEYS: Array[int] = [InputFrame.ATTACK, InputFrame.JUMP, InputFrame.DASH]
const REBOOT_LABELS: Array[String] = ["CTRL", "ALT", "CANC"]
## Entro questa distanza orizzontale SU funziona alla lapide e al banco (e compare il suggerimento).
const USE_REACH := 40
## Dopo il riavvio, i tick prima che gli Esattori sfondino la porta, e ogni quanto bussano.
const DOOR_BREAK := 540
const DOOR_BANG := 60

## Le ripartenze: i cartelli superati coi piedi a terra. Quelle dopo l'arena non rifanno lo scontro.
const CHECKPOINT_SIGNS: Array[String] = ["e", "f", "i", "j"]

const C_RAIN := Color8(150, 170, 200, 120)
const C_VIGNETTE := Color8(18, 16, 24)
const C_INK := Color8(240, 232, 210)
## La vecchia tastiera beige del padre, sul banco.
const C_KEYBOARD := Color8(200, 190, 160)
const C_KEYBOARD_LO := Color8(120, 112, 96)
## Il dentro del garage (colonne 300-340, righe 10-22): lì non piove.
const GARAGE_INSIDE := Rect2(300 * 20, 10 * 20, 41 * 20, 13 * 20)

## Ripartenza attuale: indice in CHECKPOINT_SIGNS (-1 = la tomba).
var checkpoint: int = -1
var rebooted: bool = false
var finished: bool = false
## Vignetta aperta ("" = nessuna) e tick da quando è aperta.
var vignette: String = ""
var vignette_t: int = 0
var _after_vignette: String = ""
var seen_mimmo: bool = false
## Il riavvio: 0 = non cominciato, 1-3 = tasti già premuti, 4 = fatto.
var reboot_step: int = 0
var door_closed: bool = false
## Tick che mancano prima che gli Esattori sfondino la porta (-1 = non bussano).
var door_t: int = -1
## Piove da quando arrivano gli Esattori (decisione 54).
var raining: bool = false
var _door_cells: Array[Vector2i] = []
var _rain_seed: int = 0


func _setup_stage() -> void:
	map_path = PROLOGUE_MAP
	env_path = PROLOGUE_ART
	# Il pavimento dell'arena è la ghiaia del viale davanti al cancello, col cordolo e la terra rossa.
	floor_colors = {"floor": Color8(124, 116, 109), "line": Color8(104, 97, 92), "top": Color8(150, 141, 132),
		"kerb": Color8(96, 48, 38), "speck": Color8(158, 148, 138)}
	signs = PROLOGUE_SIGNS
	panels = {}
	arena_id = "pignoramento"
	hud_title = "PROLOGO"
	# I due Esattori del pignoramento: il messo e un rider. Il messo non c'è ancora: per ora
	# arrivano due rider.
	arena_spawns = [
		{"type": "rider", "delay": 40, "side": 1, "y": 215},
		{"type": "rider", "delay": 90, "side": 1, "y": 245},
	]


func _ready() -> void:
	super._ready()
	for p: Vector2i in grid.marks.get("/", []):
		_door_cells.append(Vector2i(p.x / SolidGrid.TILE, p.y / SolidGrid.TILE - 1))
	_reset()


func _reset() -> void:
	if grid == null or _door_cells.is_empty() and grid.marks.has("/"):
		super._reset()
		return
	var cp := checkpoint
	super._reset()
	# Il cartello dell'arena si supera solo a scontro finito (l'arena si apre 40 px prima).
	arena_done = cp >= CHECKPOINT_SIGNS.find("f")
	raining = cp >= CHECKPOINT_SIGNS.find("f")
	vignette = ""
	finished = false
	player.arm_locked = not rebooted
	player.boosts_left = player.boosts_max()
	_set_door(cp >= CHECKPOINT_SIGNS.find("j"))
	door_t = DOOR_BREAK if rebooted else -1
	if rebooted:
		reboot_step = 4
	elif reboot_step < 4:
		reboot_step = 0
	var at := _checkpoint_pos(cp)
	player.place(at.x, at.y)
	player.facing = 1
	_cam = _cam_target()


func _checkpoint_pos(cp: int) -> Vector2i:
	if rebooted and grid.marks.has("X"):
		return grid.marks["X"][0]
	if cp < 0 or not grid.marks.has(CHECKPOINT_SIGNS[cp]):
		return _start
	var p: Vector2i = grid.marks[CHECKPOINT_SIGNS[cp]][0]
	return Vector2i(p.x - 30, p.y)


func _set_door(closed: bool) -> void:
	door_closed = closed
	for c in _door_cells:
		grid.set_cell(c.x, c.y, SolidGrid.Cell.SOLID if closed else SolidGrid.Cell.EMPTY)


# ------------------------------------------------------------------ tick

func _stage_tick(frame: InputFrame) -> InputFrame:
	if finished:
		return InputFrame.new()
	if vignette != "":
		vignette_t += 1
		var close := vignette_t >= VIGNETTE_MAX or vignette_t >= VIGNETTE_MIN and (
			frame.was_pressed(InputFrame.JUMP) or frame.was_pressed(InputFrame.ATTACK))
		if close:
			vignette = ""
			if _after_vignette != "":
				var next := _after_vignette
				_after_vignette = ""
				_open_vignette(next)
			elif reboot_step == 3:
				_finish_reboot()
		return InputFrame.new()
	var on_ground := player.state == PlatformPlayer.State.GROUND
	# La lapide di Mimmo: SU davanti apre il ricordo.
	if not seen_mimmo and on_ground and _near("M", USE_REACH) and frame.was_pressed(InputFrame.UP):
		seen_mimmo = true
		_open_vignette("mimmo")
		return InputFrame.new()
	# Il riavvio: SU accanto al banco attacca la tastiera, poi i tre tasti in ordine.
	if not rebooted and on_ground and _near("X", USE_REACH):
		if reboot_step == 0 and frame.was_pressed(InputFrame.UP):
			reboot_step = 1
			_on_event("keyboard")
			return InputFrame.new()
		if reboot_step >= 1:
			if frame.was_pressed(REBOOT_KEYS[reboot_step - 1]):
				reboot_step += 1
				_on_event("reboot_key")
				if reboot_step == 4:
					reboot_step = 3
					_open_vignette("riavvio")
					_after_vignette = "naso"
			return InputFrame.new()
	elif reboot_step in [1, 2]:
		reboot_step = 0
	return frame


func _stage_after_step() -> void:
	if finished:
		return
	# Finito il pignoramento comincia a piovere (durante l'arena questo passo non gira).
	if arena_done and not raining:
		raining = true
	var on_ground := player.state == PlatformPlayer.State.GROUND
	# Ripartenze: il cartello superato coi piedi a terra.
	var nxt := checkpoint + 1
	if on_ground and nxt < CHECKPOINT_SIGNS.size() and grid.marks.has(CHECKPOINT_SIGNS[nxt]):
		var p: Vector2i = grid.marks[CHECKPOINT_SIGNS[nxt]][0]
		if player.px >= p.x and player.py == p.y:
			checkpoint = nxt
	# Entrato nel garage, la porta si chiude dietro GIG.
	if not door_closed and not _door_cells.is_empty() and player.left() > (_door_cells[0].x + 2) * SolidGrid.TILE \
			and player.py > (_door_cells[0].y - 6) * SolidGrid.TILE:
		_set_door(true)
		_on_event("door_close")
	# Dopo il riavvio gli Esattori bussano, poi sfondano: chi è ancora dentro riparte dal banco.
	if door_t > 0:
		door_t -= 1
		if door_t % DOOR_BANG == 0:
			_on_event("door_bang")
		if door_t == 0:
			_on_event("door_break")
			if _inside_garage():
				_reset()
	if grid.marks.has("Z") and player.py <= grid.marks["Z"][0].y and player.px >= grid.marks["Z"][0].x - 40:
		finished = true
		_on_event("prologue_end")


func _finish_reboot() -> void:
	reboot_step = 4
	rebooted = true
	player.arm_locked = false
	player.boosts_left = player.boosts_max()
	door_t = DOOR_BREAK
	_on_event("reboot")


func _open_vignette(id: String) -> void:
	vignette = id
	vignette_t = 0


func _near(mark: String, reach: int) -> bool:
	if not grid.marks.has(mark):
		return false
	var m: Vector2i = grid.marks[mark][0]
	return absi(player.px - m.x) <= reach and player.py == m.y


func _inside_garage() -> bool:
	if _door_cells.is_empty():
		return false
	var x0 := (_door_cells[0].x + 2) * SolidGrid.TILE
	return player.px > x0 and player.py > (_door_cells[0].y - 8) * SolidGrid.TILE


func _stage_hash() -> Array:
	return [checkpoint, rebooted, finished, vignette, vignette_t, seen_mimmo, reboot_step, door_closed, door_t, raining]


## I suoni del prologo, poi quelli della stanza.
const PROLOGUE_SFX := {
	"keyboard": [&"ui_confirm", -2.0], "reboot_key": [&"ui_move", 0.0], "reboot": [&"zap", 0.0],
	"door_close": [&"bin_hit", -4.0], "door_bang": [&"body_thud", -3.0], "door_break": [&"bin_break", 0.0],
	"prologue_end": [&"go_arrow", 0.0],
}


func _event_sound(e: String) -> void:
	if sound and PROLOGUE_SFX.has(e):
		var s: Array = PROLOGUE_SFX[e]
		Sfx.play_at(s[0], player.px, 0.05, s[1])
		return
	super._event_sound(e)


func _on_event(e: String) -> void:
	super._on_event(e)
	if e == "reboot":
		# Il braccio riparte: una scarica cyan intorno a GIG.
		for i in 24:
			var a := _spark_rng.randf_range(0.0, TAU)
			var s := _spark_rng.randf_range(1.0, 3.0)
			_spark(player.px, player.py - 60, cos(a) * s, sin(a) * s - 0.5, _spark_rng.randi_range(12, 24), C_CYAN)


# ------------------------------------------------------------------ pilota automatico

## La regia del pilota: chiude le vignette, fa il riavvio e la salita nel garage fino al tetto.
## Fuori dal garage guida il pilota della stanza.
var _pilot_seq: int = -1


func pilot_keys(t: int) -> int:
	if finished:
		return 0
	if vignette != "":
		return InputFrame.JUMP if t % 2 == 0 else 0
	if not seen_mimmo and _near("M", USE_REACH):
		return InputFrame.UP if t % 2 == 0 else 0
	if not seen_mimmo and grid.marks.has("M") and player.state == PlatformPlayer.State.GROUND and player.px > grid.marks["M"][0].x \
			and checkpoint < 0 and player.px < grid.marks["M"][0].x + 80:
		return InputFrame.LEFT
	if not door_closed:
		return -1
	if not rebooted:
		if reboot_step >= 1:
			return REBOOT_KEYS[reboot_step - 1] if t % 2 == 0 else 0
		var dx: int = grid.marks["X"][0].x - player.px
		if player.state != PlatformPlayer.State.GROUND:
			return -1
		if absi(dx) <= 8:
			return InputFrame.UP if t % 2 == 0 else 0
		return -1 if dx > 0 and dx > 40 else (InputFrame.RIGHT if dx > 0 else InputFrame.LEFT)
	return _pilot_garage()


## Nel garage dopo il riavvio: sullo scaffale con la Spinta, poi su per il lucernario con la Spinta,
## aggrappato al bordo, e sul tetto verso destra.
var _pilot_boost: bool = false
var _pilot_air_x: int = 0


func _pilot_garage() -> int:
	var T := SolidGrid.TILE
	var p := player
	if p.state == PlatformPlayer.State.LEDGE_HANG or p.state == PlatformPlayer.State.LEDGE_CLIMB:
		return -1
	if p.py <= 9 * T and p.state != PlatformPlayer.State.AIR:
		return InputFrame.RIGHT
	if p.state == PlatformPlayer.State.AIR or _pilot_seq >= 0:
		_pilot_seq += 1
		var keys := 0
		# SALTO tenuto; per la Spinta un tick lasciato e poi SALTO di nuovo.
		if _pilot_seq < 18 or (_pilot_boost and _pilot_seq >= 20 and _pilot_seq < 38):
			keys |= InputFrame.JUMP
		if p.state != PlatformPlayer.State.AIR and _pilot_seq > 3:
			_pilot_seq = -1
		# Con la testa nel lucernario: verso destra, al bordo, per aggrapparsi.
		var tx := 400 * T if p.py < 15 * T else _pilot_air_x
		if absi(tx - p.px) > 6:
			keys |= InputFrame.RIGHT if tx > p.px else InputFrame.LEFT
		return keys
	# Da terra e dallo scaffale si salta sotto il lucernario, con la Spinta.
	var from := 320 * T
	_pilot_boost = true
	_pilot_air_x = from
	var d := from - p.px
	if absi(d) > 6:
		return InputFrame.RIGHT if d > 0 else InputFrame.LEFT
	_pilot_seq = 0
	return InputFrame.JUMP


# ------------------------------------------------------------------ disegno

func _draw_stage(v: Node2D) -> void:
	# La lapide di Mimmo e la tastiera sul banco: un segno cyan che pulsa finché servono, e SU
	# quando si è abbastanza vicini.
	if grid.marks.has("X"):
		_draw_keyboard(v, grid.marks["X"][0])
	if vignette == "" and not finished:
		if not seen_mimmo and grid.marks.has("M"):
			_draw_use_spot(v, grid.marks["M"][0], _near("M", USE_REACH))
		if door_closed and not rebooted and reboot_step == 0 and grid.marks.has("X"):
			_draw_use_spot(v, grid.marks["X"][0], _near("X", USE_REACH))
	# La porta del garage, e gli Esattori che bussano.
	if door_closed and not _door_cells.is_empty():
		var c := _door_cells[0]
		var r := Rect2(c.x * SolidGrid.TILE, c.y * SolidGrid.TILE, 2 * SolidGrid.TILE, _door_cells.size() / 2 * SolidGrid.TILE)
		v.draw_rect(r, C_GATE_DARK)
		for k in range(int(r.position.y) + 4, int(r.end.y), 8):
			v.draw_rect(Rect2(r.position.x, k, r.size.x, 1), C_GATE)
		if door_t > 0 and door_t % DOOR_BANG > DOOR_BANG - 14:
			UiFont.draw_text(v, Vector2(r.position.x - 24, r.position.y - 16), "BUM!", C_LED_RED, 1, 1)
	if raining:
		_draw_rain(v)


## Il segno di un punto dove premere SU: un triangolo cyan che pulsa e ondeggia sopra la testa di
## GIG, con SU sopra quando si è vicini (solo disegno).
func _draw_use_spot(v: Node2D, at: Vector2i, near: bool) -> void:
	var f := Engine.get_physics_frames()
	var bob := roundf(sin(f * 0.12) * 2.0)
	var c := C_CYAN
	c.a = 1.0 if near else 0.55 + 0.45 * absf(sin(f * 0.08))
	var y := at.y - 112.0 + bob
	v.draw_colored_polygon(PackedVector2Array([Vector2(at.x - 6, y), Vector2(at.x + 6, y), Vector2(at.x, y + 7)]), c)
	if near:
		UiFont.draw_text(v, Vector2(at.x, y - 16), "SU", C_CYAN, 1, 1)


## La vecchia tastiera del padre sul banco, accanto al punto del riavvio; dopo, il cavo al braccio.
func _draw_keyboard(v: Node2D, at: Vector2i) -> void:
	var top := at.y - 2 * SolidGrid.TILE
	var r := Rect2(at.x - 62, top - 5, 28, 5)
	v.draw_rect(r, C_KEYBOARD)
	for i in 6:
		v.draw_rect(Rect2(r.position.x + 2 + i * 4, top - 4, 3, 1), C_KEYBOARD_LO)
		v.draw_rect(Rect2(r.position.x + 2 + i * 4, top - 2, 3, 1), C_KEYBOARD_LO)
	if not rebooted and door_closed:
		var f := Engine.get_physics_frames()
		if (f / 20) % 2 == 0:
			v.draw_rect(Rect2(r.end.x - 3, top - 4, 2, 1), C_CYAN)


## La pioggia in grigio: righe corte che cadono sullo schermo (solo disegno).
func _draw_rain(v: Node2D) -> void:
	_rain_seed += 1
	var rng := RandomNumberGenerator.new()
	rng.seed = 1234
	for i in 90:
		var x := _cam.x + rng.randf_range(-20.0, View.W + 20.0)
		var speed := rng.randf_range(5.0, 8.0)
		var y := fposmod(rng.randf_range(0.0, View.H) + _rain_seed * speed, View.H + 40.0) + _cam.y - 20.0
		if GARAGE_INSIDE.has_point(Vector2(x, y)):
			continue
		v.draw_line(Vector2(x - y * 0.05 + _cam.y * 0.05, y), Vector2(x - y * 0.05 + _cam.y * 0.05 - 2, y + 7), C_RAIN, 1.0)


func _draw_stage_hud(h: Control) -> void:
	if arena_phase == ArenaPhase.NONE:
		# L'ora, sotto il titolo (cronologia: il cimitero dalle 15.15, la fuga e il garage verso le 16).
		var ora := "GIOVEDÌ SANTO · ORE 15.15" if checkpoint < CHECKPOINT_SIGNS.find("i") else "GIOVEDÌ SANTO · ORE 16.00"
		UiFont.draw_text(h, Vector2(View.CX, 2), ora, C_DIM, 1, 1)
	if reboot_step >= 1 and reboot_step <= 3 and vignette == "":
		_draw_reboot_prompt(h)
	if door_t > 0:
		UiFont.draw_text(h, Vector2(View.CX, 20), "GLI ESATTORI SFONDANO LA PORTA: ESCI DAL LUCERNARIO", C_LED_RED, 1, 1)
	if vignette != "":
		_draw_vignette(h)
	if finished:
		h.draw_rect(Rect2(0, 0, View.W, View.H), Color(0, 0, 0, 0.6))
		UiFont.draw_text(h, Vector2(View.CX, View.H / 2.0 - 16), "FINE DEL PROLOGO", C_CYAN, 2, 1)
		UiFont.draw_text(h, Vector2(View.CX, View.H / 2.0 + 14), "poi il capitolo 1, I tetti dei Tamburi · START per il titolo", C_DIM, 1, 1)


func _draw_reboot_prompt(h: Control) -> void:
	var y := View.H - 60.0
	h.draw_rect(Rect2(View.CX - 120, y - 6, 240, 40), Color(0, 0, 0, 0.7))
	for i in 3:
		var x := View.CX - 80 + i * 80
		var done := reboot_step - 1 > i
		var now := reboot_step - 1 == i
		h.draw_rect(Rect2(x - 26, y, 52, 16), C_CYAN if done else (C_TEXT if now else C_CASE_LO))
		UiFont.draw_text(h, Vector2(x, y + 3), REBOOT_LABELS[i], C_SCREEN if done or now else C_DIM, 1, 1)
	var hint: String = ["ATTACCO", "SALTO", "SCATTO"][clampi(reboot_step - 1, 0, 2)]
	UiFont.draw_text(h, Vector2(View.CX, y + 21), "premi " + hint, C_DIM, 1, 1)


func _draw_vignette(h: Control) -> void:
	var v: Array = VIGNETTES[vignette]
	var r := Rect2(48, 40, View.W - 96, View.H - 80)
	h.draw_rect(Rect2(0, 0, View.W, View.H), Color(0, 0, 0, 0.5))
	h.draw_rect(r.grow(3), C_INK)
	h.draw_rect(r, C_VIGNETTE)
	UiFont.draw_text(h, Vector2(r.get_center().x, r.position.y + 20), str(v[0]), C_INK, 2, 1)
	UiFont.draw_text(h, Vector2(r.get_center().x, r.get_center().y), str(v[1]), C_DIM, 1, 1)
	if vignette_t >= VIGNETTE_MIN:
		UiFont.draw_text(h, Vector2(r.get_center().x, r.end.y - 16), "SALTO per continuare", C_CYAN, 1, 1)
