class_name DebugArt
extends RefCounted
## Grafica di debug generata da codice: rettangoli colorati con box e tempi coerenti.
## Si usa solo quando mancano sia la grafica vera sia il segnaposto.

const CELL := Vector2i(80, 112)
const ANCHOR := Vector2i(40, 106)

const PALETTES := {
	&"gig": {"skin": Color(0.86, 0.66, 0.52), "hair": Color(0.72, 0.72, 0.74), "shirt": Color(0.78, 0.52, 0.18),
		"pants": Color(0.34, 0.37, 0.17), "boots": Color(0.36, 0.22, 0.12), "arm": Color(0.32, 0.36, 0.42),
		"glow": Color(0.3, 0.95, 1.0), "scale": 1.0},
	&"thug_punk": {"skin": Color(0.88, 0.7, 0.66), "hair": Color(0.62, 0.3, 0.86), "shirt": Color(0.72, 0.9, 0.2),
		"pants": Color(0.16, 0.2, 0.36), "boots": Color(0.12, 0.1, 0.14), "arm": Color(0.88, 0.7, 0.66),
		"glow": Color(0.88, 0.7, 0.66), "scale": 0.95},
	&"thug_bruiser": {"skin": Color(0.55, 0.36, 0.24), "hair": Color(0.55, 0.36, 0.24), "shirt": Color(0.3, 0.3, 0.34),
		"pants": Color(0.62, 0.34, 0.12), "boots": Color(0.16, 0.12, 0.1), "arm": Color(0.55, 0.36, 0.24),
		"glow": Color(0.55, 0.36, 0.24), "scale": 1.3},
	# gli Esattori: giacca senape del rider, pettorina arancione dell'esattore, giacca rossa del messo
	&"rider": {"skin": Color(0.72, 0.52, 0.37), "hair": Color(0.77, 0.72, 0.62), "shirt": Color(0.72, 0.53, 0.17),
		"pants": Color(0.22, 0.22, 0.27), "boots": Color(0.7, 0.64, 0.56), "arm": Color(0.72, 0.53, 0.17),
		"glow": Color(0.72, 0.52, 0.37), "scale": 0.95},
	&"esattore": {"skin": Color(0.55, 0.36, 0.24), "hair": Color(0.17, 0.14, 0.13), "shirt": Color(0.94, 0.47, 0.09),
		"pants": Color(0.23, 0.24, 0.27), "boots": Color(0.44, 0.27, 0.16), "arm": Color(0.24, 0.25, 0.3),
		"glow": Color(0.55, 0.36, 0.24), "scale": 1.3},
	&"messo": {"skin": Color(0.86, 0.71, 0.61), "hair": Color(0.64, 0.64, 0.67), "shirt": Color(0.56, 0.11, 0.16),
		"pants": Color(0.36, 0.36, 0.4), "boots": Color(0.16, 0.16, 0.19), "arm": Color(0.56, 0.11, 0.16),
		"glow": Color(0.86, 0.71, 0.61), "scale": 1.0},
}

## [posa, tick, tag, eventi] per animazione.
const HUMAN_ANIMS := {
	"idle": [true, [["stand", 14, [], []], ["stand_b", 14, [], []]]],
	"walk": [true, [["walk_a", 8, [], ["step"]], ["stand", 8, [], []], ["walk_b", 8, [], ["step"]], ["stand", 8, [], []]]],
	"run": [true, [["walk_a", 5, [], ["step"]], ["walk_b", 5, [], ["step"]]]],
	"jump_rise": [true, [["air", 6, [], []]]],
	"jump_fall": [true, [["air", 6, [], []]]],
	"land": [false, [["crouch", 4, [], []]]],
	"jab1": [false, [["wind", 3, [], ["sfx:whoosh_light"]], ["punch", 2, ["active"], []], ["stand", 9, ["cancel"], []]]],
	"jab2": [false, [["wind", 3, [], ["sfx:whoosh_light"]], ["punch", 2, ["active"], []], ["stand", 9, ["cancel"], []]]],
	"hook": [false, [["wind", 6, [], ["sfx:whoosh_heavy"]], ["hook", 3, ["active"], []], ["stand", 12, ["cancel"], []]]],
	"kick": [false, [["wind", 10, [], ["sfx:whoosh_heavy"]], ["kick", 3, ["active"], []], ["stand", 20, [], []]]],
	"air_kick": [false, [["air", 4, ["air"], ["sfx:whoosh_heavy"]], ["air_kick", 8, ["active", "air"], []], ["air", 1, ["air", "hold"], []]]],
	"grab_hold": [true, [["grab", 8, [], []]]],
	"knee": [false, [["grab", 4, [], []], ["knee", 3, ["active"], []], ["grab", 10, [], []]]],
	"throw": [false, [["grab", 8, [], []], ["throw", 14, [], []]]],
	"jab": [false, [["wind", 18, [], []], ["punch", 4, ["active"], ["sfx:whoosh_light"]], ["stand", 18, [], []]]],
	"haymaker": [false, [["wind", 20, [], []], ["wind", 13, [], ["glint"]], ["hook", 4, ["active"], ["sfx:whoosh_heavy"]], ["stand", 28, [], []]]],
	"punch": [false, [["wind", 26, ["armor"], []], ["punch", 5, ["active"], ["sfx:whoosh_heavy"]], ["stand", 26, [], []]]],
	"hurt_high": [false, [["hurt", 14, [], []]]],
	"hurt_low": [false, [["hurt_low", 14, [], []]]],
	"knock_air": [false, [["air_back", 6, [], []]]],
	"knock_down": [false, [["down", 6, ["hold"], []]]],
	"getup": [false, [["crouch", 10, [], []], ["stand", 6, [], []]]],
	"grabbed": [true, [["hurt", 8, [], []]]],
	"kneed": [false, [["hurt_low", 8, [], []]]],
	"thrown": [false, [["air_back", 6, [], []]]],
}

