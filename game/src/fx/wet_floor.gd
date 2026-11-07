class_name WetFloor
extends Node2D
## I riflessi sul pavimento bagnato dell'arena (Luigi, 7 novembre 2026: «SUBITO, in questo giro»).
## Due strati, tutti e due solo disegno, fuori dalla simulazione e dall'hash:
## - il fondo: lo schermo sopra la linea del pavimento (il muro, le luci, le insegne), specchiato nella
##   fascia del pavimento, con l'acqua che lo increspa e la retinatura che lo dirada verso chi guarda;
## - gli attori: ogni combattente capovolto sotto i suoi piedi (non sotto la linea del muro, perché sta
##   in profondità), più tenue man mano che il riflesso si allontana dai piedi.
## Va in un nodo del mondo sopra il pavimento e sotto le ombre e gli attori.

const FONDO_SHADER := """
shader_type canvas_item;
uniform sampler2D screen : hint_screen_texture, filter_nearest;
uniform float line_uv = 0.7;
uniform float depth_uv = 0.3;
uniform float strength = 0.0;
uniform float t = 0.0;
uniform vec3 tint = vec3(0.70, 0.78, 0.95);
const float BAYER[16] = float[](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
void fragment() {
	vec2 px = floor(SCREEN_UV / SCREEN_PIXEL_SIZE);
	float d = clamp((SCREEN_UV.y - line_uv) / max(depth_uv, 1e-4), 0.0, 1.0);
	// L'acqua: ogni riga si sposta di un pixel intero, di più verso chi guarda.
	float wob = floor(sin(px.y * 0.85 + t * 0.21) * (0.6 + 1.6 * d) + 0.5);
	float sy = line_uv - (SCREEN_UV.y - line_uv) * 1.15;
	vec3 c = texture(screen, vec2(SCREEN_UV.x + wob * SCREEN_PIXEL_SIZE.x, sy)).rgb;
	// Le luci si riflettono più del buio.
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	float a = strength * (1.0 - d) * (1.0 - d) * (0.25 + 1.1 * l);
	float b = (BAYER[int(mod(px.y, 4.0)) * 4 + int(mod(px.x, 4.0))] + 0.5) / 16.0;
	a = clamp(floor(a * 4.0 + b) / 4.0, 0.0, 1.0);
	COLOR = vec4(c * tint, a);
}
"""

const ATTORI_SHADER := """
shader_type canvas_item;
uniform float t = 0.0;
const float BAYER[16] = float[](0., 8., 2., 10., 12., 4., 14., 6., 3., 11., 1., 9., 15., 7., 13., 5.);
void fragment() {
	vec2 px = floor(FRAGCOORD.xy);
	float wob = floor(sin(px.y * 0.85 + t * 0.21) * 0.9 + 0.5);
	vec4 c = texture(TEXTURE, UV + vec2(wob * TEXTURE_PIXEL_SIZE.x, 0.0));
	float a = c.a * COLOR.a;
	float b = (BAYER[int(mod(px.y, 4.0)) * 4 + int(mod(px.x, 4.0))] + 0.5) / 16.0;
	a = clamp(floor(a * 4.0 + b) / 4.0, 0.0, 1.0);
	COLOR = vec4(c.rgb * COLOR.rgb, a);
}
"""

## Quanto è forte il riflesso con la pioggia piena: il fondo e gli attori (l'alfa ai piedi).
const FONDO_MAX := 0.52
const ATTORI_MAX := 0.42
## Il colore dell'acqua sugli attori riflessi: più scuri e più blu.
const ATTORI_TINT := Color(0.58, 0.66, 0.86)

static var _fondo_shader: Shader
static var _attori_shader: Shader

var _fondo_mat: ShaderMaterial
var _attori_mat: ShaderMaterial
var _attori: Node2D
var _band := Rect2()
var _strength: float = 0.0
var _fighters: Array = []
var _origin := Vector2.ZERO


func _init() -> void:
	name = "Riflessi"
	if _fondo_shader == null:
		_fondo_shader = Shader.new()
		_fondo_shader.code = FONDO_SHADER
		_attori_shader = Shader.new()
		_attori_shader.code = ATTORI_SHADER
	_fondo_mat = ShaderMaterial.new()
	_fondo_mat.shader = _fondo_shader
	material = _fondo_mat
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_attori = Node2D.new()
	_attori.name = "Attori"
	_attori.z_index = 1
	_attori_mat = ShaderMaterial.new()
	_attori_mat.shader = _attori_shader
	_attori.material = _attori_mat
	_attori.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_attori.draw.connect(_draw_attori)
	add_child(_attori)
	visible = false


## Una volta per tick. `band`: il pavimento in coordinate del nodo (la linea del muro in alto);
## `strength`: quanto è bagnato (0 lo spegne); `fighters`: chi si riflette, nel nodo `origin` (la
## posizione dell'arena nel mondo); `t`: il tick, per l'acqua.
func update(band: Rect2, strength: float, fighters: Array, origin: Vector2, t: int) -> void:
	_band = band
	_strength = strength
	_fighters = fighters
	_origin = origin
	visible = strength > 0.0 and band.size.y > 1.0
	if not visible:
		return
	var vp := get_viewport_rect().size
	var xf := get_global_transform_with_canvas()
	var top := (xf * band.position).y
	var bottom := (xf * band.end).y
	_fondo_mat.set_shader_parameter(&"line_uv", top / vp.y)
	_fondo_mat.set_shader_parameter(&"depth_uv", maxf(bottom - top, 1.0) / vp.y)
	_fondo_mat.set_shader_parameter(&"strength", FONDO_MAX * strength)
	_fondo_mat.set_shader_parameter(&"t", float(t))
	_attori_mat.set_shader_parameter(&"t", float(t))
	queue_redraw()
	_attori.queue_redraw()


func _draw() -> void:
	draw_rect(_band, Color.WHITE)


## Ogni combattente capovolto sotto i piedi: un quadrilatero con i colori ai vertici, pieno ai piedi e
## trasparente all'altezza della testa (lo shader poi lo dirada a gradini).
func _draw_attori() -> void:
	var a0 := ATTORI_MAX * _strength
	for f in _fighters:
		if not is_instance_valid(f) or not f.visible:
			continue
		var body: Sprite2D = f.body
		if body == null or not body.visible or body.texture == null:
			continue
		var r := body.region_rect
		var anchor := -body.offset
		var face := signf(body.scale.x)
		var ground: Vector2 = _origin + f.position
		var g := Vector2(ground.x + body.position.x, ground.y - body.position.y)
		var tex_size := Vector2(body.texture.get_size())
		var tint := ATTORI_TINT * body.modulate
		var top := -anchor.y
		var bottom := r.size.y - anchor.y
		var qs := [Vector2(-anchor.x, top), Vector2(r.size.x - anchor.x, top),
				Vector2(r.size.x - anchor.x, bottom), Vector2(-anchor.x, bottom)]
		var pts := PackedVector2Array()
		var uvs := PackedVector2Array()
		var cols := PackedColorArray()
		for q: Vector2 in qs:
			pts.append((g + Vector2(face * q.x, -q.y)).round())
			uvs.append((r.position + q + anchor) / tex_size)
			cols.append(Color(tint, a0 if q.y >= 0.0 else 0.0))
		_attori.draw_polygon(pts, cols, uvs, body.texture)
