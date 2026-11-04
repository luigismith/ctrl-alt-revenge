class_name UiFont
extends RefCounted
## Testo pixel dell'interfaccia. Usa i font di game/assets/fonts/ (CAR Pixel, vedi il README lì);
## se mancano, un font bitmap 5×7 disegnato qui, solo maiuscole, con le lettere accentate
## italiane (À È É Ì Ò Ù) e le stesse misure di riga. Tutto il testo passa da draw_text().

const GLYPH_W := 5
const GLYPH_H := 9
const ADVANCE := 6
const LINE_H := 12
## Righe 0-1 per gli accenti, 2-8 per la lettera.
const GLYPHS := {
	"A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
	"B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
	"C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
	"D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
	"E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
	"F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
	"G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"],
	"H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
	"I": [".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."],
	"J": ["..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."],
	"K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
	"L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
	"M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
	"N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
	"O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
	"P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
	"Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
	"R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
	"S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
	"T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
	"U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
	"V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
	"W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."],
	"X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
	"Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
	"Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],
	"0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
	"1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
	"2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
	"3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
	"4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
	"5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
	"6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
	"7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
	"8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
	"9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],
	".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
	",": [".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."],
	":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
	";": [".....", ".##..", ".##..", ".....", ".##..", "..#..", ".#..."],
	"!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
	"?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
	"'": ["..#..", "..#..", ".#...", ".....", ".....", ".....", "....."],
	"\"": [".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."],
	"-": [".....", ".....", ".....", ".###.", ".....", ".....", "....."],
	"+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
	"/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
	"(": ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."],
	")": [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."],
	"[": [".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."],
	"]": [".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."],
	"%": ["##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"],
	"&": [".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"],
	"*": [".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."],
	"#": [".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."],
	"=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
	"<": ["...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."],
	">": [".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."],
	"_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
	"·": [".....", ".....", ".....", "..#..", ".....", ".....", "....."],
	"▶": ["#....", "##...", "###..", "####.", "###..", "##...", "#...."],
	"×": [".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "....."],
	"@": [".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."],
	"$": ["..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."],
	" ": [".....", ".....", ".....", ".....", ".....", ".....", "....."],
}
const ACCENTS := {"À": ["A", "grave"], "È": ["E", "grave"], "É": ["E", "acute"], "Ì": ["I", "grave"],
	"Ò": ["O", "grave"], "Ù": ["U", "grave"], "Ó": ["O", "acute"], "Ú": ["U", "acute"], "Í": ["I", "acute"]}

## Ombra di 1 px dei testi dell'interfaccia (colore "shadow" di ui.json).
const SHADOW := Color8(11, 8, 22)

static var _atlas: ImageTexture
static var _index: Dictionary = {}
static var _bold: Font
static var _regular: Font
static var _font_size: int = 12
static var _font_checked: bool = false


static func _build() -> void:
	if _atlas != null:
		return
	var chars: Array[String] = []
	for k: String in GLYPHS:
		chars.append(k)
	for k: String in ACCENTS:
		chars.append(k)
	var img := Image.create_empty(ADVANCE * chars.size(), GLYPH_H, false, Image.FORMAT_RGBA8)
	for i in chars.size():
		var ch := chars[i]
		var base: String = ch
		var accent := ""
		if ACCENTS.has(ch):
			base = ACCENTS[ch][0]
			accent = ACCENTS[ch][1]
		var rows: Array = GLYPHS[base]
		for y in 7:
			var row: String = rows[y]
			for x in GLYPH_W:
				if row[x] == "#":
					img.set_pixel(i * ADVANCE + x, y + 2, Color.WHITE)
		if accent == "grave":
			img.set_pixel(i * ADVANCE + 1, 0, Color.WHITE)
			img.set_pixel(i * ADVANCE + 2, 1, Color.WHITE)
		elif accent == "acute":
			img.set_pixel(i * ADVANCE + 3, 0, Color.WHITE)
			img.set_pixel(i * ADVANCE + 2, 1, Color.WHITE)
		_index[ch] = i
	_atlas = ImageTexture.create_from_image(img)


## Font forniti dalla grafica (game/assets/fonts/font.json): grassetto per nomi, punteggio e
## menu, regolare per i testi lunghi. Dimensione esatta 12 (un pixel del font = un pixel del
## gioco), multipli per le scritte grandi.
static func _find_font() -> void:
	if _font_checked:
		return
	_font_checked = true
	var dir := "res://assets/fonts"
	var cfg_path := dir.path_join("font.json")
	if not FileAccess.file_exists(cfg_path):
		return
	var cfg: Variant = JSON.parse_string(FileAccess.get_file_as_string(cfg_path))
	if not (cfg is Dictionary):
		return
	_font_size = int(cfg.get("size", 12))
	var fonts: Dictionary = cfg.get("fonts", {}) if cfg.get("fonts") is Dictionary else {}
	var bold_file := str(cfg.get("file", ""))
	if fonts.has("bold"):
		bold_file = str(fonts["bold"].get("file", bold_file))
	_bold = _load_font(dir.path_join(bold_file)) if bold_file != "" else null
	if fonts.has("regular"):
		_regular = _load_font(dir.path_join(str(fonts["regular"].get("file", ""))))
	if _regular == null:
		_regular = _bold


static func _load_font(path: String) -> Font:
	if not ResourceLoader.exists(path):
		return null
	var f := ResourceLoader.load(path) as Font
	if f is FontFile:
		var ff := f as FontFile
		ff.antialiasing = TextServer.FONT_ANTIALIASING_NONE
		ff.hinting = TextServer.HINTING_NONE
		ff.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
	return f


## Il font esterno, se in uso (null = font bitmap interno).
static func external_font(regular: bool = false) -> Font:
	_find_font()
	return _regular if regular else _bold


## Sostituti dei caratteri tipografici che i font possono non avere.
const SUBSTITUTES := {"→": "->", "←": "<-", "–": "-", "—": "-", "…": "...", "“": "\"", "”": "\"",
	"„": "\"", "‘": "'", "’": "'", "≥": ">=", "≤": "<=", "\t": " "}


## `text` con i soli caratteri che il font sa disegnare: gli altri diventano il loro sostituto
## (la freccia "→" diventa "->") oppure "?". Senza, Godot disegna un riquadro col codice
## esadecimale (per esempio "2192"). Da usare per i testi che non scriviamo noi (licenze).
static func safe_text(text: String, regular: bool = false) -> String:
	var f := external_font(regular)
	var out := ""
	for ch in text:
		if _has_glyph(f, ch):
			out += ch
			continue
		var sub: String = SUBSTITUTES.get(ch, "?")
		for c in sub:
			out += c if _has_glyph(f, c) else "?"
	return out


static func _has_glyph(f: Font, ch: String) -> bool:
	if ch == " ":
		return true
	if f != null:
		return f.has_char(ch.unicode_at(0))
	_build()
	return _index.has(ch.to_upper())


static func text_width(text: String, scale: int = 1, regular: bool = false) -> int:
	var f := external_font(regular)
	if f != null:
		return int(f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, _font_size * scale).x)
	return maxi(0, text.length() * ADVANCE - 1) * scale


