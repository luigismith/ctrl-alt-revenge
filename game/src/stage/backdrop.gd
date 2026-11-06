class_name Backdrop
extends RefCounted
## Piani dello sfondo da game/assets/env/<livello>/layers.json (§6): parallasse su posizioni
## intere, ripetizione orizzontale e maschere emissive in additivo, con lo sfarfallio di
## qualche neon. Se il file manca usa i piani segnaposto di PlaceholderEnv.
## I piani con z < 0 vanno dietro agli attori, quelli con z ≥ 0 davanti.
## Nei tratti platform la telecamera sale e scende: ogni piano scende di scroll_y px per ogni px che
## la telecamera sale sopra cam_ref_y (lo slice non la muove in verticale e non li usa).
## Un livello può cambiare ambiente a metà (il prologo passa dal cimitero ai Tamburi): ogni piano può
## valere solo per un tratto della telecamera (x_from-x_to), comparire e sparire in dissolvenza
## (fade_in, fade_out, in px della telecamera) e partire da origin_x invece che da 0.

const VIEW_W := View.W
const FAR := 1 << 30
const EMISSIVE_SHADER := """shader_type canvas_item;
render_mode blend_add;
uniform sampler2D group_map : filter_nearest;
uniform vec4 levels = vec4(1.0);
uniform float fade = 1.0;
void fragment() {
	vec4 c = texture(TEXTURE, UV);
	float g = floor(texture(group_map, vec2(UV.x, 0.5)).r * 255.0 + 0.5);
	float k = levels.x;
	if (g > 0.5 && g < 1.5) { k = levels.y; }
	else if (g > 1.5 && g < 2.5) { k = levels.z; }
	else if (g > 2.5) { k = levels.w; }
	COLOR = vec4(c.rgb * k, c.a * fade);
}
"""


class Layer:
	var name: String = ""
	var scroll: float = 1.0
	var scroll_y: float = 0.0
	var y: int = 0
	var repeat_x: int = 0
	var z: int = 0
	## Il tratto della telecamera in cui il piano si vede, e le dissolvenze ai due capi.
	var x_from: int = -FAR
	var x_to: int = FAR
	var fade_in: int = 0
	var fade_out: int = 0
	## La x della telecamera per cui il bordo sinistro del piano sta sul bordo dello schermo.
	var origin_x: int = 0
	var texture: Texture2D
	var emissive: Texture2D
	var node: Node2D
	var sprites: Array[Sprite2D] = []
	var emis_sprites: Array[Sprite2D] = []
	var emis_mat: ShaderMaterial
	## Per ogni gruppo di neon che sfarfalla: [prossimo tick, tick rimasti della raffica].
	var flicker: Array[PackedInt32Array] = []


var layers: Array[Layer] = []
var level_width: int = 2400
var floor_band: Vector2i = Vector2i(188, 260)
## La y della telecamera per cui valgono le "y" dei piani.
var cam_ref_y: float = 0.0
## La scena del campo di gioco, se c'è: uno o più pezzi {"image": file, "x": px, "y": px}, alla scala
## del mondo, uno dopo l'altro (nel json "scenes", o "scene" se è uno solo).
var scenes: Array[Dictionary] = []
var dir: String = ""
var placeholder: bool = false
var errors: PackedStringArray = []
var warnings: PackedStringArray = []

var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
static var _shader: Shader


