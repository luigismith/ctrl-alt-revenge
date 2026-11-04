extends Node2D
## Verifica dei font CAR Pixel in Godot: disegna frasi note in posizioni note, salva la
## schermata a 384x216 e stampa DONE. godot_check.py la confronta pixel per pixel con il
## disegno fatto in Python dagli stessi bitmap.

const PHRASES: Array[String] = [
	"CTRL+ALT REVENGE! TARANTO · 2087",
	"GIG ×3  PUNK  BRUTO  004200  999999  VAI ▶",
	"Città, più, perché, così, però, è l’arena. È COSÌ!",
	"ÀÈÉÌÒÙ àèéìòù ÁÍÓÚ áíóú",
	"0123456789 abcdefghijklmnopqrstuvwxyz",
	"ABCDEFGHIJKLMNOPQRSTUVWXYZ !\"#$%&'()*+,-./:;<=>?@",
	"[\\]^_`{|}~ « » · ° © ‘’ “” … – — ▶◀▲▼♥",
]

var _frame := 0
var _out := ""
var _reg: FontFile
var _bold: FontFile
var _reg_light: FontFile


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("out="):
			_out = a.substr(4)
	_reg = load("res://assets/fonts/car_pixel_regular.ttf")
	_bold = load("res://assets/fonts/car_pixel_bold.ttf")
	for f: FontFile in [_reg, _bold]:
		print("FONT %s aa=%d hinting=%d subpixel=%d mipmaps=%s msdf=%s ascent=%.2f descent=%.2f height=%.2f" % [
			f.get_font_name() + " " + f.get_font_style_name(), f.antialiasing, f.hinting,
			f.subpixel_positioning, f.generate_mipmaps, f.multichannel_signed_distance_field,
			f.get_ascent(12), f.get_descent(12), f.get_height(12)])
	# copia con l'hinting leggero di Godot (predefinito per i TTF importati): solo per vedere l'effetto
	_reg_light = _reg.duplicate()
	_reg_light.hinting = TextServer.HINTING_LIGHT

	# un Label come lo userà l'HUD: grassetto, ombra di 1 px
	var lb := Label.new()
	lb.text = "GIG ×3   PUNK   004200"
	lb.add_theme_font_override("font", _bold)
	lb.add_theme_font_size_override("font_size", 12)
	lb.add_theme_color_override("font_color", Color.WHITE)
	lb.add_theme_color_override("font_shadow_color", Color(1, 0, 0))
	lb.add_theme_constant_override("shadow_offset_x", 1)
	lb.add_theme_constant_override("shadow_offset_y", 1)
	lb.add_theme_constant_override("shadow_outline_size", 0)
	lb.position = Vector2(2, 192)
	add_child(lb)
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(0, 0, 384, 216), Color("#120f24"))
	var y := 2
	for p in PHRASES:
		draw_string(_reg, Vector2(2, y + 10), p, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.WHITE)
		y += 13
	for p in PHRASES:
		draw_string(_bold, Vector2(2, y + 10), p, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color.WHITE)
		y += 13
	# riga con hinting leggero (non confrontata: serve a mostrare perché va spento)
	draw_string(_reg_light, Vector2(200, 192 + 10), "È è à ì Ù", HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0, 1, 0))


func _process(_delta: float) -> void:
	_frame += 1
	if _frame == 8:
		var img := get_viewport().get_texture().get_image()
		var err := img.save_png(_out)
		print("SAVED %s %s err=%d" % [_out, img.get_size(), err])
		print("DONE")
		get_tree().quit(0)
