class_name TitleScreen
extends Node2D
## Titolo «Il tetto»: GIG su un tetto dei Tamburi nella sera del Wind Day, di spalle, guarda la città e la
## torre di SIDERA. I piani e le posizioni li decide tools/ambienti/titolo.py in assets/ui/titolo/titolo.json:
## - il fondale dipinto, con sopra le sue luci in additivo (finestre, insegne) e le luci d'ostacolo della torre,
##   che lampeggiano lente come nel livello;
## - i panni stesi che sventolano, due Colombe (i droni bianchi di ARIA+) lontane nel cielo, la polvere rossa
##   del vento (WindDay, senza pozze e con le luci nello spazio dello schermo);
## - GIG, con le sue normali che prendono la luce della nube, e il cyan del braccio e dell'occhio che pulsa;
## - il logo, che ogni tanto ha un disturbo di 2-3 fotogrammi, il sottotitolo e il menu sul parapetto.
## Il menu: NUOVA PARTITA (il prologo e poi, di seguito, lo slice: il capitolo 2, «Il Wind Day»), CAPITOLI (i pezzi
## da rigiocare, uno per uno, più INDIETRO; il capitolo 1, «I tetti dei Tamburi», ancora non c'è), la STANZA DI PROVA (solo per PC), CREDITI ed ESCI (non nel browser). Niente
## salvataggi né CONTINUA, per ora. Musica "title".
## Solo disegno: il generatore casuale è suo e i replay non lo vedono.

## NUOVA PARTITA: il prologo, poi lo slice.
signal new_game
## CAPITOLI → 2 · IL WIND DAY: lo slice da solo.
signal start_game
## CAPITOLI → PROLOGO: il prologo da solo.
signal prologue
signal show_credits
## Solo nelle build per PC: la stanza di prova del movimento non va nella demo web.
signal test_room
signal quit_game

const NEW_GAME := "NUOVA PARTITA"
const CHAPTERS_ITEM := "CAPITOLI"
const BACK := "INDIETRO"
const MAIN_ITEMS: PackedStringArray = [NEW_GAME, CHAPTERS_ITEM, "STANZA DI PROVA", "CREDITI", "ESCI"]
## Nel browser mancano la stanza di prova, che è uno strumento, ed ESCI: chiudere il motore lascerebbe la
## pagina ferma sull'ultimo fotogramma, senza audio, finché non la si ricarica.
const WEB_ITEMS: PackedStringArray = [NEW_GAME, CHAPTERS_ITEM, "CREDITI"]
## Le voci che mandano un segnale (le altre aprono o chiudono i CAPITOLI).
const ACTIONS := {NEW_GAME: &"new_game", "STANZA DI PROVA": &"test_room", "CREDITI": &"show_credits",
	"ESCI": &"quit_game"}
## I capitoli da rigiocare, in ordine di storia: [voce, segnale]. Un capitolo nuovo è una riga in più.
const CHAPTERS := [["PROLOGO", &"prologue"], ["2 · IL WIND DAY", &"start_game"]]
const DIR := "res://assets/ui/titolo/"
## Il livello dello slice, per i dati del Wind Day (le stesse raffiche).
const LEVEL := Level.LEVEL_JSON

## Il cyan del braccio e dell'occhio: pulsa piano, un respiro ogni 2 s.
const CYAN := Color(0.35, 0.95, 1.0)
const CYAN_PERIOD := 120
## Il disturbo del logo: ogni 5-11 s, per 2 o 3 fotogrammi.
const GLITCH_EVERY := [300, 660]
const GLITCH_SHADER := """shader_type canvas_item;
// Il disturbo del logo: bande orizzontali di 2 px spostate a caso e i canali rosso e ciano separati.
uniform float glitch = 0.0;
uniform float seed = 0.0;
float h(float n) { return fract(sin(n * 12.9898 + seed * 78.233) * 43758.5453); }
void fragment() {
	vec2 px = TEXTURE_PIXEL_SIZE;
	float row = floor(UV.y / px.y / 2.0);
	float shift = h(row) > 0.72 ? floor((h(row + 31.0) - 0.5) * 14.0) * px.x : 0.0;
	vec2 uv = UV + vec2(shift * glitch, 0.0);
	vec4 c = texture(TEXTURE, uv);
	vec4 r = texture(TEXTURE, uv - vec2(2.0 * px.x * glitch, 0.0));
	vec4 b = texture(TEXTURE, uv + vec2(2.0 * px.x * glitch, 0.0));
	float a = max(c.a, max(r.a, b.a) * glitch);
	COLOR = vec4(mix(c.r, r.r, glitch), c.g, mix(c.b, b.b, glitch), a);
}
"""