const HIT_BOXES := {
	"punch": Rect2i(8, -68, 26, 9),
	"hook": Rect2i(6, -74, 28, 13),
	"kick": Rect2i(8, -48, 32, 11),
	"air_kick": Rect2i(4, -44, 30, 13),
	"knee": Rect2i(4, -48, 16, 14),
}


static func make_sheet(sheet_id: StringName, kind: String) -> SpriteSheet:
	if kind == "props":
		return _make_prop(sheet_id)
	return _make_human(sheet_id)


static func _make_human(sheet_id: StringName) -> SpriteSheet:
	var pal: Dictionary = PALETTES.get(sheet_id, PALETTES[&"thug_punk"])
	var names: PackedStringArray = SpriteSheet.REQUIRED.get(sheet_id, SpriteSheet.REQUIRED[&"thug_punk"])
	var poses: Array[String] = []
	# le mosse proprie dei nemici (pignora, block, read...) non hanno un disegno di debug: le alternative di
	# SpriteSheet.FALLBACKS ripiegano su quelle comuni
	names = PackedStringArray(Array(names).filter(func(n: String) -> bool: return HUMAN_ANIMS.has(n)))
	for n in names:
		for fr: Array in HUMAN_ANIMS[n][1]:
			if not poses.has(fr[0]):
				poses.append(fr[0])
	var img := Image.create_empty(CELL.x * poses.size(), CELL.y, false, Image.FORMAT_RGBA8)
	for i in poses.size():
		_draw_pose(img, Vector2i(CELL.x * i, 0) + ANCHOR, poses[i], pal)
	var s := SpriteSheet.new()
	s.id = sheet_id
	s.source = SpriteSheet.Source.DEBUG
	s.texture = ImageTexture.create_from_image(img)
	s.image_size = img.get_size()
	var k: float = pal["scale"]
	for n in names:
		var spec: Array = HUMAN_ANIMS[n]
		var clip := AnimClip.new()
		clip.name = StringName(n)
		clip.loop = spec[0]
		for fr: Array in spec[1]:
			var f := AnimFrame.new()
			var pose: String = fr[0]
			f.rect = Rect2i(CELL.x * poses.find(pose), 0, CELL.x, CELL.y)
			f.anchor = ANCHOR
			f.ticks = fr[1]
			f.tags = AnimFrame.tags_from_names(fr[2])
			f.events = PackedStringArray(fr[3])
			f.hurt = [_hurt_box(pose, k)]
			if f.has_tag(AnimFrame.TAG_ACTIVE) and HIT_BOXES.has(pose):
				var hb: Rect2i = HIT_BOXES[pose]
				f.hit = [Rect2i(int(hb.position.x * k), hb.position.y, int(hb.size.x * k), hb.size.y)]
			clip.frames.append(f)
		s.animations[StringName(n)] = clip
	return s


static func _hurt_box(pose: String, k: float) -> Rect2i:
	var w := int(22 * k)
	match pose:
		"down":
			return Rect2i(-30, -14, 60, 14)
		"air_back":
			return Rect2i(-20, -62, 40, 30)
		"crouch":
			return Rect2i(-(w >> 1), -70, w, 70)
		_:
			return Rect2i(-(w >> 1), -86, w, 86)


