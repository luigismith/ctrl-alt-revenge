class_name SolidGrid
extends RefCounted
## La griglia dei solidi dei tratti platform: celle da 20 px, cioè un terzo di metro a 60 px/m.
##
## Le celle sono di tre tipi:
## - vuote;
## - piene: muri, pavimenti e soffitti, solidi da ogni lato;
## - sottili: si attraversano da sotto e di lato, e reggono solo chi ci arriva sopra cadendo
##   (balconi, impalcature, tettoie). Con GIÙ + SALTO si scende.
##
## La griglia si legge da una mappa di testo (vedi from_rows) o da un livello dell'editor LDtk
## (vedi LdtkMap e docs/ldtk.md), che porta anche le entità e i testi dei cartelli.

const TILE := 20

enum Cell { EMPTY, SOLID, THIN }

var width: int = 0
var height: int = 0
var cells: PackedByteArray = PackedByteArray()
## Segni della mappa che non sono celle: lettera → posizioni in pixel del mondo (centro in
## basso della cella), per esempio il punto di partenza di GIG ("G").
var marks: Dictionary[String, Array] = {}
## Solo dai livelli LDtk: i testi dei cartelli (lettera → [titolo, riga]), le lettere dei cartelli
## che fanno da ripartenza, da sinistra, e tutte le entità (vedi LdtkMap.entities).
var signs: Dictionary = {}
var checkpoints: Array[String] = []
var entities: Array[Dictionary] = []
## Solo dai livelli LDtk: dove porta l'Uscita (un altro livello dello stesso file o una scena) e le
## arene disegnate come zone, da sinistra (vedi LdtkMap._marks).
var next_level: String = ""
var arenas: Array[Dictionary] = []
## Solo dai livelli LDtk: le celle Rompibile ancora intere (indice → true), piene finché lo scatto non
## le rompe (legenda §3), e quelle rotte, in ordine, per l'impronta.
var breakable: Dictionary = {}
var broken: PackedInt32Array = []


func _init(w: int = 0, h: int = 0) -> void:
	width = w
	height = h
	cells.resize(w * h)
	cells.fill(Cell.EMPTY)


## Legge una mappa di testo, una riga per fila di celle:
##   "#" pieno · "=" sottile · "." vuoto · qualsiasi altra lettera è un segno su cella vuota.
## Le righe più corte si completano con celle vuote.
static func from_rows(rows: PackedStringArray) -> SolidGrid:
	var w := 0
	for r in rows:
		w = maxi(w, r.length())
	var g := SolidGrid.new(w, rows.size())
	for y in rows.size():
		var r := rows[y]
		for x in r.length():
			var c := r[x]
			match c:
				"#":
					g.set_cell(x, y, Cell.SOLID)
				"=":
					g.set_cell(x, y, Cell.THIN)
				".", " ":
					pass
				_:
					if not g.marks.has(c):
						g.marks[c] = []
					g.marks[c].append(Vector2i(x * TILE + TILE / 2, (y + 1) * TILE))
	return g


## Legge una mappa da file: le righe che iniziano con ";" sono commenti. Un file .ldtk (con
## "#Livello" in fondo per sceglierne uno) lo legge LdtkMap.
static func load_file(path: String) -> SolidGrid:
	if path.get_slice("#", 0).ends_with(".ldtk"):
		return LdtkMap.read(path).grid
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("Mappa non leggibile: %s" % path)
		return SolidGrid.new(1, 1)
	var rows := PackedStringArray()
	for line in text.replace("\r", "").split("\n"):
		if not line.begins_with(";"):
			rows.append(line)
	while not rows.is_empty() and rows[rows.size() - 1].strip_edges().is_empty():
		rows.remove_at(rows.size() - 1)
	return from_rows(rows)


func set_cell(x: int, y: int, c: Cell) -> void:
	if x >= 0 and y >= 0 and x < width and y < height:
		cells[y * width + x] = c


