class_name TitleScreen
extends Node2D
## Titolo: lo sfondo del livello fermo nella sera del Wind Day, con la polvere rossa portata dal vento (GIG è in
## guardia: la strada non deve scorrere), il logo,
## il sottotitolo e il menu (PROLOGO, GIOCA, CREDITI, ESCI; nel browser senza ESCI). Il prologo viene
## prima perché la storia comincia da lì. Musica "title".

signal start_game
signal show_credits
## Solo nelle build per PC: la stanza di prova del movimento non va nella demo web.
signal test_room
signal prologue
signal quit_game

const ITEMS: PackedStringArray = ["PROLOGO", "GIOCA", "STANZA DI PROVA", "CREDITI", "ESCI"]
## Punto a terra fra i piedi di GIG sullo schermo.
const GIG_FEET := Vector2(66, 198)

## Voci del menu. Nel browser mancano la stanza di prova, che è uno strumento, ed ESCI: chiudere il
## motore lascerebbe la pagina ferma sull'ultimo fotogramma, senza audio, finché non la si ricarica.
var _items: PackedStringArray = PackedStringArray(["PROLOGO", "GIOCA", "CREDITI"]) if OS.has_feature("web") else ITEMS

var _backdrop: Backdrop
var _wind: WindDay
var _fx: FxLayer
var _ui: Control
var _gig: Sprite2D
var _gig_anim: FrameAnim
## Ombra di GIG, in un nodo disegnato prima di lui (così non copre gli stivali).
var _shadow: Node2D
var _index: int = 0
var _t: int = 0
## Punto del livello inquadrato: fisso, perché GIG è fermo e la strada sotto i piedi non deve scorrere.
const TITLE_CAM := 220
## Il livello dello sfondo, per le luci della torre e i lampioni del Wind Day.
const LEVEL := Level.LEVEL_JSON
## Tick in cui il menu ignora i tasti: almeno quanto la dissolvenza d'entrata di Main (16 tick).
var _locked: int = 18
var _text := Color8(247, 232, 189)
var _gold := Color8(255, 226, 122)
var _orange := Color8(228, 138, 46)


func _ready() -> void:
	_text = UiArt.color("menu_other", _text)
	_gold = UiArt.color("menu_selected", _gold)
	_orange = UiArt.color("accent_orange", _orange)
	var back := CanvasLayer.new()
	back.layer = -1
	add_child(back)
	var front := CanvasLayer.new()
	front.layer = 1
	add_child(front)
	_backdrop = Backdrop.new()
	if not _backdrop.load_json("res://assets/env/sotto_la_linea/layers.json"):
		_backdrop.use_placeholder(1)
	_backdrop.build(back, front, 1)
	_fx = FxLayer.new()
	_fx.load_defs()
	_fx.visible = false
	add_child(_fx)
	# GIG in guardia a sinistra con la sua ombra, sotto la polvere.
	_shadow = Node2D.new()
	_shadow.draw.connect(_draw_shadow)
	add_child(_shadow)
	var sheet := SpriteSheet.get_sheet(&"gig")
	_gig_anim = FrameAnim.new(sheet)
	_gig_anim.play(&"idle")
	_gig = Sprite2D.new()
	_gig.texture = sheet.texture
	_gig.centered = false
	_gig.region_enabled = true
	_gig.position = GIG_FEET
	add_child(_gig)
	# La sera del Wind Day come nel livello, senza le pozze: polvere, tinta rossa e luci della torre.
	var level: Variant = JSON.parse_string(FileAccess.get_file_as_string(LEVEL))
	var data: Dictionary = level if level is Dictionary else {}
	_wind = WindDay.new()
	_wind.setup(3, data)
	_wind.attach(front, null, _backdrop, WindDay.lamps_of(data), false)
	var ui_layer := CanvasLayer.new()
	ui_layer.layer = 5
	add_child(ui_layer)
	_ui = Control.new()
	_ui.size = View.SIZE
	_ui.draw.connect(_draw_ui)
	ui_layer.add_child(_ui)
	# Dopo un GAME OVER la musica è ancora abbassata (CONTINUA? la abbassa).
	Music.duck(false)
	Music.play(&"title")


