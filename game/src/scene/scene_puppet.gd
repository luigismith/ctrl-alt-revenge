class_name ScenePuppet
extends Node2D
## Una comparsa delle scene: lo sprite di un personaggio mosso dalla regia, fuori dalla simulazione.
## Durante la scena prende il posto dell'attore vero (che resta nascosto e fermo) e alla fine glielo
## restituisce nella stessa posa e nello stesso punto: per questo usa lo stesso materiale dei
## combattenti (luci, varianti di colore) e la stessa ombra.
##
## Coordinate: (px, py) sono i piedi nello spazio del nodo che la contiene (il mondo dell'arena o
## quello del platform); `depth_sort` ordina il disegno per profondità come i combattenti.

var sheet: SpriteSheet
var anim: FrameAnim
var body: Sprite2D
var px: float = 0.0
var py: float = 0.0
var facing: int = 1
var depth_sort: bool = true
## Il segno rosso del laser sul braccio sinistro (solo GIG).
var marked: bool = false
var sound: bool = true
## Animazione dopo una camminata.
var rest_anim: StringName = &"idle"

var _target: Vector2 = Vector2.ZERO
var _speed: float = 0.0
var _walking: bool = false
var _walk_anim: StringName = &"walk"
var _mat: ShaderMaterial
var _shadow: Node2D
var _shadow_def: FxLayer.FxDef
var _shadow_w: int = 0
var _mark_node: Node2D
var _mark_glow: Glow
var _step_parity: bool = false
var _t: int = 0


## `sheet_id`: lo sprite; `variant`: la variante di colore (come set_palette_variant dei combattenti).
func setup(sheet_id: StringName, variant: Dictionary = {}, shadow_def: FxLayer.FxDef = null, shadow_w: int = 0) -> void:
	sheet = SpriteSheet.get_sheet(sheet_id)
	anim = FrameAnim.new(sheet)
	body = Sprite2D.new()
	body.centered = false
	body.region_enabled = true
	body.texture = sheet.texture
	if sheet.has_normals:
		body.light_mask = Fighter.LIGHT_MASK_ACTORS
	_mat = ShaderMaterial.new()
	_mat.shader = Fighter._get_flash_shader()
	body.material = _mat
	add_child(body)
	_set_variant(variant)
	_shadow_def = shadow_def
	_shadow_w = shadow_w
	if shadow_w > 0:
		# L'ombra sotto tutti i corpi, come lo strato delle ombre dei combattenti (z 60).
		_shadow = Node2D.new()
		_shadow.z_as_relative = false
		_shadow.z_index = 60
		_shadow.draw.connect(_draw_shadow)
		add_child(_shadow)
	_mark_node = Node2D.new()
	_mark_node.z_index = 1
	_mark_node.draw.connect(_draw_mark)
	add_child(_mark_node)
	_mark_glow = Glow.new(_mark_node)
	anim.play(&"idle")


func _set_variant(v: Dictionary) -> void:
	var from := PackedVector3Array()
	var to := PackedVector3Array()
	for k: String in v:
		var a := Color.html(k)
		var b := Color.html(str(v[k]))
		from.append(Vector3(a.r, a.g, a.b))
		to.append(Vector3(b.r, b.g, b.b))
	from.resize(8)
	to.resize(8)
	_mat.set_shader_parameter(&"swap_n", mini(v.size(), 8))
	_mat.set_shader_parameter(&"swap_from", from)
	_mat.set_shader_parameter(&"swap_to", to)


## Parte da una posa precisa (l'attore vero nel tick in cui la scena comincia).
func start_from(anim_name: StringName, index: int, frame_tick: int = 0) -> void:
	if not sheet.has_anim(anim_name):
		anim.play(&"idle")
		return
	anim.play(anim_name)
	anim.index = clampi(index, 0, anim.clip.frames.size() - 1)
	anim.frame_tick = clampi(frame_tick, 0, anim.clip.frames[anim.index].ticks - 1)
	anim.take_events()


