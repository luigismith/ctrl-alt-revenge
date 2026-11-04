class_name ShadowLayer
extends Node2D
## Ombre di tutte le entità, disegnate sotto i corpi in (px, py). Con l'effetto "ombra" di
## fx.json a varianti (0 grande, 1 media, 2 piccola) si sceglie la variante e la si disegna a 1x;
## senza, un'ellisse da codice. In salto l'ombra diventa più piccola.

var level: Level


func _draw() -> void:
	if level == null:
		return
	var def: FxLayer.FxDef = level.fx.defs.get(&"ombra")
	for e in level.shadow_casters():
		var w := e.shadow_width()
		if w <= 0 or not e.visible:
			continue
		if def != null and def.texture != null and def.count >= 3:
			var k := 0 if w >= 34 else (1 if w >= 20 else 2)
			if e is Fighter and (e as Fighter).is_down():
				k = 0
			if e.ph > 36.0:
				k = mini(k + 1, 2)
			var o := Vector2(roundf(e.px) - def.anchor.x, roundf(e.py) - def.anchor.y)
			draw_texture_rect_region(def.texture, Rect2(o, def.frame), Rect2(k * def.frame.x, 0, def.frame.x, def.frame.y))
			continue
		var s := clampf(1.0 - e.ph / 140.0, 0.45, 1.0)
		var sw := maxi(6, int(round(w * s)))
		var sh := maxi(2, int(round(sw * 0.26)))
		var x := roundf(e.px) - sw / 2
		var y := roundf(e.py) - sh / 2
		if def != null and def.texture != null:
			draw_texture_rect_region(def.texture, Rect2(x, y, sw, sh), Rect2(Vector2.ZERO, def.frame))
		else:
			draw_rect(Rect2(x, y, sw, sh), Color(0.03, 0.01, 0.07, 0.5))
