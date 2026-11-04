class_name HitInfo
extends RefCounted
## Dettagli di un colpo andato a segno.

## Punto di contatto (centro della sovrapposizione), in coordinate del mondo.
var point: Vector2 = Vector2.ZERO
## Direzione della spinta: +1 verso destra, -1 verso sinistra.
var dir: int = 1
## Colpo alto (reazione hurt_high) o basso (hurt_low).
var high: bool = true


func _init(p: Vector2 = Vector2.ZERO, d: int = 1, is_high: bool = true) -> void:
	point = p
	dir = d
	high = is_high
