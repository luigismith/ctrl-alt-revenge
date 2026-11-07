class_name ScenePlayer
extends Node
## Il lettore delle scene nel motore (decisione 68): recita il copione di una SceneData con le comparse,
## le inquadrature (stacchi, movimenti di macchina, zoom interi), le bande nere, i primi piani e le
## battute che avanzano a pressione, come in Celeste. Un filmato ha sempre una regia vera, mai gameplay
## che va da solo (Luigi, 6 novembre 2026).
##
## È solo disegno. La simulazione resta ferma finché il copione recita: l'esito della scena (dove
## finiscono gli attori, il segno del laser, la pioggia) l'ha già applicato chi la ospita, nel tick in cui
## la scena è partita. Così replay e test non cambiano, con la scena o senza.
##
## I passaggi fra gioco e filmato (Luigi: «Mi raccomando alla transizione tra gameplay e filmati e
## viceversa»):
## - all'entrata le comparse partono dalla posa degli attori veri nello stesso fotogramma, la telecamera
##   parte da quella del gioco, bande e interfaccia scorrono in INTRO tick, la musica si abbassa o passa al
##   brano della scena;
## - all'uscita le comparse sono nel punto degli attori veri (l'esito), che le sostituiscono; il gioco
##   riparte subito mentre la telecamera torna morbida all'inquadratura del gioco e le bande escono in
##   OUTRO tick; i tasti tenuti per l'ultima battuta non diventano pressioni.
##
## Chi ospita la scena (TestRoom) offre: scene_frame(space, rif) → {"origin", "offset", "parent"},
## scene_camera_center(), scene_bounds(), scene_apply_camera(centro, zoom), scene_ui_alpha(a),
## scene_event(nome), scene_handoff(lettore), scene_end(lettore), scene_live().

signal done

enum Phase { PLAY, OUTRO, DONE }

const BAR_H := 32
## Tick delle bande e dell'interfaccia che scorrono all'entrata e all'uscita.
const INTRO := 18
const OUTRO := 26
## Caratteri per tick della battuta che si scrive.
const TYPE_SPEED := 1.0
## Tick prima che una pressione completi o chiuda la battuta.
const LINE_MIN := 10
## In automatico (test, pilota, replay) la battuta resta AUTO_HOLD tick più AUTO_PER_CHAR per carattere.
const AUTO_HOLD := 50
const AUTO_PER_CHAR := 2
## START salta la scena, ma non nei primi SKIP_AFTER tick (per non saltarla per sbaglio).
const SKIP_AFTER := 30
## Il riquadro del primo piano, e i tick in cui entra ed esce.
const PANEL := 96
const PANEL_IN := 10
## Il primo piano a tutto schermo: 2x, sullo sfondo sfocato che entra in FULL_IN tick.
const FULL_SCALE := 2
const FULL_IN := 10
## Margine del testo e altezza delle righe nella banda di sotto.
const TEXT_X := 16
const C_BAR := Color(0, 0, 0)
const C_INK := Color8(240, 232, 210)
const C_TEXT := Color8(236, 232, 220)
const C_PANEL := Color8(18, 16, 24)
const C_HINT := Color8(150, 146, 140)

## Lo sfondo del primo piano a tutto schermo: lo schermo sfocato, un po' spento e scuro.
const BLUR_SHADER := """shader_type canvas_item;
uniform sampler2D screen : hint_screen_texture, filter_linear;
uniform float amount = 0.0;
void fragment() {
	vec2 px = SCREEN_PIXEL_SIZE * 1.6;
	vec3 c = vec3(0.0);
	float w = 0.0;
	for (int y = -3; y <= 3; y++) {
		for (int x = -3; x <= 3; x++) {
			float k = exp(-float(x * x + y * y) / 5.0);
			c += textureLod(screen, SCREEN_UV + vec2(float(x), float(y)) * px, 0.0).rgb * k;
			w += k;
		}
	}
	c /= w;
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(c, vec3(l), 0.4) * 0.42;
	COLOR = vec4(c, amount);
}
"""

static var _blur_shader: Shader

var data: SceneData
var host: TestRoom
## Le battute avanzano da sole (test, pilota automatico, replay); dal vivo a pressione.
var auto: bool = false
var sound: bool = true
var phase: Phase = Phase.PLAY
## Tick dall'inizio della scena.
var t: int = 0
## Le comparse, per nome dell'attore.
var puppets: Dictionary = {}
## Gli eventi già mandati a chi ospita (per non ripeterli saltando la scena).
var events_sent: PackedStringArray = []

