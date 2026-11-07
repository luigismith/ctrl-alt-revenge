class_name WindDay
extends Node2D
## La sera del Wind Day nello slice «Sotto la Linea» (decisione 5; coerenza-slice A3, A7 e M10): la pioggia del
## pomeriggio è finita, tira il maestrale e porta la polvere rossa del minerale. Qui c'è tutto il disegno:
## - la polvere: granelli da 1 px e qualche strisciata su tre piani di parallasse, da destra verso sinistra
##   (contro la corsa di GIG, come il vapore delle cupole), che cadono appena; ogni 4-8 s una raffica di un
##   secondo raddoppia i granelli, li spinge più forte e fa passare basso un velo di polvere; sotto i lampioni
##   i granelli prendono la luce gialla;
## - la luce: gli sfondi dipinti virano verso il rosso-arancio della nube accesa dalla città, più forte in
##   alto (le insegne e le lampade dipinte restano com'erano, come accenti); gli attori con la normal map
##   prendono la stessa luce dall'alto; le luci di segnalazione della torre di SIDERA lampeggiano lontane;
## - l'asfalto bagnato e le pozze col fango rosso: il fondo specchiato, con l'acqua che increspa, poco
##   sull'asfalto e molto nelle pozze, che hanno un velo di fango rosso; gli attori capovolti sotto i piedi,
##   netti solo dove c'è acqua.
## Solo disegno: ha un generatore casuale suo e la simulazione, i replay e i loro hash non lo vedono.
##
## Uso, dal livello: setup(seme, dati del livello); attach(primo piano, mondo, sfondo, lampioni); a ogni tick
## della simulazione tick(telecamera); a ogni disegno sync(telecamera, combattenti, luci accese). Il titolo la
## usa senza mondo e senza pozze: solo polvere, tinta e luci della torre.

const W := View.W
const H := View.H

## I tre piani della polvere, dal fondo. par: parallasse; n: granelli fuori dalle raffiche (altrettanti
## arrivano con la raffica); v: velocità in px per tick; col: colore; streak: quanti sono strisciate; len:
## lunghezza delle strisciate.
const LAYERS := [
	{"par": 0.45, "n": 16, "v": [0.7, 1.1], "col": Color8(112, 48, 31), "streak": 0.0, "len": [1, 1]},
	{"par": 1.0, "n": 22, "v": [1.6, 2.4], "col": Color8(160, 71, 43), "streak": 0.2, "len": [3, 4]},
	{"par": 1.6, "n": 10, "v": [2.8, 3.8], "col": Color8(192, 106, 69), "streak": 0.45, "len": [4, 6]},
]
## Cadono di 10-15°: px in giù per px in orizzontale.
const FALL := 0.22
const MARGIN := 24.0
## Le raffiche: ogni GUST_EVERY tick (da-a) una raffica di GUST_TICKS; la velocità cresce di GUST_SPEED.
const GUST_EVERY := [240, 480]
const GUST_TICKS := 66
const GUST_SPEED := 1.3
## Il velo della raffica: una fascia bassa, sullo schermo, e quanto copre al massimo.
const VEIL_Y := 192
const VEIL_H := 64
const VEIL_ALPHA := 0.17
const C_LAMP := Color(1.0, 0.78, 0.38)

## La luce della nube sugli attori: rosso-arancio, dall'alto e un po' davanti.
const SKY_COLOR := Color(1.0, 0.47, 0.27)
const SKY_ENERGY := 0.4
const SKY_HEIGHT := 1800.0
const FAR := 3000.0

## Le luci di segnalazione della torre: rosse, lente e in sincrono (accese 0,5 s ogni 1,5 s).
const BEACON_COLOR := Color8(255, 48, 32)
const BEACON_PERIOD := 90
const BEACON_ON := 30

