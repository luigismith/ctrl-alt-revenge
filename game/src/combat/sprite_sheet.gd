class_name SpriteSheet
extends RefCounted
## Atlante di uno sprite nel formato §4: <id>.png più <id>.json.
##
## Cerca, in quest'ordine:
##   1. res://assets/<kind>/<id>/<id>.json   (grafica vera)
##   2. res://assets/<kind>/<id>.json
##   3. res://assets/sprites/_placeholder/<id>.json   (segnaposto)
## e se non trova nulla genera rettangoli di debug, così il gioco funziona anche senza grafica.
## I file veri vengono usati automaticamente appena esistono.

enum Source { REAL, PLACEHOLDER, DEBUG }

## Animazioni richieste dalla specifica (§4).
const REQUIRED: Dictionary[StringName, PackedStringArray] = {
	&"gig": ["idle", "walk", "run", "jump_rise", "jump_fall", "land", "jab1", "jab2", "hook", "kick",
		"air_kick", "grab_hold", "knee", "throw", "hurt_high", "hurt_low", "knock_air", "knock_down", "getup"],
	# GIG prima del riavvio, col braccio morto: le mosse del prologo
	&"gig_spento": ["idle", "walk", "run", "jump_rise", "jump_fall", "jump_arc", "land", "jab2", "mazza",
		"hurt_high", "hurt_low", "knock_air", "knock_down", "getup", "crouch", "crouch_walk", "slide", "ledge_hang",
		"ledge_climb"],
	&"thug_punk": ["idle", "walk", "jab", "haymaker", "hurt_high", "hurt_low", "knock_air", "knock_down",
		"getup", "grabbed", "kneed", "thrown"],
	&"thug_bruiser": ["idle", "walk", "punch", "hurt_high", "hurt_low", "knock_air", "knock_down", "getup",
		"grabbed", "kneed", "thrown"],
	# gli Esattori del prologo: le mosse dei nemici dello slice, più le loro
	&"rider": ["idle", "walk", "jab", "haymaker", "pignora", "hurt_high", "hurt_low", "knock_air", "knock_down",
		"getup", "grabbed", "kneed", "thrown"],
	&"esattore": ["idle", "walk", "punch", "block", "charge_wind", "charge_run", "dizzy", "hurt_high", "hurt_low",
		"knock_air", "knock_down", "getup", "grabbed", "kneed", "thrown"],
	&"messo": ["idle", "walk", "read", "laser", "call", "hurt_high", "hurt_low", "knock_air", "knock_down", "getup",
		"grabbed", "kneed", "thrown"],
}

## Se un'animazione manca, si prova la prima di queste che esiste.
const FALLBACKS: Dictionary[String, PackedStringArray] = {
	"run": ["walk"],
	"walk": ["idle"],
	"jump_rise": ["jump_fall", "idle"],
	"jump_fall": ["jump_rise", "idle"],
	"land": ["idle"],
	"jab1": ["jab", "punch"],
	"jab2": ["jab1", "jab", "punch"],
	"hook": ["jab2", "jab1", "haymaker", "punch"],
	"kick": ["hook", "jab1"],
	"air_kick": ["jump_fall", "kick"],
	"grab_hold": ["idle"],
	"knee": ["grab_hold", "jab1"],
	"throw": ["grab_hold", "hook"],
	"jab": ["punch", "jab1"],
	"haymaker": ["punch", "jab", "hook"],
	"punch": ["jab", "haymaker"],
	"hurt_high": ["hurt_low", "idle"],
	"hurt_low": ["hurt_high", "idle"],
	"knock_air": ["hurt_high", "knock_down"],
	"knock_down": ["knock_air", "hurt_low"],
	"getup": ["idle"],
	"grabbed": ["hurt_high", "idle"],
	"kneed": ["hurt_low", "grabbed", "hurt_high"],
	"thrown": ["knock_air", "hurt_high"],
	"pignora": ["jab", "punch"],
	"block": ["idle"],
	"charge_wind": ["punch", "idle"],
	"charge_run": ["walk"],
	"dizzy": ["hurt_low", "idle"],
	"read": ["idle"],
	"laser": ["idle"],
	"call": ["idle"],
}

const KNOWN_EVENT_PREFIXES: PackedStringArray = ["sfx:", "fx:"]
const KNOWN_EVENTS: PackedStringArray = ["glint", "step"]

var id: StringName = &""
var source: Source = Source.DEBUG
var json_path: String = ""
var texture: Texture2D
var image_size: Vector2i = Vector2i.ZERO
## La texture è una CanvasTexture con la normal map (campo normal_image): riceve le luci dinamiche.
var has_normals: bool = false
var pixels_per_meter: int = View.PPM
var animations: Dictionary[StringName, AnimClip] = {}
## Errori di struttura: con errori il file non si usa.
var errors: PackedStringArray = []
## Avvisi: il file si usa lo stesso.
var warnings: PackedStringArray = []

