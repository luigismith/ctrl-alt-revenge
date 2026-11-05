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
	"g": ["FINE DELLA STANZA", "R o SELECT per ricominciare"],
}

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
## Gli Esattori dell'arena (decisione 63): due rider, che arrivano in gruppo, e poi il bruto dello
## slice, che diventerà l'esattore di professione quando avrà l'intelligenza nuova.
const ARENA_SPAWNS := [
	{"type": "rider", "delay": 30, "side": 1, "y": 205},
	{"type": "rider", "delay": 55, "side": -1, "y": 240},
	{"type": "thug_bruiser", "delay": 320, "side": 1, "y": 243},
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
	player.step(frame)
	for e in player.events:
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
			match grid.cell(cx, cy):
				SolidGrid.Cell.SOLID:
					v.draw_rect(Rect2(cx * t, cy * t, t, t), C_SOLID)
					if grid.cell(cx, cy - 1) != SolidGrid.Cell.SOLID:
						v.draw_rect(Rect2(cx * t, cy * t, t, 2), C_SOLID_TOP)
				SolidGrid.Cell.THIN:
					v.draw_rect(Rect2(cx * t, cy * t, t, 4), C_THIN)
					v.draw_rect(Rect2(cx * t, cy * t, t, 1), C_SOLID_TOP)
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
	UiFont.draw_text(h, Vector2(View.W - 4, 2), player.state_name(), C_TEXT, 1, 2)
	var sub := float(PlatformPlayer.SUB)
	var info := "vel %.1f · %.1f px/tick   salto %d px (%.2f m)   in aria %d tick   spinte %d" % [
		player.vx / sub, player.vy / sub, player.last_peak, player.last_peak / float(View.PPM), player.air_ticks, player.boosts_left]
	h.draw_rect(Rect2(0, View.H - 15, View.W, 15), Color(0, 0, 0, 0.55))
	UiFont.draw_text(h, Vector2(4, View.H - 13), info, C_DIM, 1, 0, Color(0, 0, 0, 0), UiFont.SHADOW, true)


# ------------------------------------------------------------------ arena

## Si entra nell'arena una volta per giro, coi piedi sul pavimento oltre il punto d'ingresso.
func _arena_starts() -> bool:
	if arena_done or _arena_cam_x < 0 or player.px < _arena_trigger_x or player.py != _floor_y:
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
	for s: Array in _sparks:
		var a := float(s[4]) / float(s[5])
		# Le scintille cyan sbiadiscono nel bianco, come una scarica.
		var c: Color = s[6] if a > 0.4 else C_TEXT
		c.a = a
		n.draw_rect(Rect2(roundf(s[0]), roundf(s[1]), 1 if a < 0.5 else 2, 1 if a < 0.5 else 2), c)
