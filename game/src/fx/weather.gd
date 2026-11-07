class_name Weather
extends Node2D
## Il tempo del prologo (decisioni 5 e 54): il cimitero all'asciutto sotto il sole velato delle 15; quando
## arrivano gli Esattori il cielo si chiude sulle cupole e cadono le prime gocce; poi piove fino al
## garage, dove non piove. Qui c'è tutto il disegno del tempo:
## - la pioggia a quattro strati, con la parallasse e il vento;
## - gli spruzzi sulle cime dei blocchi e i cerchi sul pavimento dell'arena;
## - il cielo e i piani dipinti col sole che si scuriscono e si raffreddano (grade_backdrop);
## - la luce del sole e poi quella della pioggia sugli attori con la normal map (lo shader dei
##   combattenti, Fighter.FLASH_SHADER, maschera Fighter.LIGHT_MASK_ACTORS).
##
## È solo disegno: ha un generatore casuale suo, avanza solo con tick() e legge la griglia dei solidi
## senza cambiarla. La simulazione, i replay e i loro hash non lo vedono.
##
## Uso, da chi ospita (il prologo):
##   setup(griglia, [rettangoli asciutti]); attach(stanza, mondo, stanza_dei_blocchi); grade_backdrop(...)
##   ogni tick, dopo la telecamera, anche durante le scene: tick(rettangolo visibile, zoom[, pavimento])
##   set_rain(true) comincia piano; set_rain(true, true) piove già; set_rain(false) torna all'asciutto
##   sugli attori: modulate = actor_tint(); sul pavimento dell'arena disegnato da codice: ground_tint()
##
## Le gocce vivono sullo schermo (480 × 270): con lo zoom intero delle scene restano fitte uguali e si
## disegnano grandi `zoom` pixel, come il resto del mondo; quelle alla profondità di GIG si disegnano nel
## mondo, dietro gli attori, e si fermano sulle cime dei blocchi.
##
## Orientamento (cronologia, 3.7 e 5.2): il cimitero guarda a ovest-nord-ovest, verso la fabbrica e le
## cupole; alle 15.15 il sole è a sud-ovest, alto 45°: in alto a sinistra e un po' dietro la scena, cioè
## in controluce, come il primo piano dipinto. Il fronte viene da ovest, dietro le cupole; il vento, che
## gira verso libeccio, spinge le gocce verso destra.

const W := View.W
const H := View.H

## Le inclinazioni delle gocce (px in orizzontale per px in giù), a passi: uno sprite per passo.
const SLANT_STEP := 0.0625
const SLANT_MAX := 6
## Il vento a pioggia piena e le raffiche; all'inizio le gocce cadono quasi dritte.
const WIND := 0.19
const WIND_START := 0.04
const GUST := 0.05

## I quattro strati, dal fondo. par: parallasse (come i piani dello sfondo); n: gocce a pioggia piena a
## zoom 1; v: velocità in px per tick (a 60 px/m, 7 px per tick sono 7 m/s, la pioggia vera); len:
## lunghezze degli sprite; w: larghezza; col: colore; z: ordine di disegno (assoluto). Lo strato "gioco"
## ha z 0 nel mondo, subito dopo la stanza dei blocchi, e passa a 61 quando c'è il pavimento dell'arena.
const LAYERS := [
	{"name": "lontana", "par": 0.12, "n": 200, "v": [2.8, 3.6], "len": [3, 4, 5], "w": 1,
		"col": Color(0.74, 0.79, 0.87, 0.26), "z": -95},
	{"name": "media", "par": 0.45, "n": 160, "v": [4.4, 5.4], "len": [5, 6, 8], "w": 1,
		"col": Color(0.78, 0.83, 0.90, 0.40), "z": -85},
	{"name": "gioco", "par": 1.0, "n": 115, "v": [6.6, 8.2], "len": [9, 11, 14], "w": 1,
		"col": Color(0.84, 0.88, 0.95, 0.55), "z": 0},
	{"name": "vicina", "par": 1.6, "n": 15, "v": [13.0, 16.0], "len": [24, 30, 36], "w": 2,
		"col": Color(0.88, 0.92, 0.98, 0.26), "z": 1050},
]
const PLAY := 2
## Margini fuori dallo schermo dove le gocce nascono e si riavvolgono.
const MARGIN_X := 48.0
const MARGIN_Y := 40.0

## Gli spruzzi: tentativi per tick a pioggia piena (sulle cime dei blocchi che si vedono), cerchi per tick
## sul pavimento dell'arena, e le loro durate in tick per fotogramma.
const SPLASH_RATE := 3.2
const RIPPLE_RATE := 4.5
const SPLASH_TICKS := 2
const RIPPLE_TICKS := 3
const C_SPLASH := Color(0.86, 0.90, 0.96, 0.75)
const C_RIPPLE := Color(0.80, 0.85, 0.93, 0.55)

## I tempi, in tick: il cielo si chiude in CLOSE_TICKS (2,5 s); le prime gocce arrivano dopo FIRST_DROP e
## la pioggia è piena dopo FULL_RAIN.
const CLOSE_TICKS := 150
const FIRST_DROP := 30
const FULL_RAIN := 420

