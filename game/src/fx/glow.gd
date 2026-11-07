class_name Glow
extends RefCounted
## Il bagliore finto in pixel art, senza HDR (Luigi, 7 novembre 2026): aloni additivi a retinatura, a
## gradini di un quarto con la matrice di Bayer 4×4, invece della sfocatura morbida del glow vero (che
## resta spento in PostFx). Servono al laser, al braccio cyan, alle scintille e ai lumini.
##
## Si disegna con una Glow ("penna") legata a un nodo: è un canvas item figlio, in additivo, che il nodo
## riempie nella sua stessa funzione di disegno (clear(), poi halo() e band()), così l'alone segue il
## disegno nello stesso fotogramma. Solo disegno: la simulazione non lo vede.

const LEVELS := 4.0
const BAYER := [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5]

static var _halos: Dictionary = {}
static var _bands: Dictionary = {}
static var _add: CanvasItemMaterial

var _rid: RID


## Una penna per `owner`: il suo canvas item figlio, sopra quello che il nodo disegna.
func _init(owner: CanvasItem) -> void:
	if _add == null:
		_add = CanvasItemMaterial.new()
		_add.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_rid = RenderingServer.canvas_item_create()
	RenderingServer.canvas_item_set_parent(_rid, owner.get_canvas_item())
	RenderingServer.canvas_item_set_material(_rid, _add.get_rid())
	RenderingServer.canvas_item_set_default_texture_filter(_rid, RenderingServer.CANVAS_ITEM_TEXTURE_FILTER_NEAREST)
	RenderingServer.canvas_item_set_default_texture_repeat(_rid, RenderingServer.CANVAS_ITEM_TEXTURE_REPEAT_ENABLED)


func _notification(what: int) -> void:
	if what == NOTIFICATION_PREDELETE and _rid.is_valid():
		RenderingServer.free_rid(_rid)


## Da chiamare all'inizio della funzione di disegno del nodo.
func clear() -> void:
	RenderingServer.canvas_item_clear(_rid)


## Un alone tondo di raggio `r` centrato in `at` (coordinate del nodo), del colore `color` (l'alfa è la
## forza: in additivo, 1 somma il colore pieno al centro).
func halo(at: Vector2, r: int, color: Color) -> void:
	if r <= 0 or color.a <= 0.0:
		return
	halo_texture(r).draw(_rid, (at - Vector2(r, r)).round(), color)


## Una striscia di alone larga 2r+1 lungo il segmento da `a` a `b` (il laser).
func band(a: Vector2, b: Vector2, r: int, color: Color) -> void:
	var d := b - a
	var n := d.length()
	if n < 1.0 or color.a <= 0.0:
		return
	RenderingServer.canvas_item_add_set_transform(_rid, Transform2D(d.angle(), a.round()))
	band_texture(r).draw_rect(_rid, Rect2(0, -r, roundf(n), 2 * r + 1), true, color)
	RenderingServer.canvas_item_add_set_transform(_rid, Transform2D.IDENTITY)


## Un rettangolo pieno in additivo (le scie delle scintille).
func rect(r: Rect2, color: Color) -> void:
	RenderingServer.canvas_item_add_rect(_rid, r, color)


## La forza dell'alone a distanza `d` (0 al centro, 1 al bordo), già a gradini con la retinatura nel
## pixel (x, y): il centro pieno, poi tre gradini che si diradano.
static func _dither(a: float, x: int, y: int) -> float:
	var b := (float(BAYER[(y & 3) * 4 + (x & 3)]) + 0.5) / 16.0
	return clampf(floorf(a * LEVELS + b) / LEVELS, 0.0, 1.0)


static func _falloff(d: float) -> float:
	var k := clampf(1.0 - d, 0.0, 1.0)
	return k * k


static func halo_texture(r: int) -> Texture2D:
	if _halos.has(r):
		return _halos[r]
	var s := 2 * r + 1
	var img := Image.create_empty(s, s, false, Image.FORMAT_RGBA8)
	for y in s:
		for x in s:
			var d := Vector2(x - r, y - r).length() / (float(r) + 0.5)
			img.set_pixel(x, y, Color(1, 1, 1, _dither(_falloff(d), x, y)))
	var t := ImageTexture.create_from_image(img)
	_halos[r] = t
	return t


## La striscia: 4 px di larghezza (si ripete), 2r+1 di altezza, il centro pieno.
static func band_texture(r: int) -> Texture2D:
	if _bands.has(r):
		return _bands[r]
	var s := 2 * r + 1
	var img := Image.create_empty(4, s, false, Image.FORMAT_RGBA8)
	for y in s:
		for x in 4:
			var d := absf(y - r) / (float(r) + 0.5)
			img.set_pixel(x, y, Color(1, 1, 1, _dither(_falloff(d), x, y)))
	var t := ImageTexture.create_from_image(img)
	_bands[r] = t
	return t
