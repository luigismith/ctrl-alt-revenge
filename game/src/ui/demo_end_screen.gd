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
	size = Vector2(384, 216)
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
	draw_rect(Rect2(0, 0, 384, 216), Color8(14, 10, 32))
	for i in 12:
		draw_rect(Rect2(0, 150 + i * 6, 384, 3), Color8(24, 15, 44))
	if not UiArt.draw_centered(self, "msg_demo_end", 192, 40):
		UiFont.draw_text(self, Vector2(192, 40), "FINE DELLA DEMO", _text, 2, 1, UiArt.color("accent_red", Color8(122, 23, 15)))
	UiFont.draw_text(self, Vector2(192, 80), "ZONA LIBERATA: SOTTO LA LINEA", UiArt.color("text_dim", Color8(207, 174, 116)), 1, 1)
	UiFont.draw_text(self, Vector2(120, 102), "PUNTEGGIO", _text)
	UiFont.draw_text(self, Vector2(264, 102), "%06d" % score, _gold, 1, 2)
	UiFont.draw_text(self, Vector2(120, 116), "TEMPO", _text)
	UiFont.draw_text(self, Vector2(264, 116), format_time(ticks), _gold, 1, 2)
	UiFont.draw_text(self, Vector2(192, 144), "Grazie per aver giocato!", _text, 1, 1, Color(0, 0, 0, 0), UiFont.SHADOW, true)
	if (_t / 20) % 2 == 0 and _t > 45:
		UiFont.draw_text(self, Vector2(192, 184), "PREMI ATTACCO", _gold, 1, 1)
