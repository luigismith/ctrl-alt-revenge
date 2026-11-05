class_name TestRoom
extends Node2D
## La stanza di prova in grigio (tappa 1 del piano): niente grafica, solo blocchi, GIG e i
## numeri che servono a tarare il movimento con il pad. Le misure che vanno bene diventano le
## regole per disegnare i livelli.
##
## La simulazione (PlatformPlayer) gira a tick fissi come il resto del gioco; la telecamera e
## le scintille sono solo disegno, quindi possono essere morbide.

signal quit_to_title
## Esce dal gioco a replay finito (--quit-at-end), dopo aver stampato l'hash.
signal replay_done

## Nelle build di debug ogni partita giocata dal vivo si salva qui, un file per sessione: si
## rigioca con --stanza --replay <file>, per vedere i problemi senza doverli spiegare.
const SESSION_DIR := "user://stanza_sessioni"

const MAP := "res://data/platform/stanza_prova.txt"
const MOVES := "res://data/platform/gig_moves.tres"

## Testi dei cartelli, per le lettere minuscole della mappa.
const SIGNS := {
	"a": ["CORRI E SALTA", "tieni SALTO per saltare più in alto"],
	"b": ["FOSSI DA 3, 5, 7 E 9 BLOCCHI", "il 9 si passa solo con la Spinta"],
	"c": ["PIATTAFORME SOTTILI", "si sale da sotto · GIÙ + SALTO per scendere"],
	"d": ["SPORGENZE", "in caduta verso il muro ti aggrappi · SU o SALTO per salire"],
	"e": ["CUNICOLO BASSO", "GIÙ mentre corri: scivolata"],
	"f": ["ARENA", "entra: la telecamera si inclina e arrivano gli Esattori · poi VAI"],
	"h": ["SALTO A MURO", "in caduta spingi contro il muro: il braccio frena · SALTO per staccarti"],
	"i": ["SCATTO", "in aria L, C o un dorsale: 3 blocchi in avanti, uno per salto"],
	"j": ["CORSA SUL MURO", "di corsa contro il muro, SALTO: qualche passo in su"],
	"k": ["HACKING", "tieni SU sotto la centralina, poi corri"],
	"l": ["DUE PANNELLI", "tempi diversi: conta l'ordine"],
	"g": ["FINE DELLA STANZA", "R o SELECT per ricominciare"],
}

## L'hacking "Collega e corri" (decisione del 5 novembre 2026, in docs/gameplay.md): GIG tiene SU
## sotto una centralina e appoggia il pugno cyber alla presa; dopo HACK_TICKS il cancello del
## pannello si apre per `open` tick, poi si richiude. Il puzzle è il percorso: arrivarci in tempo e,
## con più pannelli, scegliere l'ordine giusto.
const HACK_TICKS := 30
## Distanza orizzontale massima fra GIG e il suo posto sotto la centralina per collegarsi, in px.
## Collegato, GIG fa i passi che mancano (1 px per tick) per avere il pugno sotto la presa.
const HACK_REACH := 14
## Il pugno cyber nella posa dell'hacking, rispetto ai piedi: davanti di 13 px (lo sprite "hack").
const HACK_FIST_X := 13
## Pannello (lettera maiuscola della mappa) → simbolo delle celle del suo cancello e tick di apertura.
## Nella prova dei due pannelli Q, a terra accanto al cancello vicino, apre quello lontano per poco;
## R, sul ballatoio che si incontra prima, apre quello vicino per molto. Chi forza subito Q deve
## tornare indietro fino al ballatoio, e il cancello lontano si richiude: prima R, poi Q, e via.
const PANELS := {
	"P": {"gate": "|", "open": 150},
	"Q": {"gate": ";", "open": 180},
	"R": {"gate": ":", "open": 360},
}
## La centralina sul muro: larga, alta, e col fondo (la presa) all'altezza del pugno alzato.
const PANEL_W := 44
const PANEL_H := 46
const PANEL_BOTTOM := 124
## Tick dell'animazione del cancello che sale o scende (solo disegno).
const GATE_ANIM := 8
const C_GATE := Color8(214, 160, 58)
const C_GATE_DARK := Color8(120, 84, 30)
const C_PANEL := Color8(24, 26, 34)
const C_CASE := Color8(58, 62, 78)
const C_CASE_HI := Color8(108, 114, 134)
const C_CASE_LO := Color8(30, 32, 42)
const C_SCREEN := Color8(8, 20, 26)
const C_HAZARD := Color8(232, 184, 48)
const C_LED_RED := Color8(255, 64, 72)
const C_OK := Color8(110, 230, 120)

const C_BG := Color8(38, 38, 46)
const C_GRID := Color8(46, 46, 56)
const C_SOLID := Color8(92, 92, 106)
const C_SOLID_TOP := Color8(140, 140, 156)
const C_THIN := Color8(120, 120, 136)
const C_TEXT := Color8(232, 228, 214)
const C_DIM := Color8(160, 156, 150)
const C_CYAN := Color8(64, 232, 255)
const C_BOX := Color8(255, 80, 80)
const C_FLOOR := Color8(66, 66, 80)
const C_FLOOR_LINE := Color8(84, 84, 100)
const C_KERB := Color8(30, 30, 38)

## L'arena della stanza (decisione del 4 novembre 2026, in docs/gameplay.md): quando GIG entra la
## telecamera si blocca e si inclina un po' dall'alto, il pavimento si allarga in profondità e si
## combatte con il sistema dello slice (un Level ospitato, a corsie); a scontro finito compare VAI,
## la telecamera torna laterale e si riprende a saltare.
enum ArenaPhase { NONE, ENTER, FIGHT, LEAVE }
## La fascia calpestabile dell'arena in coordinate dello schermo, come nello slice: il bordo dietro
## coincide con la linea del pavimento del platform.
const ARENA_BAND := Vector2(188, 260)
## Tick dell'inclinazione all'entrata e all'uscita.
const TILT_IN := 40
const TILT_OUT := 32
## Quanto si schiaccia in verticale la stanza dietro il pavimento, a telecamera inclinata.
const TILT_SQUASH := 0.12
## Quanto GIG scende nella fascia mentre la telecamera si inclina.
const ENTRY_DEPTH := 26.0
## Distanza del punto di fuga delle linee del pavimento, in px sopra la linea del pavimento.
const PERSP := 240.0
## Posizione dell'arena rispetto al suo cartello ("f"): telecamera bloccata e punto d'ingresso.
const ARENA_CAM_FROM_SIGN := -170
const ARENA_TRIGGER_FROM_SIGN := -40
## Gli Esattori dell'arena (decisione 63): due rider, che arrivano in gruppo, e poi l'esattore di
## professione, che para e carica.
const ARENA_SPAWNS := [
	{"type": "rider", "delay": 30, "side": 1, "y": 205},
	{"type": "rider", "delay": 55, "side": -1, "y": 240},
	{"type": "esattore", "delay": 320, "side": 1, "y": 243},
]