## Il rettangolo (in pixel, come rect_hits_solid) tocca una cella Rompibile ancora intera?
func has_breakable(left: int, top: int, right: int, bottom: int) -> bool:
	if breakable.is_empty() or right <= left or bottom <= top:
		return false
	for cy in range(floori(float(top) / TILE), floori(float(bottom - 1) / TILE) + 1):
		for cx in range(floori(float(left) / TILE), floori(float(right - 1) / TILE) + 1):
			if cx >= 0 and cy >= 0 and cx < width and cy < height and breakable.has(cy * width + cx):
				return true
	return false


## Rompe le celle Rompibile che il rettangolo (in pixel, come rect_hits_solid) tocca, con tutte quelle
## attaccate: una porta o una parete di tavole si rompe tutta insieme. Restituisce il riquadro in pixel
## delle celle rotte, vuoto se non ha rotto niente.
func break_in(left: int, top: int, right: int, bottom: int) -> Rect2i:
	if breakable.is_empty() or right <= left or bottom <= top:
		return Rect2i()
	var todo: Array[int] = []
	for cy in range(floori(float(top) / TILE), floori(float(bottom - 1) / TILE) + 1):
		for cx in range(floori(float(left) / TILE), floori(float(right - 1) / TILE) + 1):
			if cx >= 0 and cy >= 0 and cx < width and cy < height and breakable.has(cy * width + cx):
				todo.append(cy * width + cx)
	var out := Rect2i()
	while not todo.is_empty():
		var i: int = todo.pop_back()
		if not breakable.has(i):
			continue
		breakable.erase(i)
		broken.append(i)
		cells[i] = Cell.EMPTY
		var x := i % width
		var y := i / width
		var r := Rect2i(x * TILE, y * TILE, TILE, TILE)
		out = r if not out.has_area() else out.merge(r)
		for n: int in [i - 1, i + 1, i - width, i + width]:
			if breakable.has(n) and (n / width == y or n % width == x):
				todo.append(n)
	return out


## Fuori dalla griglia ai lati è pieno (non si esce dalla stanza) e sopra è vuoto. Sotto continua
## l'ultima riga: dove è vuota la fossa non ha fondo e si cade fuori (vita persa); dove è piena si sta.
func cell(x: int, y: int) -> int:
	if y < 0:
		return Cell.EMPTY
	if x < 0 or x >= width:
		return Cell.SOLID
	if y >= height:
		return Cell.EMPTY if cells[(height - 1) * width + x] == Cell.EMPTY else Cell.SOLID
	return cells[y * width + x]


func pixel_width() -> int:
	return width * TILE


func pixel_height() -> int:
	return height * TILE


## Il rettangolo (in pixel interi, estremi inclusi a sinistra e in alto, esclusi a destra e in
## basso) tocca una cella piena?
func rect_hits_solid(left: int, top: int, right: int, bottom: int) -> bool:
	if right <= left or bottom <= top:
		return false
	var x0 := floori(float(left) / TILE)
	var x1 := floori(float(right - 1) / TILE)
	var y0 := floori(float(top) / TILE)
	var y1 := floori(float(bottom - 1) / TILE)
	for cy in range(y0, y1 + 1):
		for cx in range(x0, x1 + 1):
			if cell(cx, cy) == Cell.SOLID:
				return true
	return false


## C'è un bordo d'appoggio (pieno o sottile) esattamente alla riga di pixel `y` sotto i piedi,
## fra le colonne left e right? Una cella sottile regge solo dalla sua riga più alta.
func floor_at(left: int, right: int, y: int, include_thin: bool) -> bool:
	if right <= left:
		return false
	var cy := floori(float(y) / TILE)
	var x0 := floori(float(left) / TILE)
	var x1 := floori(float(right - 1) / TILE)
	for cx in range(x0, x1 + 1):
		var c := cell(cx, cy)
		if c == Cell.SOLID:
			return true
		if include_thin and c == Cell.THIN and y == cy * TILE:
			return true
	return false


## Sotto i piedi (riga `y`) c'è solo pavimento sottile, nessun pieno?
func only_thin_at(left: int, right: int, y: int) -> bool:
	return floor_at(left, right, y, true) and not floor_at(left, right, y, false)