var _retimed: Dictionary = {}

static var _cache: Dictionary = {}
## Quanto alzare i fotogrammi perché le suole tocchino la collisione: vedi _apply_soles.
const SOLES_JSON := "res://data/sprites/suole.json"
static var _soles: Variant = null
## Percorsi dei file di cui si sono già segnalati gli avvisi.
static var _warned: Dictionary = {}


static func get_sheet(sheet_id: StringName, kind: String = "sprites") -> SpriteSheet:
	var key := "%s/%s" % [kind, sheet_id]
	if _cache.has(key):
		return _cache[key]
	var sheet: SpriteSheet = null
	for path in candidate_paths(sheet_id, kind):
		if not FileAccess.file_exists(path):
			continue
		var s := load_json(path)
		if s.errors.is_empty():
			sheet = s
			# Gli avvisi non impediscono di usare il file: si segnalano una volta per file.
			if not s.warnings.is_empty() and OS.is_debug_build() and not _warned.has(path):
				_warned[path] = true
				push_warning("Sprite %s (%s): %s" % [sheet_id, path, "; ".join(s.warnings.slice(0, 5))])
			break
		push_warning("Sprite %s scartato (%s): %s" % [sheet_id, path, "; ".join(s.errors.slice(0, 3))])
	if sheet == null:
		sheet = DebugArt.make_sheet(sheet_id, kind)
	_cache[key] = sheet
	return sheet


static func clear_cache() -> void:
	_cache.clear()


static func candidate_paths(sheet_id: StringName, kind: String) -> PackedStringArray:
	return PackedStringArray([
		"res://assets/%s/%s/%s.json" % [kind, sheet_id, sheet_id],
		"res://assets/%s/%s.json" % [kind, sheet_id],
		"res://assets/sprites/_placeholder/%s.json" % sheet_id,
	])


## Carica una texture importata; se il file è appena arrivato e non è ancora importato
## (solo durante lo sviluppo) la legge direttamente dal PNG.
static func load_texture(path: String) -> Texture2D:
	if ResourceLoader.exists(path):
		var t := load(path) as Texture2D
		if t != null:
			return t
	if FileAccess.file_exists(path):
		var img := Image.load_from_file(ProjectSettings.globalize_path(path))
		if img != null and not img.is_empty():
			return ImageTexture.create_from_image(img)
	return null


static func load_json(path: String) -> SpriteSheet:
	var s := SpriteSheet.new()
	s.json_path = path
	s.source = Source.PLACEHOLDER if path.contains("/_placeholder/") else Source.REAL
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (data is Dictionary):
		s.errors.append("JSON non leggibile")
		return s
	var d: Dictionary = data
	s.id = StringName(str(d.get("id", path.get_file().get_basename())))
	if int(d.get("format", 0)) != 1:
		s.errors.append("format deve essere 1")
	s.pixels_per_meter = int(d.get("pixels_per_meter", View.PPM))
	if s.pixels_per_meter != View.PPM:
		s.warnings.append("pixels_per_meter = %d invece di %d" % [s.pixels_per_meter, View.PPM])
	var image_name := str(d.get("image", ""))
	if image_name == "":
		s.errors.append("manca image")
		return s
	s.texture = load_texture(path.get_base_dir().path_join(image_name))
	if s.texture == null:
		s.errors.append("immagine non trovata: %s" % image_name)
		return s
	# Atlante delle normali (§4, normal_image): colore + normali in una CanvasTexture per le luci 2D.
	var normal_name := str(d.get("normal_image", ""))
	if normal_name != "":
		var nt := load_texture(path.get_base_dir().path_join(normal_name))
		if nt == null:
			s.warnings.append("normal_image non trovata: %s (niente luci dinamiche)" % normal_name)
		elif nt.get_width() != s.texture.get_width() or nt.get_height() != s.texture.get_height():
			s.warnings.append("normal_image di misura diversa dall'atlante: ignorata")
		else:
			var ct := CanvasTexture.new()
			ct.diffuse_texture = s.texture
			ct.normal_texture = nt
			s.texture = ct
			s.has_normals = true
	s.image_size = Vector2i(s.texture.get_width(), s.texture.get_height())
	var anims: Variant = d.get("animations")
	if not (anims is Dictionary) or (anims as Dictionary).is_empty():
		s.errors.append("animations vuoto o mancante")
		return s
	for anim_name: Variant in anims:
		var clip := s._parse_clip(str(anim_name), anims[anim_name])
		if clip != null:
			s.animations[StringName(str(anim_name))] = clip
	for missing in s.missing_required():
		s.warnings.append("manca l'animazione richiesta %s" % missing)
	if s.source == Source.REAL:
		s._apply_soles()
	return s


