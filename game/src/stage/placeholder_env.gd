class_name PlaceholderEnv
extends RefCounted
## Sfondo segnaposto di "Sotto la Linea", disegnato da codice con un seme fisso:
## cielo notturno, torri lontane, palazzi con i neon, marciapiede e asfalto bagnato,
## piloni dell'arena e la ferrovia sopraelevata in primo piano. Si usa solo finché
## mancano gli sfondi veri (game/assets/env/sotto_la_linea/layers.json).

const LEVEL_W := 2400

const SKY_TOP := Color8(13, 10, 36)
const SKY_LOW := Color8(46, 20, 66)
const FAR := Color8(24, 21, 54)
const FAR_EDGE := Color8(34, 30, 72)
const MID := Color8(17, 14, 38)
const MID_EDGE := Color8(30, 25, 62)
const WIN_DIM := Color8(44, 36, 82)
const WARM := Color8(220, 120, 64)
const NEON_RED := Color8(255, 52, 76)
const NEON_ORANGE := Color8(255, 142, 44)
const NEON_CYAN := Color8(46, 238, 255)
const WALK := Color8(46, 34, 70)
const CURB := Color8(78, 62, 112)
const ASPHALT := Color8(36, 22, 58)
const STEEL := Color8(12, 11, 22)
const STEEL_HI := Color8(36, 33, 56)


static func make_layers(rng_seed: int) -> Array[Dictionary]:
	var rng := RandomNumberGenerator.new()
	rng.seed = rng_seed * 7919 + 17
	var out: Array[Dictionary] = []
	out.append({"name": "sky", "scroll": 0.0, "y": 0, "repeat_x": 0, "z": -100, "texture": _sky()})
	var far := _far(rng)
	out.append({"name": "far", "scroll": 0.125, "y": 0, "repeat_x": 768, "z": -90, "texture": far[0], "emissive": far[1]})
	var mid := _mid(rng)
	out.append({"name": "mid", "scroll": 0.4, "y": 0, "repeat_x": 768, "z": -80, "texture": mid[0], "emissive": mid[1]})
	out.append({"name": "floor", "scroll": 1.0, "y": 136, "repeat_x": 0, "z": -10, "texture": _floor(rng)})
	out.append({"name": "pillars", "scroll": 1.0, "y": 0, "repeat_x": 0, "z": -5, "texture": _pillars()})
	out.append({"name": "fg", "scroll": 1.25, "y": 0, "repeat_x": 768, "z": 100, "texture": _rail(rng)})
	return out


static func _tex(img: Image) -> ImageTexture:
	return ImageTexture.create_from_image(img)


static func _rect(img: Image, x: int, y: int, w: int, h: int, c: Color) -> void:
	var r := Rect2i(x, y, w, h).intersection(Rect2i(Vector2i.ZERO, img.get_size()))
	if r.size.x > 0 and r.size.y > 0:
		img.fill_rect(r, c)


static func _sky() -> ImageTexture:
	var img := Image.create_empty(View.W, 188, false, Image.FORMAT_RGBA8)
	for y in 188:
		var t := float(y) / 187.0
		var c := SKY_TOP.lerp(SKY_LOW, t * t)
		if y > 138:
			c = c.lerp(Color8(70, 22, 58), (y - 138) / 100.0)
		_rect(img, 0, y, View.W, 1, c)
	return _tex(img)


static func _far(rng: RandomNumberGenerator) -> Array[ImageTexture]:
	var img := Image.create_empty(768, 188, false, Image.FORMAT_RGBA8)
	var em := Image.create_empty(768, 188, false, Image.FORMAT_RGBA8)
	var x := 0
	while x < 760:
		var w := rng.randi_range(26, 64)
		w = mini(w, 768 - x)
		var h := rng.randi_range(56, 128)
		var top := 188 - h
		_rect(img, x, top, w, h, FAR)
		_rect(img, x, top, 1, h, FAR_EDGE)
		if rng.randf() < 0.4:
			_rect(img, x + w / 2, top - rng.randi_range(6, 16), 1, 16, FAR_EDGE)
		for wy in range(top + 4, 146, 5):
			for wx in range(x + 3, x + w - 3, 4):
				var roll := rng.randf()
				if roll < 0.07:
					_rect(img, wx, wy, 2, 2, WARM.darkened(0.3))
					_rect(em, wx, wy, 2, 2, Color(WARM, 0.55))
				elif roll < 0.45:
					_rect(img, wx, wy, 2, 2, WIN_DIM)
		if rng.randf() < 0.3:
			var nx := x + rng.randi_range(3, maxi(3, w - 6))
			var ny := top + rng.randi_range(8, 30)
			var col := NEON_RED if rng.randf() < 0.6 else NEON_ORANGE
			_rect(img, nx, ny, 3, 16, col.darkened(0.2))
			_rect(em, nx - 1, ny - 1, 5, 18, Color(col, 0.35))
			_rect(em, nx, ny, 3, 16, Color(col, 0.9))
		x += w + rng.randi_range(0, 6)
	return [_tex(img), _tex(em)]


