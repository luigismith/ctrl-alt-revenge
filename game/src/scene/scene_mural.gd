class_name SceneMural
extends Node2D
## Un murale di Totò dentro una scena (decisione 68: i murales animati per l'introduzione, i ricordi e i
## passaggi fra i capitoli). Lo apre il passo «murale» del lettore delle scene.
##
## I file li prepara car-grafica con tools/murales/ in res://assets/murales/<capitolo>/<id>/:
## - murale.png: la vignetta, opaca (512x288 di solito, fino a 960x288 per le panoramiche);
## - murale_emis.png: le luci da sommare, che pulsano;
## - murale_rivela.png: l'ordine dello spray in grigio, 0 compare subito e 255 per ultimo;
## - murale.json: "scorri" {"da", "a"} (l'angolo in alto a sinistra del riquadro dello schermo), oppure
##   "camera" {"zoom_da", "centro_da", "zoom_a", "centro_a"}; le "figure" {"file", "x", "y",
##   "profondita", "nome", "blink", "talk"} sono strati davanti alla vignetta, con la parallasse (con
##   "blink" e "talk" il volto batte le palpebre e muove la bocca quando l'attore "nome" parla);
##   "riusa" {"murale", "logo"} prende immagini e figure da un altro murale (MP08 riusa MP06) e il logo
##   da spruzzare a "logo".pos;
##   "scritte" [{"nome", "file"}] sono scritte sopra la vignetta, grandi come lei; "passaggio"
##   {"centro", "camera"} dice da dove si scioglie nel gioco e dove sta allora la telecamera del gioco.
##
## Le scritte (il passo «scritta» del lettore) compaiono riga per riga e lettera per lettera: a spray,
## con qualche colatura, oppure nette come un registro. Vengono dalle "scritte" di murale.json, dal logo
## di "riusa", o dalle "scritte" {"id", "zona"} del passo «murale»: la scritta già dipinta nella
## vignetta (la data di MP05, il titolo di MP13) si stacca dal fondo, il buco si riempie col fondo di
## sopra e di sotto, e si spruzza quando il copione lo chiede.
##
## La rivelazione è il passaggio morbido fra gioco e murale: i pixel compaiono nell'ordine dello spray,
## col bordo a puntini come una bomboletta, e sotto quelli che mancano si vede ancora il gioco. Chiudendo
## si torna indietro: l'ultimo pixel dipinto è il primo che sparisce. Sciogliendo (MP08 nel prologo) se
## ne va invece dal centro del "passaggio" verso i bordi, a puntini e scurendosi, senza vernice fresca:
## sotto c'è il gioco che combacia. È solo disegno: la simulazione è ferma come nel resto della scena.
##
## L'aggancio (hook, il passo con "aggancio": l'attore) lega il murale a una sua figura che è anche nel
## gioco: aprendo, la figura compare per prima sopra lo sprite, nell'inquadratura dove combacia con lui
## (la calcola il lettore), e lo spray si allarga da lei; sciogliendo, il murale se ne va dai bordi verso
## la figura, che sfuma per ultima nello sprite.

const DIR_DEFAULT := "res://assets/murales"
## La cartella dei murales; il test la cambia per un murale finto in user://.
static var dir: String = DIR_DEFAULT

## La larghezza del bordo a puntini, nell'ordine dello spray (0-1).
const EDGE := 0.14
## La rivelazione e la chiusura, in tick, se il passo non le dice.
const REVEAL_TICKS := 60
## Lo scorrimento, in tick, se il passo non lo dice.
const SCROLL_TICKS := 300
## Le luci: periodo del respiro, in tick, e quanto scendono al minimo.
const PULSE_TICKS := 96
const PULSE_DEPTH := 0.35
## Lo scioglimento, se il passo non lo dice, e il suo fronte (più largo: si sfa a puntini).
const MELT_TICKS := 90
const MELT_EDGE := 0.3
## Con l'aggancio: quanto conta la distanza dalla figura nell'ordine dello spray (il resto è l'ordine di
## murale_rivela.png); in quanti tick la figura agganciata compare sopra lo sprite, e in che parte della
## chiusura (o dello scioglimento) se ne va.
const HOOK_MIX := 0.6
const HOOK_FADE_TICKS := 16
const HOOK_FADE := 0.15
## Le scritte: tick per lettera, se il passo non dice "tick"; le colature: quante lettere ne hanno una
## (su 100), quanto lunghe al massimo e quanti tick per pixel.
const WRITE_TICKS_PER_GLYPH := 5
const DRIP_CHANCE := 40
const DRIP_MAX := 7
const DRIP_TICKS := 7
## Fin dove si stacca, intorno alla scritta, quello che non è muro (contorni, mezzi toni).
const LIFT_REACH := 3

