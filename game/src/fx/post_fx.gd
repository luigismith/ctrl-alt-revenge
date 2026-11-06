class_name PostFx
extends Node
## Proposta, spenta finché Luigi non dice sì: il post-processing "retro con la tecnologia di oggi".
## - HDR 2D e bagliore (glow) solo su quello che emette luce: il braccio cyan di GIG dopo il riavvio, il
##   laser rosso del messo, le scintille, i lumini, i neon. Brilla solo quello che è più forte del bianco
##   (soglia 1): chi disegna un'emissione la moltiplica per `emissive()`; il resto non cambia.
## - Una vignettatura leggera, a retinatura sui pixel dello schermo (niente sfumature morbide).
##
## I pixel restano netti: il bagliore si calcola a 480 × 270 e si ingrandisce come il resto; i
## personaggi non si sfocano mai. È solo disegno: la simulazione non lo vede.
##
## Uso (da chi ospita, per esempio il prologo):
##   var post := PostFx.new(); add_child(post); post.enable(PostFx.ENABLED)
##   colori che brillano: draw_rect(r, PostFx.emissive(colore, 2.5))

## L'interruttore: falso finché Luigi non lo approva. Si prova anche con --post-fx (vedi enable_from_args).
const ENABLED := false

## Il bagliore: soglia (solo sopra il bianco), forza, e i livelli di sfocatura usati (i primi tre: aloni
## stretti, come un neon nella pioggia, non una nebbia su tutto lo schermo).
const GLOW_THRESHOLD := 1.0
const GLOW_INTENSITY := 0.8
const GLOW_STRENGTH := 1.0
const GLOW_LEVELS := [0.0, 1.0, 0.7, 0.35, 0.0, 0.0, 0.0]
## Fin dove arrivano gli effetti: i CanvasLayer fino a questo numero (il gioco). L'interfaccia (10), le
## scene (15 e 20) e la dissolvenza (50) restano fuori.
const MAX_LAYER := 4

## La vignettatura: un'ellisse con le proporzioni dello schermo, da dove comincia a dove è piena (1 è
## l'angolo, 0,71 il bordo a metà), e quanto scurisce agli angoli.
const VIGNETTE_LAYER := 5
const VIGNETTE_INNER := 0.55
const VIGNETTE_OUTER := 1.05
const VIGNETTE_STRENGTH := 0.30
const VIGNETTE_COLOR := Color(0.035, 0.025, 0.07)

const VIGNETTE_SHADER := """shader_type canvas_item;
uniform float inner = 0.55;
uniform float outer = 1.05;
uniform float strength = 0.3;
uniform vec3 tint = vec3(0.035, 0.025, 0.07);
uniform vec2 size = vec2(480.0, 270.0);
float bayer4(vec2 p) {
	int x = int(mod(p.x, 4.0));
	int y = int(mod(p.y, 4.0));
	int m[16] = int[](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
	return (float(m[y * 4 + x]) + 0.5) / 16.0;
}
void fragment() {
	vec2 p = floor(UV * size);
	float r = length((UV - 0.5) * 2.0) * 0.70710678;
	float v = smoothstep(inner, outer, r);
	// quattro gradini di scuro, con la retinatura fra uno e l'altro
	float a = floor(v * 4.0 + bayer4(p)) / 4.0;
	COLOR = vec4(tint, a * strength);
}
"""

## Acceso adesso (lo leggono emissive() e chi disegna).
static var on: bool = false

var _env: WorldEnvironment
var _vignette: CanvasLayer
var _was_hdr: bool = false


## Un colore che emette luce: con il bagliore acceso è `k` volte più forte (oltre il bianco, e brilla);
## spento resta com'è.
static func emissive(c: Color, k: float = 2.0) -> Color:
	if not on:
		return c
	return Color(c.r * k, c.g * k, c.b * k, c.a)


## Acceso con --post-fx sulla riga di comando (per le prove), altrimenti come dice ENABLED.
func enable_from_args() -> void:
	enable(ENABLED or OS.get_cmdline_user_args().has("--post-fx") or OS.get_cmdline_args().has("--post-fx"))


func enable(enabled: bool) -> void:
	if enabled == (_env != null):
		return
	var vp := get_viewport()
	if enabled:
		_was_hdr = vp.use_hdr_2d
		vp.use_hdr_2d = true
		_env = WorldEnvironment.new()
		_env.name = "Bagliore"
		_env.environment = _make_environment()
		add_child(_env)
		_vignette = _make_vignette()
		add_child(_vignette)
	else:
		vp.use_hdr_2d = _was_hdr
		_env.queue_free()
		_env = null
		_vignette.queue_free()
		_vignette = null
	on = enabled


func _exit_tree() -> void:
	if _env != null:
		get_viewport().use_hdr_2d = _was_hdr
		on = false


func _make_environment() -> Environment:
	var e := Environment.new()
	e.background_mode = Environment.BG_CANVAS
	e.background_canvas_max_layer = MAX_LAYER
	e.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	e.glow_enabled = true
	e.glow_normalized = false
	e.glow_intensity = GLOW_INTENSITY
	e.glow_strength = GLOW_STRENGTH
	e.glow_bloom = 0.0
	e.glow_hdr_threshold = GLOW_THRESHOLD
	e.glow_hdr_scale = 2.0
	e.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	for i in GLOW_LEVELS.size():
		e.set_glow_level(i, float(GLOW_LEVELS[i]))
	return e


func _make_vignette() -> CanvasLayer:
	var layer := CanvasLayer.new()
	layer.name = "Vignettatura"
	layer.layer = VIGNETTE_LAYER
	var rect := ColorRect.new()
	rect.size = View.SIZE
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var sh := Shader.new()
	sh.code = VIGNETTE_SHADER
	var m := ShaderMaterial.new()
	m.shader = sh
	m.set_shader_parameter(&"inner", VIGNETTE_INNER)
	m.set_shader_parameter(&"outer", VIGNETTE_OUTER)
	m.set_shader_parameter(&"strength", VIGNETTE_STRENGTH)
	m.set_shader_parameter(&"tint", Vector3(VIGNETTE_COLOR.r, VIGNETTE_COLOR.g, VIGNETTE_COLOR.b))
	m.set_shader_parameter(&"size", View.SIZE)
	rect.material = m
	layer.add_child(rect)
	return layer
