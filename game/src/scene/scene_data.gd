class_name SceneData
extends RefCounted
## Il copione di una scena nel motore (decisione 68: bande nere, primi piani, battute a pressione),
## letto da game/data/scene/<id>.json. È pubblico: dice chi c'è, dove si muove, le inquadrature e chi
## parla, ma non il testo delle battute, che sta nei file privati (SceneLines).
##
## Il formato:
##   "formato": 1, "id", "spazio" ("arena": x dal bordo sinistro della telecamera dell'arena, y nella
##   fascia del pavimento; "stanza": coordinate del mondo platform, rispetto al segno "rif" della mappa),
##   "battute" (il file privato), "musica" (brano della scena, se c'è),
##   "attori": {nome: {"tipo" (i dati del combattente), "foglio" (sprite, se diverso), "dal_gioco"
##     (parte dalla posa dell'attore vero), "x", "y", "verso", "anim", "variante", "nome", "colore",
##     "primo_piano", "resta" (a scena finita resta come comparsa)}},
##   "esito": {nome: {"x", "y", "verso"}}: dove stanno gli attori alla fine. La simulazione lo applica
##     subito, quando la scena parte; il lettore lo usa per il passaggio di consegne alle comparse;
##   "passi": [{"fai": ..., ...}] (vedi STEPS).
## Durante la scena la simulazione è ferma, come nella pausa: replay e test non cambiano.

const DIR := "res://data/scene"

## I passi della regia e i loro parametri ammessi (li controlla un test).
const STEPS := {
	# Le bande nere: dentro (true) o fuori. Di solito non serve: entrano ed escono da sole.
	"bande": ["entra", "tick", "aspetta"],
	# Stacco: l'inquadratura cambia di colpo. Centro dato ("centro") o un attore ("su", con "alto" px
	# sopra i piedi o il "punto" dello sprite, più lo "scarto" [dx, dy]), e lo zoom (2-3 per i piani
	# stretti e i dettagli); "segui" tiene l'attore in quadro mentre si muove.
	"inquadra": ["centro", "su", "alto", "punto", "scarto", "zoom", "segui"],
	# Movimento di macchina verso un'inquadratura, morbido, in "tick".
	"camera": ["centro", "su", "alto", "punto", "scarto", "zoom", "tick", "segui", "aspetta"],
	"cammina": ["chi", "a", "vel", "anim", "aspetta"],
	"anim": ["chi", "anim"],
	"verso": ["chi", "verso"],
	"attendi": ["tick"],
	# Una battuta: chi parla, l'id del testo, il primo piano (o "" per nessuno), "pieno" per il primo
	# piano a tutto schermo con lo sfondo sfocato, e l'animazione di chi parla.
	"battuta": ["chi", "id", "primo_piano", "pieno", "anim"],
	# Un primo piano senza parole, per "tick": uno sguardo, una reazione.
	"primo_piano": ["chi", "primo_piano", "pieno", "tick"],
	"suono": ["nome", "vol"],
	# Il laser del messo: la linea rossa da "da" al "punto" di "a" per "tick", poi il segno.
	"laser": ["da", "a", "punto", "tick", "segno"],
	# Un evento per chi ospita la scena (per esempio "pioggia").
	"evento": ["nome"],
	# Un murale di Totò (SceneMural), da res://assets/murales/<capitolo>/<id>/: "id" come
	# "<capitolo>/<id>" (o con "capitolo"); "da"/"a" sono l'angolo del riquadro dello schermo nel murale
	# (se mancano, lo scorrimento o la camera di murale.json) in "tick"; "rivela" (vero) lo dipinge a
	# spray sopra il gioco in "rivela_tick", se no è uno stacco; "luci" (vero) fa pulsare le luci.
	# "chiudi": true lo toglie con lo spray all'indietro e torna il gioco. Si aspetta la fine dello spray.
	"murale": ["id", "capitolo", "da", "a", "tick", "rivela", "rivela_tick", "luci", "chiudi", "aspetta"],
}

static var _cache: Dictionary = {}

var id: String = ""
var space: String = "arena"
var rif: String = ""
var lines_file: String = ""
var music: String = ""
var actors: Dictionary = {}
var outcome: Dictionary = {}
var steps: Array = []
var errors: PackedStringArray = []


static func path_of(scene_id: String) -> String:
	return DIR.path_join(scene_id + ".json")


## Il copione `scene_id` (letto una volta sola); con errori di formato, `errors` non è vuoto.
static func load_scene(scene_id: String) -> SceneData:
	if _cache.has(scene_id):
		return _cache[scene_id]
	var s := SceneData.new()
	s.id = scene_id
	var p := path_of(scene_id)
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(p)) if FileAccess.file_exists(p) else null
	if not (d is Dictionary):
		s.errors.append("copione mancante o non valido: %s" % p)
	else:
		s._parse(d)
	_cache[scene_id] = s
	return s


static func clear_cache() -> void:
	_cache.clear()


func _parse(d: Dictionary) -> void:
	if int(d.get("formato", 0)) != 1:
		errors.append("formato diverso da 1")
	space = str(d.get("spazio", "arena"))
	if not space in ["arena", "stanza"]:
		errors.append("spazio sconosciuto: %s" % space)
	rif = str(d.get("rif", ""))
	lines_file = str(d.get("battute", ""))
	music = str(d.get("musica", ""))
	actors = d.get("attori", {})
	outcome = d.get("esito", {})
	steps = d.get("passi", [])
	for k: String in outcome:
		if not actors.has(k):
			errors.append("esito di un attore che non c'è: %s" % k)
	for i in steps.size():
		var st: Variant = steps[i]
		if not (st is Dictionary):
			errors.append("passo %d non è un oggetto" % i)
			continue
		var fai := str((st as Dictionary).get("fai", ""))
		if not STEPS.has(fai):
			errors.append("passo %d: azione sconosciuta \"%s\"" % [i, fai])
			continue
		var allowed: Array = STEPS[fai]
		for k: String in st:
			if k != "fai" and not allowed.has(k):
				errors.append("passo %d (%s): parametro sconosciuto \"%s\"" % [i, fai, k])
		if fai == "murale" and not bool((st as Dictionary).get("chiudi", false)):
			var ci := SceneMural.split_id(st)
			if ci[0] == "" or ci[1] == "":
				errors.append("passo %d (murale): manca \"id\" come \"<capitolo>/<id>\"" % i)
			for k in ["da", "a"]:
				if (st as Dictionary).has(k) and not ((st[k] is Array) and (st[k] as Array).size() == 2):
					errors.append("passo %d (murale): \"%s\" vuole [x, y]" % [i, k])
			continue
		for k in ["chi", "su", "da", "a"]:
			if (st as Dictionary).has(k) and (st[k] is String) and not actors.has(str(st[k])):
				errors.append("passo %d (%s): attore sconosciuto \"%s\"" % [i, fai, st[k]])


## Gli id delle battute, nell'ordine del copione.
func line_ids() -> PackedStringArray:
	var out := PackedStringArray()
	for st: Dictionary in steps:
		if str(st.get("fai", "")) == "battuta":
			out.append(str(st.get("id", "")))
	return out


## L'esito di un attore: {"x", "y", "verso"}, o vuoto.
func end_of(actor: String) -> Dictionary:
	return outcome.get(actor, {})