var grid: SolidGrid
var player: PlatformPlayer
var input: PlayerInput
var pilot: RoomPilot
var moves: PlatformMoves
var tick: int = 0
var show_boxes: bool = false
## Musica ed effetti sonori (spenti nei test).
var sound: bool = true

var _start: Vector2i = Vector2i(100, 380)
## Tick in cui si è premuto R (ricomincia): fanno parte della sessione registrata.
var _resets: Array = []
var _replay_resets: Array = []
var _record_path: String = ""
var _view: Node2D
var _room_node: Node2D
var _floor_node: Node2D
var _body: Sprite2D
var _hud: Control
var _overlay: LevelOverlay

## L'arena: il Level ospitato esiste solo mentre si combatte.
var arena: Level
var arena_phase: ArenaPhase = ArenaPhase.NONE
var arena_done: bool = false
var _arena_t: int = 0
## Inclinazione della telecamera, da 0 (laterale) a 1 (arena). Solo disegno, ma segue i tick.
var tilt: float = 0.0
var _floor_y: int = 460
var _arena_cam_x: int = -1
var _arena_trigger_x: int = -1
var _cam_from: Vector2 = Vector2.ZERO
var _leave_from_py: float = 0.0
var _cam: Vector2 = Vector2.ZERO
## I cancelli, per simbolo della mappa: {"cells": celle, "rect": Rect2i in pixel, "timer": tick di
## apertura che restano (0 = chiuso), "lift": quanto è alzato nel disegno, da 0 a 1}.
var gates: Dictionary = {}
var _gate_cells: Dictionary = {}
## Il pannello a cui GIG è collegato ("" se nessuno) e da quanti tick.
var hack_panel: String = ""
var hack_t: int = 0
## Quante volte è stato forzato ogni pannello, in questo giro.
var hacks_done: Dictionary = {}
var last_hacked: String = ""
## Scintille della Spinta e degli atterraggi: [x, y, vx, vy, vita, vita iniziale, colore]. Solo disegno.
var _sparks: Array = []
var _spark_rng := RandomNumberGenerator.new()


func configure(opts: Dictionary) -> void:
	input = opts.get("input", null)
	pilot = opts.get("pilot", null)
	_record_path = str(opts.get("record", ""))
	sound = bool(opts.get("sound", true))
	if input != null and input.mode == PlayerInput.Mode.REPLAY:
		_replay_resets = input.replay.start.get("resets", [])


func _ready() -> void:
	if input == null:
		input = PlayerInput.live()
	moves = load(MOVES) as PlatformMoves
	if moves == null:
		moves = PlatformMoves.new()
	grid = SolidGrid.load_file(MAP)
	if grid.marks.has("G"):
		_start = grid.marks["G"][0]
	if Game.options.start_x >= 0.0:
		_start.x = roundi(Game.options.start_x)
	if grid.marks.has("f"):
		var f: Vector2i = grid.marks["f"][0]
		_floor_y = f.y
		_arena_cam_x = clampi(f.x + ARENA_CAM_FROM_SIGN, 0, grid.pixel_width() - View.W)
		_arena_trigger_x = f.x + ARENA_TRIGGER_FROM_SIGN
	_build_gates()
	_spark_rng.seed = 7
	# La musica del livello, se il laboratorio ha i brani (non tocca la simulazione).
	if sound:
		Music.duck(false)
		Music.play(&"stage1")
	_view = Node2D.new()
	_view.draw.connect(_draw_back)
	add_child(_view)
	_room_node = Node2D.new()
	_room_node.draw.connect(_draw_room)
	_view.add_child(_room_node)
	_floor_node = Node2D.new()
	_floor_node.z_index = 1
	_floor_node.draw.connect(_draw_floor)
	_view.add_child(_floor_node)
	var sheet := SpriteSheet.get_sheet(&"gig")
	player = PlatformPlayer.new(moves, grid, sheet)
	if pilot != null:
		pilot.player = player
		pilot.room = self
	_body = Sprite2D.new()
	_body.centered = false
	_body.region_enabled = true
	_body.texture = sheet.texture
	_view.add_child(_body)
	var fx := Node2D.new()
	fx.z_index = 5
	fx.draw.connect(func() -> void: _draw_fx(fx))
	_view.add_child(fx)
	var layer := CanvasLayer.new()
	layer.layer = 10
	add_child(layer)
	_hud = Control.new()
	_hud.size = View.SIZE
	_hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hud.draw.connect(_draw_hud)
	layer.add_child(_hud)
	_overlay = LevelOverlay.new()
	layer.add_child(_overlay)
	show_boxes = Game.options.debug_boxes
	if input.mode == PlayerInput.Mode.REPLAY and input.replay.start.has("x"):
		_start.x = int(input.replay.start["x"])
	if _record_path != "":
		input.recorder = Replay.new()
		input.recorder.note = "Stanza di prova, sessione dal vivo"
	_reset()
	# --skip-to <tick>: un replay corre senza disegnare fino a quel tick (per guardare un momento).
	if input.mode == PlayerInput.Mode.REPLAY and Game.options.skip_to > 0:
		while tick < Game.options.skip_to and not input.replay_finished(tick):
			_sim_tick()
		_cam = _cam_target()


