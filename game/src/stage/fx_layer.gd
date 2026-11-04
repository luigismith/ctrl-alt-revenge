class_name FxLayer
extends Node2D
## Effetti visivi a strisce da game/assets/fx/fx.json (§7):
##   {"hit_spark_light": {"image": "hit_spark_light.png", "frame": [24, 24], "count": 4, "ticks": 2, "anchor": [12, 12]}}
## Gli effetti che mancano vengono disegnati da codice, così il gioco funziona lo stesso.
## Avanzano nei tick della simulazione: le catture con Movie Maker sono ripetibili.

const FX_JSON := "res://assets/fx/fx.json"
const REQUIRED: PackedStringArray = ["hit_spark_light", "hit_spark_heavy", "dust_land", "dust_skid", "glint", "cyber_spark", "ombra"]


class FxDef:
	var texture: Texture2D
	var frame: Vector2i = Vector2i(16, 16)
	var count: int = 1
	var ticks: int = 2
	var anchor: Vector2i = Vector2i(8, 8)
	var from_file: bool = false


class FxItem:
	var def: FxDef
	var x: float
	var y: float
	var facing: int = 1
	var age: int = 0
	var sprite: Sprite2D


var defs: Dictionary[StringName, FxDef] = {}
var errors: PackedStringArray = []
## Gli errori di fx.json si segnalano una volta sola.
static var _warned: bool = false
var _items: Array[FxItem] = []
var _pool: Array[Sprite2D] = []


func _ready() -> void:
	if defs.is_empty():
		load_defs()


func load_defs() -> void:
	defs.clear()
	if FileAccess.file_exists(FX_JSON):
		var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(FX_JSON))
		if data is Dictionary:
			for k: Variant in data:
				var d := _parse_def(str(k), data[k])
				if d != null:
					defs[StringName(str(k))] = d
		else:
			errors.append("fx.json non leggibile")
	for n in REQUIRED:
		if not defs.has(StringName(n)):
			defs[StringName(n)] = _procedural(n)
	if not errors.is_empty() and OS.is_debug_build() and not _warned:
		_warned = true
		push_warning("fx.json: %s (gli effetti mancanti si disegnano da codice)" % "; ".join(errors.slice(0, 5)))


func _parse_def(n: String, v: Variant) -> FxDef:
	if not (v is Dictionary):
		errors.append("%s: non è un oggetto" % n)
		return null
	var d := FxDef.new()
	var tex := SpriteSheet.load_texture(FX_JSON.get_base_dir().path_join(str(v.get("image", ""))))
	var fr: Variant = v.get("frame", [])
	var an: Variant = v.get("anchor", [])
	if tex == null or not (fr is Array) or (fr as Array).size() != 2:
		errors.append("%s: immagine o frame non validi" % n)
		return null
	d.texture = tex
	d.frame = Vector2i(int(fr[0]), int(fr[1]))
	d.count = maxi(1, int(v.get("count", 1)))
	d.ticks = maxi(1, int(v.get("ticks", 2)))
	d.anchor = Vector2i(int(an[0]), int(an[1])) if an is Array and (an as Array).size() == 2 else d.frame / 2
	d.from_file = true
	if d.frame.x * d.count > tex.get_width() or d.frame.y > tex.get_height():
		errors.append("%s: la striscia è più piccola di %d fotogrammi" % [n, d.count])
		return null
	return d


func has_def(fx_name: StringName) -> bool:
	return defs.has(fx_name)


## Crea un effetto con l'ancora in (x, y) del mondo; `z` è l'ordine di disegno.
func spawn(fx_name: StringName, x: float, y: float, facing: int, z: int) -> void:
	if fx_name == &"" or not defs.has(fx_name):
		return
	var it := FxItem.new()
	it.def = defs[fx_name]
	it.x = x
	it.y = y
	it.facing = facing
	it.sprite = _pool.pop_back() if not _pool.is_empty() else _new_sprite()
	it.sprite.visible = true
	it.sprite.texture = it.def.texture
	it.sprite.z_index = z
	_items.append(it)
	_sync(it)


func _new_sprite() -> Sprite2D:
	var s := Sprite2D.new()
	s.centered = false
	s.region_enabled = true
	add_child(s)
	return s


func tick() -> void:
	var keep: Array[FxItem] = []
	for it in _items:
		it.age += 1
		if it.age >= it.def.count * it.def.ticks:
			it.sprite.visible = false
			_pool.append(it.sprite)
		else:
			keep.append(it)
			_sync(it)
	_items = keep


func clear() -> void:
	for it in _items:
		it.sprite.visible = false
		_pool.append(it.sprite)
	_items.clear()


func active_count() -> int:
	return _items.size()