static func _mid(rng: RandomNumberGenerator) -> Array[ImageTexture]:
	var img := Image.create_empty(768, 188, false, Image.FORMAT_RGBA8)
	var em := Image.create_empty(768, 188, false, Image.FORMAT_RGBA8)
	var x := 0
	var cyan_done := false
	while x < 740:
		var w := mini(rng.randi_range(70, 150), 768 - x)
		var h := rng.randi_range(66, 104)
		var top := 188 - h
		_rect(img, x, top, w, h, MID)
		_rect(img, x, top, w, 2, MID_EDGE)
		_rect(img, x, top, 2, h, MID_EDGE)
		for wy in range(top + 8, 116, 9):
			for wx in range(x + 6, x + w - 8, 10):
				var lit := rng.randf() < 0.18
				_rect(img, wx, wy, 5, 5, WARM.darkened(0.45) if lit else WIN_DIM.darkened(0.25))
				if lit:
					_rect(em, wx, wy, 5, 5, Color(WARM, 0.35))
		# Vetrina al piano terra con l'insegna.
		_rect(img, x + 4, 122, w - 8, 26, Color8(26, 18, 44))
		var sw := mini(rng.randi_range(28, 56), w - 16)
		var sx := x + rng.randi_range(8, maxi(8, w - sw - 8))
		var col := NEON_RED if rng.randf() < 0.55 else NEON_ORANGE
		if not cyan_done and x > 300:
			col = NEON_CYAN
			cyan_done = true
		_rect(img, sx, 110, sw, 9, Color8(20, 14, 30))
		_rect(img, sx + 2, 112, sw - 4, 1, col.darkened(0.1))
		_rect(img, sx + 2, 116, sw - 4, 1, col.darkened(0.1))
		_rect(em, sx - 2, 108, sw + 4, 13, Color(col, 0.22))
		_rect(em, sx + 2, 112, sw - 4, 1, Color(col, 1.0))
		_rect(em, sx + 2, 116, sw - 4, 1, Color(col, 1.0))
		_rect(em, x + 6, 124, w - 12, 20, Color(col, 0.10))
		x += w + rng.randi_range(4, 18)
	return [_tex(img), _tex(em)]


static func _floor(rng: RandomNumberGenerator) -> ImageTexture:
	var img := Image.create_empty(LEVEL_W, 80, false, Image.FORMAT_RGBA8)
	_rect(img, 0, 0, LEVEL_W, 14, WALK)
	_rect(img, 0, 0, LEVEL_W, 1, CURB.lightened(0.15))
	for x in range(0, LEVEL_W, 24):
		_rect(img, x, 1, 1, 12, WALK.darkened(0.25))
	_rect(img, 0, 13, LEVEL_W, 2, CURB)
	_rect(img, 0, 15, LEVEL_W, 65, ASPHALT)
	for i in 5200:
		var px := rng.randi_range(0, LEVEL_W - 1)
		var py := rng.randi_range(15, 79)
		_rect(img, px, py, 1, 1, ASPHALT.lightened(0.12) if rng.randf() < 0.5 else ASPHALT.darkened(0.25))
	# Riflessi dei neon sull'asfalto bagnato.
	for i in 70:
		var px := rng.randi_range(0, LEVEL_W - 4)
		var col: Color = [NEON_RED, NEON_ORANGE, NEON_RED, Color8(120, 70, 160)][rng.randi() % 4]
		var len := rng.randi_range(8, 30)
		for k in len:
			var a := 0.28 * (1.0 - float(k) / len)
			_rect(img, px, 16 + k * 2, rng.randi_range(2, 5), 1, ASPHALT.lerp(col, a))
	# Segnaletica orizzontale sbiadita.
	for x in range(0, LEVEL_W, 64):
		_rect(img, x + 8, 58, 30, 2, Color8(70, 56, 86))
	return _tex(img)


static func _pillars() -> ImageTexture:
	var img := Image.create_empty(LEVEL_W, 188, false, Image.FORMAT_RGBA8)
	for px: int in [1988, 2300]:
		_rect(img, px, 18, 40, 170, Color8(28, 25, 50))
		_rect(img, px, 18, 3, 170, Color8(48, 44, 78))
		_rect(img, px + 36, 18, 4, 170, Color8(18, 16, 32))
		for y in range(32, 182, 28):
			_rect(img, px + 3, y, 33, 1, Color8(22, 20, 40))
		_rect(img, px - 4, 175, 48, 13, Color8(34, 30, 58))
	return _tex(img)


static func _rail(rng: RandomNumberGenerator) -> ImageTexture:
	var img := Image.create_empty(768, 40, false, Image.FORMAT_RGBA8)
	_rect(img, 0, 0, 768, 20, STEEL)
	_rect(img, 0, 18, 768, 2, STEEL_HI)
	_rect(img, 0, 5, 768, 1, STEEL_HI.darkened(0.3))
	for x in range(4, 768, 12):
		_rect(img, x, 12, 2, 2, STEEL_HI)
	for x in range(0, 768, 192):
		_rect(img, x + 10, 20, 14, 10, STEEL)
		_rect(img, x + 10, 29, 14, 1, STEEL_HI)
	# Cavi che pendono dalla ferrovia.
	for c in 3:
		var x0 := rng.randi_range(30, 700)
		var span := rng.randi_range(40, 70)
		for k in span:
			var sag := int(10.0 * sin(PI * k / span))
			_rect(img, x0 + k, 20 + sag, 1, 1, Color8(8, 8, 14))
	return _tex(img)