func _reset() -> void:
	_close_arena()
	arena_done = false
	_reset_hacking()
	player.place(_start.x, _start.y)
	player.facing = 1
	_sparks.clear()
	_cam = _cam_target()


func _physics_process(_delta: float) -> void:
	if input.mode == PlayerInput.Mode.LIVE:
		if Input.is_action_just_pressed(&"pause"):
			quit_to_title.emit()
			return
		if Input.is_action_just_pressed(&"room_reset"):
			_resets.append(tick)
			_reset()
		if Input.is_action_just_pressed(&"debug_boxes"):
			show_boxes = not show_boxes
	if input.mode == PlayerInput.Mode.REPLAY and input.replay_finished(tick):
		replay_done.emit()
		return
	_sim_tick()
	_tick_sparks()
	_follow_camera()
	_sync_visual()
	_overlay.tick()
	_view.queue_redraw()
	_hud.queue_redraw()
	for c in _view.get_children():
		if c is Node2D and c != _body:
			(c as Node2D).queue_redraw()


## Un tick della simulazione: ingressi, GIG, eventi. Il disegno resta fuori.
func _sim_tick() -> void:
	if input.mode == PlayerInput.Mode.REPLAY and (_replay_resets.has(float(tick)) or _replay_resets.has(tick)):
		_reset()
	var frame := input.next_frame(tick)
	tick += 1
	if arena_phase != ArenaPhase.NONE:
		_arena_tick(frame)
		return
	var hack_events := PackedStringArray()
	frame = _hack_tick(frame, hack_events)
	# Collegato al pannello, GIG alza il braccio cyber verso la cassetta.
	player.pose_override = &"hack" if hack_panel != "" else &""
	player.step(frame)
	for e in player.events:
		_on_event(e)
	for e in hack_events:
		_on_event(e)
	if player.py > grid.pixel_height() + 80:
		_reset()
	elif _arena_starts():
		_open_arena()


func _exit_tree() -> void:
	_save_recording()


func _save_recording() -> void:
	if input == null or input.recorder == null or _record_path == "" or input.recorder.length == 0:
		return
	input.recorder.start = {"x": _start.x, "resets": _resets}
	DirAccess.make_dir_recursive_absolute(_record_path.get_base_dir())
	if input.recorder.save_file(_record_path) == OK:
		print("Sessione salvata: %s (%d tick)" % [ProjectSettings.globalize_path(_record_path), input.recorder.length])
	input.recorder = null


# ------------------------------------------------------------------ telecamera

func _cam_target() -> Vector2:
	# Un po' avanti nella direzione dello sguardo, con GIG nel terzo basso dello schermo.
	return Vector2(player.px + player.facing * 45 - View.CX, player.py - 188)


func _follow_camera() -> void:
	if arena_phase != ArenaPhase.NONE:
		_arena_camera()
		return
	var t := _cam_target()
	_cam.x += (t.x - _cam.x) * 0.12
	# In verticale segue piano mentre GIG salta, deciso quando atterra o cade a lungo.
	var k := 0.18 if player.state != PlatformPlayer.State.AIR or player.vy > PlatformPlayer.to_sub(5.0) else 0.04
	_cam.y += (t.y - _cam.y) * k
	_cam.x = clampf(_cam.x, 0.0, float(grid.pixel_width() - View.W))
	_cam.y = clampf(_cam.y, float(-80), float(grid.pixel_height() - View.H))
	_view.position = -_cam.round()


# ------------------------------------------------------------------ disegno

func _sync_visual() -> void:
	# A telecamera inclinata la stanza dietro il pavimento si schiaccia verso la linea del pavimento.
	var s := 1.0 - TILT_SQUASH * tilt
	_room_node.scale = Vector2(1, s)
	_room_node.position = Vector2(0, _floor_y * (1.0 - s))
	_body.visible = arena == null
	if arena != null:
		arena.player.sync_visual()
		# Mentre la telecamera si inclina il livello non fa step(), che di solito ridisegna le ombre.
		arena.shadows.queue_redraw()
		return
	for gs: String in gates:
		var gt: Dictionary = gates[gs]
		gt["lift"] = move_toward(gt["lift"], 1.0 if gt["timer"] > 0 else 0.0, 1.0 / GATE_ANIM)
	if hack_panel != "" and tick % 3 == 0:
		# Le scintille sul pannello mentre il braccio lo forza.
		var fist := _cyber_fist()
		_spark(fist.x + _spark_rng.randf_range(-4, 4), fist.y - 6, _spark_rng.randf_range(-1.2, 1.2), -_spark_rng.randf_range(0.4, 1.6), _spark_rng.randi_range(8, 14), C_CYAN)
	var f := player.anim.frame()
	_body.region_rect = Rect2(f.rect)
	_body.offset = Vector2(-f.anchor)
	_body.scale = Vector2(player.facing, 1)
	_body.position = Vector2(player.sprite_anchor())


func _draw_back() -> void:
	_view.draw_rect(Rect2(_cam.x - 8, _cam.y - 8, View.W + 16, View.H + 16), C_BG)