## La luce sugli attori. Il sole: caldo, velato, radente da in alto a sinistra: sui bordi della sagoma
## verso il sole arriva il colore della luce, il davanti resta com'è. Con la pioggia il sole si spegne
## quando le nuvole lo coprono e resta la luce fredda del cielo, dall'alto. Sono PointLight2D lontane e
## senza attenuazione, che fanno da luci direzionali: DirectionalLight2D in Godot 4.7.2 non rispetta
## range_item_cull_mask e illuminerebbe anche gli sfondi, che hanno la luce già dipinta.
const SUN_COLOR := Color(1.0, 0.85, 0.66)
const SUN_ENERGY := 1.0
## Direzione verso il sole, sullo schermo: in alto a sinistra, 52° sopra l'orizzontale (cronologia: alle
## 15.15 il sole è a sud-ovest, alto 45°; il cimitero guarda a ovest-nord-ovest). Altezza 0: radente.
## Il controluce vero (il sole un po' dietro gli attori) chiederebbe un'altezza negativa, che Godot ignora.
const SUN_DIR := Vector2(-0.611, -0.792)
const SUN_HEIGHT := 0.0
const SKY_COLOR := Color(0.62, 0.71, 0.84)
const SKY_ENERGY_DRY := 0.10
const SKY_ENERGY_RAIN := 0.32
## La luce del cielo coperto: dall'alto e un po' davanti (altezza in px a FAR px di distanza).
const SKY_DIR := Vector2(0.0, -1.0)
const SKY_HEIGHT := 1800.0
## Le luci stanno a FAR px dal centro dello schermo: la direzione cambia di pochi gradi da un bordo all'altro.
const FAR := 3000.0
## Gli attori: com'erano col sole velato, più scuri e freddi con la pioggia (come il piano della scena),
## ancora di più al chiuso.
const TINT_RAIN := Color(0.80, 0.83, 0.91)
const TINT_INSIDE := Color(0.70, 0.72, 0.80)
## Il pavimento dell'arena (la ghiaia del viale) bagnato.
const TINT_GROUND := Color(0.72, 0.76, 0.86)

## Come la pioggia cambia i piani dipinti col sole velato (il cimitero): moltiplicatore a pioggia piena,
## colore tolto, foschia. Da vicino le cose bagnate si scuriscono ma tengono il colore (il rosa delle
## cappelle resta rosa); da lontano spariscono nel grigio chiaro della pioggia. I piani che non sono qui
## (la fuga, già dipinta con la pioggia) restano come sono. `contrast` riapre i toni che il grigio della
## pioggia schiaccia (Luigi, 7 novembre 2026: la pioggia più fitta, ma senza perdere il colore).
## `lamp_band`: le righe del disegno dove stanno i lumini, che lì hanno l'alone (LUMINI_SHADER); fuori
## dalla fascia lo stesso colore (i riflessi sulle colonne) resta senza.
const GRADE := {
	"cielo": {"sky": true},
	"medio": {"mul": Color(0.80, 0.82, 0.88), "desat": 0.26, "haze": 0.40, "contrast": 0.10},
	"vicino": {"mul": Color(0.74, 0.77, 0.85), "desat": 0.16, "haze": 0.20, "contrast": 0.18},
	"davanti": {"mul": Color(0.64, 0.67, 0.77), "desat": 0.10, "haze": 0.0, "contrast": 0.24, "lamps": true,
		"lamp_band": [252, 276]},
	"scena": {"mul": Color(0.78, 0.80, 0.88), "desat": 0.06, "haze": 0.0, "contrast": 0.20},
}
## Il grigio della pioggia in lontananza: quello del cielo chiuso vicino all'orizzonte.
const HAZE := Color(0.50, 0.54, 0.61)

