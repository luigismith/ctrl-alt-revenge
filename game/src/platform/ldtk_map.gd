class_name LdtkMap
extends RefCounted
## Legge un livello di un progetto LDtk 1.5 (il JSON che salva l'editor) e lo trasforma nei dati del
## motore: la griglia delle celle, i segni e le entità. La legenda dei tipi è quella della sessione
## mappe (docs/lore/livelli/legenda-ldtk.md); come si usa l'editor è in docs/ldtk.md.
##
## Il percorso è "res://…/nome.ldtk" (il primo livello) o "res://…/nome.ldtk#Livello". La lettura è
## deterministica: a parità di file dà la stessa griglia, gli stessi segni nello stesso ordine e quindi
## gli stessi replay della mappa di testo da cui viene.

const TILE := SolidGrid.TILE

## I valori del livello Collisioni (legenda §3).
enum Val { NIENTE, PIENO, SOTTILE, BAGNATO, ELASTICO, CROLLO, MURO_FINTO, ROMPIBILE, VUOTO, ELETTRICO }
## Come li gioca il motore oggi. Quelli che non ha ancora vanno alla cella più vicina, con un avviso:
## Bagnato, Crollo ed Elettrico sono pieni, Rompibile è pieno finché lo scatto non lo rompe, Elastico è sottile, il muro finto è vuoto.
## Vuoto è una cella vuota: in fondo alla mappa la fossa non ha fondo e si perde una vita.
const CELL_OF: Array[int] = [
	SolidGrid.Cell.EMPTY, SolidGrid.Cell.SOLID, SolidGrid.Cell.THIN, SolidGrid.Cell.SOLID, SolidGrid.Cell.THIN,
	SolidGrid.Cell.SOLID, SolidGrid.Cell.EMPTY, SolidGrid.Cell.SOLID, SolidGrid.Cell.EMPTY, SolidGrid.Cell.SOLID,
]
const NOMI: Array[String] = ["", "Pieno", "Sottile", "Bagnato", "Elastico", "Crollo", "MuroFinto", "Rompibile",
	"Vuoto", "Elettrico"]
## I valori che il motore gioca già come dice la legenda.
const PRONTI: Array[int] = [Val.NIENTE, Val.PIENO, Val.SOTTILE, Val.VUOTO, Val.ROMPIBILE]
## Le scene che nella mappa di testo hanno una lettera (tools/ldtk/livelli_ldtk.py ha la stessa tabella).
const SEGNI_SCENA := {"MIMMO": "M"}
## Prima del riavvio nessuna fossa supera queste celle (legenda §1).
const FOSSA_MAX := 6
## I soli nemici che stanno fuori dalle arene, sulle piattaforme (legenda §4b): rider, Esattori e gli
## altri umani stanno solo nelle arene.
const DRONI: Array[String] = ["colomba", "vedetta", "segugio", "ragno"]

var grid: SolidGrid
## I valori di Collisioni, una cella per byte, riga per riga.
var values: PackedByteArray = PackedByteArray()
## Le entità dei livelli Entita e Zone, nell'ordine del file:
## {"tipo", "iid", "livello" ("Entita"/"Zone"), "px": Vector2i (il perno), "pos": Vector2i (in alto a
## sinistra), "size": Vector2i, "campi": {nome: valore}}. I riferimenti diventano l'iid dell'entità,
## i punti Vector2i di cella.
var entities: Array[Dictionary] = []
## Quello che non va, trovato da check(): gli errori rompono il livello, gli avvisi no.
var errors: PackedStringArray = PackedStringArray()
var warnings: PackedStringArray = PackedStringArray()
## I nomi dei livelli del file, nell'ordine dell'editor (il prologo nuovo ne ha due, A e B).
var levels: PackedStringArray = PackedStringArray()

## I progetti già letti, per percorso del file: i test caricano il prologo molte volte.
static var _parsed: Dictionary = {}


static func read(path: String) -> LdtkMap:
	var m := LdtkMap.new()
	var file := path
	var level_id := ""
	if "#" in path:
		file = path.get_slice("#", 0)
		level_id = path.get_slice("#", 1)
	var project := _project(file)
	if project.is_empty():
		m.grid = SolidGrid.new(1, 1)
		return m
	var level: Dictionary = {}
	for lv: Dictionary in project.get("levels", []):
		m.levels.append(String(lv.get("identifier", "")))
		if level.is_empty() and (level_id.is_empty() or lv.get("identifier") == level_id):
			level = lv
	if level.is_empty():
		push_error("Livello %s non trovato in %s" % [level_id, file])
		m.grid = SolidGrid.new(1, 1)
		return m
	m._build(level)
	return m


