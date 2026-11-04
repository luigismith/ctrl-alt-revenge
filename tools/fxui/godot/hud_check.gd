extends Node2D
## Verifica dell'HUD in Godot: ricostruisce il mockup "hud_plain" di make_mockups.py con le
## texture vere (res://assets/ui/), la disposizione di ui.json e il font CAR Pixel Bold.
## Disegna anche il fotogramma 0 di ogni effetto di fx.json (controllo d'importazione).
## Salva la schermata a 384x216 e stampa DONE; godot_check.py confronta i pixel.

const BG := Color8(0x12, 0x0f, 0x24)

var _frame := 0
var _out := ""
var _fx_out := ""
var _ui: Dictionary
var _fx: Dictionary
var _bold: FontFile
var _mode := "hud"


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("out="):
			_out = a.substr(4)
		if a.begins_with("mode="):
			_mode = a.substr(5)
	_ui = JSON.parse_string(FileAccess.get_file_as_string("res://assets/ui/ui.json"))
	_fx = JSON.parse_string(FileAccess.get_file_as_string("res://assets/fx/fx.json"))
	_bold = load(_ui["fonts"]["bold"]["file"])
	for k: String in _ui:
		if _ui[k] is Dictionary and (_ui[k] as Dictionary).has("image"):
			var t := _tex("res://assets/ui/" + str(_ui[k]["image"]))
			var sz: Array = _ui[k]["size"]
			if t == null or t.get_width() != int(sz[0]) or t.get_height() != int(sz[1]):
				push_error("UI %s: texture mancante o di misura diversa" % k)
	for k: String in _fx:
		var t := _tex("res://assets/fx/" + str(_fx[k]["image"]))
		var fr: Array = _fx[k]["frame"]
		if t == null or t.get_width() != int(fr[0]) * int(_fx[k]["count"]) or t.get_height() != int(fr[1]):
			push_error("FX %s: striscia mancante o di misura diversa" % k)
	print("UI elementi: %d, FX: %d" % [_ui.size(), _fx.size()])
	queue_redraw()


## Le texture usate in _draw() vanno tenute in vita: se il riferimento sparisce subito dopo
## la chiamata, il disegno registrato punta a una texture liberata e appare bianco.
var _keep: Dictionary = {}


func _tex(path: String) -> Texture2D:
	if not _keep.has(path):
		_keep[path] = load(path) as Texture2D
	return _keep[path]


func _ui_tex(key: String) -> Texture2D:
	return _tex("res://assets/ui/" + str(_ui[key]["image"]))


func _text(pos: Vector2, s: String, col: Color, right := false) -> void:
	var x := pos.x
	if right:
		x -= _bold.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x - 1
	var base := Vector2(x, pos.y + _bold.get_ascent(12))
	draw_string(_bold, base + Vector2(1, 1), s, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(_ui["colors"]["shadow"]))
	draw_string(_bold, base, s, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, col)


func _bar(r: Array, ratio: float, ghost: float, suffix: String) -> void:
	var x := int(r[0])
	var y := int(r[1])
	var w := int(r[2])
	var h := int(r[3])
	draw_texture_rect_region(_ui_tex("bar_back" + suffix), Rect2(x, y, w, h), Rect2(0, 0, w, h))
	var gw := int(round(w * ghost))
	var fw := int(round(w * ratio))
	if gw > 0:
		draw_texture_rect_region(_ui_tex("bar_ghost" + suffix), Rect2(x, y, gw, h), Rect2(0, 0, gw, h))
	if fw > 0:
		draw_texture_rect_region(_ui_tex("bar_fill" + suffix), Rect2(x, y, fw, h), Rect2(0, 0, fw, h))
	draw_texture(_ui_tex("bar_frame" + suffix), Vector2(x - 2, y - 2))


func _draw() -> void:
	draw_rect(Rect2(0, 0, 384, 216), BG)
	if _mode == "fx":
		_draw_fx()
		return
	var L: Dictionary = _ui["hud_layout"]
	var pf: Array = L["portrait_frame"]
	draw_texture(_ui_tex("portrait_back"), Vector2(pf[0], pf[1]))
	var pp: Array = L["portrait"]
	draw_texture(_tex("res://portrait_placeholder.png"), Vector2(pp[0], pp[1]))
	draw_texture(_ui_tex("portrait_frame"), Vector2(pf[0], pf[1]))
	var cream := Color(_ui["colors"]["text"])
	var gold := Color(_ui["colors"]["score"])
	var gn: Array = L["gig_name"]
	_text(Vector2(gn[0], gn[1]), "GIG", cream)
	var gl: Array = L["gig_lives_right"]
	_text(Vector2(gl[0], gl[1]), "×3", gold, true)
	_bar(L["gig_bar"], 0.70, 0.82, "")
	var en: Array = L["enemy_name"]
	_text(Vector2(en[0], en[1]), "PUNK", cream)
	_bar(L["enemy_bar"], 0.40, 0.55, "_enemy")
	var sc: Array = L["score_right"]
	_text(Vector2(sc[0], sc[1]), "%06d" % 4200, gold, true)
	var ga: Array = L["go_arrow_right_center_y"]
	var fr: Array = _ui["go_arrow"]["frame"]
	var fw := int(fr[0])
	var fh := int(fr[1])
	draw_texture_rect_region(_ui_tex("go_arrow"), Rect2(int(ga[0]) - fw, int(ga[1]) - fh / 2, fw, fh), Rect2(0, 0, fw, fh))


func _draw_fx() -> void:
	# primo fotogramma "pieno" di ogni effetto, in griglia: solo per vederli in Godot
	var x := 4
	var y := 4
	var row_h := 0
	for k: String in _fx:
		var d: Dictionary = _fx[k]
		var fr: Array = d["frame"]
		var w := mini(int(fr[0]), 128)
		var h := mini(int(fr[1]), 64)
		if x + w > 380:
			x = 4
			y += row_h + 4
			row_h = 0
		var idx := 1 if int(d["count"]) > 1 else 0
		draw_texture_rect_region(_tex("res://assets/fx/" + str(d["image"])), Rect2(x, y, w, h), Rect2(idx * int(fr[0]), 0, w, h))
		x += w + 4
		row_h = maxi(row_h, h)


func _process(_delta: float) -> void:
	_frame += 1
	if _frame == 8:
		var img := get_viewport().get_texture().get_image()
		var err := img.save_png(_out)
		print("SAVED %s %s err=%d" % [_out, img.get_size(), err])
		print("DONE")
		get_tree().quit(0)