## Il cielo che si chiude: il fronte delle nuvole entra da destra (dalle cupole) e copre il sole a
## sinistra; sotto la loro base resta il cielo dipinto, più scuro e freddo. Le nuvole sono a gradini,
## coi toni di quelle già dipinte e i bordi netti (due pixel di retinatura): niente sfumature morbide.
## Finché il sole c'è, il bordo del fronte verso di lui è illuminato, come nelle nuvole dipinte.
const SKY_SHADER := """shader_type canvas_item;
uniform float front = 0.0;
uniform float k = 0.0;
uniform float sun = 1.0;
uniform float drift = 0.0;
uniform float base = 92.0;
uniform vec3 mul = vec3(0.66, 0.70, 0.80);
uniform float desat = 0.40;
uniform vec3 c0 = vec3(0.243, 0.302, 0.361);
uniform vec3 c1 = vec3(0.282, 0.357, 0.420);
uniform vec3 c2 = vec3(0.325, 0.396, 0.455);
uniform vec3 c3 = vec3(0.384, 0.443, 0.494);
uniform vec3 c_rim = vec3(0.553, 0.588, 0.612);
uniform vec3 c_lit = vec3(0.871, 0.859, 0.792);

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}
// ottave ruotate: col rumore a griglia dritta, a gradini, si vedrebbero i quadrati
float fbm(vec2 p) {
	float s = 0.0;
	float a = 0.5;
	mat2 r = mat2(vec2(1.6, 1.2), vec2(-1.2, 1.6));
	p = mat2(vec2(0.8, 0.6), vec2(-0.6, 0.8)) * p;
	for (int i = 0; i < 4; i++) {
		s += a * noise(p);
		p = r * p + vec2(17.0, 9.0);
		a *= 0.5;
	}
	return s;
}
float bayer4(vec2 p) {
	int x = int(mod(p.x, 4.0));
	int y = int(mod(p.y, 4.0));
	int m[16] = int[](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
	return (float(m[y * 4 + x]) + 0.5) / 16.0;
}
void fragment() {
	vec2 size = 1.0 / TEXTURE_PIXEL_SIZE;
	vec2 p = floor(UV * size);
	vec3 c = COLOR.rgb;
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	// la luce della pioggia: più scuro e freddo, meno colore, e il chiarore del sole si spegne
	vec3 g = mix(c, vec3(l), desat) * mul;
	g = min(g, vec3(0.62));
	vec3 col = mix(c, g, k);
	// le nuvole: rumore che scorre col vento, il fronte che entra da destra, la base sfrangiata
	vec2 q = vec2(p.x + drift, p.y * 1.6);
	float n = fbm(q / 34.0);
	float big = fbm(q / 80.0 + vec2(31.0, 7.0));
	float edge = mix(size.x + 120.0, -160.0, front);
	float a = (p.x - edge) / 60.0 + (big - 0.5) * 2.8 + (n - 0.5) * 0.9;
	float b = (base - p.y) / 22.0 + (n - 0.5) * 1.5;
	float d = min(a, b);
	// soglia netta: la retinatura prende solo un paio di pixel sul bordo
	float th = (bayer4(p) - 0.5) * 0.1;
	if (d > th) {
		// dentro: toni a gradini, più scuri in basso, verso la base gonfia di pioggia
		float t = fbm(vec2(p.x + drift * 1.3, p.y * 1.8) / 30.0 + vec2(5.0, 3.0));
		float s = t * 0.8 + clamp((p.y - base + 70.0) / 70.0, 0.0, 1.0) * 0.22 + (bayer4(p) - 0.5) * 0.03;
		vec3 cc = s > 0.66 ? c0 : (s > 0.57 ? c1 : (s > 0.48 ? c2 : c3));
		// il bordo del fronte verso il sole: una fascia chiara finché il sole c'è
		if (a < b && d < 0.16 + th) {
			cc = mix(cc, mix(c_rim, c_lit, 0.45), sun);
		}
		col = cc;
	}
	COLOR.rgb = col;
}
"""

## La luce della pioggia sui piani dipinti col sole velato: più scuri e freddi, meno colore, la foschia
## in lontananza. Nel primo piano i lumini (la fiamma dipinta, 229 186 138: chiara, calda, poco blu)
## restano accesi; con il bagliore (set_glow) diventano più forti del bianco e brillano.
const GRADE_SHADER := """shader_type canvas_item;
uniform float k = 0.0;
uniform vec3 mul = vec3(0.7, 0.75, 0.85);
uniform float desat = 0.3;
uniform vec3 haze = vec3(0.43, 0.48, 0.56);
uniform float haze_k = 0.0;
uniform float lamps = 0.0;
uniform float glow = 1.0;
uniform float contrast = 0.0;
void fragment() {
	vec3 c = COLOR.rgb;
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	vec3 g = mix(mix(c, vec3(l), desat) * mul, haze, haze_k);
	g = clamp((g - 0.40) * (1.0 + contrast) + 0.40, 0.0, 1.0);
	float lamp = lamps * step(0.85, c.r) * step(0.5, c.g) * step(c.b, 0.56);
	COLOR.rgb = mix(c, g, k * (1.0 - lamp)) * mix(1.0, glow, lamp);
}
"""

## L'alone dei lumini, il bagliore finto in pixel art (senza HDR): uno sprite in additivo sopra il
## piano, con la stessa texture, che somma i texel color fiamma vicini (solo nella fascia `band`), a
## gradini con la retinatura di Bayer sui texel, così l'alone non scivola quando la telecamera si muove.
const LUMINI_SHADER := """shader_type canvas_item;
render_mode blend_add;
uniform float k = 0.0;
uniform vec2 band = vec2(252.0, 276.0);
uniform vec3 tint = vec3(1.0, 0.66, 0.34);
const float BAYER[16] = float[](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
const int R = 5;
void fragment() {
	vec2 tp = floor(UV / TEXTURE_PIXEL_SIZE);
	float s = 0.0;
	if (k > 0.0 && tp.y >= band.x - float(R) && tp.y <= band.y + float(R)) {
		for (int dy = -R; dy <= R; dy++) {
			float y = tp.y + float(dy);
			if (y < band.x || y > band.y) {
				continue;
			}
			for (int dx = -R; dx <= R; dx++) {
				float d = length(vec2(float(dx), float(dy))) / (float(R) + 0.5);
				if (d >= 1.0) {
					continue;
				}
				vec4 c = texture(TEXTURE, (vec2(tp.x + float(dx), y) + 0.5) * TEXTURE_PIXEL_SIZE);
				float lamp = c.a * step(0.85, c.r) * step(0.5, c.g) * step(c.b, 0.56);
				s += lamp * (1.0 - d) * (1.0 - d);
			}
		}
	}
	float a = clamp(s * 0.16, 0.0, 0.8) * k;
	float b = (BAYER[int(mod(tp.y, 4.0)) * 4 + int(mod(tp.x, 4.0))] + 0.5) / 16.0;
	a = clamp(floor(a * 4.0 + b) / 4.0, 0.0, 1.0);
	COLOR = vec4(tint, a);
}
"""

static var _sky_shader: Shader
static var _grade_shader: Shader
static var _lumini_shader: Shader