var _step_i: int = 0
var _wait: Callable = Callable()
## Origine della scena nel nodo delle comparse e scarto di quel nodo nel mondo della stanza.
var _origin: Vector2 = Vector2.ZERO
var _offset: Vector2 = Vector2.ZERO
var _parent: Node2D
## La telecamera della scena: centro (coordinate della scena) e zoom.
var _cam_c: Vector2 = Vector2.ZERO
var _cam_z: float = 1.0
var _move: Dictionary = {}
var _follow: Dictionary = {}
var _bars: float = 0.0
var _bars_target: float = 1.0
var _bars_speed: float = 1.0 / INTRO
var _ui_alpha: float = 1.0
var _outro_t: int = 0
var _outro_c: Vector2 = Vector2.ZERO
var _outro_z: float = 1.0
## La battuta in corso: {"who", "name", "color", "lines", "chars", "shown", "t", "hold"}.
var _line: Dictionary = {}
## La voce della battuta in corso (SceneVoices), solo con il suono: {"env", "ticks", "k"}.
var _voice: Dictionary = {}
var _voice_player: AudioStreamPlayer
## Il primo piano: {"who", "name", "full", "side", "tex", "blink", "talk", "mirror", "scale", "k", "out"}.
var _cu: Dictionary = {}
var _cu_old: Dictionary = {}
var _blur_k: float = 0.0
## Il laser: {"src", "dst", "n", "k", "mark", "flash"}.
var _laser: Dictionary = {}
var _flash: Array = []
var _music_prev: StringName = &""
var _music_mode: int = 0

var _ui_layer: CanvasLayer
var _ui: Control
var _blur_layer: CanvasLayer
var _blur: ColorRect
var _blur_mat: ShaderMaterial
var _fx: Node2D


## Prepara la scena: comparse dalle pose degli attori veri (`poses`: nome → {"x", "y", "verso",
## "anim", "index", "frame_tick", "foglio"}, in coordinate della scena), telecamera, bande, musica.
func start(scene: SceneData, room: TestRoom, poses: Dictionary, auto_lines: bool, with_sound: bool) -> void:
	data = scene
	host = room
	auto = auto_lines
	sound = with_sound
	var fr: Dictionary = host.scene_frame(data.space, data.rif)
	_origin = fr["origin"]
	_offset = fr["offset"]
	_parent = fr["parent"]
	_build_layers()
	for actor: String in data.actors:
		_add_puppet(actor, data.actors[actor], poses.get(actor, {}))
	_cam_c = host.scene_camera_center() - _origin - _offset
	_cam_z = 1.0
	if sound:
		_music_prev = Music.current_track()
		if data.music != "" and Music.has_track(StringName(data.music)):
			_music_mode = 2
			Music.play(StringName(data.music), 0.8)
		else:
			_music_mode = 1
			Music.duck(true)


func _build_layers() -> void:
	# Lo sfondo sfocato sotto l'interfaccia della scena e sopra il gioco (anche sopra l'interfaccia
	# dell'arena, che durante la scena è comunque spenta).
	_blur_layer = CanvasLayer.new()
	_blur_layer.layer = 15
	add_child(_blur_layer)
	_blur = ColorRect.new()
	_blur.size = View.SIZE
	_blur.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if _blur_shader == null:
		_blur_shader = Shader.new()
		_blur_shader.code = BLUR_SHADER
	_blur_mat = ShaderMaterial.new()
	_blur_mat.shader = _blur_shader
	_blur.material = _blur_mat
	_blur.visible = false
	_blur_layer.add_child(_blur)
	_ui_layer = CanvasLayer.new()
	_ui_layer.layer = 20
	add_child(_ui_layer)
	_ui = Control.new()
	_ui.size = View.SIZE
	_ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ui.draw.connect(_draw_ui)
	_ui_layer.add_child(_ui)
	# Il laser sta nel mondo, sopra gli attori.
	_fx = Node2D.new()
	_fx.z_index = 2500
	_fx.z_as_relative = false
	_fx.draw.connect(_draw_fx)