static func _project(file: String) -> Dictionary:
	var project: Dictionary = _parsed.get(file, {})
	if project.is_empty():
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(file))
		if not parsed is Dictionary:
			push_error("Progetto LDtk non leggibile: %s" % file)
			return {}
		project = parsed
		_parsed[file] = project
	return project


## I nomi dei livelli di un file .ldtk (con o senza "#Livello" in fondo).
static func level_names(path: String) -> PackedStringArray:
	var out := PackedStringArray()
	for lv: Dictionary in _project(path.get_slice("#", 0)).get("levels", []):
		out.append(String(lv.get("identifier", "")))
	return out


## Il percorso del livello dopo questo, se l'Uscita porta a un altro livello dello stesso file;
## altrimenti "" (l'Uscita porta a una scena o al capitolo dopo, e ci pensa il gioco).
static func next_path(path: String, g: SolidGrid) -> String:
	var file := path.get_slice("#", 0)
	if g.next_level.is_empty() or g.next_level not in level_names(file):
		return ""
	return file + "#" + g.next_level


func _build(level: Dictionary) -> void:
	var layers := {}
	for li: Dictionary in level.get("layerInstances", []):
		layers[li["__identifier"]] = li
	var coll: Dictionary = layers.get("Collisioni", {})
	var w := int(coll.get("__cWid", 1))
	var h := int(coll.get("__cHei", 1))
	grid = SolidGrid.new(w, h)
	values.resize(w * h)
	var csv: Array = coll.get("intGridCsv", [])
	for i in mini(csv.size(), w * h):
		var v := int(csv[i])
		if v < 0 or v >= CELL_OF.size():
			v = Val.NIENTE
		values[i] = v
		grid.cells[i] = CELL_OF[v]
		if v == Val.ROMPIBILE:
			grid.breakable[i] = true
	for layer_name: String in ["Entita", "Zone"]:
		for e: Dictionary in layers.get(layer_name, {}).get("entityInstances", []):
			entities.append(_entity(e, layer_name))
	_marks()


static func _entity(e: Dictionary, layer_name: String) -> Dictionary:
	var px := Vector2i(int(e["px"][0]), int(e["px"][1]))
	var size := Vector2i(int(e.get("width", TILE)), int(e.get("height", TILE)))
	var pivot: Array = e.get("__pivot", [0, 0])
	var pos := px - Vector2i(roundi(float(pivot[0]) * size.x), roundi(float(pivot[1]) * size.y))
	var campi := {}
	for f: Dictionary in e.get("fieldInstances", []):
		campi[f["__identifier"]] = _value(f.get("__value"))
	return {"tipo": e["__identifier"], "iid": e.get("iid", ""), "livello": layer_name, "px": px, "pos": pos,
		"size": size, "campi": campi}


static func _value(v: Variant) -> Variant:
	if v is Array:
		var out := []
		for x: Variant in v:
			out.append(_value(x))
		return out
	if v is Dictionary:
		if v.has("entityIid"):
			return v["entityIid"]
		if v.has("cx"):
			return Vector2i(int(v["cx"]), int(v["cy"]))
		return v
	if v is float and v == floorf(v) and absf(v) < 1e9:
		return v  # JSON dà sempre float: chi legge un Int usa int()
	return v


