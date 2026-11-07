class_name SceneMural
extends Node2D
## Un murale di Totò dentro una scena (decisione 68: i murales animati per l'introduzione, i ricordi e i
## passaggi fra i capitoli). Lo apre il passo «murale» del lettore delle scene.
##
## I file li prepara car-grafica con tools/murales/ in res://assets/murales/<capitolo>/<id>/:
## - murale.png: la vignetta, opaca (512x288 di solito, fino a 960x288 per le panoramiche);
## - murale_emis.png: le luci da sommare, che pulsano;
## - murale_rivela.png: l'ordine dello spray in grigio, 0 compare subito e 255 per ultimo;
## - murale.json: "scorri" {"da", "a"} (l'angolo in alto a sinistra del riquadro dello schermo), oppure
##   "camera" {"zoom_da", "centro_da", "zoom_a", "centro_a"}; le "figure" {"file", "x", "y",
##   "profondita"} sono strati davanti alla vignetta, con la parallasse.
##
## La rivelazione è il passaggio morbido fra gioco e murale: i pixel compaiono nell'ordine dello spray,
## col bordo a puntini come una bomboletta, e sotto quelli che mancano si vede ancora il gioco. Chiudendo
## si torna indietro: l'ultimo pixel dipinto è il primo che sparisce. È solo disegno: la simulazione è
## ferma come nel resto della scena.

const DIR_DEFAULT := "res://assets/murales"
## La cartella dei murales; il test la cambia per un murale finto in user://.
static var dir: String = DIR_DEFAULT

## La larghezza del bordo a puntini, nell'ordine dello spray (0-1).
const EDGE := 0.14
## La rivelazione e la chiusura, in tick, se il passo non le dice.
const REVEAL_TICKS := 60
## Lo scorrimento, in tick, se il passo non lo dice.
const SCROLL_TICKS := 300
## Le luci: periodo del respiro, in tick, e quanto scendono al minimo.
const PULSE_TICKS := 96
const PULSE_DEPTH := 0.35

const SHADER := """shader_type canvas_item;
render_mode unshaded;
uniform sampler2D reveal_tex : filter_nearest;
uniform sampler2D emis_tex : filter_nearest;
uniform bool has_reveal = true;
uniform bool has_emis = false;
uniform vec2 size = vec2(512.0, 288.0);
uniform float progress = 0.0;
uniform float edge = 0.14;
uniform float glow = 1.0;
uniform float seed = 0.0;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233)) + seed) * 43758.5453);
}

void fragment() {
	vec2 px = floor(UV * size);
	float r = has_reveal ? texture(reveal_tex, UV).r : hash(px * 0.37 + 5.0);
	// davanti al fronte dello spray il pixel c'è a caso, tanto più quanto è vicino
	float k = (progress - r) / edge;
	if (k < 1.0 && hash(px) >= k) {
		discard;
	}
	vec4 c = texture(TEXTURE, UV);
	// la vernice fresca, appena più chiara sul fronte
	c.rgb = mix(c.rgb, vec3(1.0), clamp(1.0 - k, 0.0, 1.0) * 0.18);
	if (has_emis) {
		vec4 e = texture(emis_tex, UV);
		c.rgb += e.rgb * e.a * glow;
	}
	COLOR = c;
}
"""

static var _shader: Shader

var mural_id: String = ""
var chapter: String = ""
var size: Vector2 = Vector2(512, 288)
var info: Dictionary = {}
var errors: PackedStringArray = []

## L'inquadratura, in pixel del murale: centro e zoom, da (0) ad (1).
var c0: Vector2 = Vector2.ZERO
var c1: Vector2 = Vector2.ZERO
var z0: float = 1.0
var z1: float = 1.0
var scroll_n: int = SCROLL_TICKS
var scroll_k: int = 0
## La rivelazione: k va da 0 a n aprendo, e da n a 0 chiudendo.
var reveal_n: int = REVEAL_TICKS
var reveal_k: int = 0
var closing: bool = false
var pulse: bool = true
var t: int = 0

var _sprite: Sprite2D
var _mat: ShaderMaterial
var _figures: Array = []   # [{"sprite", "pos" (nel murale), "depth"}]