func _add_puppet(actor: String, a: Dictionary, pose: Dictionary) -> void:
	var fd: FighterData = null
	var tipo := str(a.get("tipo", ""))
	if tipo != "" and ResourceLoader.exists("res://data/fighters/%s.tres" % tipo):
		fd = load("res://data/fighters/%s.tres" % tipo) as FighterData
	var sheet_id := StringName(str(pose.get("foglio", a.get("foglio", fd.sprite_id if fd != null else tipo))))
	var variant: Dictionary = {}
	if fd != null and not fd.palette_variants.is_empty() and a.has("variante"):
		variant = fd.palette_variants[int(a["variante"]) % fd.palette_variants.size()]
	var p := ScenePuppet.new()
	p.name = "Comparsa_" + actor
	var shadow_w := 0
	if data.space == "arena" and fd != null:
		shadow_w = fd.shadow_width
	p.setup(sheet_id, variant, host.scene_shadow_def() if shadow_w > 0 else null, shadow_w)
	p.sound = sound
	p.depth_sort = data.space == "arena"
	var from_game := bool(a.get("dal_gioco", false)) and not pose.is_empty()
	var src: Dictionary = pose if from_game else a
	p.px = float(src.get("x", 0.0)) + _origin.x
	p.py = float(src.get("y", 0.0)) + _origin.y
	p.facing = int(src.get("verso", 1))
	if from_game:
		p.start_from(StringName(str(pose.get("anim", "idle"))), int(pose.get("index", 0)), int(pose.get("frame_tick", 0)))
	else:
		p.play(StringName(str(a.get("anim", "idle"))))
	p.marked = bool(pose.get("segno", false))
	_parent.add_child(p)
	p.sync()
	puppets[actor] = p
	if _fx.get_parent() == null:
		_parent.add_child(_fx)


# ------------------------------------------------------------------ tick

## Un tick della scena (lo chiama chi la ospita, una volta per tick di fisica).
func tick() -> void:
	if phase == Phase.DONE:
		return
	t += 1
	if phase == Phase.OUTRO:
		_tick_outro()
		return
	_bars = move_toward(_bars, _bars_target, _bars_speed)
	_ui_alpha = move_toward(_ui_alpha, 0.0, 1.0 / INTRO)
	host.scene_ui_alpha(_ui_alpha)
	if not auto and t > SKIP_AFTER and Input.is_action_just_pressed(&"pause"):
		_skip()
		return
	_run_steps()
	if phase != Phase.PLAY:
		return
	for p: ScenePuppet in puppets.values():
		p.tick()
	_tick_camera()
	_tick_line()
	_tick_closeup()
	_tick_laser()
	_apply_camera()
	_redraw()


## La simulazione è ferma finché la scena recita (durante l'uscita il gioco riparte).
func holds_sim() -> bool:
	return phase == Phase.PLAY


func _run_steps() -> void:
	# Al massimo un giro per passo: i passi immediati si fanno tutti nello stesso tick.
	for guard in data.steps.size() + 2:
		if _wait.is_valid():
			if not bool(_wait.call()):
				return
			_wait = Callable()
		if _step_i >= data.steps.size():
			_begin_outro()
			return
		var st: Dictionary = data.steps[_step_i]
		_step_i += 1
		_start_step(st)


func _start_step(st: Dictionary) -> void:
	var wait := bool(st.get("aspetta", true))
	match str(st["fai"]):
		"bande":
			_bars_target = 1.0 if bool(st.get("entra", true)) else 0.0
			_bars_speed = 1.0 / maxf(1.0, float(st.get("tick", INTRO)))
			if wait:
				_wait = func() -> bool: return is_equal_approx(_bars, _bars_target)
		"inquadra":
			_move = {}
			_cam_z = float(st.get("zoom", _cam_z))
			_cam_c = _shot_center(st)
			_follow = st if st.has("segui") and bool(st["segui"]) else {}
		"camera":
			_follow = {}
			var n := maxi(1, int(st.get("tick", 40)))
			_move = {"st": st, "c0": _cam_c, "z0": _cam_z, "n": n, "k": 0}
			if wait:
				_wait = func() -> bool: return _move.is_empty()
		"cammina":
			var p: ScenePuppet = puppets[str(st["chi"])]
			var to: Array = st.get("a", [p.px - _origin.x, p.py - _origin.y])
			p.walk_to(Vector2(float(to[0]), float(to[1])) + _origin, float(st.get("vel", 1.5)), StringName(str(st.get("anim", "walk"))))
			if wait:
				_wait = func() -> bool: return not p.is_walking()
		"anim":
			(puppets[str(st["chi"])] as ScenePuppet).play(StringName(str(st["anim"])))
		"verso":
			var pv: ScenePuppet = puppets[str(st["chi"])]
			pv.facing = int(st["verso"])
			pv.sync()
		"attendi":
			var until := t + int(st.get("tick", 30))
			_wait = func() -> bool: return t >= until
		"battuta":
			_start_line(st)
			_wait = func() -> bool: return _line.is_empty()
		"primo_piano":
			var who := str(st["chi"])
			_show_closeup(who, _closeup_name(who, st), bool(st.get("pieno", false)))
			var until_cu := t + int(st.get("tick", 60))
			_wait = func() -> bool:
				if t < until_cu:
					return false
				_after_closeup()
				return true
		"suono":
			if sound:
				Sfx.play(StringName(str(st["nome"])), 0.02, float(st.get("vol", 0.0)))
		"laser":
			var src: ScenePuppet = puppets[str(st["da"])]
			var dst: ScenePuppet = puppets[str(st["a"])]
			src.play(&"laser")
			_laser = {"src": src, "dst": dst, "n": maxi(1, int(st.get("tick", 60))), "k": 0,
				"mark": bool(st.get("segno", true))}
			if sound:
				Sfx.play_at(&"glint", src.px, 0.0, -6.0)
			_wait = func() -> bool: return _laser.is_empty()
		"evento":
			_send_event(str(st["nome"]))