const SHADER := """shader_type canvas_item;
render_mode unshaded;
uniform sampler2D reveal_tex : filter_nearest;
uniform sampler2D emis_tex : filter_nearest;
uniform bool has_reveal = true;
uniform bool has_emis = false;
uniform vec2 size = vec2(512.0, 288.0);
uniform float progress = 0.0;
uniform float edge = 0.14;
uniform float glow = 1.0;
uniform float seed = 0.0;
uniform bool melt = false;
uniform vec2 melt_center = vec2(256.0, 144.0);
uniform bool melt_inward = false;
uniform vec2 focus = vec2(0.0);
uniform float focus_mix = 0.0;
uniform float fresh = 0.18;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(12.9898, 78.233)) + seed) * 43758.5453);
}

void fragment() {
	vec2 px = floor(UV * size);
	float r = has_reveal ? texture(reveal_tex, UV).r : hash(px * 0.37 + 5.0);
	if (focus_mix > 0.0) {
		// con l'aggancio lo spray si allarga dalla figura
		float ff = length(max(focus, size - focus));
		r = mix(r, length(px - focus) / ff, focus_mix);
	}
	if (melt) {
		// sciogliendo: prima il centro, per ultimi i bordi (o, verso la figura, il contrario), col fronte
		// frastagliato
		float far = length(max(melt_center, size - melt_center));
		float d = length(px - melt_center) / far;
		r = 0.82 * (melt_inward ? d : 1.0 - d) + 0.18 * hash(px * 0.53 + 11.0);
	}
	// davanti al fronte dello spray il pixel c'è a caso, tanto più quanto è vicino
	float k = (progress - r) / edge;
	if (k < 1.0 && hash(px) >= k) {
		discard;
	}
	vec4 c = texture(TEXTURE, UV);
	if (melt) {
		// il colore che si scioglie si scurisce sul fronte
		c.rgb *= 1.0 - clamp(1.0 - k, 0.0, 1.0) * 0.45;
	} else {
		// la vernice fresca, appena più chiara sul fronte
		c.rgb = mix(c.rgb, vec3(1.0), clamp(1.0 - k, 0.0, 1.0) * fresh);
	}
	if (has_emis) {
		vec4 e = texture(emis_tex, UV);
		c.rgb += e.rgb * e.a * glow;
	}
	COLOR = c;
}
"""

static var _shader: Shader

var mural_id: String = ""
var chapter: String = ""
var size: Vector2 = Vector2(512, 288)
var info: Dictionary = {}
var errors: PackedStringArray = []

## L'inquadratura, in pixel del murale: centro e zoom, da (0) ad (1).
var c0: Vector2 = Vector2.ZERO
var c1: Vector2 = Vector2.ZERO
var z0: float = 1.0
var z1: float = 1.0
var scroll_n: int = SCROLL_TICKS
var scroll_k: int = 0
## La rivelazione: k va da 0 a n aprendo, e da n a 0 chiudendo.
var reveal_n: int = REVEAL_TICKS
var reveal_k: int = 0
var closing: bool = false
var melting: bool = false
var pulse: bool = true
var t: int = 0

## Le scritte: id → {"node", "sprite", "mat", "pos" (nel murale), "size", "glyphs", "mode", "n", "k",
## "t" (tick da quando è cominciata), "on", "edge", "drips" [{"x", "y", "color", "len", "glyph"}]}.
var writings: Dictionary = {}

var _sprite: Sprite2D
var _mat: ShaderMaterial
var _figures: Array = []   # [{"sprite", "pos" (nel murale), "depth", "name", "tex", "blink", "talk"}]
## La figura agganciata (il suo nome), o "".
var hooked: String = ""
## Chi parla adesso (nome → bocca aperta): lo dà il lettore, per le figure con la variante "talk".
var mouth: Callable


## La cartella di un murale.
static func path_of(chapter_id: String, id: String) -> String:
	return dir.path_join(chapter_id).path_join(id)


## Il capitolo e l'id dal passo: "id" come "<capitolo>/<id>", oppure "id" con "capitolo".
static func split_id(st: Dictionary) -> PackedStringArray:
	var id := str(st.get("id", ""))
	var ch := str(st.get("capitolo", ""))
	if ch == "" and id.contains("/"):
		ch = id.get_slice("/", 0)
		id = id.get_slice("/", 1)
	return PackedStringArray([ch, id])


## C'è il murale del passo? (lo usa il test dei copioni)
static func exists(st: Dictionary) -> bool:
	var ci := split_id(st)
	if ci[0] == "" or ci[1] == "":
		return false
	var own := path_of(ci[0], ci[1])
	var jp := own.path_join("murale.json")
	if not FileAccess.file_exists(jp):
		return false
	return _file_exists(_images_dir(own, _read_json(jp)).path_join("murale.png"))


## La cartella delle immagini: quella del murale, o quella che "riusa".
static func _images_dir(own: String, d: Dictionary) -> String:
	var r: Variant = d.get("riusa", {})
	if r is Dictionary and str((r as Dictionary).get("murale", "")) != "":
		return str(r["murale"]).trim_suffix("/")
	return own


static func _read_json(p: String) -> Dictionary:
	var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(p)) if FileAccess.file_exists(p) else null
	return d if d is Dictionary else {}


