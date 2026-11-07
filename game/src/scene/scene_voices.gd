class_name SceneVoices
extends RefCounted
## Le voci delle battute (decisione 92 della storia). Come il testo, non stanno nel repo: le fa il
## laboratorio (tts/script/voci.py, fase "finali") in una cartella per file di battute, con un
## manifest.json {"formato": 1, "battute": {"<scena>/<id>": {"file", "durata_s", "testo_sha1",
## "inviluppo", ...}}} e gli OGG accanto (file è relativo al manifest).
##
## Dove si cerca la cartella, in quest'ordine:
##   1. res://assets_private/voci/<file>/: c'è solo nelle build (lo copia tools/site/export_web.sh);
##   2. <laboratorio>/tts/voci/<file>/: solo durante lo sviluppo (non nelle build esportate).
## Una voce si usa solo se testo_sha1 torna con il testo della battuta di oggi: una voce vecchia
## resta muta invece di dire un'altra cosa. Senza voci le scene girano come prima.

const BUILD_DIR := "res://assets_private/voci"
## Inviluppo sopra questa soglia (0-100): la bocca è aperta.
const MOUTH_OPEN := 28

static var _cache: Dictionary = {}
## Per i test: una cartella da cercare prima delle altre ("" per nessuna).
static var root_override: String = ""


## La voce della battuta: {"stream": AudioStream, "env": PackedByteArray (0-100 per tick),
## "ticks": durata in tick}, oppure {} se manca o non torna con `text`.
static func voice(file_id: String, scene_id: String, id: String, text: String) -> Dictionary:
	var man := _load(file_id)
	if man.is_empty():
		return {}
	var e: Variant = (man["data"].get("battute", {}) as Dictionary).get(scene_id + "/" + id)
	if not (e is Dictionary):
		return {}
	var entry: Dictionary = e
	if str(entry.get("testo_sha1", "")) != text.sha1_text():
		return {}
	var path := str(man["dir"]).path_join(str(entry.get("file", "")))
	var stream := _load_stream(path)
	if stream == null:
		return {}
	var env := PackedByteArray()
	for v: Variant in entry.get("inviluppo", []):
		env.append(clampi(int(v), 0, 100))
	var ticks := maxi(env.size(), int(ceil(float(entry.get("durata_s", 0.0)) * 60.0)))
	return {"stream": stream, "env": env, "ticks": ticks}


## La cartella delle voci di `file_id`, o "" se non c'è.
static func dir_of(file_id: String) -> String:
	if root_override != "" and FileAccess.file_exists(root_override.path_join(file_id).path_join("manifest.json")):
		return root_override.path_join(file_id)
	var p := BUILD_DIR.path_join(file_id)
	if FileAccess.file_exists(p.path_join("manifest.json")):
		return p
	if OS.has_feature("template"):
		return ""
	var dev := lab_dir().path_join(file_id)
	return dev if FileAccess.file_exists(dev.path_join("manifest.json")) else ""


## La cartella delle voci nel laboratorio di questo PC, durante lo sviluppo.
static func lab_dir() -> String:
	var home := OS.get_environment("USERPROFILE")
	if home.is_empty():
		home = OS.get_environment("HOME")
	if home.is_empty():
		return ""
	return home.replace("\\", "/").path_join("ctrlaltrevenge-lab/tts/voci")


static func clear_cache() -> void:
	_cache.clear()


static func _load(file_id: String) -> Dictionary:
	if _cache.has(file_id):
		return _cache[file_id]
	var out := {}
	var dir := dir_of(file_id)
	if dir != "":
		var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(dir.path_join("manifest.json")))
		if d is Dictionary and int((d as Dictionary).get("formato", 0)) == 1:
			out = {"dir": dir, "data": d}
		else:
			push_warning("Voci non valide: %s" % dir)
	_cache[file_id] = out
	return out


## Nelle build l'OGG è importato (si carica con load); nel laboratorio si legge dal file.
static func _load_stream(path: String) -> AudioStream:
	if path.begins_with("res://") and ResourceLoader.exists(path):
		return load(path) as AudioStream
	if FileAccess.file_exists(path):
		return AudioStreamOggVorbis.load_from_file(path)
	return null