## I segni di una volta, per il codice che li chiede per lettera (vedi la mappa di testo):
## G la partenza, X quella dopo il riavvio, Z l'uscita, le lettere dei cartelli, M e le altre scene
## della tabella, "/" ogni cella della porta. Dentro ogni lettera l'ordine è riga per riga, da
## sinistra, come in SolidGrid.from_rows. Ci sono anche i testi dei cartelli e le ripartenze.
func _marks() -> void:
	var cps: Array[Dictionary] = []
	for e in entities:
		if e["livello"] != "Entita":
			continue
		var c: Dictionary = e["campi"]
		var p: Vector2i = e["px"]
		match e["tipo"]:
			"Partenza":
				_mark("X" if c.get("dopo_riavvio", false) else "G", p)
			"Uscita":
				_mark("Z", p)
				grid.next_level = _str(c.get("prossima"))
			"Scena":
				if SEGNI_SCENA.has(c.get("id", "")):
					_mark(SEGNI_SCENA[c["id"]], p)
			"Cartello":
				var id: String = c.get("id", "")
				if id.is_empty():
					continue
				_mark(id, p)
				grid.signs[id] = [String(c.get("titolo", "")), String(c.get("riga", ""))]
				if c.get("ripartenza", true):
					cps.append({"id": id, "x": p.x})
			"Porta":
				var pos: Vector2i = e["pos"]
				var size: Vector2i = e["size"]
				for y in range(pos.y / TILE, (pos.y + size.y) / TILE):
					for x in range(pos.x / TILE, (pos.x + size.x) / TILE):
						_mark("/", Vector2i(x * TILE + TILE / 2, (y + 1) * TILE))
	# Riga per riga e da sinistra, come from_rows: così anche l'ordine delle lettere è lo stesso.
	_pending.sort_custom(func(a: Array, b: Array) -> bool:
		var pa: Vector2i = a[1]
		var pb: Vector2i = b[1]
		return pa.y < pb.y or (pa.y == pb.y and pa.x < pb.x))
	for m in _pending:
		if not grid.marks.has(m[0]):
			grid.marks[m[0]] = []
		grid.marks[m[0]].append(m[1])
	_pending.clear()
	cps.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a["x"] < b["x"])
	for cp in cps:
		grid.checkpoints.append(cp["id"])
	grid.entities = entities
	grid.arenas = _arenas()


## Le arene, dalle zone Arena (legenda §5): {"id", "rect" (in pixel: la telecamera si ferma sul suo
## lato sinistro, il fondo è il pavimento), "inclinata", "corsie", "fine", "ripartenza" (l'id del
## cartello o della ripartenza che chiude l'arena, "" se manca)}. Da sinistra.
func _arenas() -> Array[Dictionary]:
	var ids := {}
	for e in entities:
		ids[e["iid"]] = _str(e["campi"].get("id"))
	var out: Array[Dictionary] = []
	for e in entities:
		if e["tipo"] != "Arena":
			continue
		var c: Dictionary = e["campi"]
		var ref: Variant = c.get("ripartenza")
		out.append({"id": _str(c.get("id")),
			"rect": Rect2i(e["pos"], e["size"]),
			"inclinata": bool(c.get("inclinata", true)), "corsie": int(c.get("corsie", 3)),
			"fine": _str(c.get("fine")) if c.get("fine") != null else "tutti_ko",
			"ripartenza": ids.get(ref, "") if ref is String else ""})
	out.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return (a["rect"] as Rect2i).position.x < (b["rect"] as Rect2i).position.x)
	return out


var _pending: Array[Array] = []


func _mark(k: String, p: Vector2i) -> void:
	_pending.append([k, p])


## Un campo di testo, che LDtk lascia null quando è vuoto.
static func _str(v: Variant) -> String:
	return "" if v == null else String(v)


func value(x: int, y: int) -> int:
	if x < 0 or y < 0 or x >= grid.width or y >= grid.height:
		return Val.NIENTE
	return values[y * grid.width + x]


