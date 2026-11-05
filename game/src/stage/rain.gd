class_name Rain
extends Node2D
## Pioggia leggera in spazio schermo, con un generatore con seme proprio (deterministica).
## Le gocce scorrono con il mondo quando la telecamera si muove; quando toccano il suolo,
## nella fascia calpestabile, lasciano uno spruzzo. Usa gli sprite "rain_streak" e
## "rain_splash" di fx.json se ci sono, altrimenti disegna linee e pixel.
## Le gocce stanno in primo piano; gli spruzzi, se c'è un nodo apposito (set_splash_canvas),
## si disegnano lì, sotto gli attori, così non compaiono sopra gambe e stivali.

const VIEW := View.SIZE_I
const DROPS := 64
const SLANT := 0.25

var fx: FxLayer
var band: Vector2 = Vector2(188, 260)

var _rng: RandomNumberGenerator = RandomNumberGenerator.new()
## Per goccia: x nel mondo, y, velocità, lunghezza, y del suolo dove finisce.
var _drops: Array[PackedFloat32Array] = []
## Spruzzi: x nel mondo, y, età.
var _splashes: Array[PackedFloat32Array] = []
var _cam_x: int = 0
## Nodo che disegna gli spruzzi sotto gli attori (null = li disegna la pioggia, in primo piano).
var _splash_canvas: Node2D
## Il nodo degli spruzzi sta nel mondo (la telecamera lo sposta) e non in spazio schermo.
var _splash_world: bool = false


func setup(rng_seed: int, fx_layer: FxLayer, floor_band: Vector2) -> void:
	_rng.seed = rng_seed * 31 + 5
	fx = fx_layer
	band = floor_band
	for i in DROPS:
		_drops.append(_new_drop(_rng.randf_range(-25.0, VIEW.y)))


## Gli spruzzi si disegnano in `canvas`, da mettere sotto gli attori. `world_space`: il nodo è
## nel mondo e la telecamera lo sposta da sé (nel livello); altrimenti è in spazio schermo.
func set_splash_canvas(canvas: Node2D, world_space: bool) -> void:
	_splash_canvas = canvas
	_splash_world = world_space
	canvas.draw.connect(_draw_splashes.bind(canvas))


func _new_drop(y: float) -> PackedFloat32Array:
	var ground := _rng.randf_range(band.x - 50.0, band.y + 10.0)
	return PackedFloat32Array([_cam_x + _rng.randf_range(-25.0, VIEW.x + 50.0), y, _rng.randf_range(6.875, 9.375), _rng.randf_range(6.25, 11.25), ground])


func tick(cam_x: int) -> void:
	_cam_x = cam_x
	for i in _drops.size():
		var d := _drops[i]
		d[1] += d[2]
		d[0] -= d[2] * SLANT
		if d[1] >= d[4]:
			if d[4] >= band.x - 2.5:
				_splashes.append(PackedFloat32Array([d[0], d[4], 0]))
			d = _new_drop(_rng.randf_range(-38.0, -5.0))
		var sx := d[0] - cam_x
		if sx < -38.0 or sx > VIEW.x + 63.0:
			d[0] = cam_x + posmod(int(sx), VIEW.x + 75) - 25
		_drops[i] = d
	var keep: Array[PackedFloat32Array] = []
	var splash: FxLayer.FxDef = fx.defs.get(&"rain_splash") if fx != null else null
	var life := splash.count * splash.ticks if splash != null else 9
	for s in _splashes:
		s[2] += 1
		if s[2] < life:
			keep.append(s)
	_splashes = keep
	queue_redraw()
	if _splash_canvas != null:
		_splash_canvas.queue_redraw()


func _draw() -> void:
	var streak: FxLayer.FxDef = fx.defs.get(&"rain_streak") if fx != null else null
	var splash: FxLayer.FxDef = fx.defs.get(&"rain_splash") if fx != null else null
	for d in _drops:
		var x := roundf(d[0] - _cam_x)
		var y := roundf(d[1])
		if streak != null:
			# Ogni goccia usa sempre la stessa variante (lunghezza) della striscia.
			var v := int(d[3] * 7.0) % streak.count
			draw_texture_rect_region(streak.texture, Rect2(x - streak.anchor.x, y - streak.anchor.y, streak.frame.x, streak.frame.y), Rect2(v * streak.frame.x, 0, streak.frame.x, streak.frame.y))
		else:
			var l := d[3]
			draw_line(Vector2(x, y), Vector2(x + l * SLANT, y - l), Color(0.62, 0.66, 0.95, 0.35), 1.0)
	if _splash_canvas == null:
		_draw_splashes(self)


func _draw_splashes(ci: CanvasItem) -> void:
	var splash: FxLayer.FxDef = fx.defs.get(&"rain_splash") if fx != null else null
	var shift := 0 if (_splash_world and ci != self) else _cam_x
	for s in _splashes:
		var x := roundf(s[0] - shift)
		var y := roundf(s[1])
		var age := int(s[2])
		if splash != null:
			var k := mini(age / maxi(1, splash.ticks), splash.count - 1)
			ci.draw_texture_rect_region(splash.texture, Rect2(x - splash.anchor.x, y - splash.anchor.y, splash.frame.x, splash.frame.y), Rect2(k * splash.frame.x, 0, splash.frame.x, splash.frame.y))
		else:
			var r := 1 + age / 3
			var c := Color(0.7, 0.74, 1.0, 0.45 - age * 0.04)
			ci.draw_rect(Rect2(x - r, y - 1 - age / 4, 1, 1), c)
			ci.draw_rect(Rect2(x + r, y - 1 - age / 4, 1, 1), c)