## Gli id delle scritte che il murale del passo `st` sa dipingere (per i controlli dei copioni).
static func writing_ids(st: Dictionary) -> PackedStringArray:
	var out := PackedStringArray()
	var ci := split_id(st)
	var d := _read_json(path_of(ci[0], ci[1]).path_join("murale.json"))
	for w: Variant in d.get("scritte", []):
		if w is Dictionary:
			out.append(str(w.get("nome", "")))
	var r: Variant = d.get("riusa", {})
	if r is Dictionary and str((r as Dictionary).get("logo", "")) != "":
		out.append("logo")
	for z: Variant in st.get("scritte", []):
		if z is Dictionary:
			out.append(str(z.get("id", "")))
	return out


## Prepara il murale del passo `st`; se qualcosa manca, `errors` non è vuoto e il murale non si vede.
func setup(st: Dictionary) -> void:
	var ci := split_id(st)
	chapter = ci[0]
	mural_id = ci[1]
	name = "Murale_" + mural_id
	var own := path_of(chapter, mural_id)
	var jp := own.path_join("murale.json")
	info = _read_json(jp)
	if info.is_empty():
		errors.append("murale.json mancante o non valido: %s" % jp)
	var base := _images_dir(own, info)
	var tex := _texture(base.path_join("murale.png"))
	if tex == null:
		errors.append("murale mancante: %s" % base)
		return
	size = Vector2(tex.get_width(), tex.get_height())
	# Le figure: quelle del murale, o quelle del murale che riusa.
	var figures: Variant = info.get("figure", null)
	if figures == null and base != own:
		figures = _read_json(base.path_join("murale.json")).get("figure", [])
	# Le scritte già dipinte nelle zone del passo si staccano dalla vignetta.
	var zones: Array = st.get("scritte", []) if st.get("scritte", []) is Array else []
	var lifted: Array = []
	if not zones.is_empty():
		var img := _rgba(tex.get_image())
		if img != null:
			for z: Variant in zones:
				if z is Dictionary and (z as Dictionary).has("zona"):
					lifted.append(_lift_writing(img, str(z.get("id", "")), _rect(z["zona"])))
			tex = ImageTexture.create_from_image(img)
	_frame_from(st)
	reveal_n = maxi(1, int(st.get("rivela_tick", REVEAL_TICKS)))
	reveal_k = reveal_n if not bool(st.get("rivela", true)) else 0
	pulse = bool(st.get("luci", true))

	_mat = ShaderMaterial.new()
	_mat.shader = _shader_get()
	var rv := _texture(base.path_join("murale_rivela.png"))
	var em := _texture(base.path_join("murale_emis.png"))
	_mat.set_shader_parameter(&"has_reveal", rv != null)
	if rv != null:
		_mat.set_shader_parameter(&"reveal_tex", rv)
	_mat.set_shader_parameter(&"has_emis", em != null)
	if em != null:
		_mat.set_shader_parameter(&"emis_tex", em)
	_mat.set_shader_parameter(&"size", size)
	_mat.set_shader_parameter(&"edge", EDGE)
	_mat.set_shader_parameter(&"seed", float(hash(mural_id) % 997))
	_sprite = Sprite2D.new()
	_sprite.texture = tex
	_sprite.centered = false
	_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_sprite.material = _mat
	add_child(_sprite)
	for f: Variant in (figures if figures is Array else []):
		if not (f is Dictionary):
			continue
		var ft := _texture(base.path_join(str((f as Dictionary).get("file", ""))))
		if ft == null:
			errors.append("figura mancante: %s" % str((f as Dictionary).get("file", "")))
			continue
		var s := Sprite2D.new()
		s.texture = ft
		s.centered = false
		s.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		add_child(s)
		# Il volto (MP12): palpebre chiuse ("blink") e bocca aperta ("talk"), grandi come la figura.
		var face := {}
		for k: String in ["blink", "talk"]:
			face[k] = null
			if str((f as Dictionary).get(k, "")) != "":
				face[k] = _texture(base.path_join(str(f[k])))
				if face[k] == null:
					errors.append("figura mancante: %s" % str(f[k]))
		_figures.append({"sprite": s, "pos": Vector2(float(f.get("x", 0)), float(f.get("y", 0))),
			"depth": float(f.get("profondita", 1.0)), "name": str(f.get("nome", "")), "tex": ft,
			"blink": face["blink"], "talk": face["talk"]})
	# Le scritte, sopra figure e vignetta: quelle staccate, quelle di murale.json (immagini grandi come la
	# vignetta) e il logo di "riusa".
	for l: Variant in lifted:
		if l is Array:
			_add_writing(l[0], l[1], l[2], "spray", l[3])
	for w: Variant in info.get("scritte", []):
		if not (w is Dictionary):
			continue
		var wt := _texture(base.path_join(str((w as Dictionary).get("file", ""))))
		if wt == null:
			errors.append("scritta mancante: %s" % str(w.get("file", "")))
			continue
		var wi := _rgba(wt.get_image())
		var used := wi.get_used_rect()
		if used.size.x > 0 and used.size.y > 0:
			_add_writing(str(w.get("nome", "")), wi.get_region(used), Vector2(used.position), "scrivi")
	var riusa: Dictionary = info.get("riusa", {}) if info.get("riusa", {}) is Dictionary else {}
	var logo_p := str(riusa.get("logo", ""))
	if logo_p != "":
		var lt := _texture(logo_p)
		if lt == null:
			errors.append("logo mancante: %s" % logo_p)
		else:
			var lp: Dictionary = info.get("logo", {}) if info.get("logo", {}) is Dictionary else {}
			_add_writing("logo", _rgba(lt.get_image()), _vec(lp.get("pos", null), Vector2.ZERO), "spray")
	_apply()