## La cartella di un murale.
static func path_of(chapter_id: String, id: String) -> String:
	return dir.path_join(chapter_id).path_join(id)


## Il capitolo e l'id dal passo: "id" come "<capitolo>/<id>", oppure "id" con "capitolo".
static func split_id(st: Dictionary) -> PackedStringArray:
	var id := str(st.get("id", ""))
	var ch := str(st.get("capitolo", ""))
	if ch == "" and id.contains("/"):
		ch = id.get_slice("/", 0)
		id = id.get_slice("/", 1)
	return PackedStringArray([ch, id])


## C'è il murale del passo? (lo usa il test dei copioni)
static func exists(st: Dictionary) -> bool:
	var ci := split_id(st)
	return ci[0] != "" and ci[1] != "" and _file_exists(path_of(ci[0], ci[1]).path_join("murale.png")) \
		and FileAccess.file_exists(path_of(ci[0], ci[1]).path_join("murale.json"))


## Prepara il murale del passo `st`; se qualcosa manca, `errors` non è vuoto e il murale non si vede.
func setup(st: Dictionary) -> void:
	var ci := split_id(st)
	chapter = ci[0]
	mural_id = ci[1]
	name = "Murale_" + mural_id
	var base := path_of(chapter, mural_id)
	var tex := _texture(base.path_join("murale.png"))
	if tex == null:
		errors.append("murale mancante: %s" % base)
		return
	size = Vector2(tex.get_width(), tex.get_height())
	var jp := base.path_join("murale.json")
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(jp)) if FileAccess.file_exists(jp) else null
	info = d if d is Dictionary else {}
	if info.is_empty():
		errors.append("murale.json mancante o non valido: %s" % jp)
	_frame_from(st)
	reveal_n = maxi(1, int(st.get("rivela_tick", REVEAL_TICKS)))
	reveal_k = reveal_n if not bool(st.get("rivela", true)) else 0
	pulse = bool(st.get("luci", true))

	if _shader == null:
		_shader = Shader.new()
		_shader.code = SHADER
	_mat = ShaderMaterial.new()
	_mat.shader = _shader
	var rv := _texture(base.path_join("murale_rivela.png"))
	var em := _texture(base.path_join("murale_emis.png"))
	_mat.set_shader_parameter(&"has_reveal", rv != null)
	if rv != null:
		_mat.set_shader_parameter(&"reveal_tex", rv)
	_mat.set_shader_parameter(&"has_emis", em != null)
	if em != null:
		_mat.set_shader_parameter(&"emis_tex", em)
	_mat.set_shader_parameter(&"size", size)
	_mat.set_shader_parameter(&"edge", EDGE)
	_mat.set_shader_parameter(&"seed", float(hash(mural_id) % 997))
	_sprite = Sprite2D.new()
	_sprite.texture = tex
	_sprite.centered = false
	_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_sprite.material = _mat
	add_child(_sprite)
	for f: Variant in info.get("figure", []):
		if not (f is Dictionary):
			continue
		var ft := _texture(base.path_join(str((f as Dictionary).get("file", ""))))
		if ft == null:
			errors.append("figura mancante: %s" % str((f as Dictionary).get("file", "")))
			continue
		var s := Sprite2D.new()
		s.texture = ft
		s.centered = false
		s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		add_child(s)
		_figures.append({"sprite": s, "pos": Vector2(float(f.get("x", 0)), float(f.get("y", 0))),
			"depth": float(f.get("profondita", 1.0))})
	_apply()