## Uno strato di gocce: posizioni sullo schermo e il resto, una voce per goccia.
class Layer:
	var spec: Dictionary
	var par: float = 1.0
	var n: int = 0
	var x: PackedFloat32Array = PackedFloat32Array()
	var y: PackedFloat32Array = PackedFloat32Array()
	var v: PackedFloat32Array = PackedFloat32Array()
	## Sullo strato del gioco: dove cade sul pavimento dell'arena (0-1 della profondità).
	var depth: PackedFloat32Array = PackedFloat32Array()
	## Riga (inclinazione) e colonna (lunghezza) dello sprite.
	var row: PackedInt32Array = PackedInt32Array()
	var col: PackedInt32Array = PackedInt32Array()
	## La goccia c'è se la sua soglia è sotto la densità: le prime a comparire sono sempre le stesse.
	var gate: PackedFloat32Array = PackedFloat32Array()
	var on: PackedByteArray = PackedByteArray()
	var atlas: Texture2D
	var cell: Vector2i = Vector2i.ONE
	var anchors: Array[Vector2i] = []
	var lens: int = 1
	var node: Node2D


var grid: SolidGrid
## I rettangoli del mondo dove non piove (il dentro del garage).
var dry: Array[Rect2] = []
## Piove (anche mentre il cielo si sta ancora chiudendo).
var raining: bool = false

var _rng := RandomNumberGenerator.new()
var _layers: Array[Layer] = []
## Per colonna di celle: la y della prima cima col cielo sopra (piena o sottile); oltre il fondo se non c'è.
var _tops: PackedInt32Array = PackedInt32Array()
var _t: int = 0
## Tick da quando piove (-1: asciutto).
var _rain_t: int = -1
var _view: Rect2 = Rect2(Vector2.ZERO, View.SIZE)
var _zoom: float = 1.0
var _prev_c: Vector2 = Vector2.ZERO
var _has_prev: bool = false
var _floor: Rect2 = Rect2()
var _inside: float = 0.0
## Spruzzi e cerchi: x e y nel mondo, età in tick, tipo (0 spruzzo, 1 cerchio).
var _sp_x: PackedFloat32Array = PackedFloat32Array()
var _sp_y: PackedFloat32Array = PackedFloat32Array()
var _sp_age: PackedInt32Array = PackedInt32Array()
var _sp_kind: PackedByteArray = PackedByteArray()
var _splash_acc: float = 0.0
var _ripple_acc: float = 0.0
var _splash_tex: Texture2D
var _world_node: Node2D
var _sun: PointLight2D
var _sky: PointLight2D
var _sky_mats: Array[ShaderMaterial] = []
var _grade_mats: Array[ShaderMaterial] = []
var _lumini_mats: Array[ShaderMaterial] = []
var _lamp_glow: float = 1.0


## Prepara il tempo sopra `grid` (le cime dei blocchi col cielo sopra fermano le gocce e fanno gli
## spruzzi). `dry_rects`: i rettangoli del mondo dove non piove. `rng_seed`: il seme del disegno.
func setup(solid: SolidGrid, dry_rects: Array = [], rng_seed: int = 1) -> void:
	grid = solid
	dry.clear()
	for r: Variant in dry_rects:
		dry.append(r as Rect2)
	_rng.seed = rng_seed * 7919 + 13
	refresh_surfaces()
	_layers.clear()
	for spec: Dictionary in LAYERS:
		_layers.append(_make_layer(spec))
	_splash_tex = _make_splash_atlas()


## Le cime col cielo sopra, da rifare se la griglia cambia sopra il pavimento (le porte del prologo no:
## stanno sotto il muro).
func refresh_surfaces() -> void:
	_tops.resize(grid.width)
	for cx in grid.width:
		_tops[cx] = grid.pixel_height() + 1000
		for cy in grid.height:
			if grid.cell(cx, cy) != SolidGrid.Cell.EMPTY:
				_tops[cx] = cy * SolidGrid.TILE
				break


## Aggiunge i nodi: gli strati sullo schermo e le luci sotto `screen` (il nodo della stanza, con la
## trasformazione dello schermo); lo strato del gioco e gli spruzzi dentro `world` (il nodo che la
## telecamera sposta e ingrandisce), subito dopo `after` (la stanza dei blocchi), dietro agli attori.
func attach(screen: Node, world: Node2D, after: Node = null) -> void:
	name = "Tempo"
	screen.add_child(self)
	for i in _layers.size():
		var l := _layers[i]
		l.node = Node2D.new()
		l.node.name = "Pioggia_" + str(l.spec["name"])
		if i == PLAY:
			world.add_child(l.node)
			if after != null and after.get_parent() == world:
				world.move_child(l.node, after.get_index() + 1)
			l.node.draw.connect(_draw_world.bind(l))
			_world_node = l.node
		else:
			l.node.z_as_relative = false
			l.node.z_index = int(l.spec["z"])
			add_child(l.node)
			l.node.draw.connect(_draw_screen.bind(l))
	_build_lights()


## Il cielo e i piani del cimitero si chiudono con la pioggia: lo shader del cielo e quello della luce
## della pioggia sui piani di `bd` con un nome in GRADE, e sugli sprite di `scene_art` (la scena del
## cimitero, con le regole di "scena"). I piani della fuga, già dipinti con la pioggia, restano com'erano.
func grade_backdrop(bd: Backdrop, scene_art: Array = []) -> void:
	if bd != null:
		for l: Backdrop.Layer in bd.layers:
			if GRADE.has(l.name):
				for s in l.sprites:
					s.material = _material_for(l.name)
					if GRADE[l.name].has("lamp_band"):
						_add_lumini(s, GRADE[l.name]["lamp_band"])
	for s: Variant in scene_art:
		if s is CanvasItem:
			(s as CanvasItem).material = _material_for("scena")
	_update_materials()