static func _draw_pose(img: Image, a: Vector2i, pose: String, pal: Dictionary) -> void:
	var k: float = pal["scale"]
	var torso_dx := 0
	var torso_dy := 0
	match pose:
		"stand_b":
			torso_dy = 1
		"wind":
			torso_dx = -2
		"hurt":
			torso_dx = -4
		"hurt_low":
			torso_dx = 3
			torso_dy = 6
		"crouch":
			torso_dy = 14
	var shirt: Color = pal["shirt"]
	var pants: Color = pal["pants"]
	var skin: Color = pal["skin"]
	var hair: Color = pal["hair"]
	var arm: Color = pal["arm"]
	var glow: Color = pal["glow"]
	var boots: Color = pal["boots"]
	if pose == "down":
		_rect(img, a + Vector2i(-26, -12), Vector2i(_sc(40, k), 12), shirt)
		_rect(img, a + Vector2i(-40, -9), Vector2i(16, 8), pants)
		_rect(img, a + Vector2i(14, -12), Vector2i(12, 11), skin)
		_rect(img, a + Vector2i(22, -12), Vector2i(4, 11), hair)
		return
	if pose == "air_back":
		_rect(img, a + Vector2i(-14, -60), Vector2i(_sc(30, k), 16), shirt)
		_rect(img, a + Vector2i(14, -56), Vector2i(18, 9), pants)
		_rect(img, a + Vector2i(-27, -66), Vector2i(12, 12), skin)
		_rect(img, a + Vector2i(-28, -68), Vector2i(12, 4), hair)
		return
	# Gambe
	var leg_h := 36 - (14 if pose == "crouch" else 0)
	var legs: Array[Vector2i] = [Vector2i(-8, 0), Vector2i(2, 0)]
	match pose:
		"walk_a":
			legs = [Vector2i(-13, 0), Vector2i(7, 0)]
		"walk_b":
			legs = [Vector2i(-5, 0), Vector2i(-1, 0)]
		"air", "air_kick":
			legs = [Vector2i(-8, -10), Vector2i(2, -14)]
	for l in legs:
		var lh := leg_h if l.y == 0 else 18
		_rect(img, a + Vector2i(_sc(l.x, k), -lh + l.y), Vector2i(_sc(6, k), lh), pants)
		_rect(img, a + Vector2i(_sc(l.x, k) - 1, -4 + l.y), Vector2i(_sc(8, k), 4), boots)
	if pose == "kick":
		_rect(img, a + Vector2i(4, -48), Vector2i(_sc(34, k), 8), pants)
		_rect(img, a + Vector2i(4 + _sc(34, k), -50), Vector2i(5, 10), boots)
	elif pose == "air_kick":
		_rect(img, a + Vector2i(2, -44), Vector2i(_sc(30, k), 8), pants)
		_rect(img, a + Vector2i(2 + _sc(30, k), -46), Vector2i(5, 10), boots)
	elif pose == "knee":
		_rect(img, a + Vector2i(4, -50), Vector2i(_sc(14, k), 14), pants)
	# Busto e testa
	var top := -leg_h - 34 + torso_dy
	_rect(img, a + Vector2i(_sc(-10, k) + torso_dx, top), Vector2i(_sc(20, k), 34), shirt)
	_rect(img, a + Vector2i(-7 + torso_dx, top - 16), Vector2i(14, 16), skin)
	_rect(img, a + Vector2i(-8 + torso_dx, top - 18), Vector2i(12, 5), hair)
	_rect(img, a + Vector2i(1 + torso_dx, top - 11), Vector2i(2, 2), glow)
	# Braccia
	var sx := _sc(6, k) + torso_dx
	match pose:
		"punch":
			_rect(img, a + Vector2i(sx, top + 2), Vector2i(_sc(26, k), 6), arm)
			_rect(img, a + Vector2i(sx + _sc(26, k), top), Vector2i(7, 9), glow)
		"hook":
			_rect(img, a + Vector2i(sx - 2, top - 4), Vector2i(_sc(26, k), 8), arm)
			_rect(img, a + Vector2i(sx + _sc(24, k), top - 6), Vector2i(8, 10), glow)
		"wind":
			_rect(img, a + Vector2i(_sc(-18, k) + torso_dx, top + 4), Vector2i(10, 6), arm)
		"grab", "knee":
			_rect(img, a + Vector2i(sx, top + 6), Vector2i(_sc(18, k), 6), arm)
		"throw":
			_rect(img, a + Vector2i(sx - 4, top - 22), Vector2i(6, 24), arm)
		_:
			_rect(img, a + Vector2i(sx - 2, top + 4), Vector2i(6, 18), arm)
			_rect(img, a + Vector2i(sx - 1, top - 2), Vector2i(7, 7), glow)