func _draw_room() -> void:
	var v := _room_node
	var x0 := maxi(int(_cam.x) / SolidGrid.TILE - 1, 0)
	var x1 := mini(int(_cam.x + View.W) / SolidGrid.TILE + 1, grid.width - 1)
	# Con la stanza schiacciata dall'inclinazione si vedono un paio di file in più in alto.
	var y0 := maxi(int(_cam.y) / SolidGrid.TILE - 3, 0)
	var y1 := mini(int(_cam.y + View.H) / SolidGrid.TILE + 1, grid.height - 1)
	# Una riga ogni metro (3 blocchi), per leggere le misure a occhio.
	var t := SolidGrid.TILE
	for cx in range(x0, x1 + 1):
		if cx % 3 == 0:
			v.draw_rect(Rect2(cx * t, y0 * t, 1, (y1 - y0 + 1) * t), C_GRID)
	for cy in range(y0, y1 + 1):
		if cy % 3 == 1:
			v.draw_rect(Rect2(x0 * t, cy * t, (x1 - x0 + 1) * t, 1), C_GRID)
	for cy in range(y0, y1 + 1):
		for cx in range(x0, x1 + 1):
			if _gate_cells.has(Vector2i(cx, cy)):
				continue
			match grid.cell(cx, cy):
				SolidGrid.Cell.SOLID:
					v.draw_rect(Rect2(cx * t, cy * t, t, t), C_SOLID)
					if grid.cell(cx, cy - 1) != SolidGrid.Cell.SOLID:
						v.draw_rect(Rect2(cx * t, cy * t, t, 2), C_SOLID_TOP)
				SolidGrid.Cell.THIN:
					v.draw_rect(Rect2(cx * t, cy * t, t, 4), C_THIN)
					v.draw_rect(Rect2(cx * t, cy * t, t, 1), C_SOLID_TOP)
	_draw_hacking(v)
	if show_boxes and arena == null:
		var r := Rect2(player.left(), player.top(), moves.body_width, player.height)
		v.draw_rect(Rect2(r.position, Vector2(r.size.x, 1)), C_BOX)
		v.draw_rect(Rect2(r.position + Vector2(0, r.size.y - 1), Vector2(r.size.x, 1)), C_BOX)
		v.draw_rect(Rect2(r.position, Vector2(1, r.size.y)), C_BOX)
		v.draw_rect(Rect2(r.position + Vector2(r.size.x - 1, 0), Vector2(1, r.size.y)), C_BOX)


## I cartelli non si schiacciano con la stanza (il testo in pixel verrebbe storto): si sposta
## solo la loro altezza, come i blocchi.
func _draw_signs(v: Node2D) -> void:
	var s := 1.0 - TILT_SQUASH * tilt
	for k: String in SIGNS:
		if not grid.marks.has(k):
			continue
		var p: Vector2i = grid.marks[k][0]
		if p.x < _cam.x - 250 or p.x > _cam.x + View.W + 250:
			continue
		var lines: Array = SIGNS[k]
		var y := roundf(_floor_y - (_floor_y - (p.y - 150)) * s)
		UiFont.draw_text(v, Vector2(p.x, y), str(lines[0]), C_TEXT, 1, 1)
		UiFont.draw_text(v, Vector2(p.x, y + 12), str(lines[1]), C_DIM, 1, 1, Color(0, 0, 0, 0), UiFont.SHADOW, true)


## Il pavimento in profondità dell'arena: si apre sotto la linea del pavimento mentre la telecamera
## si inclina, con una linea ogni metro che si allarga verso chi guarda.
func _draw_floor() -> void:
	var v := _floor_node
	if tilt > 0.0:
		var top := float(_floor_y)
		var depth := roundf((View.H - ARENA_BAND.x + 8.0) * tilt)
		var band := roundf((ARENA_BAND.y - ARENA_BAND.x) * tilt)
		var x0 := _cam.x - 8.0
		var w := View.W + 16.0
		v.draw_rect(Rect2(x0, top, w, depth), C_FLOOR)
		var vp_x := _cam.x + View.CX
		var m := float(View.PPM)
		var lx := floorf((x0 - 200.0) / m) * m
		while lx < x0 + w + 200.0:
			for r in int(band):
				var xr := vp_x + (lx - vp_x) * (1.0 + r / PERSP)
				v.draw_rect(Rect2(roundf(xr), top + r, 1, 1), C_FLOOR_LINE)
			lx += m
		# Linee di traverso: più fitte in fondo, più larghe davanti.
		for k: float in [0.2, 0.43, 0.7]:
			v.draw_rect(Rect2(x0, roundf(top + band * k), w, 1), C_FLOOR_LINE)
		v.draw_rect(Rect2(x0, top, w, 2), C_SOLID_TOP)
		# Il bordo davanti della fascia calpestabile, poi il marciapiede scuro fino al fondo dello schermo.
		if depth > band:
			v.draw_rect(Rect2(x0, top + band, w, depth - band), C_KERB)
			v.draw_rect(Rect2(x0, top + band, w, 1), C_FLOOR_LINE)
	_draw_signs(v)


func _draw_hud() -> void:
	var h := _hud
	if arena_phase != ArenaPhase.NONE:
		# Nell'arena c'è l'interfaccia dello slice, con la vita di GIG e del nemico.
		return
	h.draw_rect(Rect2(0, 0, View.W, 15), Color(0, 0, 0, 0.55))
	UiFont.draw_text(h, Vector2(4, 2), "STANZA DI PROVA", C_CYAN)
	var st := "COLLEGATO" if hack_panel != "" else player.state_name()
	UiFont.draw_text(h, Vector2(View.W - 4, 2), st, C_CYAN if hack_panel != "" else C_TEXT, 1, 2)
	var sub := float(PlatformPlayer.SUB)
	var info := "vel %.1f · %.1f px/tick   salto %d px (%.2f m)   in aria %d tick   spinte %d" % [
		player.vx / sub, player.vy / sub, player.last_peak, player.last_peak / float(View.PPM), player.air_ticks, player.boosts_left]
	h.draw_rect(Rect2(0, View.H - 15, View.W, 15), Color(0, 0, 0, 0.55))
	UiFont.draw_text(h, Vector2(4, View.H - 13), info, C_DIM, 1, 0, Color(0, 0, 0, 0), UiFont.SHADOW, true)


# ------------------------------------------------------------------ arena

## Si entra nell'arena una volta per giro, coi piedi sul pavimento oltre il punto d'ingresso e
## dentro lo schermo dell'arena (partendo più avanti con --start-x l'arena non si apre).
func _arena_starts() -> bool:
	if arena_done or _arena_cam_x < 0 or player.px < _arena_trigger_x or player.py != _floor_y:
		return false
	if player.px > _arena_cam_x + View.W - 40:
		return false
	return player.state in [PlatformPlayer.State.GROUND, PlatformPlayer.State.CROUCH, PlatformPlayer.State.SLIDE]


func _arena_data() -> Dictionary:
	return {
		"id": "stanza_arena",
		"width": grid.pixel_width(),
		"floor_band": [ARENA_BAND.x, ARENA_BAND.y],
		"waves": [{"id": "arena_prova", "camera_x": _arena_cam_x, "music_layer": "arena", "spawns": ARENA_SPAWNS}],
	}