## Come vira ogni piano dipinto: k quanto, haze quanto lo vela la raffica. Il cielo non si tocca: è già la nube.
const GRADE := {
	"far": {"k": 0.45, "haze": 1.0},
	"mid": {"k": 0.85, "haze": 0.8},
	"near": {"k": 1.0, "haze": 0.6},
	"backdrop": {"k": 1.0, "haze": 0.35},
	"floor": {"k": 1.0, "haze": 0.25},
	"fg": {"k": 0.9, "haze": 0.15},
}

const GRADE_SHADER := """shader_type canvas_item;
uniform float k = 1.0;
uniform vec3 mul = vec3(1.24, 0.85, 0.74);
uniform vec3 cloud = vec3(0.48, 0.14, 0.07);
uniform float cloud_k = 0.17;
uniform vec3 dust = vec3(0.36, 0.16, 0.10);
uniform float haze = 0.0;
void fragment() {
	vec3 c = COLOR.rgb;
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	// Le lampade e le insegne dipinte restano com'erano.
	float keep = smoothstep(0.55, 0.85, l);
	float up = clamp(1.0 - SCREEN_UV.y * 1.1, 0.0, 1.0);
	vec3 g = c * mul + cloud * cloud_k * up * up;
	g = mix(g, dust, haze);
	COLOR.rgb = mix(c, g, k * (1.0 - keep));
}
"""

## Le pozze: una maschera grande come il pavimento (r: pozza, g: bordo di fango, b: asfalto, a: pavimento) e
## lo schermo specchiato sopra la linea del muro.
const POZZE_SHADER := """shader_type canvas_item;
uniform sampler2D screen : hint_screen_texture, filter_nearest;
uniform float line_y = 181.0;
uniform float view_h = 270.0;
uniform float wet = 0.16;
uniform float pool = 0.72;
uniform float t = 0.0;
uniform vec3 tint = vec3(1.0, 0.68, 0.56);
uniform vec3 mud = vec3(0.32, 0.12, 0.07);
uniform float mud_k = 0.55;
const float BAYER[16] = float[](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
void fragment() {
	vec4 m = texture(TEXTURE, UV);
	if (m.a < 0.5) { discard; }
	vec2 px = floor(SCREEN_UV / SCREEN_PIXEL_SIZE);
	float d = clamp((px.y - line_y) / max(view_h - line_y, 1.0), 0.0, 1.0);
	float wob = floor(sin(px.y * 0.85 + t * 0.21) * (0.6 + 1.6 * d) * (0.5 + m.r) + 0.5);
	float sy = line_y - (px.y - line_y) * 1.15;
	vec3 c = texture(screen, vec2(SCREEN_UV.x + wob * SCREEN_PIXEL_SIZE.x, (sy + 0.5) * SCREEN_PIXEL_SIZE.y)).rgb;
	float lum = dot(c, vec3(0.299, 0.587, 0.114));
	float s = mix(wet * m.b, pool, m.r);
	float b = (BAYER[int(mod(px.y, 4.0)) * 4 + int(mod(px.x, 4.0))] + 0.5) / 16.0;
	float a = clamp(floor(s * (1.0 - 0.5 * d) * (0.2 + 1.5 * lum) * 4.0 + b) / 4.0, 0.0, 1.0);
	float mk = clamp(floor(mud_k * max(0.45 * m.r, m.g) * 4.0 + b) / 4.0, 0.0, 1.0);
	float A = 1.0 - (1.0 - mk) * (1.0 - a);
	if (A <= 0.0) { discard; }
	COLOR = vec4((mud * mk * (1.0 - a) + c * tint * a) / A, A);
}
"""