func _send_event(e: String) -> void:
	if events_sent.has(e):
		return
	events_sent.append(e)
	host.scene_event(e)


# ------------------------------------------------------------------ telecamera

## Il centro di un'inquadratura, in coordinate della scena: un attore ("su": i piedi, alzati di "alto"
## px o al "punto" dello sprite) con lo "scarto", oppure il "centro" dato.
func _shot_center(st: Dictionary) -> Vector2:
	var c := _cam_c
	if st.has("su") and puppets.has(str(st["su"])):
		var p: ScenePuppet = puppets[str(st["su"])]
		if st.has("punto"):
			c = p.point(str(st["punto"])) - _origin
		else:
			c = Vector2(p.px, p.py) - _origin - Vector2(0, float(st.get("alto", 60)))
	elif st.has("centro"):
		var a: Array = st["centro"]
		c = Vector2(float(a[0]), float(a[1]))
	if st.has("scarto"):
		var o: Array = st["scarto"]
		c += Vector2(float(o[0]), float(o[1]))
	return c


func _tick_camera() -> void:
	if not _move.is_empty():
		_move["k"] = int(_move["k"]) + 1
		var e := _ease(float(_move["k"]) / float(_move["n"]))
		var st: Dictionary = _move["st"]
		var z1 := float(st.get("zoom", _move["z0"]))
		_cam_c = (_move["c0"] as Vector2).lerp(_shot_center(st), e)
		_cam_z = exp(lerpf(log(float(_move["z0"])), log(z1), e))
		if int(_move["k"]) >= int(_move["n"]):
			_cam_z = z1
			_follow = st if bool(st.get("segui", false)) else {}
			_move = {}
	elif not _follow.is_empty():
		_cam_c = _cam_c.lerp(_shot_center(_follow), 0.18)


## Il centro nel mondo della stanza, dentro i bordi di quello che si può mostrare.
func _view_center(c: Vector2, z: float) -> Vector2:
	var v := c + _origin + _offset
	var b: Rect2 = host.scene_bounds()
	var half := View.SIZE / (2.0 * z)
	v.x = clampf(v.x, b.position.x + half.x, maxf(b.position.x + half.x, b.end.x - half.x))
	v.y = clampf(v.y, b.position.y + half.y, maxf(b.position.y + half.y, b.end.y - half.y))
	return v


func _apply_camera() -> void:
	host.scene_apply_camera(_view_center(_cam_c, _cam_z), _cam_z)


# ------------------------------------------------------------------ battute

func _start_line(st: Dictionary) -> void:
	var who := str(st["chi"])
	var a: Dictionary = data.actors.get(who, {})
	var text := SceneLines.text(data.lines_file, data.id, str(st["id"]))
	_line = {"who": who, "name": str(a.get("nome", who.to_upper())), "color": Color.html(str(a.get("colore", "#ece8dc"))),
		"lines": _wrap(text, View.W - 2 * TEXT_X), "chars": text.length(), "shown": 0.0, "t": 0, "hold": 0}
	_start_voice(str(st["id"]))
	if st.has("anim") and puppets.has(who):
		(puppets[who] as ScenePuppet).play(StringName(str(st["anim"])))
	var cu := _closeup_name(who, st)
	if cu != "":
		_show_closeup(who, cu, bool(st.get("pieno", false)))
	elif not _cu.is_empty():
		_hide_closeup()