func _open_arena() -> void:
	arena = Level.new()
	arena.configure({"seed": 1, "input": input, "embedded": true, "auto_tick": false, "card": false, "sound": sound,
		"data": _arena_data(), "start_x": float(player.px), "start_y": ARENA_BAND.x})
	# Il bordo dietro della fascia sta sulla linea del pavimento del platform.
	arena.position = Vector2(0, _floor_y - ARENA_BAND.x)
	_view.add_child(arena)
	arena.camera.min_x = _arena_cam_x
	arena.camera.max_x = _arena_cam_x
	arena.camera.x = _arena_cam_x
	var g := arena.player
	g.facing = player.facing
	g.play_anim(&"walk")
	arena_phase = ArenaPhase.ENTER
	_arena_t = 0
	_cam_from = _cam
	_sparks.clear()
	if pilot != null:
		pilot.arena = arena


func _arena_tick(frame: InputFrame) -> void:
	var g := arena.player
	_arena_t += 1
	match arena_phase:
		ArenaPhase.ENTER:
			# GIG fa qualche passo dentro la fascia mentre la telecamera si inclina; gli ingressi aspettano.
			var k := float(_arena_t) / TILT_IN
			tilt = _ease(k)
			g.py = ARENA_BAND.x + ENTRY_DEPTH * k
			g.anim.advance()
			if _arena_t >= TILT_IN:
				g.set_state(Fighter.State.IDLE, &"idle")
				arena_phase = ArenaPhase.FIGHT
				_arena_t = 0
		ArenaPhase.FIGHT:
			arena.step(frame)
			# Zona liberata (il livello ha già acceso VAI): si esce appena GIG è libero e coi piedi a terra.
			if arena.waves_cleared > 0 and arena.active_wave.is_empty() and g.is_free() and g.ph <= 0.0:
				arena_phase = ArenaPhase.LEAVE
				_arena_t = 0
				_leave_from_py = g.py
				_cam_from = _cam
				g.play_anim(&"walk")
		ArenaPhase.LEAVE:
			# GIG torna sul bordo dietro e la telecamera torna laterale.
			var k := float(_arena_t) / TILT_OUT
			tilt = 1.0 - _ease(k)
			g.py = lerpf(_leave_from_py, ARENA_BAND.x, k)
			g.anim.advance()
			arena.overlay.tick()
			if _arena_t >= TILT_OUT:
				player.place(roundi(g.px), _floor_y)
				player.facing = g.facing
				_overlay.go_ticks = arena.overlay.go_ticks
				arena_done = true
				_close_arena()


## Toglie l'arena, a fine scontro o quando si ricomincia.
func _close_arena() -> void:
	if arena != null:
		# Ricominciando a metà scontro, lo strato "arena" della musica resterebbe acceso.
		if sound and not arena.active_wave.is_empty():
			Music.set_layer(&"arena", false)
		_view.remove_child(arena)
		arena.queue_free()
	arena = null
	arena_phase = ArenaPhase.NONE
	tilt = 0.0
	if pilot != null:
		pilot.arena = null


func _arena_camera() -> void:
	var lock := Vector2(_arena_cam_x, _floor_y - ARENA_BAND.x)
	match arena_phase:
		ArenaPhase.ENTER:
			_cam = _cam_from.lerp(lock, _ease(float(_arena_t) / TILT_IN))
		ArenaPhase.FIGHT:
			_cam = lock
		ArenaPhase.LEAVE:
			var g := arena.player
			var back := Vector2(g.px + g.facing * 45 - View.CX, _floor_y - 188)
			back.x = clampf(back.x, 0.0, float(grid.pixel_width() - View.W))
			back.y = clampf(back.y, -80.0, float(grid.pixel_height() - View.H))
			_cam = lock.lerp(back, _ease(float(_arena_t) / TILT_OUT))
	_view.position = -_cam.round() + Vector2(arena.camera.shake)


static func _ease(k: float) -> float:
	k = clampf(k, 0.0, 1.0)
	return k * k * (3.0 - 2.0 * k)


# ------------------------------------------------------------------ hacking

## Le celle dei cancelli, dai simboli della mappa: chiuse (piene) all'inizio.
func _build_gates() -> void:
	gates.clear()
	_gate_cells.clear()
	for id: String in PANELS:
		var s: String = PANELS[id]["gate"]
		if not grid.marks.has(s):
			continue
		var cells: Array[Vector2i] = []
		var r := Rect2i()
		for m: Vector2i in grid.marks[s]:
			var c := Vector2i((m.x - SolidGrid.TILE / 2) / SolidGrid.TILE, m.y / SolidGrid.TILE - 1)
			cells.append(c)
			_gate_cells[c] = true
			var cr := Rect2i(c * SolidGrid.TILE, Vector2i(SolidGrid.TILE, SolidGrid.TILE))
			r = cr if r.size == Vector2i.ZERO else r.merge(cr)
		gates[s] = {"cells": cells, "rect": r, "timer": 0, "lift": 0.0}
	_reset_hacking()


func _reset_hacking() -> void:
	hack_panel = ""
	hack_t = 0
	hacks_done.clear()
	for s: String in gates:
		gates[s]["timer"] = 0
		gates[s]["lift"] = 0.0
		_set_gate(s, false)


func _set_gate(s: String, open: bool) -> void:
	for c: Vector2i in gates[s]["cells"]:
		grid.set_cell(c.x, c.y, SolidGrid.Cell.EMPTY if open else SolidGrid.Cell.SOLID)


func _panel_pos(id: String) -> Vector2i:
	return grid.marks[id][0]


## Dove deve stare GIG per avere il pugno cyber sotto la presa della centralina, col verso di adesso.
func hack_spot(id: String) -> int:
	return _panel_pos(id).x - player.facing * HACK_FIST_X


## Il pannello a portata di GIG (sotto la centralina, sullo stesso piano), o "".
func panel_in_reach() -> String:
	for id: String in PANELS:
		if not grid.marks.has(id) or not gates.has(PANELS[id]["gate"]):
			continue
		if absi(player.px - hack_spot(id)) <= HACK_REACH and player.py == _panel_pos(id).y:
			return id
	return ""


