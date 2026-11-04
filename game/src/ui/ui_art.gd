class_name UiArt
extends RefCounted
## Elementi grafici dell'interfaccia da game/assets/ui/ (logo, ritratti, freccia VAI, barre).
## Ogni elemento è facoltativo: se manca, chi disegna usa un segnaposto pulito.
## Se c'è game/assets/ui/ui.json, i nomi dei file si leggono da lì:
##   {"logo": "logo.png", "subtitle": "sottotitolo.png", "go_arrow": "vai.png", ...}

const UI_DIR := "res://assets/ui"

## Nomi di file provati per ogni elemento, in ordine.
const DEFAULTS := {
	"logo": ["logo.png", "logo_ctrl_alt_revenge.png", "title_logo.png"],
	"subtitle": ["subtitle.png", "sottotitolo.png", "picchia_duro.png"],
	"go_arrow": ["go_arrow.png", "vai.png", "freccia_vai.png"],
	"bar_frame": ["bar_frame.png", "lifebar_frame.png", "cornice_barra.png"],
	"bar_fill": ["bar_fill.png", "lifebar_fill.png", "barra_vita.png"],
	"bar_fill_enemy": ["bar_fill_enemy.png", "lifebar_fill_enemy.png", "barra_vita_nemico.png"],
	"portrait_frame": ["portrait_frame.png", "cornice_ritratto.png"],
}

static var _cache: Dictionary = {}
static var _manifest: Dictionary = {}
static var _manifest_loaded: bool = false


static func manifest() -> Dictionary:
	if not _manifest_loaded:
		_manifest_loaded = true
		var p := UI_DIR.path_join("ui.json")
		if FileAccess.file_exists(p):
			var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(p))
			if d is Dictionary:
				_manifest = d
	return _manifest


## Texture dell'elemento `key`, oppure null se la grafica non c'è.
static func texture(key: String) -> Texture2D:
	if _cache.has(key):
		return _cache[key]
	var t: Texture2D = null
	var names: Array = []
	var m := manifest()
	var entry: Variant = m.get(key, null)
	if entry is String:
		names.append(entry)
	elif entry is Dictionary and (entry as Dictionary).has("image"):
		names.append(str(entry["image"]))
	names.append_array(DEFAULTS.get(key, []))
	for n: Variant in names:
		var path := UI_DIR.path_join(str(n))
		if FileAccess.file_exists(path) or ResourceLoader.exists(path):
			t = SpriteSheet.load_texture(path)
			if t != null:
				break
	_cache[key] = t
	return t


## Ritratto 32×32: game/assets/ui/portraits/<id>.png, altrimenti il volto ritagliato dallo sprite.
static func portrait(sprite_id: StringName) -> Texture2D:
	var key := "portrait:" + String(sprite_id)
	if _cache.has(key):
		return _cache[key]
	var t := SpriteSheet.load_texture(UI_DIR.path_join("portraits/%s.png" % sprite_id))
	if t == null:
		t = _portrait_from_sprite(sprite_id)
	_cache[key] = t
	return t


static func _portrait_from_sprite(sprite_id: StringName) -> Texture2D:
	var sheet := SpriteSheet.get_sheet(sprite_id)
	if sheet.texture == null:
		return null
	var img := sheet.texture.get_image()
	if img == null:
		return null
	if img.is_compressed():
		img.decompress()
	var f := sheet.clip(&"idle").frames[0]
	# Cima dello sprite: prima riga con pixel opachi nel rettangolo del fotogramma.
	var top := f.rect.position.y
	var found := false
	for y in range(f.rect.position.y, f.rect.end.y):
		for x in range(f.rect.position.x, f.rect.end.x):
			if img.get_pixel(x, y).a > 0.5:
				top = y
				found = true
				break
		if found:
			break
	var cx := f.rect.position.x + f.anchor.x
	var src := Rect2i(cx - 14, top - 2, 32, 32).intersection(Rect2i(Vector2i.ZERO, img.get_size()))
	var out := Image.create_empty(32, 32, false, Image.FORMAT_RGBA8)
	out.fill(Color8(28, 20, 52))
	out.blend_rect(img, src, Vector2i.ZERO)
	return ImageTexture.create_from_image(out)


static func clear_cache() -> void:
	_cache.clear()
	_manifest_loaded = false
	_manifest = {}


## Disposizione dell'HUD da ui.json → hud_layout (coordinate dello schermo), con un valore di riserva.
static func layout(key: String, fallback: Array) -> Array:
	var hl: Variant = manifest().get("hud_layout", {})
	if hl is Dictionary and (hl as Dictionary).get(key) is Array and (hl[key] as Array).size() == fallback.size():
		return hl[key]
	return fallback


## Colore da ui.json → colors ("#rrggbb"), con un valore di riserva.
static func color(key: String, fallback: Color) -> Color:
	var c: Variant = manifest().get("colors", {})
	if c is Dictionary and (c as Dictionary).has(key):
		return Color.html(str(c[key]))
	return fallback


## Dati di una striscia di fotogrammi (es. go_arrow): {"frame": Vector2i, "count": n, "ticks": t}.
static func strip(key: String) -> Dictionary:
	var e: Variant = manifest().get(key, {})
	var out := {"frame": Vector2i.ZERO, "count": 1, "ticks": 8}
	if e is Dictionary:
		var fr: Variant = e.get("frame", null)
		if fr is Array and (fr as Array).size() == 2:
			out["frame"] = Vector2i(int(fr[0]), int(fr[1]))
		out["count"] = maxi(1, int(e.get("count", 1)))
		out["ticks"] = maxi(1, int(e.get("ticks", 8)))
	return out


## Disegna un'immagine dell'interfaccia centrata in orizzontale su `cx`, con la cima in `y`.
## Ritorna false se l'immagine non c'è.
static func draw_centered(ci: CanvasItem, key: String, cx: float, y: float, alpha: float = 1.0) -> bool:
	var t := texture(key)
	if t == null:
		return false
	ci.draw_texture(t, Vector2(roundf(cx - t.get_width() / 2.0), roundf(y)), Color(1, 1, 1, alpha))
	return true
