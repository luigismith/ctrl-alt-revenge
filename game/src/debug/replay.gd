class_name Replay
extends RefCounted
## Registrazione degli ingressi tick per tick, in JSON.
##
## Formato (format 1):
##   {
##     "format": 1,
##     "seed": 7,                      seme del livello
##     "start": {"x": 60, "y": 180},   facoltativo: punto di partenza di GIG
##     "length": 1234,                 numero di tick registrati
##     "note": "testo libero",
##     "input": [[0, ""], [12, "R"], [40, "RA"], [41, "R"]]
##   }
## Ogni voce di "input" vale [tick, tasti tenuti] e resta valida fino alla voce successiva.
## Lettere: L R U D (direzioni), A (attacco), J (salto). Un tasto è "appena premuto" nel
## primo tick in cui compare; una terza stringa facoltativa elenca i tasti premuti di nuovo
## senza essere stati rilasciati (capita solo dal vivo, fra due tick).
## I tick sono quelli della simulazione del livello: il primo tick è 0.

const FORMAT := 1

var level_seed: int = 1
var start: Dictionary = {}
var length: int = 0
var note: String = ""
var source_path: String = ""

## Voci [tick, held, extra_pressed], ordinate per tick.
var _entries: Array[PackedInt32Array] = []
var _last_held: int = 0
var _cursor: int = 0
var _cursor_held: int = 0
var _cursor_prev: int = 0


static func load_file(path: String) -> Replay:
	if not FileAccess.file_exists(path):
		push_warning("Replay non trovato: %s" % path)
		return null
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	var r := from_dict(data)
	if r != null:
		r.source_path = path
	else:
		push_warning("Replay non valido: %s" % path)
	return r


static func from_dict(data: Variant) -> Replay:
	if not (data is Dictionary):
		return null
	var d: Dictionary = data
	if int(d.get("format", 0)) != FORMAT or not (d.get("input") is Array):
		return null
	var r := Replay.new()
	r.level_seed = int(d.get("seed", 1))
	r.start = d.get("start", {}) if d.get("start") is Dictionary else {}
	r.length = int(d.get("length", 0))
	r.note = str(d.get("note", ""))
	var last_tick := -1
	for item: Variant in d["input"]:
		if not (item is Array) or (item as Array).size() < 2:
			return null
		var a: Array = item
		var t := int(a[0])
		if t <= last_tick:
			return null
		last_tick = t
		var held := InputFrame.letters_to_bits(str(a[1]))
		var extra := InputFrame.letters_to_bits(str(a[2])) if a.size() > 2 else 0
		r._entries.append(PackedInt32Array([t, held, extra]))
	if r.length <= 0:
		r.length = last_tick + 1
	r.rewind()
	return r


func to_dict() -> Dictionary:
	var input: Array = []
	for e in _entries:
		var item: Array = [e[0], InputFrame.bits_to_letters(e[1])]
		if e[2] != 0:
			item.append(InputFrame.bits_to_letters(e[2]))
		input.append(item)
	var d := {
		"format": FORMAT,
		"seed": level_seed,
		"length": length,
		"input": input,
	}
	if not start.is_empty():
		d["start"] = start
	if note != "":
		d["note"] = note
	return d


## Scrive il replay con una voce di input per riga, così i diff restano leggibili.
func save_file(path: String) -> Error:
	var d := to_dict()
	var lines: PackedStringArray = []
	lines.append("{")
	lines.append("  \"format\": %d," % FORMAT)
	lines.append("  \"seed\": %d," % level_seed)
	if not start.is_empty():
		lines.append("  \"start\": %s," % JSON.stringify(start))
	if note != "":
		lines.append("  \"note\": %s," % JSON.stringify(note))
	lines.append("  \"length\": %d," % length)
	lines.append("  \"input\": [")
	var input: Array = d["input"]
	for i in input.size():
		lines.append("    %s%s" % [JSON.stringify(input[i]), "," if i < input.size() - 1 else ""])
	lines.append("  ]")
	lines.append("}")
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		return FileAccess.get_open_error()
	f.store_string("\n".join(lines) + "\n")
	f.close()
	return OK


## Registra gli ingressi del tick `tick` (chiamata una volta per tick, in ordine).
func record(tick: int, held: int, pressed: int) -> void:
	var extra := pressed & ~(held & ~_last_held)
	if _entries.is_empty() or held != _last_held or extra != 0:
		_entries.append(PackedInt32Array([tick, held, extra]))
	_last_held = held
	length = tick + 1


func rewind() -> void:
	_cursor = 0
	_cursor_held = 0
	_cursor_prev = 0


## Ingressi del tick `tick`. Va chiamata con tick crescenti (a passi di 1) dopo rewind().
## Dopo la fine della registrazione nessun tasto è tenuto (GIG si ferma invece di continuare
## con gli ultimi tasti).
func frame_at(tick: int) -> InputFrame:
	if tick >= length:
		_cursor_prev = 0
		return InputFrame.new()
	var extra := 0
	while _cursor < _entries.size() and _entries[_cursor][0] <= tick:
		var e := _entries[_cursor]
		_cursor_held = e[1]
		if e[0] == tick:
			extra = e[2]
		_cursor += 1
	var pressed := (_cursor_held & ~_cursor_prev) | extra
	_cursor_prev = _cursor_held
	return InputFrame.new(_cursor_held, pressed)


func finished(tick: int) -> bool:
	return tick >= length


func entry_count() -> int:
	return _entries.size()