## Il primo piano del passo: quello dato, "" per nessuno, altrimenti quello dell'attore.
func _closeup_name(who: String, st: Dictionary) -> String:
	if st.has("primo_piano"):
		return str(st["primo_piano"])
	return str((data.actors.get(who, {}) as Dictionary).get("primo_piano", ""))


## La voce della battuta, se c'è e torna con il testo (SceneVoices); la precedente si ferma.
func _start_voice(id: String) -> void:
	_stop_voice()
	if not sound:
		return
	var text := SceneLines.find(data.lines_file, data.id, id)
	if text == "":
		return
	var v := SceneVoices.voice(data.lines_file, data.id, id, text)
	if v.is_empty():
		return
	if _voice_player == null:
		_voice_player = AudioStreamPlayer.new()
		_voice_player.bus = Sfx.BUS
		add_child(_voice_player)
	_voice_player.stream = v["stream"]
	_voice_player.play()
	_voice = {"env": v["env"], "ticks": int(v["ticks"]), "k": 0}


func _stop_voice() -> void:
	_voice = {}
	if _voice_player != null:
		_voice_player.stop()


## La bocca è aperta: con la voce la dice l'inviluppo, senza voce va mentre la battuta si scrive.
func _mouth_open(who: String) -> bool:
	if _line.is_empty() or str(_line["who"]) != who:
		return false
	if not _voice.is_empty():
		var env: PackedByteArray = _voice["env"]
		var k := int(_voice["k"])
		return k < env.size() and env[k] >= SceneVoices.MOUTH_OPEN
	return float(_line["shown"]) < int(_line["chars"]) and (t / 5) % 2 == 0


func _tick_line() -> void:
	if _line.is_empty():
		return
	if not _voice.is_empty():
		_voice["k"] = int(_voice["k"]) + 1
	_line["t"] = int(_line["t"]) + 1
	var total := int(_line["chars"])
	var typing := float(_line["shown"]) < total
	if typing:
		_line["shown"] = minf(float(total), float(_line["shown"]) + TYPE_SPEED)
	var pressed := not auto and int(_line["t"]) > LINE_MIN and _advance_pressed()
	if typing and pressed:
		_line["shown"] = float(total)
		return
	if float(_line["shown"]) >= total:
		_line["hold"] = int(_line["hold"]) + 1
		var auto_done := auto and int(_line["hold"]) >= AUTO_HOLD + AUTO_PER_CHAR * total
		# In automatico, con la voce, si aspetta anche che finisca di parlare.
		if auto_done and not _voice.is_empty():
			auto_done = int(_voice["k"]) >= int(_voice["ticks"]) + AUTO_HOLD / 2
		if pressed or auto_done:
			_end_line()


func _advance_pressed() -> bool:
	return Input.is_action_just_pressed(&"attack") or Input.is_action_just_pressed(&"jump") \
		or Input.is_action_just_pressed(&"menu_confirm")


func _end_line() -> void:
	_line = {}
	_stop_voice()
	_after_closeup()


## Finita una battuta o un primo piano muto: il primo piano resta se il passo dopo è dello stesso
## personaggio nello stesso modo, cambia di colpo (campo e controcampo) se è un altro primo piano nello
## stesso modo, altrimenti esce.
func _after_closeup() -> void:
	if _cu.is_empty():
		return
	var nxt: Dictionary = data.steps[_step_i] if _step_i < data.steps.size() else {}
	var kind := str(nxt.get("fai", ""))
	if kind == "battuta" or kind == "primo_piano":
		var who := str(nxt.get("chi", ""))
		if _closeup_name(who, nxt) != "" and bool(nxt.get("pieno", false)) == bool(_cu["full"]):
			return
	_hide_closeup()


## Le righe della battuta, al massimo due: va a capo fra le parole.
static func _wrap(text: String, width: int) -> PackedStringArray:
	var out := PackedStringArray()
	var cur := ""
	for w in text.split(" ", false):
		var trial := w if cur == "" else cur + " " + w
		if cur != "" and UiFont.text_width(trial, 1, true) > width:
			out.append(cur)
			cur = w
		else:
			cur = trial
	if cur != "":
		out.append(cur)
	return out