## L'inquadratura: "da"/"a" del passo (angoli del riquadro, come "scorri"), se no la "camera" del
## murale.json se ha gli zoom, se no il suo "scorri"; senza niente, il murale fermo al centro.
func _frame_from(st: Dictionary) -> void:
	var half := View.SIZE / 2.0
	var mid := size / 2.0
	var cam: Dictionary = info.get("camera", {}) if info.get("camera", {}) is Dictionary else {}
	var sc: Dictionary = info.get("scorri", {}) if info.get("scorri", {}) is Dictionary else {}
	c0 = mid
	c1 = mid
	z0 = 1.0
	z1 = 1.0
	if st.has("da") or st.has("a"):
		c0 = _vec(st.get("da", st.get("a")), mid - half) + half
		c1 = _vec(st.get("a", st.get("da")), mid - half) + half
	elif cam.has("centro_da") or cam.has("zoom_da"):
		c0 = _vec(cam.get("centro_da", null), mid)
		c1 = _vec(cam.get("centro_a", cam.get("centro_da", null)), c0)
		z0 = maxf(0.25, float(cam.get("zoom_da", 1.0)))
		z1 = maxf(0.25, float(cam.get("zoom_a", z0)))
	elif not sc.is_empty():
		c0 = _vec(sc.get("da", null), mid - half) + half
		c1 = _vec(sc.get("a", sc.get("da", null)), c0 - half) + half
	scroll_n = maxi(1, int(st.get("tick", SCROLL_TICKS)))
	scroll_k = 0


## Un tick: scorrimento, rivelazione (o chiusura) e respiro delle luci.
func tick() -> void:
	t += 1
	scroll_k = mini(scroll_k + 1, scroll_n)
	if closing:
		reveal_k = maxi(reveal_k - 1, 0)
	else:
		reveal_k = mini(reveal_k + 1, reveal_n)
	_apply()


## Comincia a chiudersi: lo spray all'indietro in `n` tick (predefinito: quanto la rivelazione).
func close(n: int = -1) -> void:
	if closing:
		return
	if n > 0:
		# stessa frazione di adesso, sulla durata nuova
		reveal_k = roundi(float(reveal_k) / reveal_n * n)
		reveal_n = n
	closing = true


func is_revealed() -> bool:
	return not closing and reveal_k >= reveal_n


func is_closed() -> bool:
	return closing and reveal_k <= 0


func is_scrolled() -> bool:
	return scroll_k >= scroll_n


## Quanto si vede, da 0 a 1 (con la curva morbida della rivelazione).
func amount() -> float:
	return _ease(float(reveal_k) / reveal_n)


## Centro e zoom di adesso, in pixel del murale.
func view() -> Array:
	var k := _ease(float(scroll_k) / scroll_n)
	return [c0.lerp(c1, k), exp(lerpf(log(z0), log(z1), k))]


func _apply() -> void:
	if _sprite == null:
		return
	var v := view()
	var c: Vector2 = v[0]
	var z: float = v[1]
	var half := View.SIZE / 2.0
	_sprite.scale = Vector2(z, z)
	_sprite.position = (half - c * z).round()
	var a := amount()
	_mat.set_shader_parameter(&"progress", a * (1.0 + EDGE))
	var g := 1.0
	if pulse:
		g = 1.0 - PULSE_DEPTH * 0.5 * (1.0 - cos(TAU * t / PULSE_TICKS))
	_mat.set_shader_parameter(&"glow", g)
	# Le figure: la parallasse rispetto all'inquadratura iniziale, e compaiono a fine spray.
	var fa := clampf((a - 0.6) / 0.4, 0.0, 1.0)
	for f: Dictionary in _figures:
		var s: Sprite2D = f["sprite"]
		var depth: float = f["depth"]
		var p: Vector2 = f["pos"]
		s.scale = Vector2(z, z)
		s.position = (half + (p - c0) * z - (c - c0) * z * depth).round()
		s.modulate.a = fa


static func _vec(v: Variant, fallback: Vector2) -> Vector2:
	if v is Array and (v as Array).size() >= 2:
		return Vector2(float(v[0]), float(v[1]))
	return fallback


static func _file_exists(p: String) -> bool:
	return ResourceLoader.exists(p) or FileAccess.file_exists(p)


## Le texture importate dal progetto, o un PNG letto al volo (il murale finto del test, in user://).
static func _texture(p: String) -> Texture2D:
	if p.ends_with("/") or p == "":
		return null
	if ResourceLoader.exists(p):
		return load(p) as Texture2D
	if FileAccess.file_exists(p):
		var img := Image.load_from_file(p)
		if img != null and not img.is_empty():
			return ImageTexture.create_from_image(img)
	return null


static func _ease(k: float) -> float:
	k = clampf(k, 0.0, 1.0)
	return k * k * (3.0 - 2.0 * k)