## Le Colombe: x, y, velocità in px per tick (negativa: verso sinistra), fase del faro. Lontane, sopra la città.
const DOVES := [[420.0, 38.0, -0.11, 0], [250.0, 58.0, 0.07, 47]]
const DOVE_BODY := Color8(214, 178, 170)
const DOVE_ROTOR := Color8(150, 108, 104)

var web: bool = OS.has_feature("web")
## true: è aperto il sottomenu dei CAPITOLI.
var in_chapters: bool = false

var _layout: Dictionary = {}
var _wind: WindDay
var _ui: Control
var _gig: Sprite2D
var _gig_mat: ShaderMaterial
var _cyan: Sprite2D
var _panni: Sprite2D
var _panni_fps: int = 8
var _tower: Sprite2D
var _doves: Node2D
var _dove_x: PackedFloat32Array = PackedFloat32Array()
var _logo: Sprite2D
var _logo_mat: ShaderMaterial
var _rng := RandomNumberGenerator.new()
var _glitch_next: int = 0
var _glitch_left: int = 0
var _index: int = 0
var _t: int = 0
## Tick in cui il menu ignora i tasti: almeno quanto la dissolvenza d'entrata di Main (16 tick).
var _locked: int = 18
var _text := Color8(247, 232, 189)
var _gold := Color8(255, 226, 122)
var _orange := Color8(228, 138, 46)


func _ready() -> void:
	_text = UiArt.color("menu_other", _text)
	_gold = UiArt.color("menu_selected", _gold)
	_orange = UiArt.color("accent_orange", _orange)
	_rng.seed = 2087
	_glitch_next = _rng.randi_range(GLITCH_EVERY[0], GLITCH_EVERY[1]) / 2
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(DIR + "titolo.json"))
	_layout = parsed if parsed is Dictionary else {}
	var back := CanvasLayer.new()
	back.layer = -1
	add_child(back)
	var front := CanvasLayer.new()
	front.layer = 1
	add_child(front)
	# Il fondale e le sue luci.
	_sprite(back, str(_layout.get("base", "base.png")), Vector2.ZERO)
	var emis := _sprite(back, str(_layout.get("emis", "base_emis.png")), Vector2.ZERO, true)
	if emis != null:
		emis.modulate.a = 0.9
	_tower = _sprite(back, str(_layout.get("torre_emis", "torre_emis.png")), Vector2.ZERO, true)
	_doves = Node2D.new()
	_doves.draw.connect(_draw_doves)
	back.add_child(_doves)
	for d: Array in DOVES:
		_dove_x.append(float(d[0]))
	var panni: Dictionary = _layout.get("panni", {})
	_panni = _sprite(back, str(panni.get("png", "panni.png")), Vector2(float(panni.get("x", 121)), float(panni.get("y", 125))))
	if _panni != null:
		_panni.hframes = int(panni.get("fotogrammi", 8))
		_panni_fps = maxi(1, int(panni.get("fps", 8)))
	_add_gig()
	# La polvere rossa e la luce della nube su GIG, come nel livello; il fondale è già dipinto rosso, quindi
	# niente tinta sullo sfondo e niente lampioni.
	var level: Variant = JSON.parse_string(FileAccess.get_file_as_string(LEVEL))
	_wind = WindDay.new()
	_wind.setup(3, level if level is Dictionary else {})
	_wind.attach(front, self, null, [], false, true)
	var ui_layer := CanvasLayer.new()
	ui_layer.layer = 5
	add_child(ui_layer)
	_add_logo(ui_layer)
	_ui = Control.new()
	_ui.size = View.SIZE
	_ui.draw.connect(_draw_ui)
	ui_layer.add_child(_ui)
	# Dopo un GAME OVER la musica è ancora abbassata (CONTINUA? la abbassa).
	Music.duck(false)
	Music.play(&"title")


## Uno sprite del titolo, con l'angolo in alto a sinistra in `at`; `add`: luce in additivo.
func _sprite(parent: Node, file: String, at: Vector2, add: bool = false) -> Sprite2D:
	var tex := load(DIR + file) as Texture2D
	if tex == null:
		return null
	var s := Sprite2D.new()
	s.texture = tex
	s.centered = false
	s.position = at
	if add:
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		s.material = m
	parent.add_child(s)
	return s