## L'inquadratura: "da"/"a" del passo (angoli del riquadro, come "scorri"), se no la "camera" del
## murale.json se ha gli zoom, se no il suo "scorri"; senza niente, il murale fermo al centro.
func _frame_from(st: Dictionary) -> void:
	var half := View.SIZE / 2.0
	var mid := size / 2.0
	var cam: Dictionary = info.get("camera", {}) if info.get("camera", {}) is Dictionary else {}
	var sc: Dictionary = info.get("scorri", {}) if info.get("scorri", {}) is Dictionary else {}
	c0 = mid
	c1 = mid
	z0 = 1.0
	z1 = 1.0
	if st.has("centro") or st.has("zoom"):
		c0 = _vec(st.get("centro", null), mid)
		c1 = c0
		z0 = maxf(0.25, float(st.get("zoom", 1.0)))
		z1 = z0
	elif st.has("da") or st.has("a"):
		c0 = _vec(st.get("da", st.get("a")), mid - half) + half
		c1 = _vec(st.get("a", st.get("da")), mid - half) + half
	elif cam.has("centro_da") or cam.has("zoom_da"):
		c0 = _vec(cam.get("centro_da", null), mid)
		c1 = _vec(cam.get("centro_a", cam.get("centro_da", null)), c0)
		z0 = maxf(0.25, float(cam.get("zoom_da", 1.0)))
		z1 = maxf(0.25, float(cam.get("zoom_a", z0)))
	elif not sc.is_empty():
		c0 = _vec(sc.get("da", null), mid - half) + half
		c1 = _vec(sc.get("a", sc.get("da", null)), c0 - half) + half
	scroll_n = maxi(1, int(st.get("tick", SCROLL_TICKS)))
	scroll_k = 0


## Un tick: scorrimento, rivelazione (o chiusura), scritte e respiro delle luci.
func tick() -> void:
	t += 1
	scroll_k = mini(scroll_k + 1, scroll_n)
	if closing:
		reveal_k = maxi(reveal_k - 1, 0)
	else:
		reveal_k = mini(reveal_k + 1, reveal_n)
	for w: Dictionary in writings.values():
		if bool(w["on"]):
			w["t"] = int(w["t"]) + 1
			w["k"] = mini(int(w["k"]) + 1, int(w["n"]))
	_apply()


## Comincia a chiudersi: lo spray all'indietro in `n` tick (predefinito: quanto la rivelazione).
func close(n: int = -1) -> void:
	if closing:
		return
	if n > 0:
		# stessa frazione di adesso, sulla durata nuova
		reveal_k = roundi(float(reveal_k) / reveal_n * n)
		reveal_n = n
	closing = true


## Si scioglie nel gioco in `n` tick: dal centro del "passaggio" (o dell'inquadratura) verso i bordi;
## con la figura agganciata, dai bordi verso di lei.
func melt(n: int = MELT_TICKS) -> void:
	if closing or _mat == null:
		return
	var ps: Dictionary = info.get("passaggio", {}) if info.get("passaggio", {}) is Dictionary else {}
	_mat.set_shader_parameter(&"melt", true)
	var fr := figure_rect(hooked)
	_mat.set_shader_parameter(&"melt_inward", fr.has_area())
	_mat.set_shader_parameter(&"focus_mix", 0.0)
	_mat.set_shader_parameter(&"melt_center", fr.get_center() if fr.has_area() else _vec(ps.get("centro", null), view()[0]))
	_mat.set_shader_parameter(&"edge", MELT_EDGE)
	melting = true
	close(n)


## Dove sta la telecamera del gioco quando il murale si scioglie ("passaggio".camera: l'angolo in alto
## a sinistra, nel mondo della stanza), o null.
func handoff_camera() -> Variant:
	var ps: Dictionary = info.get("passaggio", {}) if info.get("passaggio", {}) is Dictionary else {}
	var cam: Variant = ps.get("camera", null)
	if cam is Dictionary and (cam as Dictionary).has("x") and (cam as Dictionary).has("y"):
		return Vector2(float(cam["x"]), float(cam["y"]))
	return null


## Il riquadro del corpo della figura `who` (per "nome"), in pixel del murale; vuoto se non c'è.
func figure_rect(who: String) -> Rect2:
	if who == "":
		return Rect2()
	for f: Dictionary in _figures:
		if str(f["name"]) == who:
			if not f.has("used"):
				var img := (f["tex"] as Texture2D).get_image()
				f["used"] = body_box(img) if img != null else Rect2(Vector2.ZERO, (f["tex"] as Texture2D).get_size())
			var u: Rect2 = f["used"]
			return Rect2(Vector2(f["pos"]) + u.position, u.size)
	return Rect2()


