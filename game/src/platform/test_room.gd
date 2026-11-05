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
	"f": ["ARENA", "il passaggio all'arena arriva nella prossima tappa"],
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

var grid: SolidGrid
var player: PlatformPlayer
var input: PlayerInput
var pilot: RoomPilot
var moves: PlatformMoves
var tick: int = 0
var show_boxes: bool = false

var _start: Vector2i = Vector2i(100, 380)
## Tick in cui si è premuto R (ricomincia): fanno parte della sessione registrata.
var _resets: Array = []
var _replay_resets: Array = []
var _record_path: String = ""
var _view: Node2D
var _body: Sprite2D
var _hud: Control
var _cam: Vector2 = Vector2.ZERO
## Scintille della Spinta e degli atterraggi: [x, y, vx, vy, vita, vita iniziale, colore]. Solo disegno.
var _sparks: Array = []
var _spark_rng := RandomNumberGenerator.new()


func configure(opts: Dictionary) -> void:
	input = opts.get("input", null)
	pilot = opts.get("pilot", null)
	_record_path = str(opts.get("record", ""))
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
	_spark_rng.seed = 7
	# La musica del livello, se il laboratorio ha i brani (non tocca la simulazione).
	Music.duck(false)
	Music.play(&"stage1")
	_view = Node2D.new()
	_view.draw.connect(_draw_room)
	add_child(_view)
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
	player.step(frame)
	for e in player.events:
		_on_event(e)
	if player.py > grid.pixel_height() + 80:
		_reset()


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
	var f := player.anim.frame()
	_body.region_rect = Rect2(f.rect)
	_body.offset = Vector2(-f.anchor)
	_body.scale = Vector2(player.facing, 1)
	_body.position = Vector2(player.sprite_anchor())


func _draw_room() -> void:
	var v := _view
	var x0 := maxi(int(_cam.x) / SolidGrid.TILE - 1, 0)
	var x1 := mini(int(_cam.x + View.W) / SolidGrid.TILE + 1, grid.width - 1)
	var y0 := maxi(int(_cam.y) / SolidGrid.TILE - 1, 0)
	var y1 := mini(int(_cam.y + View.H) / SolidGrid.TILE + 1, grid.height - 1)
	v.draw_rect(Rect2(_cam.x - 8, _cam.y - 8, View.W + 16, View.H + 16), C_BG)
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
	for k: String in SIGNS:
		if not grid.marks.has(k):
			continue
		var p: Vector2i = grid.marks[k][0]
		if p.x < _cam.x - 250 or p.x > _cam.x + View.W + 250:
			continue
		var lines: Array = SIGNS[k]
		UiFont.draw_text(v, Vector2(p.x, p.y - 150), str(lines[0]), C_TEXT, 1, 1)
		UiFont.draw_text(v, Vector2(p.x, p.y - 138), str(lines[1]), C_DIM, 1, 1, Color(0, 0, 0, 0), UiFont.SHADOW, true)
	if show_boxes:
		var r := Rect2(player.left(), player.top(), moves.body_width, player.height)
		v.draw_rect(Rect2(r.position, Vector2(r.size.x, 1)), C_BOX)
		v.draw_rect(Rect2(r.position + Vector2(0, r.size.y - 1), Vector2(r.size.x, 1)), C_BOX)
		v.draw_rect(Rect2(r.position, Vector2(1, r.size.y)), C_BOX)
		v.draw_rect(Rect2(r.position + Vector2(r.size.x - 1, 0), Vector2(1, r.size.y)), C_BOX)


func _draw_hud() -> void:
	var h := _hud
	h.draw_rect(Rect2(0, 0, View.W, 15), Color(0, 0, 0, 0.55))
	UiFont.draw_text(h, Vector2(4, 2), "STANZA DI PROVA", C_CYAN)
	UiFont.draw_text(h, Vector2(View.W - 4, 2), player.state_name(), C_TEXT, 1, 2)
	var sub := float(PlatformPlayer.SUB)
	var info := "vel %.1f · %.1f px/tick   salto %d px (%.2f m)   in aria %d tick   spinte %d" % [
		player.vx / sub, player.vy / sub, player.last_peak, player.last_peak / float(View.PPM), player.air_ticks, player.boosts_left]
	h.draw_rect(Rect2(0, View.H - 15, View.W, 15), Color(0, 0, 0, 0.55))
	UiFont.draw_text(h, Vector2(4, View.H - 13), info, C_DIM, 1, 0, Color(0, 0, 0, 0), UiFont.SHADOW, true)


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