## Gli attori capovolti: pieni dove c'è la pozza, poco sull'asfalto, niente fuori dal pavimento.
const ATTORI_SHADER := """shader_type canvas_item;
uniform sampler2D mask : filter_nearest;
uniform vec2 mask_origin = vec2(0.0, 162.0);
uniform vec2 mask_size = vec2(2400.0, 108.0);
uniform float wet = 0.3;
uniform float t = 0.0;
const float BAYER[16] = float[](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
varying vec2 wpos;
void vertex() {
	wpos = VERTEX;
}
void fragment() {
	vec2 px = floor(FRAGCOORD.xy);
	float wob = floor(sin(px.y * 0.85 + t * 0.21) * 0.9 + 0.5);
	vec4 c = texture(TEXTURE, UV + vec2(wob * TEXTURE_PIXEL_SIZE.x, 0.0));
	vec4 m = texture(mask, (floor(wpos) + 0.5 - mask_origin) / mask_size);
	float a = c.a * COLOR.a * mix(wet * m.b, 1.0, m.r) * step(0.5, m.a);
	float b = (BAYER[int(mod(px.y, 4.0)) * 4 + int(mod(px.x, 4.0))] + 0.5) / 16.0;
	a = clamp(floor(a * 4.0 + b) / 4.0, 0.0, 1.0);
	COLOR = vec4(c.rgb * COLOR.rgb, a);
}
"""
const ATTORI_ALPHA := 0.5
const ATTORI_TINT := Color(0.74, 0.50, 0.46)

## Un granello: x e y sullo schermo, piano, velocità, lunghezza, soglia della raffica (0: c'è sempre).
class Grain:
	var x: float
	var y: float
	var layer: int
	var v: float
	var len: int
	var gust_th: float


var _rng := RandomNumberGenerator.new()
var _grains: Array[Grain] = []
var _cam_x: float = 0.0
var _t: int = 0
var _gust_next: int = 0
var _gust_t: int = -1
var _gust: float = 0.0
var _veil_x: float = 0.0
var _veil_tex: Texture2D
var _glow: Glow
var _lamps: Array = []

var _grade_mats: Dictionary = {}
var _pozze: Sprite2D
var _pozze_mat: ShaderMaterial
var _floor_layer: Backdrop.Layer
var _attori: Node2D
var _attori_mat: ShaderMaterial
var _fighters: Array = []
var _sky: PointLight2D
var _beacons: Array[Dictionary] = []
var _beacon_data: Array = []
var _line_y: float = 181.0


func setup(rng_seed: int, data: Dictionary) -> void:
	name = "WindDay"
	_rng.seed = rng_seed * 53 + 11
	for i in LAYERS.size():
		var spec: Dictionary = LAYERS[i]
		for j in int(spec["n"]) * 2:
			var g := Grain.new()
			g.layer = i
			g.v = _rng.randf_range(spec["v"][0], spec["v"][1])
			g.len = 1
			if _rng.randf() < float(spec["streak"]):
				g.len = _rng.randi_range(spec["len"][0], spec["len"][1])
			# La seconda metà arriva solo con la raffica, a soglie diverse.
			g.gust_th = 0.0 if j < int(spec["n"]) else _rng.randf_range(0.1, 0.8)
			g.x = _rng.randf_range(-MARGIN, W + MARGIN)
			g.y = _rng.randf_range(-MARGIN, H)
			_grains.append(g)
	_gust_next = _rng.randi_range(GUST_EVERY[0], GUST_EVERY[1]) / 2
	_beacon_data = data.get("beacons", [])
	_line_y = float(data.get("floor_band", [188, 260])[0]) - 7.0



## `front`: il primo piano (spazio dello schermo); `world`: il mondo (null: niente luce sugli attori né
## pozze); `bd`: lo sfondo; `lamps`: i lampioni, [x, parallasse] per ognuno (vedi lamps_of); `pools`: le pozze.
func attach(front: Node, world: Node2D, bd: Backdrop, lamps: Array, pools: bool = true) -> void:
	z_index = 50
	texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	front.add_child(self)
	_glow = Glow.new(self)
	_lamps = lamps
	_veil_tex = _make_veil()
	if bd != null:
		_grade_backdrop(bd)
		if pools and world != null:
			_add_pozze(bd, world)
		_add_beacons(bd)
	if world != null:
		_add_sky_light(world)