## Il corpo di una figura: le righe e le colonne piene (almeno BODY_MIN pixel) più lunghe di fila, così
## gocce, scie e schizzi staccati (le gocce cyan sotto GIG in MP13) non contano per l'aggancio.
const BODY_MIN := 2
static func body_box(img: Image) -> Rect2:
	var w := img.get_width()
	var h := img.get_height()
	var rows := PackedInt32Array()
	rows.resize(h)
	var cols := PackedInt32Array()
	cols.resize(w)
	for y in h:
		for x in w:
			if img.get_pixel(x, y).a > 0.0:
				rows[y] += 1
				cols[x] += 1
	var ry := _longest_run(rows)
	var rx := _longest_run(cols)
	if ry.y <= 0 or rx.y <= 0:
		return Rect2(img.get_used_rect())
	return Rect2(rx.x, ry.x, rx.y, ry.y)


## La fila più lunga di valori >= BODY_MIN: (inizio, lunghezza).
static func _longest_run(v: PackedInt32Array) -> Vector2i:
	var best := Vector2i(0, 0)
	var start := -1
	for i in v.size() + 1:
		var full := i < v.size() and v[i] >= BODY_MIN
		if full and start < 0:
			start = i
		elif not full and start >= 0:
			if i - start > best.y:
				best = Vector2i(start, i - start)
			start = -1
	return best


## Aggancia la figura `who` (vedi in cima); falso se il murale non ce l'ha.
func hook(who: String) -> bool:
	var fr := figure_rect(who)
	if not fr.has_area() or _mat == null:
		return false
	hooked = who
	_mat.set_shader_parameter(&"focus", fr.get_center())
	_mat.set_shader_parameter(&"focus_mix", HOOK_MIX)
	_apply()
	return true


## L'inquadratura d'apertura (centro e zoom, in pixel del murale), al posto di quella del murale.json;
## lo scorrimento poi va da lì a quella d'arrivo.
func set_opening(c: Vector2, z: float) -> void:
	c0 = c
	z0 = z
	_apply()


## Quanto si vede la figura agganciata (0-1), o -1 se non c'è aggancio.
func hook_alpha() -> float:
	for f: Dictionary in _figures:
		if hooked != "" and str(f["name"]) == hooked:
			return (f["sprite"] as Sprite2D).modulate.a
	return -1.0


## Lo zoom più piccolo con cui il murale copre lo schermo.
func cover_zoom() -> float:
	return maxf(View.SIZE.x / size.x, View.SIZE.y / size.y)


## Il centro `c` spostato quanto basta perché a zoom `z` il murale copra lo schermo.
func clamp_center(c: Vector2, z: float) -> Vector2:
	var h := View.SIZE / (2.0 * z)
	return Vector2(clampf(c.x, h.x, maxf(h.x, size.x - h.x)), clampf(c.y, h.y, maxf(h.y, size.y - h.y)))


func has_writing(id: String) -> bool:
	return writings.has(id)


## Comincia la scritta `id`: in `n` tick (se no WRITE_TICKS_PER_GLYPH per lettera), "spray" con le
## colature o "scrivi" (lettera per lettera, nette, come un registro). Falso se non c'è.
func write(id: String, n: int = -1, mode: String = "") -> bool:
	if not writings.has(id):
		return false
	var w: Dictionary = writings[id]
	if mode in ["spray", "scrivi"] and mode != str(w["mode"]):
		w["mode"] = mode
		_writing_order(w)
	w["n"] = n if n > 0 else maxi(1, int(w["glyphs"]) * WRITE_TICKS_PER_GLYPH)
	w["k"] = 0
	w["t"] = 0
	w["on"] = true
	_apply()
	return true


func writing_done(id: String) -> bool:
	return not writings.has(id) or bool(writings[id]["on"]) and int(writings[id]["k"]) >= int(writings[id]["n"])


func is_revealed() -> bool:
	return not closing and reveal_k >= reveal_n


func is_closed() -> bool:
	return closing and reveal_k <= 0


func is_scrolled() -> bool:
	return scroll_k >= scroll_n


## Quanto si vede, da 0 a 1 (con la curva morbida della rivelazione).
func amount() -> float:
	return _ease(float(reveal_k) / reveal_n)


## Centro e zoom di adesso, in pixel del murale.
func view() -> Array:
	var k := _ease(float(scroll_k) / scroll_n)
	return [c0.lerp(c1, k), exp(lerpf(log(z0), log(z1), k))]