# ------------------------------------------------------------------ primi piani

func _show_closeup(who: String, cu_name: String, full: bool) -> void:
	var p: ScenePuppet = puppets.get(who)
	var side := -1
	if p != null:
		var sx := (p.px + _offset.x - _view_center(_cam_c, _cam_z).x) * _cam_z + View.CX
		side = -1 if sx < View.CX else 1
	if not _cu.is_empty() and _cu["who"] == who and _cu["name"] == cu_name and bool(_cu["full"]) == full:
		_cu["out"] = false
		return
	var cut := not _cu.is_empty() and bool(_cu["full"]) == full
	if not _cu.is_empty() and not cut:
		_cu_old = _cu
		_cu_old["out"] = true
	# Chi sta a sinistra guarda a destra, verso il centro, e viceversa.
	var art := _closeup_art(cu_name, 1 if side < 0 else -1, StringName(str(p.sheet.id)) if p != null else &"")
	_cu = {"who": who, "name": cu_name, "full": full, "side": side, "k": PANEL_IN if cut else 0, "out": false}
	_cu.merge(art)
	if full:
		_blur.visible = true


func _hide_closeup() -> void:
	if not _cu.is_empty():
		_cu_old = _cu
		_cu_old["out"] = true
	_cu = {}


## Le immagini del primo piano `cu_name` rivolto verso `look` (+1 destra, -1 sinistra), da
## assets/ui/closeups (<nome>_dx / _sx, con _blink e _talk), oppure il ritratto dell'interfaccia.
## GIG non si specchia mai (decisione 21): se manca il verso giusto si usa l'altro così com'è.
static func _closeup_art(cu_name: String, look: int, sheet_id: StringName) -> Dictionary:
	const DIR := "res://assets/ui/closeups/"
	var want := cu_name + ("_dx" if look > 0 else "_sx")
	var other := cu_name + ("_sx" if look > 0 else "_dx")
	var base := ""
	var mirror := false
	for n: String in [want, cu_name, other]:
		if FileAccess.file_exists(DIR + n + ".png") or ResourceLoader.exists(DIR + n + ".png"):
			base = n
			break
	var out := {"tex": null, "blink": null, "talk": null, "mirror": false, "scale": 1}
	if base == "":
		var portrait := UiArt.portrait(sheet_id if sheet_id != &"" else StringName(cu_name))
		out["tex"] = portrait
		out["scale"] = 3
		return out
	if base == other:
		mirror = not cu_name.begins_with("gig")
	out["tex"] = SpriteSheet.load_texture(DIR + base + ".png")
	out["blink"] = SpriteSheet.load_texture(DIR + base + "_blink.png")
	out["talk"] = SpriteSheet.load_texture(DIR + base + "_talk.png")
	out["mirror"] = mirror
	return out


func _tick_closeup() -> void:
	for c: Dictionary in [_cu, _cu_old]:
		if c.is_empty():
			continue
		c["k"] = clampi(int(c["k"]) + (-1 if bool(c["out"]) else 1), 0, PANEL_IN)
	if not _cu_old.is_empty() and int(_cu_old["k"]) <= 0:
		_cu_old = {}
	var want_blur := not _cu.is_empty() and bool(_cu["full"])
	_blur_k = move_toward(_blur_k, 1.0 if want_blur else 0.0, 1.0 / FULL_IN)
	_blur_mat.set_shader_parameter(&"amount", _blur_k)
	_blur.visible = _blur_k > 0.0


## La texture del primo piano adesso: palpebre che battono ogni tanto, bocca che si muove mentre la
## battuta si scrive.
func _closeup_frame(c: Dictionary) -> Texture2D:
	var tex: Texture2D = c["tex"]
	var who := str(c["who"])
	if c["talk"] != null and _mouth_open(who):
		return c["talk"]
	# Le palpebre: ogni 150-230 tick, per 7 tick (dal tick e dal nome, senza caso).
	var period := 150 + (who.hash() & 63) + 16
	if c["blink"] != null and (t + (who.hash() & 31)) % period < 7:
		return c["blink"]
	return tex


# ------------------------------------------------------------------ laser