## I lampioni dalle luci del livello (tipo "lamp"): [x, parallasse] per ognuno.
static func lamps_of(data: Dictionary) -> Array:
	var out: Array = []
	for v: Variant in data.get("lights", []):
		if v is Dictionary and str(v.get("kind", "")) == "lamp":
			out.append([float(v.get("x", 0)), float(v.get("scroll", 1.0))])
	return out


## Una volta per tick della simulazione (solo disegno: non tocca lo stato del gioco).
func tick(cam_x: float) -> void:
	var dx := cam_x - _cam_x
	_cam_x = cam_x
	_t += 1
	_update_gust()
	var push := 1.0 + GUST_SPEED * _gust
	for g in _grains:
		var par: float = LAYERS[g.layer]["par"]
		g.x -= g.v * push + dx * par
		g.y += g.v * push * FALL + 0.12 * sin((_t + g.v * 97.0) * 0.06)
		if g.x < -MARGIN or g.y > H + 4.0:
			g.x = W + _rng.randf_range(0.0, MARGIN)
			g.y = _rng.randf_range(-MARGIN, H - 20.0)
		elif g.x > W + MARGIN:
			g.x = -_rng.randf_range(0.0, MARGIN)
	_veil_x += 3.0 + 4.0 * _gust + dx


func _update_gust() -> void:
	if _gust_t < 0 and _t >= _gust_next:
		_gust_t = 0
	if _gust_t >= 0:
		var u := float(_gust_t) / GUST_TICKS
		_gust = sin(PI * clampf(u, 0.0, 1.0))
		_gust_t += 1
		if _gust_t > GUST_TICKS:
			_gust_t = -1
			_gust = 0.0
			_gust_next = _t + _rng.randi_range(GUST_EVERY[0], GUST_EVERY[1])


## Quanto è forte la raffica adesso (0-1).
func gust() -> float:
	return _gust


## A ogni disegno: posizioni, materiali, riflessi e luci.
func sync(cam_x: float, fighters: Array, lights_on: bool) -> void:
	for n: String in _grade_mats:
		(_grade_mats[n] as ShaderMaterial).set_shader_parameter(&"haze", 0.2 * _gust * float(GRADE[n]["haze"]))
	if _pozze != null and not _floor_layer.sprites.is_empty():
		_pozze.position = _floor_layer.sprites[0].position
		_pozze.visible = _floor_layer.node.visible
		_pozze_mat.set_shader_parameter(&"t", float(_t))
	if _attori != null:
		_fighters = fighters
		_attori_mat.set_shader_parameter(&"t", float(_t))
		_attori.queue_redraw()
	if _sky != null:
		_sky.enabled = lights_on
		_sky.position = Vector2(cam_x + W / 2.0, H / 2.0 - FAR)
	for b in _beacons:
		(b["node"] as Node2D).queue_redraw()
	queue_redraw()


# --- La polvere ----------------------------------------------------------------------------------

func _draw() -> void:
	_glow.clear()
	if _gust > 0.0:
		var a := VEIL_ALPHA * _gust
		var off := posmod(int(_veil_x), _veil_tex.get_width())
		draw_texture_rect(_veil_tex, Rect2(-off, VEIL_Y, W + _veil_tex.get_width(), VEIL_H), true,
				Color(LAYERS[1]["col"], a))
	for g in _grains:
		if g.gust_th > 0.0 and _gust < g.gust_th:
			continue
		var col: Color = LAYERS[g.layer]["col"]
		var n := g.len + (roundi(2.0 * _gust) if g.len > 1 else 0)
		var r := Rect2(roundf(g.x), roundf(g.y), n, 1)
		draw_rect(r, col)
		if g.layer > 0:
			var lit := _lamp_light(g.x, g.y)
			if lit > 0.15:
				_glow.rect(r, Color(C_LAMP, 0.5 * lit))