## Comincia a piovere: piano (il cielo si chiude, poi le prime gocce) o, con `immediate`, già a pioggia
## piena (le ripartenze dopo l'arena). Con `on` falso torna subito all'asciutto (le ripartenze di prima).
func set_rain(on: bool, immediate: bool = false) -> void:
	if on == raining and not immediate:
		return
	raining = on
	if not on:
		_rain_t = -1
		_clear_drops()
	elif immediate:
		_rain_t = FULL_RAIN + CLOSE_TICKS
		for l in _layers:
			for i in l.n:
				_respawn(l, i, _rng.randf_range(-MARGIN_Y, H))
	else:
		_rain_t = 0
	_update_materials()
	_update_lights()


## Quanto si è chiuso il cielo (0-1).
func closing() -> float:
	if _rain_t < 0:
		return 0.0
	return _smooth(float(_rain_t) / CLOSE_TICKS)


## Quanto è fitta la pioggia (0-1): prima poche gocce, poi sempre di più.
func density() -> float:
	if _rain_t < FIRST_DROP:
		return 0.0
	var k := clampf(float(_rain_t - FIRST_DROP) / (FULL_RAIN - FIRST_DROP), 0.0, 1.0)
	return 0.08 + 0.92 * k * k


## Quanto si vede ancora il sole (0-1): si spegne quando il fronte gli passa sopra.
func sun_visible() -> float:
	return 1.0 - _smooth((closing() - 0.4) / 0.45)


## La luce della pioggia sui piani e sugli attori (0-1): segue il sole che si copre.
func rain_light() -> float:
	return clampf(0.25 * closing() + 0.75 * (1.0 - sun_visible()), 0.0, 1.0)


## Il colore per il modulate degli attori.
func actor_tint() -> Color:
	var c := Color.WHITE.lerp(TINT_RAIN, rain_light())
	return c.lerp(TINT_INSIDE, _inside)


## Il colore per il modulate del pavimento dell'arena disegnato da codice.
func ground_tint() -> Color:
	return Color.WHITE.lerp(TINT_GROUND, rain_light())


## Il vento adesso: inclinazione delle gocce, con le raffiche.
func wind() -> float:
	var base := lerpf(WIND_START, WIND, closing())
	return base + GUST * (0.7 * sin(_t * 0.011) + 0.3 * sin(_t * 0.037 + 1.3)) * closing()


## Un tick di disegno, dopo la telecamera. `view`: il rettangolo del mondo che si vede; `zoom`: lo zoom
## delle scene; `floor_band`: il pavimento dell'arena in profondità, in coordinate del mondo (vuoto fuori
## dall'arena).
func tick(view: Rect2, zoom: float, floor_band: Rect2 = Rect2()) -> void:
	_t += 1
	if _rain_t >= 0:
		_rain_t += 1
	_view = view
	_zoom = maxf(zoom, 0.01)
	_floor = floor_band
	var c := view.get_center()
	var dc := c - _prev_c if _has_prev else Vector2.ZERO
	# Uno stacco (una ripartenza, un cambio d'inquadratura): niente scia della parallasse.
	if dc.length() > 160.0:
		dc = Vector2.ZERO
	_prev_c = c
	_has_prev = true
	var inside := 1.0 if _is_dry(c) else 0.0
	_inside = move_toward(_inside, inside, 1.0 / 30.0)
	var dens := density()
	for i in _layers.size():
		_tick_layer(_layers[i], i == PLAY, dc, dens)
	_tick_splashes(dens)
	if _world_node != null:
		# Nell'arena gli spruzzi stanno sopra il pavimento in profondità (z 1) e sotto le ombre (60).
		_world_node.z_as_relative = floor_band.size.y <= 0.0
		_world_node.z_index = 0 if floor_band.size.y <= 0.0 else 61
	_update_materials()
	_update_lights()
	for l in _layers:
		if l.node != null:
			l.node.queue_redraw()


# ------------------------------------------------------------------ gocce

func _make_layer(spec: Dictionary) -> Layer:
	var l := Layer.new()
	l.spec = spec
	l.par = float(spec["par"])
	l.n = int(spec["n"])
	var lens := PackedInt32Array()
	for v: Variant in spec["len"]:
		lens.append(int(v))
	l.lens = lens.size()
	_streak_atlas(l, lens, int(spec["w"]))
	l.x.resize(l.n)
	l.y.resize(l.n)
	l.v.resize(l.n)
	l.depth.resize(l.n)
	l.gate.resize(l.n)
	l.row.resize(l.n)
	l.col.resize(l.n)
	l.on.resize(l.n)
	for i in l.n:
		l.gate[i] = _rng.randf()
		_respawn(l, i, _rng.randf_range(-MARGIN_Y, H))
		l.on[i] = 0
	return l