func _tick_laser() -> void:
	for f: Array in _flash:
		f[1] = int(f[1]) - 1
	_flash = _flash.filter(func(f: Array) -> bool: return int(f[1]) > 0)
	if _laser.is_empty():
		return
	_laser["k"] = int(_laser["k"]) + 1
	if int(_laser["k"]) >= int(_laser["n"]):
		var dst: ScenePuppet = _laser["dst"]
		if bool(_laser["mark"]):
			dst.marked = true
		_flash.append([dst.arm_point(), 10])
		if sound:
			Sfx.play_at(&"zap", dst.px, 0.0, -4.0)
		(_laser["src"] as ScenePuppet).play(&"idle")
		_laser = {}


## La punta della penna laser del messo: davanti alla mano destra.
static func _pen_tip(p: ScenePuppet) -> Vector2:
	return p.point("fist_r", Vector2(17, -69)) + Vector2(5 * p.facing, -1)


func _draw_fx() -> void:
	if not _laser.is_empty():
		var src: ScenePuppet = _laser["src"]
		var dst: ScenePuppet = _laser["dst"]
		ArmMark.draw_beam(_fx, _pen_tip(src), dst.arm_point(), t, float(_laser["k"]) / float(_laser["n"]))
	for f: Array in _flash:
		ArmMark.draw_flash(_fx, f[0], int(f[1]))


# ------------------------------------------------------------------ uscita

## START: la scena salta alla fine. Gli eventi che mancano partono, il segno del laser c'è, le
## comparse vanno al loro posto, e si esce come sempre.
func _skip() -> void:
	for i in range(_step_i, data.steps.size()):
		var st: Dictionary = data.steps[i]
		match str(st["fai"]):
			"evento":
				_send_event(str(st["nome"]))
			"laser":
				if bool(st.get("segno", true)) and puppets.has(str(st["a"])):
					(puppets[str(st["a"])] as ScenePuppet).marked = true
	if not _laser.is_empty() and bool(_laser["mark"]):
		(_laser["dst"] as ScenePuppet).marked = true
	_laser = {}
	_line = {}
	_stop_voice()
	_hide_closeup()
	_step_i = data.steps.size()
	_wait = Callable()
	_begin_outro()


func _begin_outro() -> void:
	if phase != Phase.PLAY:
		return
	# Le comparse al posto degli attori veri (l'esito, già applicato alla simulazione).
	for actor: String in data.outcome:
		if not puppets.has(actor):
			continue
		var e: Dictionary = data.outcome[actor]
		var p: ScenePuppet = puppets[actor]
		p.px = float(e.get("x", p.px - _origin.x)) + _origin.x
		p.py = float(e.get("y", p.py - _origin.y)) + _origin.y
		p.facing = int(e.get("verso", p.facing))
		p.sync()
	_line = {}
	_hide_closeup()
	_outro_c = _view_center(_cam_c, _cam_z)
	_outro_z = _cam_z
	_outro_t = 0
	phase = Phase.OUTRO
	host.scene_handoff(self)
	_redraw()


func _tick_outro() -> void:
	_outro_t += 1
	var k := _ease(float(_outro_t) / OUTRO)
	var game: Vector2 = host.scene_camera_center()
	var z := exp(lerpf(log(_outro_z), 0.0, k))
	host.scene_apply_camera(_outro_c.lerp(game, k), z)
	_bars = 1.0 - k
	host.scene_ui_alpha(k)
	_tick_closeup()
	_redraw()
	if _outro_t >= OUTRO:
		_finish()


func _finish() -> void:
	phase = Phase.DONE
	if sound:
		if _music_mode == 2 and _music_prev != &"":
			Music.play(_music_prev, 0.8)
		elif _music_mode == 1:
			Music.duck(false)
	host.scene_end(self)
	for p: ScenePuppet in puppets.values():
		if is_instance_valid(p) and p.get_parent() == _parent:
			p.queue_free()
	puppets.clear()
	if is_instance_valid(_fx):
		_fx.queue_free()
	done.emit()
	queue_free()


## Le comparse che restano nel mondo a scena finita ("resta": true), tolte dal lettore.
func take_extras() -> Array[ScenePuppet]:
	var out: Array[ScenePuppet] = []
	for actor: String in data.actors:
		if bool((data.actors[actor] as Dictionary).get("resta", false)) and puppets.has(actor):
			out.append(puppets[actor])
			puppets.erase(actor)
	return out


## Le comparse degli attori veri (quelli dell'esito) spariscono: al loro posto ci sono gli attori.
func hide_handed_over() -> void:
	for actor: String in data.outcome:
		if puppets.has(actor):
			(puppets[actor] as ScenePuppet).visible = false