func _apply() -> void:
	if _sprite == null:
		return
	var v := view()
	var c: Vector2 = v[0]
	var z: float = v[1]
	var half := View.SIZE / 2.0
	_sprite.scale = Vector2(z, z)
	_sprite.position = (half - c * z).round()
	var a := amount()
	_mat.set_shader_parameter(&"progress", a * (1.0 + (MELT_EDGE if melting else EDGE)))
	var g := 1.0
	if pulse:
		g = 1.0 - PULSE_DEPTH * 0.5 * (1.0 - cos(TAU * t / PULSE_TICKS))
	_mat.set_shader_parameter(&"glow", g)
	# Le figure: la parallasse rispetto all'inquadratura iniziale, e compaiono a fine spray. Quella
	# agganciata compare per prima e, sciogliendo, se ne va per ultima; sciogliendo verso di lei, le altre
	# se ne vanno col fronte, dove stanno.
	var fa := clampf((a - 0.6) / 0.4, 0.0, 1.0)
	var fr := figure_rect(hooked)
	var fc := fr.get_center()
	var far := Vector2(maxf(fc.x, size.x - fc.x), maxf(fc.y, size.y - fc.y)).length()
	for f: Dictionary in _figures:
		var s: Sprite2D = f["sprite"]
		var depth: float = f["depth"]
		var p: Vector2 = f["pos"]
		s.scale = Vector2(z, z)
		s.position = (half + (p - c0) * z - (c - c0) * z * depth).round()
		s.modulate.a = fa
		if fr.has_area():
			if str(f["name"]) == hooked:
				s.modulate.a = clampf(a / HOOK_FADE if closing else float(reveal_k) / HOOK_FADE_TICKS, 0.0, 1.0)
			elif melting:
				var rf := 0.82 * (p + (f["tex"] as Texture2D).get_size() / 2.0).distance_to(fc) / far
				s.modulate.a = clampf((a * (1.0 + MELT_EDGE) - rf) / MELT_EDGE, 0.0, 1.0)
		s.texture = _figure_frame(f)
	# Le scritte: dipinte sul muro (si muovono con la vignetta), e se ne vanno con lei.
	for w: Dictionary in writings.values():
		var node: Node2D = w["node"]
		node.scale = Vector2(z, z)
		node.position = (half + (Vector2(w["pos"]) - c) * z).round()
		node.modulate.a = 1.0 if not closing else (fa if melting else a)
		var wk := 0.0 if not bool(w["on"]) else float(w["k"]) / float(w["n"])
		(w["mat"] as ShaderMaterial).set_shader_parameter(&"progress", wk * (1.0 + float(w["edge"])))
		node.queue_redraw()


## La texture della figura adesso: la bocca si muove quando parla, le palpebre battono ogni 150-230 tick
## per 7 tick (dal tick e dal nome, come i primi piani del lettore).
func _figure_frame(f: Dictionary) -> Texture2D:
	var who := str(f["name"])
	if f["talk"] != null and mouth.is_valid() and bool(mouth.call(who)):
		return f["talk"]
	var period := 150 + (who.hash() & 63) + 16
	if f["blink"] != null and (t + (who.hash() & 31)) % period < 7:
		return f["blink"]
	return f["tex"]


# ------------------------------------------------------------------ scritte

## Stacca dalla vignetta la scritta chiara dentro `zone` (in pixel del murale): i pixel più chiari del
## fondo della zona, più quelli intorno coi mezzi toni, diventano la scritta; nella vignetta il buco si
## riempie colonna per colonna sfumando dal fondo di sopra a quello di sotto. Ritorna gli argomenti di
## _add_writing, o null.
func _lift_writing(img: Image, id: String, zone: Rect2i) -> Variant:
	zone = zone.intersection(Rect2i(Vector2i.ZERO, img.get_size()))
	if id == "" or zone.size.x <= 0 or zone.size.y <= 0:
		errors.append("scritta senza id o fuori dal murale: %s" % id)
		return null
	var w := zone.size.x
	var h := zone.size.y
	var orig := img.get_region(zone)
	# Il fondo: la luminosità mediana della zona (la scritta è poca rispetto al fondo).
	var lums: Array[float] = []
	for y in h:
		for x in w:
			lums.append(orig.get_pixel(x, y).get_luminance())
	lums.sort()
	var bg := lums[lums.size() / 2]
	var core := PackedByteArray()
	core.resize(w * h)
	for y in h:
		for x in w:
			core[y * w + x] = 1 if orig.get_pixel(x, y).get_luminance() > bg + 0.3 else 0
	# La maschera: la scritta, più il contorno e i mezzi toni intorno (anche dentro le lettere): fino a
	# LIFT_REACH px dalla scritta, i pixel diversi dal colore più frequente della zona (il muro).
	var counts := {}
	for y in h:
		for x in w:
			var key := orig.get_pixel(x, y).to_rgba32()
			counts[key] = int(counts.get(key, 0)) + 1
	var wall := 0
	for key: int in counts:
		if wall == 0 or int(counts[key]) > int(counts[wall]):
			wall = key
	var wall_c := Color.hex(wall)
	var mask := core.duplicate()
	var front: Array[Vector2i] = []
	for y in h:
		for x in w:
			if core[y * w + x] == 1:
				front.append(Vector2i(x, y))
	for step in LIFT_REACH:
		var next: Array[Vector2i] = []
		for p in front:
			for d: Vector2i in [Vector2i(-1, 0), Vector2i(1, 0), Vector2i(0, -1), Vector2i(0, 1)]:
				var q := p + d
				if q.x < 0 or q.y < 0 or q.x >= w or q.y >= h or mask[q.y * w + q.x] == 1:
					continue
				# il primo pixel intorno va sempre; poi solo quelli che non sono muro
				if step > 0 and _near_color(orig.get_pixel(q.x, q.y), wall_c):
					continue
				mask[q.y * w + q.x] = 1
				next.append(q)
		front = next
	var over := Image.create_empty(w, h, false, Image.FORMAT_RGBA8)
	for y in h:
		for x in w:
			if mask[y * w + x] == 1:
				over.set_pixel(x, y, orig.get_pixel(x, y))
	for x in w:
		var y := 0
		while y < h:
			if mask[y * w + x] == 0:
				y += 1
				continue
			var y1 := y
			while y1 < h and mask[y1 * w + x] == 1:
				y1 += 1
			var top := _outside(img, zone.position + Vector2i(x, y - 1), orig.get_pixel(x, mini(y1, h - 1)))
			var bot := _outside(img, zone.position + Vector2i(x, y1), top)
			for k in range(y, y1):
				var c := top.lerp(bot, float(k - y + 1) / float(y1 - y + 1))
				c.a = 1.0
				img.set_pixelv(zone.position + Vector2i(x, k), c)
			y = y1
	return [id, over, Vector2(zone.position), core]