## Una goccia nuova in alto (o all'altezza `at_y`), con la velocità, la lunghezza e l'inclinazione del
## vento di adesso; c'è solo se la sua soglia è sotto la densità.
func _respawn(l: Layer, i: int, at_y: float = NAN) -> void:
	var vr: Array = l.spec["v"]
	l.v[i] = _rng.randf_range(float(vr[0]), float(vr[1]))
	l.col[i] = _rng.randi_range(0, l.lens - 1)
	var s := wind() + _rng.randf_range(-0.03, 0.03)
	l.row[i] = clampi(roundi(s / SLANT_STEP), -SLANT_MAX, SLANT_MAX) + SLANT_MAX
	l.x[i] = _rng.randf_range(-MARGIN_X, W + MARGIN_X)
	l.y[i] = at_y if not is_nan(at_y) else -_rng.randf_range(0.0, MARGIN_Y)
	l.depth[i] = _rng.randf()
	l.on[i] = 1 if l.gate[i] < density() else 0


func _clear_drops() -> void:
	for l in _layers:
		for i in l.n:
			l.on[i] = 0
	_sp_x.clear()
	_sp_y.clear()
	_sp_age.clear()
	_sp_kind.clear()


func _tick_layer(l: Layer, play: bool, dc: Vector2, dens: float) -> void:
	var z := _zoom
	var shift := dc * z * l.par
	var span := W + 2.0 * MARGIN_X
	for i in l.n:
		var s := float(l.row[i] - SLANT_MAX) * SLANT_STEP
		var v := l.v[i] * z
		l.x[i] += s * v - shift.x
		l.y[i] += v - shift.y
		if l.x[i] < -MARGIN_X:
			l.x[i] += span
		elif l.x[i] >= W + MARGIN_X:
			l.x[i] -= span
		if l.y[i] < -MARGIN_Y - 60.0:
			# La telecamera è scesa di colpo: la goccia rientra da sotto.
			l.y[i] += H + 2.0 * MARGIN_Y
		var ch := float(l.cell.y) * maxf(1.0, roundf(z))
		var gone := l.y[i] - ch > H + 4.0
		if play and l.on[i] == 1 and not gone:
			var w := _to_world(Vector2(l.x[i], l.y[i]))
			var ground := _ground(w.x, l.depth[i])
			if w.y >= ground:
				# Arrivata a terra: sul pavimento dell'arena fa un cerchio, sulle cime uno spruzzo.
				if not _is_dry(Vector2(w.x, ground - 1.0)) and _view.has_point(Vector2(w.x, ground - 1.0)):
					_add_splash(w.x, ground, 1 if _on_floor_band(w.x, ground) else 0)
				gone = true
			elif _is_dry(w):
				gone = true
		if gone:
			_respawn(l, i)
		elif l.on[i] == 0 and l.y[i] < 0.0 and l.gate[i] < dens:
			# Le gocce nuove si accendono solo fuori dallo schermo, in alto: niente gocce che compaiono.
			l.on[i] = 1


## Dove cade a terra una goccia nella colonna `wx` del mondo: la prima cima col cielo sopra; sul
## pavimento dell'arena, alla sua profondità.
func _ground(wx: float, depth: float) -> float:
	var cx := floori(wx / SolidGrid.TILE)
	if cx < 0 or cx >= _tops.size():
		return INF
	var top := float(_tops[cx])
	if _floor.size.y > 0.0 and absf(top - _floor.position.y) < 1.0 and wx >= _floor.position.x and wx < _floor.end.x:
		return top + roundf(depth * (_floor.size.y - 1.0))
	return top


func _on_floor_band(wx: float, wy: float) -> bool:
	return _floor.size.y > 0.0 and _floor.has_point(Vector2(wx, wy - 0.5)) and wy > _floor.position.y + 0.5


func _to_world(s: Vector2) -> Vector2:
	return _view.get_center() + (s - View.SIZE / 2.0) / _zoom


func _is_dry(p: Vector2) -> bool:
	for r in dry:
		if r.has_point(p):
			return true
	return false


# ------------------------------------------------------------------ spruzzi

func _tick_splashes(dens: float) -> void:
	var keep := 0
	for i in _sp_x.size():
		_sp_age[i] += 1
		var life := 4 * SPLASH_TICKS if _sp_kind[i] == 0 else 5 * RIPPLE_TICKS
		if _sp_age[i] < life:
			_sp_x[keep] = _sp_x[i]
			_sp_y[keep] = _sp_y[i]
			_sp_age[keep] = _sp_age[i]
			_sp_kind[keep] = _sp_kind[i]
			keep += 1
	_sp_x.resize(keep)
	_sp_y.resize(keep)
	_sp_age.resize(keep)
	_sp_kind.resize(keep)
	if dens <= 0.0:
		return
	# Sulle cime che si vedono: si prova una x a caso dello schermo e si guarda la sua cima.
	_splash_acc += SPLASH_RATE * dens
	while _splash_acc >= 1.0:
		_splash_acc -= 1.0
		var wx := _view.position.x + _rng.randf() * _view.size.x
		var cx := floori(wx / SolidGrid.TILE)
		if cx < 0 or cx >= _tops.size():
			continue
		var top := float(_tops[cx])
		if _floor.size.y > 0.0 and absf(top - _floor.position.y) < 1.0:
			continue
		var p := Vector2(wx, top - 1.0)
		if _view.has_point(p) and not _is_dry(p):
			_add_splash(roundf(wx), top, 0)
	if _floor.size.y > 0.0:
		_ripple_acc += RIPPLE_RATE * dens
		while _ripple_acc >= 1.0:
			_ripple_acc -= 1.0
			var r := _floor.intersection(_view)
			if r.size.x <= 0.0 or r.size.y <= 2.0:
				break
			_add_splash(roundf(r.position.x + _rng.randf() * r.size.x), roundf(r.position.y + 1.0 + _rng.randf() * (r.size.y - 2.0)), 1)