static func _sc(v: int, k: float) -> int:
	return int(round(v * k))


static func _rect(img: Image, p: Vector2i, size: Vector2i, c: Color) -> void:
	var r := Rect2i(p, size).intersection(Rect2i(Vector2i.ZERO, img.get_size()))
	if r.size.x > 0 and r.size.y > 0:
		img.fill_rect(r, c)


## Oggetti di scena di debug: bidone, mela, cavo con scintille.
static func _make_prop(sheet_id: StringName) -> SpriteSheet:
	var s := SpriteSheet.new()
	s.id = sheet_id
	s.source = SpriteSheet.Source.DEBUG
	var img: Image
	var specs: Array = []  # [nome, loop, [[rect, anchor, ticks]...]]
	match String(sheet_id):
		"bin":
			img = Image.create_empty(96, 40, false, Image.FORMAT_RGBA8)
			for i in 3:
				var o := Vector2i(32 * i, 0)
				var h := 30 if i < 2 else 16
				var body := Color(0.22, 0.32, 0.3) if i != 1 else Color(0.5, 0.62, 0.58)
				_rect(img, o + Vector2i(4, 38 - h), Vector2i(24, h), body)
				_rect(img, o + Vector2i(3, 38 - h - 3), Vector2i(26, 4), body.lightened(0.2))
				for x in range(7, 26, 5):
					_rect(img, o + Vector2i(x, 40 - h), Vector2i(1, h - 4), body.darkened(0.3))
			specs = [["intact", true, [[Rect2i(0, 0, 32, 40), Vector2i(16, 38), 8]]],
				["hit", false, [[Rect2i(32, 0, 32, 40), Vector2i(16, 38), 6]]],
				["broken", true, [[Rect2i(64, 0, 32, 40), Vector2i(16, 38), 8]]]]
		"apple":
			img = Image.create_empty(12, 12, false, Image.FORMAT_RGBA8)
			_rect(img, Vector2i(2, 3), Vector2i(8, 8), Color(0.85, 0.12, 0.16))
			_rect(img, Vector2i(3, 2), Vector2i(6, 10), Color(0.85, 0.12, 0.16))
			_rect(img, Vector2i(4, 4), Vector2i(2, 2), Color(1, 0.6, 0.6))
			_rect(img, Vector2i(6, 0), Vector2i(1, 3), Color(0.3, 0.2, 0.1))
			_rect(img, Vector2i(7, 1), Vector2i(3, 2), Color(0.3, 0.75, 0.25))
			specs = [["idle", true, [[Rect2i(0, 0, 12, 12), Vector2i(6, 11), 8]]]]
		"cable":
			img = Image.create_empty(64 * 4, 64, false, Image.FORMAT_RGBA8)
			var rng := RandomNumberGenerator.new()
			rng.seed = 7
			var frames: Array = []
			for i in 4:
				var o := Vector2i(64 * i, 0)
				for y in range(8, 64):
					var half := int(26.0 * sin(PI * (y - 8) / 56.0)) + 4
					_rect(img, o + Vector2i(32 - half, y), Vector2i(half * 2, 1), Color(0.18, 0.12, 0.3, 0.85))
				_rect(img, o + Vector2i(30, 0), Vector2i(3, 40), Color(0.1, 0.1, 0.12))
				for k in 10:
					var p := Vector2i(rng.randi_range(14, 50), rng.randi_range(28, 58))
					_rect(img, o + p, Vector2i(1 + (k % 2), 1), Color(0.6, 0.95, 1.0))
				frames.append([Rect2i(64 * i, 0, 64, 64), Vector2i(32, 6), 3])
			specs = [["sparks", true, frames]]
		_:
			img = Image.create_empty(16, 16, false, Image.FORMAT_RGBA8)
			img.fill(Color(1, 0, 1))
			specs = [["idle", true, [[Rect2i(0, 0, 16, 16), Vector2i(8, 15), 8]]]]
	s.texture = ImageTexture.create_from_image(img)
	s.image_size = img.get_size()
	for spec: Array in specs:
		var clip := AnimClip.new()
		clip.name = StringName(spec[0])
		clip.loop = spec[1]
		for fr: Array in spec[2]:
			var f := AnimFrame.new()
			f.rect = fr[0]
			f.anchor = fr[1]
			f.ticks = fr[2]
			var r: Rect2i = fr[0]
			var an: Vector2i = fr[1]
			f.hurt = [Rect2i(-an.x + 2, -an.y + 2, r.size.x - 4, r.size.y - 2)]
			clip.frames.append(f)
		s.animations[clip.name] = clip
	return s
