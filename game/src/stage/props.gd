class_name Prop
extends Entity
## Oggetto di scena con uno sprite nel formato §4 (game/assets/props/<id>/<id>.json).
## Le animazioni si cercano per nome fra alcuni sinonimi, così i nomi scelti dalla grafica
## non bloccano il codice.

var sheet: SpriteSheet
var anim: FrameAnim
var body: Sprite2D
var shadow_w: int = 0
var depth_bias: int = 0
## Volume dei suoni degli eventi dei fotogrammi (più basso per i suoni d'ambiente in loop).
var event_volume_db: float = 0.0


func setup_prop(sheet_id: StringName, lvl: Level, id: int) -> void:
	level = lvl
	uid = id
	name = "%s_%d" % [sheet_id, uid]
	sheet = SpriteSheet.get_sheet(sheet_id, "props")
	anim = FrameAnim.new(sheet)
	body = Sprite2D.new()
	body.centered = false
	body.region_enabled = true
	body.texture = sheet.texture
	add_child(body)


## Avanza l'animazione e fa scattare gli eventi dei fotogrammi (sfx:, fx:).
## I suoni si sentono solo se l'oggetto è vicino allo schermo.
func advance_anim() -> void:
	anim.advance()
	play_events()


func play_events() -> void:
	for e in anim.take_events():
		if e.begins_with("sfx:"):
			if level.sound_enabled and px > level.view_left() - 32.0 and px < level.view_right() + 32.0:
				Sfx.play_at(StringName(e.substr(4)), px, 0.05, event_volume_db)
		elif e.begins_with("fx:"):
			level.fx.spawn(StringName(e.substr(3)), px, py - ph - 20.0, 1, depth_z(2))


static func clip_has_sfx(c: AnimClip) -> bool:
	for f in c.frames:
		for e in f.events:
			if e.begins_with("sfx:"):
				return true
	return false


## Prima animazione esistente fra i nomi dati (altrimenti la prima dello sheet).
func pick_anim(names: Array[StringName]) -> StringName:
	for n in names:
		if sheet.has_anim(n):
			return n
	for k: StringName in sheet.animations:
		return k
	return names[0]


func shadow_width() -> int:
	return 0 if removed else shadow_w


func sync_visual() -> void:
	position = Vector2(roundf(px), roundf(py))
	var f := anim.frame()
	body.region_rect = Rect2(f.rect)
	body.offset = Vector2(-f.anchor)
	body.position = Vector2(0, -roundf(ph))
	z_index = depth_z(depth_bias)
	visible = not removed


func world_hurtboxes() -> Array[Rect2]:
	var out: Array[Rect2] = []
	var f := anim.frame()
	if f.hurt.is_empty():
		out.append(Rect2(px - f.anchor.x, py - ph - f.anchor.y, f.rect.size.x, f.rect.size.y))
	else:
		for b in f.hurt:
			out.append(Rect2(px + b.position.x, py - ph + b.position.y, b.size.x, b.size.y))
	return out