## GIG di spalle: le normali per la luce della nube, il materiale dei combattenti per la luce ambiente del Wind
## Day e, sopra, la maschera del cyan in additivo.
func _add_gig() -> void:
	var g: Dictionary = _layout.get("gig", {})
	var pos := Vector2(38, 84)
	var p: Variant = g.get("pos", [])
	if p is Array and (p as Array).size() == 2:
		pos = Vector2(float(p[0]), float(p[1]))
	var diffuse := load(DIR + str(g.get("png", "gig.png"))) as Texture2D
	if diffuse == null:
		return
	var tex: Texture2D = diffuse
	var normals := load(DIR + str(g.get("normali", "gig_normali.png"))) as Texture2D
	if normals != null:
		var ct := CanvasTexture.new()
		ct.diffuse_texture = diffuse
		ct.normal_texture = normals
		tex = ct
	_gig = Sprite2D.new()
	_gig.texture = tex
	_gig.centered = false
	_gig.position = pos
	if normals != null:
		_gig.light_mask = Fighter.LIGHT_MASK_ACTORS
	_gig_mat = ShaderMaterial.new()
	_gig_mat.shader = Fighter._get_flash_shader()
	_gig.material = _gig_mat
	add_child(_gig)
	var mask := load(DIR + str(g.get("cyan", "gig_cyan.png"))) as Texture2D
	if mask != null:
		_cyan = Sprite2D.new()
		_cyan.texture = mask
		_cyan.centered = false
		_cyan.position = pos
		var m := CanvasItemMaterial.new()
		m.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
		m.light_mode = CanvasItemMaterial.LIGHT_MODE_UNSHADED
		_cyan.material = m
		_cyan.modulate = Color(CYAN, 0.0)
		add_child(_cyan)


## Il logo è uno sprite, per lo shader del disturbo; senza il PNG lo scrive _draw_ui.
func _add_logo(parent: Node) -> void:
	var tex := UiArt.texture("logo")
	if tex == null:
		return
	_logo = Sprite2D.new()
	_logo.texture = tex
	_logo.centered = false
	_logo.position = _xy(_layout.get("logo", {}).get("pos", []), Vector2(83, 6))
	var sh := Shader.new()
	sh.code = GLITCH_SHADER
	_logo_mat = ShaderMaterial.new()
	_logo_mat.shader = sh
	_logo.material = _logo_mat
	parent.add_child(_logo)


static func _xy(v: Variant, fallback: Vector2) -> Vector2:
	if v is Array and (v as Array).size() == 2:
		return Vector2(float(v[0]), float(v[1]))
	return fallback


func _physics_process(_delta: float) -> void:
	_t += 1
	_animate()
	_ui.queue_redraw()
	if _locked > 0:
		_locked -= 1
		return
	var n := items().size()
	if Input.is_action_just_pressed(&"move_up"):
		_index = posmod(_index - 1, n)
		Sfx.play(&"ui_move")
	elif Input.is_action_just_pressed(&"move_down"):
		_index = posmod(_index + 1, n)
		Sfx.play(&"ui_move")
	elif in_chapters and Input.is_action_just_pressed(&"menu_back"):
		Sfx.play(&"ui_move")
		_close_chapters()
	elif Input.is_action_just_pressed(&"menu_confirm") or Input.is_action_just_pressed(&"attack"):
		Sfx.play(&"ui_confirm")
		var sig := choose(_index)
		if sig != &"":
			_locked = 1000
			emit_signal(sig)


## Le voci del menu aperto.
func items() -> PackedStringArray:
	if not in_chapters:
		return WEB_ITEMS if web else MAIN_ITEMS
	var out := PackedStringArray()
	for c: Array in CHAPTERS:
		out.append(str(c[0]))
	out.append(BACK)
	return out


## Sceglie la voce `i` del menu aperto: apre o chiude i CAPITOLI e torna &"", oppure torna il segnale da mandare.
func choose(i: int) -> StringName:
	var item := items()[i]
	if in_chapters:
		if i < CHAPTERS.size():
			return CHAPTERS[i][1]
		_close_chapters()
		return &""
	if item == CHAPTERS_ITEM:
		in_chapters = true
		_index = 0
		return &""
	return ACTIONS.get(item, &"")


func _close_chapters() -> void:
	in_chapters = false
	_index = items().find(CHAPTERS_ITEM)


