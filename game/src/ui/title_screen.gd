class_name TitleScreen
extends Node2D
## Titolo: lo sfondo del livello fermo sotto la pioggia (GIG è in guardia: la strada non deve scorrere), il logo,
## il sottotitolo e il menu (GIOCA, CREDITI, ESCI; nel browser senza ESCI). Musica "title".

signal start_game
signal show_credits
signal quit_game

const ITEMS: PackedStringArray = ["GIOCA", "CREDITI", "ESCI"]
## Punto a terra fra i piedi di GIG sullo schermo.
const GIG_FEET := Vector2(66, 198)

## Voci del menu. Nel browser ESCI non c'è: chiudere il motore lascerebbe la pagina ferma
## sull'ultimo fotogramma, senza audio, finché non la si ricarica.
var _items: PackedStringArray = ITEMS.slice(0, 2) if OS.has_feature("web") else ITEMS

var _backdrop: Backdrop
var _rain: Rain
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
	# Spruzzi della pioggia, poi GIG in guardia a sinistra con la sua ombra: tutti sotto le gocce.
	var splashes := Node2D.new()
	add_child(splashes)
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
	_rain = Rain.new()
	_rain.z_index = 50
	_rain.setup(3, _fx, Vector2(150, 208))
	front.add_child(_rain)
	_rain.set_splash_canvas(splashes, false)
	var ui_layer := CanvasLayer.new()
	ui_layer.layer = 5
	add_child(ui_layer)
	_ui = Control.new()
	_ui.size = Vector2(384, 216)
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
	_rain.tick(TITLE_CAM)
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
		match _index:
			0:
				start_game.emit()
			1:
				show_credits.emit()
			2:
				quit_game.emit()


func _draw_ui() -> void:
	# Velo scuro sullo sfondo, così il logo e il menu si leggono sopra le insegne.
	_ui.draw_rect(Rect2(0, 0, 384, 216), Color(0.03, 0.01, 0.08, 0.38))
	var y := 14.0
	var logo := UiArt.texture("logo")
	if logo != null:
		_ui.draw_texture(logo, Vector2(roundf(192 - logo.get_width() / 2.0), y))
		y += logo.get_height() + 3
	else:
		UiFont.draw_text(_ui, Vector2(192, y), "CTRL+ALT", _text, 3, 1, UiArt.color("accent_red", Color8(122, 23, 15)))
		UiFont.draw_text(_ui, Vector2(192, y + 38), "REVENGE!", _text, 3, 1, UiArt.color("accent_red", Color8(122, 23, 15)))
		y += 80
	if not UiArt.draw_centered(_ui, "subtitle", 192, y):
		UiFont.draw_text(_ui, Vector2(192, y), "TARANTO · 2087", _orange, 1, 1)
	y = 150.0
	for i in _items.size():
		var sel := i == _index
		var col := _gold if sel else _text
		UiFont.draw_text(_ui, Vector2(192, y + i * 13), _items[i], col, 1, 1)
		if sel and (_t / 16) % 2 == 0:
			UiFont.draw_text(_ui, Vector2(192 - UiFont.text_width(_items[i]) / 2.0 - 10, y + i * 13), "▶", col)
	UiFont.draw_text(_ui, Vector2(379, 202), "© 2026 Luigi Massari", UiArt.color("text_dim", Color8(207, 174, 116)), 1, 2, Color(0, 0, 0, 0), UiFont.SHADOW, true)