## Altezza di una riga: 12 px (ascendente 10, discendente 2), come il font della grafica.
static func line_height(scale: int = 1) -> int:
	return LINE_H * scale


## Disegna `text` con la riga che parte in `pos` (le maiuscole occupano le righe 3-9).
## align: 0 sinistra, 1 centro, 2 destra. `shadow`: ombra di 1 px (in scala) in basso a destra;
## `outline`: bordo pixel di 1 px; `regular`: font regolare per i testi lunghi.
static func draw_text(ci: CanvasItem, pos: Vector2, text: String, color: Color, scale: int = 1, align: int = 0,
		outline: Color = Color(0, 0, 0, 0), shadow: Color = SHADOW, regular: bool = false) -> void:
	var w := text_width(text, scale, regular)
	var p := Vector2(roundf(pos.x - (floorf(w / 2.0) if align == 1 else (w if align == 2 else 0.0))), roundf(pos.y))
	if outline.a > 0.0:
		for o: Vector2 in [Vector2(-1, 0), Vector2(1, 0), Vector2(0, -1), Vector2(0, 1), Vector2(-1, -1), Vector2(1, -1), Vector2(-1, 1), Vector2(1, 1)]:
			_draw_raw(ci, p + o * scale, text, outline, scale, regular)
	if shadow.a > 0.0:
		_draw_raw(ci, p + Vector2(scale, scale), text, shadow, scale, regular)
	_draw_raw(ci, p, text, color, scale, regular)


static func _draw_raw(ci: CanvasItem, p: Vector2, text: String, color: Color, scale: int, regular: bool) -> void:
	var f := external_font(regular)
	if f != null:
		ci.draw_string(f, p + Vector2(0, 10 * scale), text, HORIZONTAL_ALIGNMENT_LEFT, -1, _font_size * scale, color)
		return
	_build()
	var x := p.x
	for ch in text.to_upper():
		var key := ch
		if not _index.has(key):
			key = " " if ch == char(9) else "?"
		var i: int = _index[key]
		if key != " ":
			ci.draw_texture_rect_region(_atlas, Rect2(x, p.y + scale, GLYPH_W * scale, GLYPH_H * scale), Rect2(i * ADVANCE, 0, GLYPH_W, GLYPH_H), color)
		x += ADVANCE * scale


## Cornice di 1 px con rettangoli pieni (draw_rect non pieno sbava di mezzo pixel).
static func draw_frame(ci: CanvasItem, r: Rect2, color: Color) -> void:
	ci.draw_rect(Rect2(r.position.x, r.position.y, r.size.x, 1), color)
	ci.draw_rect(Rect2(r.position.x, r.end.y - 1, r.size.x, 1), color)
	ci.draw_rect(Rect2(r.position.x, r.position.y, 1, r.size.y), color)
	ci.draw_rect(Rect2(r.end.x - 1, r.position.y, 1, r.size.y), color)