## Quanto il granello in (x, y) sullo schermo sta nel cono di un lampione (0-1).
func _lamp_light(x: float, y: float) -> float:
	if y < 40.0 or y > 200.0:
		return 0.0
	var best := 0.0
	for l: Array in _lamps:
		var lx: float = float(l[0]) - float(l[1]) * _cam_x
		var w := 14.0 + (y - 40.0) * 0.32
		var k := 1.0 - absf(x - lx) / w
		if k > best:
			best = k
	return clampf(best, 0.0, 1.0) * clampf((200.0 - y) / 60.0, 0.0, 1.0)


## Il velo: una trama orizzontale a retinatura, che si ripete in larghezza e sfuma in alto e in basso.
func _make_veil() -> Texture2D:
	const TW := 128
	var img := Image.create_empty(TW, VEIL_H, false, Image.FORMAT_RGBA8)
	for y in VEIL_H:
		var fall := sin(PI * float(y) / (VEIL_H - 1))
		for x in TW:
			var u := TAU * float(x) / TW
			var v := 0.55 + 0.3 * sin(u * 2.0 + 1.3 * sin(y * 0.45)) + 0.2 * sin(u * 5.0 + y * 0.31)
			var a := clampf(v * fall, 0.0, 1.0)
			var th := (float(Glow.BAYER[(y & 3) * 4 + (x & 3)]) + 0.5) / 16.0
			img.set_pixel(x, y, Color(1, 1, 1, 1.0 if a > th else 0.0))
	return ImageTexture.create_from_image(img)


# --- La luce -------------------------------------------------------------------------------------

func _grade_backdrop(bd: Backdrop) -> void:
	var shader := Shader.new()
	shader.code = GRADE_SHADER
	for l: Backdrop.Layer in bd.layers:
		if not GRADE.has(l.name):
			continue
		var m := ShaderMaterial.new()
		m.shader = shader
		m.set_shader_parameter(&"k", float(GRADE[l.name]["k"]))
		_grade_mats[l.name] = m
		for s in l.sprites:
			s.material = m


func _add_sky_light(world: Node2D) -> void:
	var white := Image.create_empty(8, 8, false, Image.FORMAT_RGBA8)
	white.fill(Color.WHITE)
	var tex := ImageTexture.create_from_image(white)
	_sky = PointLight2D.new()
	_sky.name = "LuceDellaNube"
	_sky.texture = tex
	_sky.texture_scale = (FAR + float(W)) * 2.0 / tex.get_width()
	_sky.height = SKY_HEIGHT
	_sky.color = SKY_COLOR
	_sky.energy = SKY_ENERGY
	_sky.blend_mode = Light2D.BLEND_MODE_ADD
	_sky.range_item_cull_mask = Fighter.LIGHT_MASK_ACTORS
	world.add_child(_sky)


## Le luci di segnalazione: un nodo figlio del piano, che si muove con lui.
func _add_beacons(bd: Backdrop) -> void:
	for v: Variant in _beacon_data:
		if not (v is Dictionary):
			continue
		var d: Dictionary = v
		for l: Backdrop.Layer in bd.layers:
			if l.name != str(d.get("layer", "far")) or l.sprites.is_empty():
				continue
			var n := Node2D.new()
			n.name = "LuceTorre"
			l.node.add_child(n)
			var b := {"node": n, "layer": l, "at": Vector2(float(d.get("x", 0)), float(d.get("y", 0))),
				"soft": bool(d.get("soft", false)), "glow": Glow.new(n)}
			n.draw.connect(_draw_beacon.bind(b))
			_beacons.append(b)


func _draw_beacon(b: Dictionary) -> void:
	var glow: Glow = b["glow"]
	glow.clear()
	var l: Backdrop.Layer = b["layer"]
	var k := _beacon_level(_t)
	if k <= 0.0:
		return
	var at: Vector2 = l.sprites[0].position + b["at"]
	var n: Node2D = b["node"]
	if b["soft"]:
		n.draw_rect(Rect2(at, Vector2(1, 1)), Color(BEACON_COLOR, 0.55 * k))
		glow.halo(at, 5, Color(BEACON_COLOR, 0.35 * k))
	else:
		n.draw_rect(Rect2(at, Vector2(1, 1)), Color(BEACON_COLOR.lerp(Color.WHITE, 0.25), k))
		glow.halo(at, 3, Color(BEACON_COLOR, 0.7 * k))