## La scatola della centralina, in pixel del mondo.
func _panel_rect(id: String) -> Rect2:
	var m := _panel_pos(id)
	return Rect2(m.x - PANEL_W / 2, m.y - PANEL_BOTTOM - PANEL_H, PANEL_W, PANEL_H)


## Un tick di hacking, prima che GIG si muova: conta il tempo dei cancelli aperti e quello del
## collegamento. Collegato, GIG non cammina (riceve un ingresso vuoto) e si sistema col pugno sotto
## la presa; SALTO, lasciare SU o allontanarsi staccano il contatto. Restituisce l'ingresso da dare a GIG.
func _hack_tick(frame: InputFrame, events: PackedStringArray) -> InputFrame:
	for s: String in gates:
		var gt: Dictionary = gates[s]
		if gt["timer"] > 0:
			gt["timer"] -= 1
			if gt["timer"] == 0:
				# Il cancello non si chiude addosso a GIG: aspetta che sia passato.
				var body := Rect2i(player.left(), player.top(), player.right() - player.left(), player.height)
				if body.intersects(gt["rect"]):
					gt["timer"] = 1
				else:
					_set_gate(s, false)
					events.append("gate_close")
	var on_ground := player.state == PlatformPlayer.State.GROUND
	if hack_panel == "":
		var id := panel_in_reach()
		if id != "" and on_ground and frame.is_held(InputFrame.UP) and gates[PANELS[id]["gate"]]["timer"] == 0:
			hack_panel = id
			hack_t = 0
			events.append("hack_start")
	if hack_panel == "":
		return frame
	if not frame.is_held(InputFrame.UP) or frame.was_pressed(InputFrame.JUMP) or not on_ground or panel_in_reach() != hack_panel:
		hack_panel = ""
		hack_t = 0
		events.append("hack_cut")
		return frame
	hack_t += 1
	# Il passo che manca per arrivare col pugno sotto la presa.
	var dx := signi(hack_spot(hack_panel) - player.px)
	if dx != 0 and not grid.rect_hits_solid(player.left() + dx, player.top(), player.right() + dx, player.py):
		player.px += dx
	if hack_t >= HACK_TICKS:
		var s: String = PANELS[hack_panel]["gate"]
		gates[s]["timer"] = int(PANELS[hack_panel]["open"])
		_set_gate(s, true)
		hacks_done[hack_panel] = int(hacks_done.get(hack_panel, 0)) + 1
		last_hacked = hack_panel
		hack_panel = ""
		hack_t = 0
		events.append("hack_done")
	return InputFrame.new()


## Impronta della stanza per i test: GIG, hacking e cancelli.
func state_hash() -> int:
	var g: Array = []
	for s: String in gates:
		g.append(gates[s]["timer"])
	return hash([player.state_hash(), hack_panel, hack_t, g, hacks_done])


## I pannelli sul muro di fondo e i cancelli, con il conto alla rovescia.
func _draw_hacking(v: Node2D) -> void:
	for id: String in PANELS:
		if not grid.marks.has(id) or not gates.has(PANELS[id]["gate"]):
			continue
		var m := _panel_pos(id)
		if m.x < _cam.x - 60 or m.x > _cam.x + View.W + 60:
			continue
		_draw_panel(v, id, gates[PANELS[id]["gate"]])
	for s: String in gates:
		var gt: Dictionary = gates[s]
		var g: Rect2i = gt["rect"]
		if g.end.x < _cam.x - 20 or g.position.x > _cam.x + View.W + 20:
			continue
		# Il cancello sale verso il soffitto: resta visibile la parte che non è ancora rientrata.
		var h := roundf(g.size.y * (1.0 - float(gt["lift"])))
		if h > 0:
			v.draw_rect(Rect2(g.position.x, g.end.y - h, g.size.x, h), C_GATE_DARK)
			var bx := g.position.x + 3
			while bx < g.end.x - 2:
				v.draw_rect(Rect2(bx, g.end.y - h, 3, h), C_GATE)
				bx += 8
			for k in range(0, int(h), 40):
				v.draw_rect(Rect2(g.position.x, g.end.y - h + k, g.size.x, 2), C_GATE_DARK.darkened(0.3))
			v.draw_rect(Rect2(g.position.x, g.end.y - 2, g.size.x, 2), C_GATE_DARK.darkened(0.3))
		if gt["timer"] > 0:
			# Il conto alla rovescia all'altezza della testa, rosso nell'ultimo secondo.
			var cx := g.position.x + g.size.x / 2.0
			var secs := float(gt["timer"]) / Engine.physics_ticks_per_second
			var col := C_BOX if gt["timer"] <= 60 else C_TEXT
			if gt["timer"] > 60 or (gt["timer"] / 6) % 2 == 0:
				UiFont.draw_text(v, Vector2(cx, g.end.y - 140), "%.1f" % secs, col, 2, 1, C_PANEL)
			var full := float(_open_ticks(s))
			var bw := roundf(30.0 * gt["timer"] / full)
			v.draw_rect(Rect2(cx - 15, g.end.y - 114, 30, 3), C_PANEL)
			v.draw_rect(Rect2(cx - 15, g.end.y - 114, bw, 3), col)


func _open_ticks(gate: String) -> int:
	for id: String in PANELS:
		if PANELS[id]["gate"] == gate:
			return int(PANELS[id]["open"])
	return 1