## Carica layers.json; false se manca o non è valido (allora si usa il segnaposto).
func load_json(path: String) -> bool:
	if not FileAccess.file_exists(path):
		return false
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (data is Dictionary):
		errors.append("layers.json non leggibile")
		return false
	var d: Dictionary = data
	if int(d.get("format", 0)) != 1:
		errors.append("format deve essere 1")
	level_width = int(d.get("level_width", 2400))
	cam_ref_y = float(d.get("cam_ref_y", 0.0))
	var sc: Variant = d.get("scenes", [d.get("scene", {})])
	if sc is Array:
		for s: Variant in sc:
			if s is Dictionary and (s as Dictionary).has("image"):
				scenes.append(s)
	var band: Variant = d.get("floor_band", [188, 260])
	if band is Array and (band as Array).size() == 2:
		floor_band = Vector2i(int(band[0]), int(band[1]))
	var list: Variant = d.get("layers")
	if not (list is Array) or (list as Array).is_empty():
		errors.append("layers vuoto")
		return false
	dir = path.get_base_dir()
	for lv: Variant in list:
		if not (lv is Dictionary):
			errors.append("piano non valido")
			continue
		var l := Layer.new()
		l.name = str(lv.get("name", "piano"))
		l.scroll = float(lv.get("scroll", 1.0))
		l.scroll_y = float(lv.get("scroll_y", 0.0))
		l.y = int(lv.get("y", 0))
		l.repeat_x = int(lv.get("repeat_x", 0))
		l.z = int(lv.get("z", 0))
		l.x_from = int(lv.get("x_from", -FAR))
		l.x_to = int(lv.get("x_to", FAR))
		l.fade_in = maxi(0, int(lv.get("fade_in", 0)))
		l.fade_out = maxi(0, int(lv.get("fade_out", 0)))
		l.origin_x = int(lv.get("origin_x", 0))
		l.texture = SpriteSheet.load_texture(dir.path_join(str(lv.get("image", ""))))
		if l.texture == null:
			errors.append("%s: immagine mancante" % l.name)
			continue
		if lv.has("emissive") and str(lv["emissive"]) != "":
			l.emissive = SpriteSheet.load_texture(dir.path_join(str(lv["emissive"])))
			if l.emissive == null:
				warnings.append("%s: maschera emissiva mancante" % l.name)
		var cam_end := mini(l.x_to, level_width - VIEW_W)
		var need := int(VIEW_W + (cam_end - l.origin_x) * l.scroll)
		if l.repeat_x == 0 and l.texture.get_width() < need:
			warnings.append("%s: largo %d px, ne servono %d" % [l.name, l.texture.get_width(), need])
		layers.append(l)
	layers.sort_custom(func(a: Layer, b: Layer) -> bool: return a.z < b.z)
	return errors.is_empty()


func use_placeholder(rng_seed: int) -> void:
	placeholder = true
	layers.clear()
	for spec in PlaceholderEnv.make_layers(rng_seed):
		var l := Layer.new()
		l.name = spec["name"]
		l.scroll = spec["scroll"]
		l.y = spec["y"]
		l.repeat_x = spec["repeat_x"]
		l.z = spec["z"]
		l.texture = spec["texture"]
		l.emissive = spec.get("emissive", null)
		layers.append(l)


## Crea i nodi: i piani con z < 0 in `back`, gli altri in `front`.
func build(back: Node, front: Node, rng_seed: int) -> void:
	_rng.seed = rng_seed
	if _shader == null:
		_shader = Shader.new()
		_shader.code = EMISSIVE_SHADER
	for l in layers:
		l.node = Node2D.new()
		l.node.name = "piano_" + l.name
		l.node.z_index = l.z
		(back if l.z < 0 else front).add_child(l.node)
		var copies := 1
		if l.repeat_x > 0:
			copies = int(ceil(float(VIEW_W) / l.repeat_x)) + 1
		for i in copies:
			l.sprites.append(_sprite(l.texture, l.node))
		if l.emissive != null:
			l.emis_mat = ShaderMaterial.new()
			l.emis_mat.shader = _shader
			var groups := _neon_groups(l.emissive)
			l.emis_mat.set_shader_parameter(&"group_map", groups)
			for g in 3:
				l.flicker.append(PackedInt32Array([_rng.randi_range(60, 300), 0]))
			for i in copies:
				var s := _sprite(l.emissive, l.node)
				s.material = l.emis_mat
				l.emis_sprites.append(s)


func _sprite(tex: Texture2D, parent: Node) -> Sprite2D:
	var s := Sprite2D.new()
	s.texture = tex
	s.centered = false
	parent.add_child(s)
	return s


