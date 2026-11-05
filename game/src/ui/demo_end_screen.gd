class_name DemoEndScreen
extends Control
## Fine della demo: punteggio, tempo e ringraziamento. Un tasto porta ai crediti.

signal done

var score: int = 0
var ticks: int = 0
var _t: int = 0
var _text := Color8(247, 232, 189)
var _gold := Color8(255, 226, 122)


func _ready() -> void:
	size = View.SIZE
	_text = UiArt.color("text", _text)
	_gold = UiArt.color("score", _gold)


func _physics_process(_delta: float) -> void:
	_t += 1
	queue_redraw()
	if _t > 45 and (Input.is_action_just_pressed(&"menu_confirm") or Input.is_action_just_pressed(&"attack")):
		Sfx.play(&"ui_confirm")
		set_physics_process(false)
		done.emit()


## Tempo in mm:ss.cc da tick a 60 Hz.
static func format_time(t: int) -> String:
	var total_cs := int(round(t * 100.0 / 60.0))
	return "%02d:%02d.%02d" % [total_cs / 6000, (total_cs / 100) % 60, total_cs % 100]


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, View.SIZE), Color8(14, 10, 32))
	for i in 14:
		draw_rect(Rect2(0, 188 + i * 6, View.W, 3), Color8(24, 15, 44))
	if not UiArt.draw_centered(self, "msg_demo_end", View.CX, 50):
		UiFont.draw_text(self, Vector2(View.CX, 50), "FINE DELLA DEMO", _text, 2, 1, UiArt.color("accent_red", Color8(122, 23, 15)))
	UiFont.draw_text(self, Vector2(View.CX, 100), "ZONA LIBERATA: SOTTO LA LINEA", UiArt.color("text_dim", Color8(207, 174, 116)), 1, 1)
	UiFont.draw_text(self, Vector2(View.CX - 72, 127), "PUNTEGGIO", _text)
	UiFont.draw_text(self, Vector2(View.CX + 72, 127), "%06d" % score, _gold, 1, 2)
	UiFont.draw_text(self, Vector2(View.CX - 72, 143), "TEMPO", _text)
	UiFont.draw_text(self, Vector2(View.CX + 72, 143), format_time(ticks), _gold, 1, 2)
	UiFont.draw_text(self, Vector2(View.CX, 180), "Grazie per aver giocato!", _text, 1, 1, Color(0, 0, 0, 0), UiFont.SHADOW, true)
	if (_t / 20) % 2 == 0 and _t > 45:
		UiFont.draw_text(self, Vector2(View.CX, 230), "PREMI ATTACCO", _gold, 1, 1)