## Tutto quello che si muove, un passo per tick (60 al secondo).
func _animate() -> void:
	_wind.tick(0.0)
	_wind.sync(0.0, [], true)
	if _gig_mat != null:
		_wind.light_actor(_gig_mat)
	if _cyan != null:
		_cyan.modulate.a = 0.22 + 0.22 * sin(TAU * float(_t % CYAN_PERIOD) / CYAN_PERIOD)
	if _tower != null:
		_tower.modulate.a = WindDay._beacon_level(_t)
	if _panni != null:
		# Il vento muove i panni: con la raffica sventolano più svelti.
		var fps := float(_panni_fps) * (1.0 + 0.6 * _wind.gust())
		_panni.frame = int(float(_t) * fps / 60.0) % _panni.hframes
	for i in DOVES.size():
		var d: Array = DOVES[i]
		_dove_x[i] += float(d[2])
		if _dove_x[i] < -12.0:
			_dove_x[i] = View.W + 12.0
		elif _dove_x[i] > View.W + 12.0:
			_dove_x[i] = -12.0
	_doves.queue_redraw()
	if _logo_mat != null:
		if _glitch_left > 0:
			_glitch_left -= 1
			if _glitch_left == 0:
				_logo_mat.set_shader_parameter(&"glitch", 0.0)
				_glitch_next = _t + _rng.randi_range(GLITCH_EVERY[0], GLITCH_EVERY[1])
		elif _t >= _glitch_next:
			# I fotogrammi del disturbo sono a 60 al secondo: 2-3 fotogrammi sono 2-3 tick.
			_glitch_left = _rng.randi_range(2, 3)
			_logo_mat.set_shader_parameter(&"glitch", 1.0)
			_logo_mat.set_shader_parameter(&"seed", _rng.randf_range(0.0, 100.0))


## Le Colombe lontane: un corpo chiaro di 3 px con i rotori ai lati, che oscillano appena, e il faro che lampeggia.
func _draw_doves() -> void:
	for i in DOVES.size():
		var d: Array = DOVES[i]
		var x := roundf(_dove_x[i])
		var y := roundf(float(d[1]) + sin((_t + int(d[3])) * 0.05) * 1.2)
		_doves.draw_rect(Rect2(x - 1, y, 3, 1), DOVE_BODY)
		_doves.draw_rect(Rect2(x - 2, y - 1, 1, 1), DOVE_ROTOR)
		_doves.draw_rect(Rect2(x + 2, y - 1, 1, 1), DOVE_ROTOR)
		if (_t + int(d[3])) % 80 < 6:
			_doves.draw_rect(Rect2(x, y + 1, 1, 1), Color(1.0, 0.95, 0.85))


func _draw_ui() -> void:
	if _logo == null:
		var lp := _xy(_layout.get("logo", {}).get("pos", []), Vector2(83, 6))
		var red := UiArt.color("accent_red", Color8(122, 23, 15))
		UiFont.draw_text(_ui, Vector2(lp.x + 100, lp.y + 16), "CTRL+ALT", _text, 3, 1, red)
		UiFont.draw_text(_ui, Vector2(lp.x + 100, lp.y + 54), "REVENGE!", _text, 3, 1, red)
	var sub: Dictionary = _layout.get("sottotitolo", {})
	var scx := float(sub.get("cx", 182))
	var sy := float(sub.get("y", 89))
	if not UiArt.draw_centered(_ui, "subtitle", scx, sy):
		UiFont.draw_text(_ui, Vector2(scx, sy), "TARANTO · 2087", _orange, 1, 1)
	var menu: Dictionary = _layout.get("menu", {})
	var cx := float(menu.get("cx", 352))
	var y := float(menu.get("y", 204))
	var step := float(menu.get("passo", 13))
	var list := items()
	# Con più di quattro voci il menu sale un poco, così l'ultima non tocca il bordo.
	y -= maxf(0.0, (list.size() - 4) * step)
	for i in list.size():
		var sel := i == _index
		var col := _gold if sel else _text
		UiFont.draw_text(_ui, Vector2(cx, y + i * step), list[i], col, 1, 1)
		if sel and (_t / 16) % 2 == 0:
			UiFont.draw_text(_ui, Vector2(cx - UiFont.text_width(list[i]) / 2.0 - 10, y + i * step), "▶", col)
	UiFont.draw_text(_ui, Vector2(View.W - 5, View.H - 14), "© 2026 Luigi Massari", UiArt.color("text_dim", Color8(207, 174, 116)), 1, 2, Color(0, 0, 0, 0), UiFont.SHADOW, true)