## Acceso BEACON_ON tick ogni BEACON_PERIOD, con due tick di accensione e due di spegnimento.
static func _beacon_level(t: int) -> float:
	var u := t % BEACON_PERIOD
	if u >= BEACON_ON:
		return 0.0
	return clampf(minf(float(u + 1) / 2.0, float(BEACON_ON - u) / 2.0), 0.0, 1.0)


# --- Le pozze ------------------------------------------------------------------------------------

func _add_pozze(bd: Backdrop, world: Node2D) -> void:
	for l: Backdrop.Layer in bd.layers:
		if l.name == "floor":
			_floor_layer = l
	if _floor_layer == null or _floor_layer.texture == null:
		return
	var mask := _puddle_mask(_floor_layer.texture.get_image())
	_pozze = Sprite2D.new()
	_pozze.name = "Pozze"
	_pozze.centered = false
	_pozze.texture = mask
	_pozze.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_pozze_mat = ShaderMaterial.new()
	var ps := Shader.new()
	ps.code = POZZE_SHADER
	_pozze_mat.shader = ps
	_pozze_mat.set_shader_parameter(&"line_y", _line_y)
	_pozze_mat.set_shader_parameter(&"view_h", float(H))
	_pozze.material = _pozze_mat
	_floor_layer.node.add_child(_pozze)

	_attori = Node2D.new()
	_attori.name = "RiflessiAttori"
	_attori.z_index = 59
	_attori.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_attori_mat = ShaderMaterial.new()
	var s := Shader.new()
	s.code = ATTORI_SHADER
	_attori_mat.shader = s
	_attori_mat.set_shader_parameter(&"mask", mask)
	_attori_mat.set_shader_parameter(&"mask_origin", Vector2(_floor_layer.origin_x, _floor_layer.y))
	_attori_mat.set_shader_parameter(&"mask_size", Vector2(mask.get_size()))
	_attori.material = _attori_mat
	_attori.draw.connect(_draw_attori)
	world.add_child(_attori)


func _draw_attori() -> void:
	WetFloor.draw_upside_down(_attori, _fighters, Vector2.ZERO, ATTORI_ALPHA, ATTORI_TINT)


## La maschera delle pozze dal pavimento dipinto: le pozze sono i pixel azzurrini (blu > verde > rosso);
## il bordo di fango è un pixel attorno a ogni pozza; l'asfalto è tutto il resto del pavimento.
static func _puddle_mask(img: Image) -> ImageTexture:
	if img.is_compressed():
		img.decompress()
	var w := img.get_width()
	var h := img.get_height()
	var pool := PackedByteArray()
	pool.resize(w * h)
	for y in h:
		for x in w:
			var c := img.get_pixel(x, y)
			var r8 := c.r8
			var g8 := c.g8
			pool[y * w + x] = 1 if c.a > 0.5 and g8 >= r8 + 4 and c.b8 > g8 + 6 else 0
	var out := Image.create_empty(w, h, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			var c := img.get_pixel(x, y)
			if c.a < 0.5:
				continue
			var p := pool[y * w + x]
			var rim := 0
			for o: Vector2i in [Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, -1), Vector2i(0, 1),
					Vector2i(-2, 0), Vector2i(2, 0)]:
				var xx := x + o.x
				var yy := y + o.y
				if xx >= 0 and yy >= 0 and xx < w and yy < h and pool[yy * w + xx] != p:
					rim = 1
					break
			out.set_pixel(x, y, Color(float(p), float(rim), 1.0, 1.0))
	return ImageTexture.create_from_image(out)