## Il pixel `p` dell'immagine, o `fallback` se è fuori.
static func _outside(img: Image, p: Vector2i, fallback: Color) -> Color:
	if p.x < 0 or p.y < 0 or p.x >= img.get_width() or p.y >= img.get_height():
		return fallback
	return img.get_pixelv(p)


## Una scritta sopra la vignetta: `img` a `pos` nel murale; `core` (facoltativo) i pixel pieni, se no
## quelli opachi.
func _add_writing(id: String, img: Image, pos: Vector2, mode: String, core: PackedByteArray = PackedByteArray()) -> void:
	if img == null or img.is_empty() or id == "":
		return
	var w := img.get_width()
	var h := img.get_height()
	if core.size() != w * h:
		core = PackedByteArray()
		core.resize(w * h)
		for y in h:
			for x in w:
				core[y * w + x] = 1 if img.get_pixel(x, y).a > 0.5 else 0
	var node := Node2D.new()
	node.name = "Scritta_" + id
	var sp := Sprite2D.new()
	sp.texture = ImageTexture.create_from_image(img)
	sp.centered = false
	sp.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	var mat := ShaderMaterial.new()
	mat.shader = _shader_get()
	mat.set_shader_parameter(&"has_reveal", true)
	mat.set_shader_parameter(&"has_emis", false)
	mat.set_shader_parameter(&"size", Vector2(w, h))
	mat.set_shader_parameter(&"seed", float(hash(id) % 997))
	mat.set_shader_parameter(&"progress", 0.0)
	sp.material = mat
	node.add_child(sp)
	add_child(node)
	var wr := {"id": id, "node": node, "sprite": sp, "mat": mat, "img": img, "core": core, "pos": pos,
		"size": Vector2i(w, h), "glyphs": 1, "mode": mode, "n": 1, "k": 0, "t": 0, "on": false, "edge": 0.1,
		"drips": []}
	_writing_order(wr)
	node.draw.connect(_draw_drips.bind(wr))
	writings[id] = wr


## L'ordine della scritta: le righe dall'alto, in ogni riga le lettere da sinistra (separate da colonne
## vuote). "spray": ogni lettera a puntini, con qualche colatura; "scrivi": lettera dopo lettera, netta.
func _writing_order(wr: Dictionary) -> void:
	var w: int = wr["size"].x
	var h: int = wr["size"].y
	var core: PackedByteArray = wr["core"]
	var img: Image = wr["img"]
	var spray := str(wr["mode"]) == "spray"
	var sid := str(wr["id"])
	# Le righe: fasce di righe piene separate da almeno 2 righe vuote; le fasce basse (gli accenti)
	# vanno con quella dopo.
	var full_rows: Array[bool] = []
	for y in h:
		var any := false
		for x in w:
			if core[y * w + x] == 1:
				any = true
				break
		full_rows.append(any)
	var bands: Array = []
	var y := 0
	while y < h:
		if not full_rows[y]:
			y += 1
			continue
		var y1 := y
		var gap := 0
		while y1 < h and gap < 2:
			gap = 0 if full_rows[y1] else gap + 1
			y1 += 1
		bands.append([y, y1 - gap])
		y = y1
	var merged: Array = []
	for b: Array in bands:
		if not merged.is_empty() and _is_accent(core, w, int(merged[-1][0]), int(merged[-1][1])):
			merged[-1] = [merged[-1][0], b[1]]
		else:
			merged.append(b)
	if merged.is_empty():
		merged = [[0, h]]
	# Le lettere di ogni riga; i pixel fra una riga e l'altra vanno con la riga di sotto.
	var glyph_of := PackedInt32Array()
	glyph_of.resize(w * h)
	var total := 0
	var drips: Array = []
	for bi in merged.size():
		var r0 := int(merged[bi][0])
		var r1 := int(merged[bi][1])
		var b0 := 0 if bi == 0 else int(merged[bi - 1][1])
		var b1 := h if bi == merged.size() - 1 else r1
		var col_g := PackedInt32Array()
		col_g.resize(w)
		var g := -1
		var prev_full := false
		for x in w:
			var full := false
			for yy in range(r0, r1):
				if core[yy * w + x] == 1:
					full = true
					break
			if full and not prev_full:
				g += 1
			prev_full = full
			col_g[x] = total + maxi(g, 0)
		var n_here := maxi(g + 1, 1)
		for yy in range(b0, b1):
			for x in w:
				glyph_of[yy * w + x] = col_g[x]
		# Le colature: sotto il pixel più basso di alcune lettere.
		if spray:
			for gi in n_here:
				var gid := total + gi
				if _rand(sid, gid, 1) % 100 >= DRIP_CHANCE:
					continue
				var cols: Array[int] = []
				for x in w:
					if col_g[x] == gid:
						cols.append(x)
				if cols.is_empty():
					continue
				var cx: int = cols[_rand(sid, gid, 2) % cols.size()]
				for yy in range(r1 - 1, r0 - 1, -1):
					if core[yy * w + cx] == 1:
						var c := img.get_pixel(cx, yy)
						c.a = 1.0
						drips.append({"x": cx, "y": yy + 1, "color": c, "glyph": gid,
							"len": 2 + _rand(sid, gid, 3) % (DRIP_MAX - 1)})
						break
		total += n_here
	var order := Image.create_empty(w, h, false, Image.FORMAT_L8)
	for yy in h:
		for x in w:
			var gi := glyph_of[yy * w + x]
			var r := (float(gi) + 0.5) / total
			if spray:
				r = (float(gi) + 0.1 + 0.8 * float(_rand(sid, yy * w + x, 4) & 0xffff) / 65535.0) / total
			order.set_pixel(x, yy, Color(r, r, r))
	var mat: ShaderMaterial = wr["mat"]
	mat.set_shader_parameter(&"reveal_tex", ImageTexture.create_from_image(order))
	wr["edge"] = (1.2 / total) if spray else 0.0001
	mat.set_shader_parameter(&"edge", float(wr["edge"]))
	mat.set_shader_parameter(&"fresh", 0.18 if spray else 0.0)
	wr["glyphs"] = total
	wr["drips"] = drips