## Aggiorna le posizioni (intere) per la telecamera in `cam_x` e lo sfarfallio dei neon; `cam_dy` è
## quanto la telecamera sta sotto cam_ref_y (negativo quando sale).
func update(cam_x: int, tick: int, cam_dy: float = 0.0) -> void:
	for l in layers:
		var a := alpha(l, cam_x)
		l.node.visible = a > 0.0
		if a <= 0.0:
			continue
		l.node.modulate.a = a
		if l.emis_mat != null:
			l.emis_mat.set_shader_parameter(&"fade", a)
		var base := -roundi((cam_x - l.origin_x) * l.scroll)
		var ly := l.y - roundi(cam_dy * l.scroll_y)
		var all: Array[Sprite2D] = l.sprites + l.emis_sprites
		var n := l.sprites.size()
		for i in all.size():
			var k := i % n
			var x := base
			if l.repeat_x > 0:
				x = posmod(base, l.repeat_x) - l.repeat_x + k * l.repeat_x
			all[i].position = Vector2(x, ly)
		if l.emis_mat != null:
			l.emis_mat.set_shader_parameter(&"levels", _levels(l, tick))


## Quanto si vede il piano con la telecamera in `cam_x` (0-1): fuori dal suo tratto niente, e
## dissolvenze lineari ai due capi.
static func alpha(l: Layer, cam_x: int) -> float:
	if cam_x < l.x_from or cam_x > l.x_to:
		return 0.0
	var a := 1.0
	if l.fade_in > 0:
		a = minf(a, float(cam_x - l.x_from) / l.fade_in)
	if l.fade_out > 0:
		a = minf(a, float(l.x_to - cam_x) / l.fade_out)
	return clampf(a, 0.0, 1.0)


## Intensità dei neon: il piano respira piano, tre gruppi ogni tanto sfarfallano.
func _levels(l: Layer, tick: int) -> Vector4:
	var out := Vector4(0.9 + 0.1 * sin(tick * 0.035), 1.0, 1.0, 1.0)
	const BURST := [0.15, 1.0, 0.1, 0.05, 1.0, 1.0, 0.2, 1.0, 0.6, 1.0, 0.1, 1.0]
	for g in l.flicker.size():
		var f := l.flicker[g]
		if f[1] > 0:
			out[g + 1] = BURST[BURST.size() - f[1]]
			f[1] -= 1
		elif tick >= f[0]:
			f[1] = BURST.size()
			f[0] = tick + BURST.size() + _rng.randi_range(90, 420)
		l.flicker[g] = f
	return out


## Mappa per colonna dei gruppi di neon che sfarfallano (1-3), 0 per gli altri.
func _neon_groups(tex: Texture2D) -> ImageTexture:
	var img := tex.get_image()
	var w := tex.get_width()
	var map := Image.create_empty(w, 1, false, Image.FORMAT_R8)
	if img == null:
		return ImageTexture.create_from_image(map)
	if img.is_compressed():
		img.decompress()
	var used := PackedByteArray()
	used.resize(w)
	var step := maxi(1, img.get_height() / 54)
	for x in w:
		for y in range(0, img.get_height(), step):
			var c := img.get_pixel(x, y)
			if c.a > 0.2 and c.get_luminance() > 0.08:
				used[x] = 1
				break
	var runs: Array[Vector2i] = []
	var start := -1
	var gap := 0
	for x in w + 1:
		var on := x < w and used[x] == 1
		if on:
			if start < 0:
				start = x
			gap = 0
		elif start >= 0:
			gap += 1
			if gap >= 5 or x == w:
				runs.append(Vector2i(start, x - gap + 1))
				start = -1
				gap = 0
	var small: Array[Vector2i] = []
	for r in runs:
		if r.y - r.x >= 5 and r.y - r.x <= 113:
			small.append(r)
	var chosen: Array[Vector2i] = []
	if not small.is_empty():
		for g in mini(3, small.size()):
			chosen.append(small[int((2 * g + 1) * small.size() / 6.0)])
	for g in chosen.size():
		for x in range(chosen[g].x, chosen[g].y):
			map.set_pixel(x, 0, Color8(g + 1, 0, 0))
	return ImageTexture.create_from_image(map)