## Ombra media (variante 1 di "ombra", come in gioco) a 1x sotto i piedi di GIG.
func _draw_shadow() -> void:
	var def: FxLayer.FxDef = _fx.defs.get(&"ombra")
	if def == null or def.texture == null:
		return
	var k := 1 if def.count > 1 else 0
	_shadow.draw_texture_rect_region(def.texture, Rect2(GIG_FEET - Vector2(def.anchor), Vector2(def.frame)),
		Rect2(k * def.frame.x, 0, def.frame.x, def.frame.y))


func _physics_process(_delta: float) -> void:
	_t += 1
	_backdrop.update(TITLE_CAM, _t)
	_wind.tick(TITLE_CAM)
	_wind.sync(TITLE_CAM, [], true)
	_gig_anim.advance()
	var f := _gig_anim.frame()
	_gig.region_rect = Rect2(f.rect)
	_gig.offset = Vector2(-f.anchor)
	_ui.queue_redraw()
	if _locked > 0:
		_locked -= 1
		return
	if Input.is_action_just_pressed(&"move_up"):
		_index = posmod(_index - 1, _items.size())
		Sfx.play(&"ui_move")
	elif Input.is_action_just_pressed(&"move_down"):
		_index = posmod(_index + 1, _items.size())
		Sfx.play(&"ui_move")
	elif Input.is_action_just_pressed(&"menu_confirm") or Input.is_action_just_pressed(&"attack"):
		Sfx.play(&"ui_confirm")
		_locked = 1000
		match _items[_index]:
			"GIOCA":
				start_game.emit()
			"PROLOGO":
				prologue.emit()
			"STANZA DI PROVA":
				test_room.emit()
			"CREDITI":
				show_credits.emit()
			"ESCI":
				quit_game.emit()


func _draw_ui() -> void:
	# Velo scuro sullo sfondo, così il logo e il menu si leggono sopra le insegne.
	_ui.draw_rect(Rect2(Vector2.ZERO, View.SIZE), Color(0.03, 0.01, 0.08, 0.38))
	var y := 22.0
	var logo := UiArt.texture("logo")
	if logo != null:
		_ui.draw_texture(logo, Vector2(roundf(View.CX - logo.get_width() / 2.0), y))
		y += logo.get_height() + 3
	else:
		UiFont.draw_text(_ui, Vector2(View.CX, y), "CTRL+ALT", _text, 3, 1, UiArt.color("accent_red", Color8(122, 23, 15)))
		UiFont.draw_text(_ui, Vector2(View.CX, y + 38), "REVENGE!", _text, 3, 1, UiArt.color("accent_red", Color8(122, 23, 15)))
		y += 80
	if not UiArt.draw_centered(_ui, "subtitle", View.CX, y):
		UiFont.draw_text(_ui, Vector2(View.CX, y), "TARANTO · 2087", _orange, 1, 1)
	y = 186.0
	for i in _items.size():
		var sel := i == _index
		var col := _gold if sel else _text
		UiFont.draw_text(_ui, Vector2(View.CX, y + i * 13), _items[i], col, 1, 1)
		if sel and (_t / 16) % 2 == 0:
			UiFont.draw_text(_ui, Vector2(View.CX - UiFont.text_width(_items[i]) / 2.0 - 10, y + i * 13), "▶", col)
	UiFont.draw_text(_ui, Vector2(View.W - 5, View.H - 14), "© 2026 Luigi Massari", UiArt.color("text_dim", Color8(207, 174, 116)), 1, 2, Color(0, 0, 0, 0), UiFont.SHADOW, true)
