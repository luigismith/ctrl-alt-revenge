class_name CreditsScreen
extends Control
## Crediti e licenze: chi ha fatto cosa, la licenza di Godot (Engine.get_license_text()),
## THIRD-PARTY-NOTICES.md e i componenti di terze parti del motore con le loro licenze
## (Engine.get_copyright_info() e get_license_info()). Scorre da solo; su e giù per scorrere,
## ATTACCO o ESC per uscire. Nel browser la sezione MUSICA dice che la demo web è muta.

signal done

const CREAM := Color8(247, 232, 189)
const YELLOW := Color8(255, 226, 122)
const MAX_CHARS := 58
## Testo dei crediti, modificabile senza toccare il codice: una riga per voce,
## le righe che iniziano con "# " sono titoli.
const CREDITS_TXT := "res://data/credits.txt"
## In fondo alla sezione MUSICA di credits.txt vanno i brani che Music ha davvero caricato (titolo e
## licenza da music.json): così i crediti sono giusti nella demo web, nelle build e con la musica
## segnaposto di un laboratorio. Senza musica, questa riga.
const NO_MUSIC := "In questa copia del gioco non c'è musica."

var _lines: Array[Array] = []  # [testo, colore, regolare, immagine o null]
var _scroll: float = -200.0
var _t: int = 0


func _ready() -> void:
	size = Vector2(384, 216)
	_build()
	# Il tema del titolo: dal titolo continua senza ripartire, dopo la fine della demo riparte
	# (prima i crediti erano muti, dopo il jingle di ZONA LIBERATA).
	Music.duck(false)
	Music.play(&"title")


## Titoli in grassetto giallo, testo normale nel font regolare; tutto a 1x (niente pixel 2x2
## accanto ai pixel 1x). I caratteri che il font non ha diventano un sostituto leggibile.
func _add(text: String, color: Color = CREAM) -> void:
	var regular := color == CREAM
	for l in word_wrap(UiFont.safe_text(text, regular), MAX_CHARS):
		_lines.append([l, color, regular, null])


## Un'immagine dell'interfaccia centrata (il logo), con `text` di riserva se manca.
func _add_image(key: String, text: String) -> void:
	var tex := UiArt.texture(key)
	if tex == null:
		_add(text, YELLOW)
		return
	_lines.append(["", YELLOW, false, tex])


func _build() -> void:
	_add_image("logo", "CTRL+ALT REVENGE!")
	_add("")
	if FileAccess.file_exists(CREDITS_TXT):
		var music := false
		for l in FileAccess.get_file_as_string(CREDITS_TXT).split("\n"):
			if l.begins_with("# "):
				if music:
					_add_music()
				music = l.substr(2).strip_edges() == "MUSICA"
				_add(l.substr(2), YELLOW)
			else:
				_add(l)
		if music:
			_add_music()
	_add("")
	_add("LICENZE", YELLOW)
	_add("")
	_add("Godot Engine", YELLOW)
	for l in Engine.get_license_text().split("\n"):
		_add(l)
	_add("")
	_add("Materiale di terze parti", YELLOW)
	var notices := _read_notices()
	if notices == "":
		_add("Vedi il file THIRD-PARTY-NOTICES.md distribuito con il gioco.")
	else:
		for l in notices.split("\n"):
			_add(_clean_markdown(l))
	_add("")
	_add_engine_components()
	_add("")
	_add("Grazie per aver giocato!", YELLOW)


## Componenti di terze parti compilati dentro Godot, con copyright e testo delle licenze,
## come chiede la loro licenza: li fornisce l'eseguibile stesso.
func _add_music() -> void:
	var tracks := Music.credit_lines()
	if tracks.is_empty():
		_add(NO_MUSIC)
	else:
		_add("In questa copia del gioco:")
		for t in tracks:
			_add(t)
	_add("")