## La tabella delle suole (data/sprites/suole.json), letta una volta.
static func soles_table() -> Dictionary:
	if _soles == null:
		_soles = {}
		var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(SOLES_JSON)) \
				if FileAccess.file_exists(SOLES_JSON) else null
		if data is Dictionary and (data as Dictionary).get("fogli") is Dictionary:
			_soles = data["fogli"]
		elif OS.is_debug_build():
			push_warning("Tabella delle suole non leggibile: %s" % SOLES_JSON)
	return _soles


## La voce del foglio nella tabella delle suole, seguendo "come"; {} se non c'è.
static func soles_entry(sheet_id: StringName) -> Dictionary:
	var table := soles_table()
	var e: Variant = table.get(String(sheet_id), null)
	for _i in 4:
		if e is Dictionary and (e as Dictionary).has("come"):
			e = table.get(str(e["come"]), null)
	return e if e is Dictionary else {}


## Alza ogni fotogramma di quanto dice la tabella delle suole, così i piedi disegnati toccano la
## collisione. Si spostano l'ancora e i punti (mani, piedi, testa: servono a disegnare); hurt, hit,
## dx/dy e victim restano come sono, quindi la logica e i replay non cambiano.
func _apply_soles() -> void:
	var e := soles_entry(id)
	if e.is_empty():
		return
	var base := int(e.get("base", 0))
	var per_anim: Dictionary = e.get("anim", {}) if e.get("anim", {}) is Dictionary else {}
	for anim_name: StringName in animations:
		var frames := animations[anim_name].frames
		var v: Variant = per_anim.get(String(anim_name), base)
		var lifts: Array[int] = []
		if v is Array:
			if (v as Array).size() == frames.size():
				for x: Variant in v:
					lifts.append(int(x))
			else:
				warnings.append("suole: %s ha %d valori per %d fotogrammi" % [anim_name, (v as Array).size(), frames.size()])
		for i in frames.size():
			var lift: int = lifts[i] if not lifts.is_empty() else (base if v is Array else int(v))
			if lift == 0:
				continue
			var f := frames[i]
			f.lift = lift
			f.anchor.y += lift
			for k: String in f.points:
				f.points[k] = f.points[k] - Vector2i(0, lift)
	# Un foglio che copia la voce di un altro ("come") può non avere tutte le sue animazioni.
	var own: Variant = soles_table().get(String(id), null)
	if own is Dictionary and (own as Dictionary).has("come"):
		return
	for anim_name: Variant in per_anim:
		if not animations.has(StringName(str(anim_name))):
			warnings.append("suole: animazione %s non nel foglio" % anim_name)


func _parse_clip(anim_name: String, v: Variant) -> AnimClip:
	if not (v is Dictionary):
		errors.append("%s: non è un oggetto" % anim_name)
		return null
	var d: Dictionary = v
	var clip := AnimClip.new()
	clip.name = StringName(anim_name)
	clip.loop = bool(d.get("loop", false))
	var frames: Variant = d.get("frames")
	if not (frames is Array) or (frames as Array).is_empty():
		errors.append("%s: frames vuoto" % anim_name)
		return null
	var i := 0
	for fv: Variant in frames:
		var f := _parse_frame("%s[%d]" % [anim_name, i], fv)
		if f == null:
			return null
		clip.frames.append(f)
		i += 1
	return clip


