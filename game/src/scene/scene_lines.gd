class_name SceneLines
extends RefCounted
## Le battute delle scene. Non stanno nel repo pubblico (la storia è privata): il copione di una
## scena (game/data/scene/*.json) nomina solo chi parla e l'id della battuta, il testo sta in un file
## privato per capitolo, {"formato": 1, "scene": {"<scena>": {"<id>": "testo"}}}.
##
## Dove si cerca il file, in quest'ordine:
##   1. res://data/battute/<file>.json: c'è solo nelle build (lo copia tools/site/export_web.sh; la
##      demo web ha le battute del prologo, decisione 68), ed è ignorato da git;
##   2. <repo>/docs/lore/battute/<file>.json: la cartella privata della storia, solo durante lo
##      sviluppo (non nelle build esportate).
## Senza file la scena gira lo stesso, con un segnaposto al posto del testo.

const BUILD_DIR := "res://data/battute"
## Il segnaposto: dice solo che la battuta c'è, senza il testo.
const PLACEHOLDER := "(battuta nella cartella privata della storia)"

static var _cache: Dictionary = {}


## Il testo della battuta `id` della scena `scene_id`, dal file `file_id`; il segnaposto se manca.
static func text(file_id: String, scene_id: String, id: String) -> String:
	var t := find(file_id, scene_id, id)
	return t if t != "" else PLACEHOLDER


## Il testo, o "" se il file o la battuta mancano.
static func find(file_id: String, scene_id: String, id: String) -> String:
	var d := _load(file_id)
	var scenes: Dictionary = d.get("scene", {})
	var lines: Dictionary = scenes.get(scene_id, {})
	return str(lines.get(id, ""))


## Il file delle battute è stato trovato (in una build o nella cartella privata).
static func available(file_id: String) -> bool:
	return not _load(file_id).is_empty()


## Dove si trova il file delle battute, o "" se non c'è.
static func path_of(file_id: String) -> String:
	var p := BUILD_DIR.path_join(file_id + ".json")
	if FileAccess.file_exists(p):
		return p
	if OS.has_feature("template"):
		return ""
	var dev := private_dir().path_join(file_id + ".json")
	return dev if FileAccess.file_exists(dev) else ""


## La cartella privata delle battute durante lo sviluppo: docs/lore/battute accanto a game/.
static func private_dir() -> String:
	return ProjectSettings.globalize_path("res://").path_join("../docs/lore/battute").simplify_path()


static func clear_cache() -> void:
	_cache.clear()


static func _load(file_id: String) -> Dictionary:
	if _cache.has(file_id):
		return _cache[file_id]
	var out := {}
	var p := path_of(file_id)
	if p != "":
		var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(p))
		if d is Dictionary and int((d as Dictionary).get("formato", 0)) == 1:
			out = d
		else:
			push_warning("Battute non valide: %s" % p)
	_cache[file_id] = out
	return out
