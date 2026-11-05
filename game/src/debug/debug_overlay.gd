class_name DebugOverlay
extends Node2D
## Sovrapposizione di debug (F1, solo nelle build di debug): hurtbox in verde, hitbox attive
## in rosso, corsia di profondità degli attacchi di GIG (±10 px) e stato di ogni attore.

const HURT := Color(0.2, 1.0, 0.4, 0.8)
const HIT := Color(1.0, 0.15, 0.2, 0.9)
const LANE := Color(0.4, 0.8, 1.0, 0.35)

var level: Level


func _draw() -> void:
	if level == null:
		return
	for e in level.hittables():
		for r in e.world_hurtboxes():
			_box(r, HURT)
	for f in level.fighters:
		for r in f.active_hitboxes():
			_box(r, HIT)
		var label: String = str(Fighter.State.keys()[f.state]).left(5)
		if f is Thug:
			label += " T" if level.director.is_holder(f) else ""
		UiFont.draw_text(self, Vector2(roundf(f.px), roundf(f.py) + 2), label, Color(1, 1, 1, 0.8), 1, 1, Color(0, 0, 0, 0.8))
	var p := level.player
	if p != null:
		var y0 := roundf(p.py)
		draw_rect(Rect2(level.view_left(), y0 - 10, View.W, 1), LANE)
		draw_rect(Rect2(level.view_left(), y0 + 10, View.W, 1), LANE)


func _box(r: Rect2, c: Color) -> void:
	var rr := Rect2(roundf(r.position.x), roundf(r.position.y), roundf(r.size.x), roundf(r.size.y))
	UiFont.draw_frame(self, rr, c)