func _add_splash(x: float, y: float, kind: int) -> void:
	if _sp_x.size() >= 160:
		return
	_sp_x.append(roundf(x))
	_sp_y.append(roundf(y))
	_sp_age.append(0)
	_sp_kind.append(kind)


# ------------------------------------------------------------------ disegno

func _draw_screen(l: Layer) -> void:
	var ci := l.node
	var zi := maxf(1.0, roundf(_zoom))
	var c: Color = l.spec["col"]
	var size := Vector2(l.cell) * zi
	var check_dry := not dry.is_empty() and l.par > 1.0
	for i in l.n:
		if l.on[i] == 0:
			continue
		var p := Vector2(roundf(l.x[i]), roundf(l.y[i]))
		if check_dry and _is_dry(_to_world(p)):
			continue
		var k := l.row[i] * l.lens + l.col[i]
		var a := l.anchors[k]
		ci.draw_texture_rect_region(l.atlas, Rect2(p - Vector2(a) * zi, size),
			Rect2(Vector2(l.col[i] * l.cell.x, l.row[i] * l.cell.y), Vector2(l.cell)), c)


## Lo strato del gioco e gli spruzzi, nel mondo (la telecamera li sposta e li ingrandisce).
func _draw_world(l: Layer) -> void:
	var ci := l.node
	var c: Color = l.spec["col"]
	for i in l.n:
		if l.on[i] == 0:
			continue
		var w := _to_world(Vector2(l.x[i], l.y[i])).round()
		if _is_dry(w):
			continue
		var k := l.row[i] * l.lens + l.col[i]
		var a := l.anchors[k]
		ci.draw_texture_rect_region(l.atlas, Rect2(w - Vector2(a), Vector2(l.cell)),
			Rect2(Vector2(l.col[i] * l.cell.x, l.row[i] * l.cell.y), Vector2(l.cell)), c)
	for i in _sp_x.size():
		var kind := int(_sp_kind[i])
		var f := _sp_age[i] / (SPLASH_TICKS if kind == 0 else RIPPLE_TICKS)
		var src := Rect2(f * 11, kind * 5, 11, 5)
		# L'impatto (5, 4) dello spruzzo sta sulla riga sopra la cima; il cerchio sul suo punto del pavimento.
		var dy := 5.0 if kind == 0 else 4.0
		ci.draw_texture_rect_region(_splash_tex, Rect2(_sp_x[i] - 5.0, _sp_y[i] - dy, 11, 5), src,
			C_SPLASH if kind == 0 else C_RIPPLE)


## Gli sprite delle gocce di uno strato: una riga per inclinazione, una colonna per lunghezza. Testa in
## basso, piena; coda in alto, sempre più trasparente a tre gradini, come la pixel art. Larghe 2, hanno
## a destra una riga più tenue.
static func _streak_atlas(l: Layer, lens: PackedInt32Array, width: int) -> void:
	var max_len := 0
	for n in lens:
		max_len = maxi(max_len, n)
	var cw := ceili(SLANT_STEP * SLANT_MAX * max_len) + width + 1
	var ch := max_len
	var rows := 2 * SLANT_MAX + 1
	var img := Image.create_empty(cw * lens.size(), ch * rows, false, Image.FORMAT_RGBA8)
	l.anchors.clear()
	for r in rows:
		var s := float(r - SLANT_MAX) * SLANT_STEP
		for ci in lens.size():
			var n := lens[ci]
			var min_x := 0
			for k in n:
				min_x = mini(min_x, -roundi(s * k))
			var hx := -min_x
			for k in n:
				var a := 1.0 if k < n * 0.3 else (0.62 if k < n * 0.66 else 0.3)
				var px := ci * cw + hx - roundi(s * k)
				var py := r * ch + ch - 1 - k
				img.set_pixel(px, py, Color(1, 1, 1, a))
				if width > 1:
					img.set_pixel(px + 1, py, Color(1, 1, 1, a * 0.4))
			l.anchors.append(Vector2i(hx, ch - 1))
	l.atlas = ImageTexture.create_from_image(img)
	l.cell = Vector2i(cw, ch)


## Gli spruzzi, fotogrammi da 11 × 5 con l'impatto in (5, 4): in alto la corona vista di lato (4
## fotogrammi), sotto il cerchio visto dall'alto, schiacciato dalla prospettiva (5 fotogrammi).
static func _make_splash_atlas() -> Texture2D:
	var img := Image.create_empty(11 * 5, 10, false, Image.FORMAT_RGBA8)
	var crown := [
		[[5, 4, 1.0], [5, 3, 0.7]],
		[[4, 3, 1.0], [6, 3, 1.0], [5, 4, 0.5]],
		[[3, 2, 0.9], [7, 2, 0.9], [4, 3, 0.4], [6, 3, 0.4]],
		[[2, 3, 0.6], [8, 3, 0.6], [3, 2, 0.25], [7, 2, 0.25]],
	]
	var ring := [
		[[5, 4, 1.0]],
		[[4, 4, 0.9], [6, 4, 0.9]],
		[[3, 4, 0.75], [7, 4, 0.75], [4, 3, 0.6], [5, 3, 0.6], [6, 3, 0.6]],
		[[2, 4, 0.5], [8, 4, 0.5], [3, 3, 0.45], [7, 3, 0.45], [5, 3, 0.3]],
		[[1, 4, 0.3], [9, 4, 0.3], [2, 3, 0.25], [8, 3, 0.25]],
	]
	for f in crown.size():
		for p: Array in crown[f]:
			img.set_pixel(f * 11 + int(p[0]), int(p[1]), Color(1, 1, 1, float(p[2])))
	for f in ring.size():
		for p: Array in ring[f]:
			img.set_pixel(f * 11 + int(p[0]), 5 + int(p[1]), Color(1, 1, 1, float(p[2])))
	return ImageTexture.create_from_image(img)