## Una fascia di accenti (bassa o stretta: l'accento di GIOVEDÌ), che va con la riga di sotto.
static func _is_accent(core: PackedByteArray, w: int, y0: int, y1: int) -> bool:
	if y1 - y0 < 4:
		return true
	var x0 := w
	var x1 := -1
	for y in range(y0, y1):
		for x in w:
			if core[y * w + x] == 1:
				x0 = mini(x0, x)
				x1 = maxi(x1, x)
	return x1 - x0 < 16


## Le colature: dopo che la loro lettera è dipinta crescono di un pixel ogni DRIP_TICKS.
func _draw_drips(wr: Dictionary) -> void:
	if not bool(wr["on"]) or str(wr["mode"]) != "spray":
		return
	var node: Node2D = wr["node"]
	var per_glyph := float(wr["n"]) / int(wr["glyphs"])
	for d: Dictionary in wr["drips"]:
		var since := float(wr["t"]) - (int(d["glyph"]) + 1) * per_glyph
		if since < 0.0:
			continue
		var ln := mini(int(d["len"]), int(since / DRIP_TICKS) + 1)
		node.draw_rect(Rect2(int(d["x"]), int(d["y"]), 1, ln), d["color"])


## Un numero a caso, ma sempre lo stesso per la stessa scritta, lo stesso indice e lo stesso uso.
static func _rand(s: String, i: int, use: int) -> int:
	return hash(s + ":" + str(i) + ":" + str(use)) & 0x7fffffff


static func _rgba(img: Image) -> Image:
	if img == null or img.is_empty():
		return null
	img = img.duplicate()
	if img.is_compressed():
		img.decompress()
	img.convert(Image.FORMAT_RGBA8)
	return img


static func _rect(v: Variant) -> Rect2i:
	if v is Array and (v as Array).size() >= 4:
		return Rect2i(int(v[0]), int(v[1]), int(v[2]), int(v[3]))
	return Rect2i()


static func _shader_get() -> Shader:
	if _shader == null:
		_shader = Shader.new()
		_shader.code = SHADER
	return _shader


static func _vec(v: Variant, fallback: Vector2) -> Vector2:
	if v is Array and (v as Array).size() >= 2:
		return Vector2(float(v[0]), float(v[1]))
	return fallback


static func _file_exists(p: String) -> bool:
	return ResourceLoader.exists(p) or FileAccess.file_exists(p)


## Le texture importate dal progetto, o un PNG letto al volo (il murale finto del test, in user://).
static func _texture(p: String) -> Texture2D:
	if p.ends_with("/") or p == "":
		return null
	if ResourceLoader.exists(p):
		return load(p) as Texture2D
	if FileAccess.file_exists(p):
		var img := Image.load_from_file(p)
		if img != null and not img.is_empty():
			return ImageTexture.create_from_image(img)
	return null


static func _ease(k: float) -> float:
	k = clampf(k, 0.0, 1.0)
	return k * k * (3.0 - 2.0 * k)


static func _near_color(a: Color, b: Color) -> bool:
	return absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b) < 0.06