## Una centralina di SIDERA: scatola d'acciaio con i bordi in rilievo, la targa, lo schermo, il led,
## le feritoie, la fascia di pericolo e sotto la presa dove si appoggia il pugno; un condotto la porta
## al soffitto. Lo schermo dice lo stato: in attesa, forzata (codici che scorrono e barra), aperta.
func _draw_panel(v: Node2D, id: String, gt: Dictionary) -> void:
	var r := _panel_rect(id)
	var x0 := r.position.x
	var y0 := r.position.y
	var w := r.size.x
	var h := r.size.y
	var hacking := hack_panel == id
	var open: bool = gt["timer"] > 0
	# Il condotto, dal tetto della scatola al primo pieno sopra, con le staffe ogni 40 px.
	var px := x0 + w - 11
	var cy := int(y0) / SolidGrid.TILE - 1
	while cy > 0 and grid.cell(int(px) / SolidGrid.TILE, cy) != SolidGrid.Cell.SOLID:
		cy -= 1
	var top := float((cy + 1) * SolidGrid.TILE)
	v.draw_rect(Rect2(px, top, 5, y0 - top), C_CASE_LO)
	v.draw_rect(Rect2(px + 1, top, 2, y0 - top), C_CASE)
	v.draw_rect(Rect2(px + 1, top, 1, y0 - top), C_CASE_HI.darkened(0.2))
	var by := y0 - 14
	while by > top + 4:
		v.draw_rect(Rect2(px - 1, by, 7, 3), C_CASE_LO)
		v.draw_rect(Rect2(px - 1, by, 7, 1), C_CASE)
		by -= 40
	# Ombra sul muro e scatola, coi bordi in rilievo e le viti.
	v.draw_rect(Rect2(x0 + 2, y0 + 2, w, h), Color(0, 0, 0, 0.35))
	v.draw_rect(r, C_CASE)
	v.draw_rect(Rect2(x0, y0, w, 1), C_CASE_HI)
	v.draw_rect(Rect2(x0, y0, 1, h), C_CASE_HI)
	v.draw_rect(Rect2(x0, y0 + h - 1, w, 1), C_CASE_LO)
	v.draw_rect(Rect2(x0 + w - 1, y0, 1, h), C_CASE_LO)
	for sp: Vector2 in [Vector2(2, 2), Vector2(w - 4, 2), Vector2(2, h - 10), Vector2(w - 4, h - 10)]:
		v.draw_rect(Rect2(x0 + sp.x, y0 + sp.y, 2, 2), C_CASE_LO)
		v.draw_rect(Rect2(x0 + sp.x, y0 + sp.y, 1, 1), C_CASE_HI)
	# La targa con la scritta.
	v.draw_rect(Rect2(x0 + 3, y0 + 3, w - 6, 10), C_CASE_LO)
	UiFont.draw_text(v, Vector2(x0 + w / 2.0, y0 + 3), "SIDERA", C_CASE_HI, 1, 1, Color(0, 0, 0, 0), Color(0, 0, 0, 0))
	# Lo schermo, con le righe.
	var sr := Rect2(x0 + 4, y0 + 15, w - 8, 14)
	v.draw_rect(Rect2(sr.position - Vector2(1, 1), sr.size + Vector2(2, 2)), C_CASE_LO)
	var glow := C_OK if open else C_CYAN
	v.draw_rect(sr, C_SCREEN.lerp(glow, 0.14 if (open or hacking) else 0.05))
	if open:
		UiFont.draw_text(v, Vector2(sr.get_center().x, sr.position.y + 3), "OK", C_OK, 1, 1, Color(0, 0, 0, 0), Color(0, 0, 0, 0))
	elif hacking:
		# Codici che scorrono e la barra di avanzamento.
		for row in 3:
			for col in 7:
				if ((col * 7 + row * 13 + tick / 3 + id.unicode_at(0)) * 31) % 7 < 3:
					v.draw_rect(Rect2(sr.position.x + 2 + col * 4, sr.position.y + 2 + row * 3, 3, 1), C_CYAN.darkened(0.25))
		v.draw_rect(Rect2(sr.position.x + 1, sr.end.y - 3, sr.size.x - 2, 2), C_SCREEN.lerp(C_CYAN, 0.2))
		v.draw_rect(Rect2(sr.position.x + 1, sr.end.y - 3, roundf((sr.size.x - 2) * hack_t / HACK_TICKS), 2), C_CYAN)
	else:
		# In attesa: un prompt e il cursore che lampeggia.
		v.draw_rect(Rect2(sr.position.x + 2, sr.position.y + 3, 2, 1), C_CYAN.darkened(0.4))
		v.draw_rect(Rect2(sr.position.x + 5, sr.position.y + 3, 12, 1), C_CYAN.darkened(0.55))
		v.draw_rect(Rect2(sr.position.x + 2, sr.position.y + 7, 8, 1), C_CYAN.darkened(0.55))
		if (tick / 20) % 2 == 0:
			v.draw_rect(Rect2(sr.position.x + 11, sr.position.y + 6, 3, 2), C_CYAN.darkened(0.2))
	for y in range(int(sr.position.y) + 1, int(sr.end.y), 2):
		v.draw_rect(Rect2(sr.position.x, y, sr.size.x, 1), Color(0, 0, 0, 0.25))
	# Feritoie e led.
	for i in 3:
		v.draw_rect(Rect2(x0 + 5, y0 + 32 + i * 2, 12, 1), C_CASE_LO)
	var led := C_LED_RED
	if open:
		led = C_OK
	elif hacking:
		led = C_CYAN if (tick / 3) % 2 == 0 else C_CASE_LO
	elif (tick / 45) % 3 == 2:
		led = C_LED_RED.darkened(0.6)
	v.draw_rect(Rect2(x0 + w - 10, y0 + 32, 4, 4), C_CASE_LO)
	v.draw_rect(Rect2(x0 + w - 9, y0 + 33, 2, 2), led)
	# La fascia di pericolo in fondo.
	var hy := y0 + h - 7
	for i in int(w) - 4:
		for j in 4:
			v.draw_rect(Rect2(x0 + 2 + i, hy + j, 1, 1), C_HAZARD if ((i + j) / 3) % 2 == 0 else C_CASE_LO)
	# La presa sotto la scatola, dove si appoggia il pugno.
	var cx := r.get_center().x
	v.draw_rect(Rect2(cx - 6, y0 + h, 12, 3), C_CASE_LO)
	v.draw_rect(Rect2(cx - 4, y0 + h + 1, 8, 1), C_CYAN if hacking else C_CYAN.darkened(0.6))
	if hack_panel == "" and not open and panel_in_reach() == id:
		UiFont.draw_text(v, Vector2(cx, y0 - 12), "SU", C_CYAN, 1, 1)