func _add_engine_components() -> void:
	_add("Componenti di terze parti inclusi in Godot Engine", YELLOW)
	for info: Dictionary in Engine.get_copyright_info():
		_add("")
		_add(str(info.get("name", "")), YELLOW)
		for part: Dictionary in info.get("parts", []):
			for c: String in part.get("copyright", PackedStringArray()):
				_add("© " + c)
			_add("Licenza: " + str(part.get("license", "")))
	var texts: Dictionary = Engine.get_license_info()
	var names: Array = texts.keys()
	names.sort()
	for n: Variant in names:
		_add("")
		_add("Licenza " + str(n), YELLOW)
		for l in str(texts[n]).split("\n"):
			_add(l)


static func _read_notices() -> String:
	if FileAccess.file_exists("res://THIRD-PARTY-NOTICES.md"):
		return FileAccess.get_file_as_string("res://THIRD-PARTY-NOTICES.md")
	if not OS.has_feature("template"):
		# Durante lo sviluppo il file è nella radice del repository, accanto a game/.
		var repo := ProjectSettings.globalize_path("res://").path_join("../THIRD-PARTY-NOTICES.md").simplify_path()
		if FileAccess.file_exists(repo):
			return FileAccess.get_file_as_string(repo)
	return ""


## Toglie la sintassi Markdown più comune (titoli, grassetto, codice, link).
static func _clean_markdown(l: String) -> String:
	var s := l.strip_edges(false, true)
	while s.begins_with("#"):
		s = s.substr(1)
	s = s.replace("**", "").replace("`", "")
	var re := RegEx.create_from_string("\\[([^\\]]+)\\]\\(([^)]+)\\)")
	s = re.sub(s, "$1 ($2)", true)
	if s.strip_edges().begins_with("- "):
		s = "· " + s.strip_edges().substr(2)
	return s.strip_edges(true, false) if not s.begins_with("  ") else s


## A capo sulle parole, al massimo `n` caratteri per riga.
static func word_wrap(text: String, n: int) -> PackedStringArray:
	var out := PackedStringArray()
	if text.strip_edges() == "":
		out.append("")
		return out
	var line := ""
	for word in text.split(" ", false):
		var w := word
		while w.length() > n:
			if line != "":
				out.append(line)
				line = ""
			out.append(w.substr(0, n))
			w = w.substr(n)
		if line == "":
			line = w
		elif line.length() + 1 + w.length() <= n:
			line += " " + w
		else:
			out.append(line)
			line = w
	if line != "":
		out.append(line)
	return out


func _physics_process(_delta: float) -> void:
	_t += 1
	var speed := 0.4
	if Input.is_action_pressed(&"move_down"):
		speed = 3.0
	elif Input.is_action_pressed(&"move_up"):
		speed = -3.0
	_scroll = clampf(_scroll + speed, -216.0, _content_height())
	queue_redraw()
	if _t > 20 and (Input.is_action_just_pressed(&"menu_back") or Input.is_action_just_pressed(&"attack") or Input.is_action_just_pressed(&"menu_confirm")):
		Sfx.play(&"ui_confirm")
		set_physics_process(false)
		done.emit()


func _content_height() -> float:
	var h := 0.0
	for l in _lines:
		h += _line_h(l)
	return h


static func _line_h(l: Array) -> int:
	var tex: Texture2D = l[3]
	return tex.get_height() + 6 if tex != null else UiFont.line_height() + 1


func _draw() -> void:
	draw_rect(Rect2(0, 0, 384, 216), Color8(12, 8, 26))
	var y := -roundf(_scroll)
	for l in _lines:
		var lh := _line_h(l)
		if y > -lh and y < 216:
			var tex: Texture2D = l[3]
			if tex != null:
				draw_texture(tex, Vector2(roundf(192 - tex.get_width() / 2.0), y + 2))
			else:
				UiFont.draw_text(self, Vector2(14, y), str(l[0]), l[1], 1, 0, Color(0, 0, 0, 0), UiFont.SHADOW, bool(l[2]))
		y += lh
	draw_rect(Rect2(0, 0, 384, 10), Color8(12, 8, 26))
	draw_rect(Rect2(0, 206, 384, 10), Color8(12, 8, 26))