func _sync(it: FxItem) -> void:
	var d := it.def
	var k := mini(it.age / d.ticks, d.count - 1)
	it.sprite.region_rect = Rect2(k * d.frame.x, 0, d.frame.x, d.frame.y)
	it.sprite.offset = Vector2(-d.anchor)
	it.sprite.scale = Vector2(it.facing, 1)
	it.sprite.position = Vector2(roundf(it.x), roundf(it.y))


# --- Effetti disegnati da codice ----------------------------------------------------------------

static func _procedural(n: String) -> FxDef:
	var d := FxDef.new()
	match n:
		"hit_spark_light":
			_burst(d, 24, 4, 2, Color(1, 1, 0.85), Color(1, 0.75, 0.3), 3)
		"hit_spark_heavy":
			_burst(d, 34, 5, 2, Color(1, 1, 1), Color(1, 0.45, 0.25), 4)
		"cyber_spark":
			_burst(d, 28, 4, 2, Color(0.85, 1, 1), Color(0.2, 0.9, 1.0), 3)
		"glint":
			_glint(d)
		"dust_land", "dust_skid":
			_dust(d, n == "dust_skid")
		"ombra":
			_shadow(d)
		_:
			_burst(d, 16, 3, 2, Color.WHITE, Color.GRAY, 2)
	return d


static func _burst(d: FxDef, size: int, count: int, ticks: int, core: Color, edge: Color, rays: int) -> void:
	var img := Image.create_empty(size * count, size, false, Image.FORMAT_RGBA8)
	var c := size / 2
	for k in count:
		var t := float(k) / maxf(1.0, count - 1)
		var r_in := 1.0 + t * size * 0.25
		var r_out := 3.0 + t * size * 0.45 if k < count - 1 else size * 0.45
		var col := core.lerp(edge, t)
		col.a = 1.0 - t * 0.5
		for i in rays * 2:
			var ang := PI * i / rays + (0.4 if k % 2 == 1 else 0.0)
			var steps := int(r_out - r_in) + 1
			for s in steps:
				var rr := r_in + s
				var x := c + int(round(cos(ang) * rr))
				var y := c + int(round(sin(ang) * rr))
				if x >= 0 and x < size and y >= 0 and y < size:
					img.set_pixel(k * size + x, y, col)
		if k == 0:
			for y in range(c - 2, c + 3):
				for x in range(c - 2, c + 3):
					if absi(x - c) + absi(y - c) <= 2:
						img.set_pixel(x, y, core)
	d.texture = ImageTexture.create_from_image(img)
	d.frame = Vector2i(size, size)
	d.count = count
	d.ticks = ticks
	d.anchor = Vector2i(c, c)


static func _glint(d: FxDef) -> void:
	var size := 17
	var count := 5
	var img := Image.create_empty(size * count, size, false, Image.FORMAT_RGBA8)
	var lens := [2, 5, 8, 5, 2]
	for k in count:
		var l: int = lens[k]
		for s in range(-l, l + 1):
			var a := 1.0 - absf(s) / (l + 1.0) * 0.6
			img.set_pixel(k * size + 8 + s, 8, Color(1, 1, 1, a))
			img.set_pixel(k * size + 8, 8 + s, Color(1, 1, 1, a))
		img.set_pixel(k * size + 8, 8, Color(1, 1, 0.8))
	d.texture = ImageTexture.create_from_image(img)
	d.frame = Vector2i(size, size)
	d.count = count
	d.ticks = 3
	d.anchor = Vector2i(8, 8)


static func _dust(d: FxDef, skid: bool) -> void:
	var w := 40
	var h := 14
	var count := 5
	var img := Image.create_empty(w * count, h, false, Image.FORMAT_RGBA8)
	for k in count:
		var t := float(k) / (count - 1)
		var col := Color(0.62, 0.56, 0.72, 0.85 - 0.7 * t)
		for side: int in ([1] if skid else [-1, 1]):
			var cx := 20 + side * int(4 + t * 12)
			var r := 2.0 + t * 3.0
			for y in h:
				for x in range(w):
					var dx := x - cx
					var dy := y - (h - 4 - int(t * 3))
					if dx * dx + dy * dy * 2.0 <= r * r:
						img.set_pixel(k * w + x, y, col)
	d.texture = ImageTexture.create_from_image(img)
	d.frame = Vector2i(w, h)
	d.count = count
	d.ticks = 3
	d.anchor = Vector2i(20, h - 2)


static func _shadow(d: FxDef) -> void:
	var w := 32
	var h := 8
	var img := Image.create_empty(w, h, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			var nx := (x + 0.5 - w / 2.0) / (w / 2.0)
			var ny := (y + 0.5 - h / 2.0) / (h / 2.0)
			if nx * nx + ny * ny <= 1.0:
				img.set_pixel(x, y, Color(0.03, 0.01, 0.07, 0.55))
	d.texture = ImageTexture.create_from_image(img)
	d.frame = Vector2i(w, h)
	d.count = 1
	d.ticks = 1
	d.anchor = Vector2i(w / 2, h / 2)