## Il pugno del braccio cyber (il sinistro, decisione 21) nel fotogramma di adesso, in pixel del mondo.
func _cyber_fist() -> Vector2:
	var f := Vector2i(HACK_FIST_X, -118)
	if player.anim != null and player.anim.frame().points.has("fist_l"):
		f = player.anim.frame().points["fist_l"]
	var a := player.sprite_anchor()
	return Vector2(a.x + player.facing * f.x, a.y + f.y)


## Il contatto: il pugno appoggiato alla presa, un bagliore e piccoli archi fra i due, e l'energia
## che sale lungo il braccio cyber a impulsi.
func _draw_contact(n: Node2D) -> void:
	var fist := _cyber_fist()
	var pr := _panel_rect(hack_panel)
	var plug := Vector2(pr.get_center().x, pr.end.y + 2)
	var pulse := 0.5 + 0.5 * sin(tick * 0.6)
	n.draw_circle(plug, 9.0, Color(C_CYAN, 0.10 + 0.08 * pulse))
	n.draw_circle(plug, 5.0, Color(C_CYAN, 0.22 + 0.12 * pulse))
	# Archi: due zigzag corti fra il pugno e la presa, che cambiano ogni due tick.
	for k in 2:
		var a := fist + Vector2(-3 + k * 6, -5)
		var prev := a
		for i in range(1, 4):
			var p := a.lerp(plug, float(i) / 3.0)
			if i < 3:
				p.x += float(((tick / 2 + i * 5 + k * 3) % 5) - 2)
			n.draw_line(prev.round(), p.round(), C_TEXT if i == 2 else C_CYAN, 1.0)
			prev = p
	# Impulsi lungo l'avambraccio, dal gomito al pugno.
	var elbow := fist + Vector2(-player.facing * 3, 34)
	for k in 4:
		var u := float((tick * 2 + k * 9) % 36) / 36.0
		var p := elbow.lerp(fist, u).round()
		n.draw_rect(Rect2(p - Vector2(2, 2), Vector2(4, 4)), Color(C_CYAN, 0.35))
		n.draw_rect(Rect2(p - Vector2(1, 1), Vector2(2, 2)), C_TEXT if u > 0.8 else C_CYAN)


# ------------------------------------------------------------------ effetti

func _on_event(e: String) -> void:
	match e:
		"spinta":
			# La scarica del braccio verso il basso: un ventaglio di scintille cyan.
			for i in 14:
				var a := _spark_rng.randf_range(0.25, 0.75) * PI
				var s := _spark_rng.randf_range(1.2, 3.2)
				_spark(player.px, player.py - 5, cos(a) * s * 1.25, sin(a) * s * 1.25, _spark_rng.randi_range(10, 20), C_CYAN)
		"land":
			for i in 6:
				var dir := -1.0 if i % 2 == 0 else 1.0
				_spark(player.px + dir * 8, player.py - 1, dir * _spark_rng.randf_range(0.6, 1.6), -_spark_rng.randf_range(0.1, 0.6), 10, C_DIM)
		"scatto":
			# Il colpo del braccio all'indietro: lo scatto spinge in avanti.
			for i in 12:
				var a := _spark_rng.randf_range(-0.35, 0.35) + (PI if player.facing > 0 else 0.0)
				var s := _spark_rng.randf_range(1.5, 3.5)
				_spark(player.px - player.facing * 8, player.py - 55, cos(a) * s * 1.25, sin(a) * s * 1.25, _spark_rng.randi_range(8, 16), C_CYAN)
		"walljump", "wallrun":
			# Il colpo contro il muro, dal lato del muro.
			var wx := player.px + player.wall_dir * 13
			for i in 10:
				var a := _spark_rng.randf_range(-0.6, 0.6) + (PI if player.wall_dir > 0 else 0.0)
				var s := _spark_rng.randf_range(1.0, 2.8)
				_spark(wx, player.py - 38, cos(a) * s, sin(a) * s, _spark_rng.randi_range(8, 14), C_CYAN)
		"wall", "wall_spark":
			# Il braccio piantato nel muro che frena: poche scintille verso l'alto.
			var wx2 := player.px + player.wall_dir * 13
			for i in (6 if e == "wall" else 2):
				_spark(wx2, player.py - 72, -player.wall_dir * _spark_rng.randf_range(0.2, 1.0), -_spark_rng.randf_range(0.5, 1.8), 10, C_CYAN)
		"hack_done":
			# Il pannello cede: una scarica dal pannello.
			var m := _panel_rect(last_hacked).get_center()
			for i in 16:
				var a := _spark_rng.randf_range(0.0, TAU)
				var s := _spark_rng.randf_range(0.8, 2.6)
				_spark(m.x, m.y, cos(a) * s, sin(a) * s - 0.8, _spark_rng.randi_range(10, 20), C_OK if i % 3 == 0 else C_CYAN)
		"hack_cut":
			for i in 4:
				_spark(_cyber_fist().x, _cyber_fist().y, _spark_rng.randf_range(-1.0, 1.0), -_spark_rng.randf_range(0.2, 1.0), 8, C_DIM)
		"slide":
			for i in 5:
				_spark(player.px - player.facing * 10, player.py - 2, -player.facing * _spark_rng.randf_range(0.5, 1.5), -_spark_rng.randf_range(0.2, 0.8), 12, C_DIM)


func _spark(x: float, y: float, sx: float, sy: float, life: int, color: Color) -> void:
	_sparks.append([x, y, sx, sy, life, life, color])


func _tick_sparks() -> void:
	var keep: Array = []
	for s: Array in _sparks:
		s[0] += s[2]
		s[1] += s[3]
		s[3] += 0.12
		s[4] -= 1
		if s[4] > 0:
			keep.append(s)
	_sparks = keep


func _draw_fx(n: Node2D) -> void:
	if hack_panel != "" and arena == null:
		_draw_contact(n)
	for s: Array in _sparks:
		var a := float(s[4]) / float(s[5])
		# Le scintille cyan sbiadiscono nel bianco, come una scarica.
		var c: Color = s[6] if a > 0.4 else C_TEXT
		c.a = a
		n.draw_rect(Rect2(roundf(s[0]), roundf(s[1]), 1 if a < 0.5 else 2, 1 if a < 0.5 else 2), c)