## I controlli della legenda (§6). Riempie errors e warnings e restituisce true se non ci sono errori.
## Non controlla ancora gli appigli oltre 8 celle e i segreti raggiungibili col braccio bloccato:
## servirebbe un risolutore dei salti.
func check() -> bool:
	errors.clear()
	warnings.clear()
	var w := grid.width
	var h := grid.height
	var by_iid := {}
	for e in entities:
		by_iid[e["iid"]] = e
	# I punti da cui si riparte e il riavvio.
	var respawn: Array[int] = []
	var reboot_x := grid.pixel_width()
	for e in entities:
		var c: Dictionary = e["campi"]
		match e["tipo"]:
			"Partenza":
				if c.get("dopo_riavvio", false):
					reboot_x = mini(reboot_x, e["px"].x)
				respawn.append(e["px"].x)
			"Ripartenza":
				respawn.append(e["px"].x)
			"Cartello":
				if c.get("ripartenza", true):
					respawn.append(e["px"].x)
	# Le fosse: le colonne con l'ultima riga vuota.
	var x := 0
	while x < w:
		if grid.cell(x, h - 1) != SolidGrid.Cell.EMPTY:
			x += 1
			continue
		var a := x
		while x < w and grid.cell(x, h - 1) == SolidGrid.Cell.EMPTY:
			x += 1
		var b := x - 1
		var where := "colonne %d-%d" % [a, b]
		var has_void := false
		for cx in range(a, b + 1):
			has_void = has_void or value(cx, h - 1) == Val.VUOTO
		if not has_void:
			warnings.append("fossa senza Vuoto alle %s: si cade fuori ma nell'editor non si vede" % where)
		var before := false
		for rx in respawn:
			if rx < a * TILE:
				before = true
			if rx >= a * TILE and rx < (b + 1) * TILE:
				errors.append("una ripartenza sta sopra la fossa alle %s" % where)
		if not before:
			errors.append("nessuna ripartenza prima della fossa alle %s" % where)
		if (b + 1) * TILE <= reboot_x and b - a + 1 > FOSSA_MAX:
			errors.append("fossa di %d celle alle %s prima del riavvio (massimo %d)" % [b - a + 1, where, FOSSA_MAX])
	# Vuoto dove c'è un fondo, e i valori che il motore non fa ancora.
	var unknown := {}
	for cy in h:
		for cx in w:
			var v := value(cx, cy)
			if v == Val.VUOTO and grid.cell(cx, h - 1) != SolidGrid.Cell.EMPTY:
				warnings.append("Vuoto alla cella %d,%d, ma la colonna ha il fondo: lì non si perde la vita" % [cx, cy])
			elif v not in PRONTI:
				unknown[v] = unknown.get(v, 0) + 1
	for v: int in unknown:
		warnings.append("%d celle %s: il motore non lo fa ancora e le gioca come %s" % [unknown[v], NOMI[v],
			["vuote", "piene", "sottili"][CELL_OF[v]]])
	# I riferimenti di pannelli, leve e persone.
	for e in entities:
		var keys: Array[String] = []
		match e["tipo"]:
			"Pannello":
				keys = ["apre", "chiude"]
			"Leva":
				keys = ["apre"]
			"Persona":
				keys = ["serve", "premio"]
			_:
				continue
		var ok := 0
		for k in keys:
			var v: Variant = e["campi"].get(k)
			for r: Variant in (v if v is Array else [v]):
				if r is String and by_iid.has(r):
					ok += 1
		if ok == 0:
			errors.append("%s a %d,%d senza un riferimento valido" % [e["tipo"], e["px"].x / TILE, e["px"].y / TILE])
	# Le arene chiudono su una ripartenza; l'uscita porta da qualche parte.
	for e in entities:
		var ref: Variant = e["campi"].get("ripartenza")
		if e["tipo"] == "Arena" and not (ref is String and by_iid.has(ref)):
			errors.append("Arena %s senza una ripartenza valida: dopo lo scontro non si saprebbe dove ripartire"
				% _str(e["campi"].get("id")))
		elif e["tipo"] == "Uscita" and _str(e["campi"].get("prossima")).is_empty():
			warnings.append("Uscita a %d,%d senza prossima: non porta da nessuna parte" % [e["px"].x / TILE, e["px"].y / TILE])
	# Fuori dalle arene solo droni.
	for e in entities:
		if e["tipo"] != "Nemico":
			continue
		var arena: Variant = e["campi"].get("arena")
		var tipo := String(e["campi"].get("tipo", ""))
		if not (arena is String and by_iid.has(arena)) and tipo not in DRONI:
			errors.append("Nemico %s a %d,%d fuori dalle arene: lì stanno solo i droni (%s)" % [tipo,
				e["px"].x / TILE, e["px"].y / TILE, ", ".join(DRONI)])
	# I pieni sospesi: gruppi di pieni che non toccano il fondo né i lati della mappa.
	var seen := PackedByteArray()
	seen.resize(w * h)
	for cy in h:
		for cx in w:
			if seen[cy * w + cx] or grid.cell(cx, cy) != SolidGrid.Cell.SOLID:
				continue
			var stack: Array[Vector2i] = [Vector2i(cx, cy)]
			seen[cy * w + cx] = 1
			var grounded := false
			while not stack.is_empty():
				var p: Vector2i = stack.pop_back()
				if p.y == h - 1 or p.x == 0 or p.x == w - 1:
					grounded = true
				for d: Vector2i in [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]:
					var q := p + d
					if q.x < 0 or q.y < 0 or q.x >= w or q.y >= h or seen[q.y * w + q.x]:
						continue
					if grid.cell(q.x, q.y) == SolidGrid.Cell.SOLID:
						seen[q.y * w + q.x] = 1
						stack.append(q)
			if not grounded:
				warnings.append("pieno sospeso alla cella %d,%d: nella grafica gli serve un sostegno" % [cx, cy])
	return errors.is_empty()