func play(anim_name: StringName) -> void:
	if not sheet.has_anim(anim_name):
		anim_name = &"idle"
	if anim.name == anim_name and anim.clip != null and anim.clip.loop:
		return
	anim.play(anim_name)
	anim.take_events()


func walk_to(target: Vector2, speed: float, walk_anim: StringName = &"walk") -> void:
	_target = target
	_speed = maxf(speed, 0.1)
	_walk_anim = walk_anim if sheet.has_anim(walk_anim) else &"walk"
	_walking = true
	if absf(target.x - px) > 0.5:
		facing = 1 if target.x > px else -1
	play(_walk_anim)


func is_walking() -> bool:
	return _walking


## Un tick della comparsa: animazione, camminata, passi.
func tick() -> void:
	_t += 1
	if _walking:
		var d := _target - Vector2(px, py)
		if d.length() <= _speed:
			px = _target.x
			py = _target.y
			_walking = false
			play(rest_anim)
		else:
			var v := d.normalized() * _speed
			px += v.x
			py += v.y
	anim.advance()
	for e in anim.take_events():
		if e == "step" and sound:
			_step_parity = not _step_parity
			Sfx.step(px, _step_parity, -4.0)
	sync()


func sync() -> void:
	position = Vector2(roundf(px), roundf(py))
	var f := anim.frame()
	if body.texture != sheet.texture:
		body.texture = sheet.texture
	body.region_rect = Rect2(f.rect)
	body.offset = Vector2(-f.anchor)
	body.scale = Vector2(facing, 1)
	if depth_sort:
		z_index = 100 + 2 * int(roundf(py))
	if _shadow != null:
		_shadow.queue_redraw()
	_mark_node.queue_redraw()


## Il riquadro dei pixel pieni del fotogramma di adesso, nello spazio del contenitore.
func body_rect() -> Rect2:
	var f := anim.frame()
	var u := Rect2i(Vector2i.ZERO, f.rect.size)
	var img := sheet.texture.get_image() if sheet.texture != null else null
	if img != null:
		u = img.get_region(f.rect).get_used_rect()
	var x0 := u.position.x - f.anchor.x
	var x1 := u.end.x - f.anchor.x
	if facing < 0:
		var tmp := x0
		x0 = -x1
		x1 = -tmp
	return Rect2(roundf(px) + x0, roundf(py) + u.position.y - f.anchor.y, x1 - x0, u.size.y)


## Un punto del fotogramma ("fist_r", "head"...), nello spazio del contenitore; `fallback` se manca.
func point(name: String, fallback: Vector2 = Vector2(0, -70)) -> Vector2:
	var f := anim.frame()
	var p: Vector2 = Vector2(f.points[name]) if f.points.has(name) else fallback
	return Vector2(roundf(px) + p.x * facing, roundf(py) + p.y)


## Il braccio sinistro (quello di MANODOPERA): a metà fra la spalla e il pugno sinistro.
func arm_point() -> Vector2:
	return Vector2(roundf(px), roundf(py)) + ArmMark.offset(anim.frame(), facing)


func _draw_shadow() -> void:
	var w := _shadow_w
	if _shadow_def != null and _shadow_def.texture != null and _shadow_def.count >= 3:
		var k := 0 if w >= 42 else (1 if w >= 25 else 2)
		var o := -Vector2(_shadow_def.anchor)
		_shadow.draw_texture_rect_region(_shadow_def.texture, Rect2(o, _shadow_def.frame), Rect2(k * _shadow_def.frame.x, 0, _shadow_def.frame.x, _shadow_def.frame.y))
		return
	var sh := maxi(3, int(round(w * 0.26)))
	_shadow.draw_rect(Rect2(-w / 2, -sh / 2, w, sh), Color(0.03, 0.01, 0.07, 0.5))


func _draw_mark() -> void:
	_mark_glow.clear()
	if not marked:
		return
	ArmMark.draw(_mark_node, ArmMark.offset(anim.frame(), facing), _t, _mark_glow)