func _parse_frame(where: String, v: Variant) -> AnimFrame:
	if not (v is Dictionary):
		errors.append("%s: non è un oggetto" % where)
		return null
	var d: Dictionary = v
	var f := AnimFrame.new()
	var rect := _int_list(d.get("rect"), 4)
	var anchor := _int_list(d.get("anchor"), 2)
	if rect.is_empty() or anchor.is_empty():
		errors.append("%s: rect o anchor non validi" % where)
		return null
	f.rect = Rect2i(rect[0], rect[1], rect[2], rect[3])
	f.anchor = Vector2i(anchor[0], anchor[1])
	if f.rect.size.x <= 0 or f.rect.size.y <= 0 or not Rect2i(Vector2i.ZERO, image_size).encloses(f.rect):
		errors.append("%s: rect %s fuori dall'atlante %s" % [where, f.rect, image_size])
		return null
	# L'ancora può stare fuori dal rect (§4: nei salti tiene il bacino all'altezza della guardia, nelle
	# cadute e in thrown è il punto a terra sotto il bacino): si segnala solo se è lontanissima.
	if not Rect2i(Vector2i(-64, -64), f.rect.size + Vector2i(128, 128)).has_point(f.anchor):
		warnings.append("%s: ancora %s molto fuori dal rect" % [where, f.anchor])
	f.ticks = int(d.get("ticks", 0))
	if f.ticks < 1:
		errors.append("%s: ticks deve essere almeno 1" % where)
		return null
	for key in ["hurt", "hit"]:
		var boxes: Variant = d.get(key, [])
		if boxes == null:
			boxes = []
		if not (boxes is Array):
			errors.append("%s: %s non è un elenco" % [where, key])
			return null
		for b: Variant in boxes:
			var box := _int_list(b, 4)
			if box.is_empty() or box[2] <= 0 or box[3] <= 0:
				errors.append("%s: box %s non valido in %s" % [where, b, key])
				return null
			var r := Rect2i(box[0], box[1], box[2], box[3])
			if key == "hurt":
				f.hurt.append(r)
			else:
				f.hit.append(r)
	var tags: Variant = d.get("tags", [])
	if tags is Array:
		for t: Variant in tags:
			if not AnimFrame.TAG_NAMES.has(str(t)):
				warnings.append("%s: tag sconosciuto %s" % [where, t])
		f.tags = AnimFrame.tags_from_names(tags)
	var events: Variant = d.get("events", [])
	if events is Array:
		for e: Variant in events:
			var es := str(e)
			if not (es in KNOWN_EVENTS or es.begins_with("sfx:") or es.begins_with("fx:")):
				warnings.append("%s: evento sconosciuto %s" % [where, es])
			f.events.append(es)
	f.dx = int(d.get("dx", 0))
	f.dy = int(d.get("dy", 0))
	var pts: Variant = d.get("points", null)
	if pts is Dictionary:
		for k: Variant in pts:
			var pv := _int_list(pts[k], 2)
			if pv.is_empty():
				warnings.append("%s: punto %s non valido" % [where, k])
				continue
			f.points[str(k)] = Vector2i(pv[0], pv[1])
	for es in f.events:
		if es.begins_with("fx:") and es.contains("@") and not f.points.has(es.get_slice("@", 1)):
			warnings.append("%s: l'effetto %s chiede un punto che il fotogramma non ha" % [where, es])
	var victim: Variant = d.get("victim", null)
	if victim is Dictionary:
		for k: Variant in victim:
			if str(k) == "behind":
				f.victim_behind = bool(victim[k])
				continue
			var e: Variant = victim[k]
			if not (e is Array) or (e as Array).size() < 2:
				warnings.append("%s: voce victim %s non valida" % [where, k])
				continue
			var arr: Array = e
			f.victim[str(k)] = [int(arr[0]), int(arr[1]), str(arr[2]) if arr.size() > 2 else "", int(arr[3]) if arr.size() > 3 else 0]
	if f.has_tag(AnimFrame.TAG_ACTIVE) and f.hit.is_empty():
		warnings.append("%s: fotogramma attivo senza hitbox" % where)
	return f


static func _int_list(v: Variant, n: int) -> Array[int]:
	var out: Array[int] = []
	if not (v is Array) or (v as Array).size() != n:
		return out
	for x: Variant in v:
		if not (x is int or x is float):
			out.clear()
			return out
		out.append(int(x))
	return out


func missing_required() -> PackedStringArray:
	var out := PackedStringArray()
	for a in REQUIRED.get(id, PackedStringArray()):
		if not animations.has(StringName(a)):
			out.append(a)
	return out


func has_anim(anim_name: StringName) -> bool:
	return animations.has(anim_name)


## Animazione con questo nome, oppure la prima alternativa disponibile.
func clip(anim_name: StringName) -> AnimClip:
	if animations.has(anim_name):
		return animations[anim_name]
	for alt in FALLBACKS.get(String(anim_name), PackedStringArray()):
		if animations.has(StringName(alt)):
			return animations[StringName(alt)]
	if animations.has(&"idle"):
		return animations[&"idle"]
	for k: StringName in animations:
		return animations[k]
	var empty := AnimClip.new()
	empty.name = anim_name
	var f := AnimFrame.new()
	f.rect = Rect2i(0, 0, 1, 1)
	empty.frames.append(f)
	return empty


## Animazione d'attacco ritemporizzata sui tempi dell'AttackData (in cache).
func attack_clip(anim_name: StringName, atk: AttackData) -> AnimClip:
	var key := "%s|%d|%d|%d|%s" % [anim_name, atk.startup, atk.active, atk.recovery, atk.air]
	if not _retimed.has(key):
		_retimed[key] = clip(anim_name).retimed(atk.startup, atk.active, -1 if atk.air else atk.recovery)
	return _retimed[key]


func source_name() -> String:
	return ["vero", "segnaposto", "debug"][source]