# ------------------------------------------------------------------ disegno

func _redraw() -> void:
	_ui.queue_redraw()
	if is_instance_valid(_fx):
		_fx.queue_redraw()


func _draw_ui() -> void:
	var h := roundf(BAR_H * _ease(_bars))
	if h > 0.0:
		_ui.draw_rect(Rect2(0, 0, View.W, h), C_BAR)
		_ui.draw_rect(Rect2(0, View.H - h, View.W, h), C_BAR)
	for c: Dictionary in [_cu_old, _cu]:
		if not c.is_empty():
			_draw_closeup(c)
	if not _line.is_empty() and h >= BAR_H - 1:
		_draw_line_text()


func _draw_closeup(c: Dictionary) -> void:
	var tex := _closeup_frame(c)
	if tex == null:
		return
	var e := _ease(float(c["k"]) / PANEL_IN)
	var side := int(c["side"])
	var sc := int(c["scale"])
	var size := Vector2(tex.get_width(), tex.get_height()) * sc
	if bool(c["full"]):
		# A tutto schermo: 2x, nel terzo dello schermo di chi parla, fra le bande.
		sc *= FULL_SCALE
		size = Vector2(tex.get_width(), tex.get_height()) * sc
		var cx := View.W / 3.0 if side < 0 else View.W * 2.0 / 3.0
		var pos := Vector2(roundf(cx - size.x / 2.0) - side * roundf((1.0 - e) * 10.0), roundf(BAR_H + (View.H - 2 * BAR_H - size.y) / 2.0))
		_draw_tex(tex, Rect2(pos, size), bool(c["mirror"]), Color(1, 1, 1, e))
		return
	# Il riquadro: entra dal suo lato, sopra la banda di sotto.
	var x := 10.0 if side < 0 else View.W - 10.0 - size.x
	x += side * roundf((1.0 - e) * (size.x + 16.0))
	var r := Rect2(x, View.H - BAR_H - size.y - 14.0, size.x, size.y)
	_ui.draw_rect(r.grow(2), C_INK)
	_ui.draw_rect(r.grow(1), C_BAR)
	_ui.draw_rect(r, C_PANEL)
	_draw_tex(tex, r, bool(c["mirror"]), Color.WHITE)


func _draw_tex(tex: Texture2D, r: Rect2, mirror: bool, mod: Color) -> void:
	if mirror:
		_ui.draw_set_transform(Vector2(r.end.x, r.position.y), 0.0, Vector2(-1, 1))
		_ui.draw_texture_rect(tex, Rect2(Vector2.ZERO, r.size), false, mod)
		_ui.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	else:
		_ui.draw_texture_rect(tex, r, false, mod)


## Il nome di chi parla su una linguetta sopra la banda, e il testo che si scrive nella banda.
func _draw_line_text() -> void:
	var name_s := str(_line["name"])
	var col: Color = _line["color"]
	var tab_w := UiFont.text_width(name_s) + 8
	var y0 := View.H - BAR_H
	_ui.draw_rect(Rect2(TEXT_X - 4, y0 - 11, tab_w, 11), C_BAR)
	UiFont.draw_text(_ui, Vector2(TEXT_X, y0 - 11), name_s, col, 1, 0, Color(0, 0, 0, 0), Color(0, 0, 0, 0))
	var left := int(_line["shown"])
	var lines: PackedStringArray = _line["lines"]
	for i in mini(lines.size(), 2):
		var s := lines[i]
		if left <= 0:
			break
		var part := s.substr(0, left)
		left -= s.length() + 1
		UiFont.draw_text(_ui, Vector2(TEXT_X, y0 + 3 + i * 12), part, C_TEXT, 1, 0, Color(0, 0, 0, 0), UiFont.SHADOW, true)
	# A battuta scritta, un segno che lampeggia: si va avanti a pressione.
	if not auto and float(_line["shown"]) >= int(_line["chars"]) and (t / 20) % 2 == 0:
		var ax := View.W - TEXT_X
		var ay := View.H - 9.0
		_ui.draw_colored_polygon(PackedVector2Array([Vector2(ax - 6, ay - 3), Vector2(ax, ay - 3), Vector2(ax - 3, ay)]), C_HINT)


static func _ease(k: float) -> float:
	k = clampf(k, 0.0, 1.0)
	return k * k * (3.0 - 2.0 * k)
