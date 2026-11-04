class_name LevelOverlay
extends Control
## Scritte e menu sopra il livello: cartello del livello, freccia "VAI ▶", "ZONA LIBERATA",
## menu di pausa e schermata CONTINUA? / GAME OVER. Usa le immagini di game/assets/ui/
## (stage_card_1, msg_*, go_arrow) e, se mancano, testo con il font dell'interfaccia.
## Disegna e basta: la logica è nel Level.

const PAUSE_ITEMS: PackedStringArray = ["RIPRENDI", "RICOMINCIA", "ESCI AL TITOLO"]
const CARD_TICKS := 170
const BANNER_Y := 88

var card_title: String = "1 · SOTTO LA LINEA"
var card_ticks: int = 0
var go_ticks: int = 0
var clear_ticks: int = -1
var paused: bool = false
var pause_index: int = 0
## -1 = nascosto; 0-9 = conto alla rovescia di CONTINUA?
var continue_count: int = -1
var game_over_ticks: int = -1
var _blink: int = 0
var _text := Color8(247, 232, 189)
var _gold := Color8(255, 226, 122)
var _red := Color8(122, 23, 15)


func _ready() -> void:
	size = Vector2(384, 216)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_text = UiArt.color("text", _text)
	_gold = UiArt.color("menu_selected", _gold)
	_red = UiArt.color("accent_red", _red)


func show_card(title: String) -> void:
	card_title = title
	card_ticks = CARD_TICKS


func tick() -> void:
	_blink += 1
	if card_ticks > 0:
		card_ticks -= 1
	if go_ticks > 0:
		go_ticks -= 1
	if clear_ticks >= 0:
		clear_ticks += 1
	if game_over_ticks >= 0:
		game_over_ticks += 1
	queue_redraw()


func _draw() -> void:
	if card_ticks > 0:
		var t := CARD_TICKS - card_ticks
		var a := clampf(minf(t / 12.0, card_ticks / 12.0), 0.0, 1.0)
		# Comparsa a gradini (niente semitrasparenze sfumate sui pixel): 0, 1/3, 2/3, pieno.
		_banner("stage_card_1", card_title, floorf(a * 3.0) / 3.0)
	if go_ticks > 0:
		_draw_go()
	if clear_ticks >= 0:
		_banner("msg_zone_clear", "ZONA LIBERATA", 1.0 if clear_ticks > 6 else 0.5)
	if paused:
		_draw_pause()
	if continue_count >= 0:
		_draw_continue()
	if game_over_ticks >= 0:
		draw_rect(Rect2(0, 0, 384, 216), Color(0, 0, 0, minf(0.6, game_over_ticks / 40.0)))
		_banner("msg_game_over", "GAME OVER", 1.0)


## Cifra grande (striscia "big_digits" di game/assets/ui, a 1x come le scritte msg_*) centrata su
## `cx`; false se l'immagine manca (allora si usa il font).
func _draw_big_digit(d: int, cx: float, y: float) -> bool:
	var tex := UiArt.texture("big_digits")
	if tex == null:
		return false
	var st := UiArt.strip("big_digits")
	var fr: Vector2i = st["frame"]
	if fr == Vector2i.ZERO or int(st["count"]) < 10:
		return false
	var k := clampi(d, 0, 9)
	draw_texture_rect_region(tex, Rect2(roundf(cx - fr.x / 2.0), y, fr.x, fr.y), Rect2(k * fr.x, 0, fr.x, fr.y))
	return true


## Scritta grande centrata: l'immagine dell'interfaccia o, se manca, il testo a 24 px.
func _banner(key: String, text: String, alpha: float) -> void:
	if alpha <= 0.0:
		return
	if not UiArt.draw_centered(self, key, 192, BANNER_Y, alpha):
		UiFont.draw_text(self, Vector2(192, BANNER_Y), text, Color(_text, alpha), 2, 1, Color(_red, alpha), Color(UiFont.SHADOW, alpha))


func _draw_go() -> void:
	var tex := UiArt.texture("go_arrow")
	var anchor := UiArt.layout("go_arrow_right_center_y", [381, 64])
	if tex != null:
		var st := UiArt.strip("go_arrow")
		var fr: Vector2i = st["frame"]
		if fr == Vector2i.ZERO:
			fr = Vector2i(tex.get_width(), tex.get_height())
		var k := (_blink / int(st["ticks"])) % int(st["count"])
		draw_texture_rect_region(tex, Rect2(anchor[0] - fr.x, anchor[1] - fr.y / 2, fr.x, fr.y), Rect2(k * fr.x, 0, fr.x, fr.y))
		return
	if (go_ticks / 12) % 2 == 0:
		UiFont.draw_text(self, Vector2(anchor[0], anchor[1] - 12), "VAI ▶", _gold, 2, 2, _red)


func _draw_pause() -> void:
	draw_rect(Rect2(0, 0, 384, 216), Color(0.02, 0.0, 0.06, 0.55))
	_banner("msg_pause", "PAUSA", 1.0)
	var y0 := BANNER_Y + 40
	for i in PAUSE_ITEMS.size():
		var sel := i == pause_index
		var y := y0 + i * 13
		UiFont.draw_text(self, Vector2(158, y), PAUSE_ITEMS[i], _gold if sel else _text)
		if sel:
			UiFont.draw_text(self, Vector2(150, y), "▶", _gold)


func _draw_continue() -> void:
	draw_rect(Rect2(0, 0, 384, 216), Color(0.02, 0.0, 0.06, 0.5))
	_banner("msg_continue", "CONTINUA?", 1.0)
	if not _draw_big_digit(continue_count, 192, BANNER_Y + 34):
		UiFont.draw_text(self, Vector2(192, BANNER_Y + 36), str(continue_count), _gold, 2, 1)
	if (_blink / 20) % 2 == 0:
		UiFont.draw_text(self, Vector2(192, BANNER_Y + 70), "Premi ATTACCO per continuare", _text, 1, 1, Color(0, 0, 0, 0), UiFont.SHADOW, true)