# ------------------------------------------------------------------ cielo, piani e luce

## L'alone dei lumini sopra lo sprite `s` del piano: un figlio con la stessa texture, in additivo.
func _add_lumini(s: Sprite2D, band: Array) -> void:
	if _lumini_shader == null:
		_lumini_shader = Shader.new()
		_lumini_shader.code = LUMINI_SHADER
	var m := ShaderMaterial.new()
	m.shader = _lumini_shader
	m.set_shader_parameter(&"band", Vector2(float(band[0]), float(band[1])))
	var h := Sprite2D.new()
	h.name = "AloneLumini"
	h.texture = s.texture
	h.centered = false
	h.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	h.material = m
	s.add_child(h)
	_lumini_mats.append(m)


func _material_for(layer_name: String) -> ShaderMaterial:
	var g: Dictionary = GRADE[layer_name]
	var m := ShaderMaterial.new()
	if g.has("sky"):
		if _sky_shader == null:
			_sky_shader = Shader.new()
			_sky_shader.code = SKY_SHADER
		m.shader = _sky_shader
		_sky_mats.append(m)
		return m
	if _grade_shader == null:
		_grade_shader = Shader.new()
		_grade_shader.code = GRADE_SHADER
	m.shader = _grade_shader
	var mul: Color = g["mul"]
	m.set_shader_parameter(&"mul", Vector3(mul.r, mul.g, mul.b))
	m.set_shader_parameter(&"desat", float(g["desat"]))
	m.set_shader_parameter(&"haze", Vector3(HAZE.r, HAZE.g, HAZE.b))
	m.set_shader_parameter(&"haze_k", float(g["haze"]))
	m.set_shader_parameter(&"contrast", float(g.get("contrast", 0.0)))
	m.set_shader_parameter(&"lamps", 1.0 if g.get("lamps", false) else 0.0)
	m.set_shader_parameter(&"glow", _lamp_glow)
	_grade_mats.append(m)
	return m


func _update_materials() -> void:
	var front := closing()
	var k := rain_light()
	for m in _sky_mats:
		m.set_shader_parameter(&"front", front)
		m.set_shader_parameter(&"k", k)
		m.set_shader_parameter(&"sun", sun_visible())
		m.set_shader_parameter(&"drift", _t * 0.12)
	for m in _grade_mats:
		m.set_shader_parameter(&"k", k)
	# Con il sole i lumini quasi non si vedono; con la pioggia e il cielo chiuso brillano.
	for m in _lumini_mats:
		m.set_shader_parameter(&"k", 0.3 + 0.7 * k)


func _build_lights() -> void:
	var white := Image.create_empty(8, 8, false, Image.FORMAT_RGBA8)
	white.fill(Color.WHITE)
	var tex := ImageTexture.create_from_image(white)
	_sun = _far_light("Sole", tex, SUN_COLOR, SUN_DIR, SUN_HEIGHT)
	_sky = _far_light("LuceDelCielo", tex, SKY_COLOR, SKY_DIR, SKY_HEIGHT)
	_update_lights()


## Una luce lontana che fa da direzionale: solo sugli attori con la normal map, uguale su tutto lo schermo.
func _far_light(light_name: String, tex: Texture2D, color: Color, dir: Vector2, height: float) -> PointLight2D:
	var l := PointLight2D.new()
	l.name = light_name
	l.texture = tex
	l.texture_scale = (FAR + float(W)) * 2.0 / tex.get_width()
	l.position = View.SIZE / 2.0 + dir.normalized() * FAR
	l.height = height
	l.color = color
	l.energy = 0.0
	l.blend_mode = Light2D.BLEND_MODE_ADD
	l.range_item_cull_mask = Fighter.LIGHT_MASK_ACTORS
	l.enabled = not Game.options.no_lights
	add_child(l)
	return l


func _update_lights() -> void:
	if _sun == null:
		return
	var out := 1.0 - _inside
	_sun.energy = SUN_ENERGY * sun_visible() * out
	_sky.energy = lerpf(SKY_ENERGY_DRY, SKY_ENERGY_RAIN, rain_light()) * out


## Con il bagliore di PostFx acceso: i lumini dipinti più forti del bianco (`k` volte), così brillano.
func set_glow(k: float) -> void:
	_lamp_glow = maxf(k, 1.0)
	for m in _grade_mats:
		m.set_shader_parameter(&"glow", _lamp_glow)


## Le luci del tempo accese o spente (F5 nel livello, --no-lights).
func set_lights(on: bool) -> void:
	for l: PointLight2D in [_sun, _sky]:
		if l != null:
			l.enabled = on


static func _smooth(k: float) -> float:
	k = clampf(k, 0.0, 1.0)
	return k * k * (3.0 - 2.0 * k)
